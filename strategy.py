import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from notifier import TelegramNotifier

class DeltaNeutralStrategy:
    """
    델타 중립 펀딩비 체리피킹 전략 클래스
    """
    def __init__(self, api=None, notifier=None, state_file="paper_balance.json", is_real_trading=False, is_testnet=False):
        self.state_file = state_file
        self.api = api
        self.is_real_trading = is_real_trading
        self.is_testnet = is_testnet
        self.initial_capital = 1000.0  # 가상 원금 $1,000 (Paper Trading용)
        self.max_positions = 5  # $50 / 5슬롯 = 포지션당 ~$9.5 (메인넷 최소 주문금액 $10 고려하여 조정 필요)
        
        state = self._load_state()
        self.positions = state.get("positions", {})
        self.total_realized_profit = state.get("total_realized_profit", 0.0)
        self.notifier = notifier or TelegramNotifier()
        
        # 전략 파라미터
        self.min_hold_hours = 4        # 최소 4시간 보유 (로테이션 효율화)
        self.slippage_rate = 0.005     # 0.5% 슬리피지 가드
        self.entry_apy_threshold = 7.5 # 연환산 APY 7.5% 이상 시 진입
        self.exit_apy_threshold = 2.0  # APY 2% 미만 시 청산 검토
        self.rebalance_gap = 10.0      # 타 종목 APY가 10% 이상 높을 때 리밸런싱
        
        # 봇 가동 상태 제어
        self.config_file = "bot_config.json"
        self.is_active = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f).get("is_active", True)
            except: return True
        return True

    def _save_config(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump({"is_active": self.is_active}, f)
        except Exception as e:
            logging.error(f"Config Save Error: {e}")

    def toggle_bot(self, active: bool):
        self.is_active = active
        self._save_config()
        logging.info(f"Bot Active Status Changed: {active}")

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except:
                return {"positions": {}, "total_realized_profit": 0.0}
        return {"positions": {}, "total_realized_profit": 0.0}

    def _save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    "positions": self.positions,
                    "total_realized_profit": self.total_realized_profit
                }, f, indent=4)
        except Exception as e:
            logging.error(f"State Save Error: {e}")

    async def sync_with_exchange(self):
        """실제 거래소의 포지션을 확인하여 내부 상태와 동기화"""
        if not self.is_real_trading or not self.api:
            return

        try:
            user_state = await self.api.get_user_state()
            asset_positions = user_state.get('assetPositions', [])
            
            # 거래소에 있는 실제 코인 리스트
            exchange_symbols = []
            for pos in asset_positions:
                p = pos.get('position', {})
                symbol = p.get('coin')
                size = float(p.get('szi', 0))
                if abs(size) > 0:
                    exchange_symbols.append(symbol)
            
            # 내부 장부(positions)에 있는데 거래소에 없는 경우 -> 청산된 것으로 간주
            to_delete = []
            for sym in self.positions:
                if sym not in exchange_symbols:
                    logging.info(f"Sync: {sym} not found on exchange. Removing from local state.")
                    to_delete.append(sym)
            
            for sym in to_delete:
                del self.positions[sym]

            # 거래소에 있는데 내부 장부에 없는 경우 -> 새로 추가 (메타데이터는 현재 시간으로)
            for sym in exchange_symbols:
                if sym not in self.positions:
                    logging.info(f"Sync: {sym} found on exchange but not in local state. Adding.")
                    self.positions[sym] = {
                        "entry_time": datetime.now().isoformat(),
                        "last_update": datetime.now().isoformat(),
                        "spot_px": 0.0, "perp_px": 0.0, "entry_apy": 0.0, "profit": 0.0
                    }
            
            if to_delete or exchange_symbols:
                self._save_state()
                
        except Exception as e:
            logging.error(f"Sync Error: {e}")

    async def execute_logic(self, perp_data, spot_data):
        """메인 전략 루프: 청산 및 진입 로직 수행"""
        if not self.is_active:
            return # 봇이 정지 상태면 로직 스킵

        current_time = datetime.now()
        
        # 0. 동적 max_positions 설정 (잔고 $50 기준 $10씩 5개)
        if self.is_real_trading:
            balance = await self.api.get_balance()
            # 델타 중립은 현물/선물에 자금이 나뉘므로, 가용 자산의 절반을 기준으로 슬롯 계산
            # 최소 주문 $10를 고려하여 $11당 1슬롯 배정
            dynamic_max = max(1, int((balance / 2) // 11))
            self.max_positions = min(dynamic_max, 10)
            
        # 1. 포지션 관리 (청산 및 리밸런싱)
        to_exit = []
        for symbol, pos_info in self.positions.items():
            # 펀딩비 수익 시뮬레이션 (Virtual Paper용)
            p_data = perp_data.get(symbol)
            if p_data:
                # 1분(루프주기) 동안의 펀딩비 수익 가산
                funding_profit = (p_data['funding'] / 60) * 100 # 단순화된 계산
                pos_info['profit'] = pos_info.get('profit', 0.0) + funding_profit
            
            # 펀딩비 수익률(APY) 계산
            apy = (p_data['funding'] * 24 * 365 * 100) if p_data else 0
            
            # 청산 조건 확인
            entry_time = datetime.fromisoformat(pos_info['entry_time'])
            hold_time = current_time - entry_time
            
            should_exit = False
            if p_data:
                # 조건 A: 최소 보유 시간 경과 + APY 하락 (기존 전략)
                if hold_time > timedelta(hours=self.min_hold_hours) and apy < self.exit_apy_threshold:
                    logging.info(f"Exit Condition (Target): Low APY for {symbol} ({apy:.2f}%)")
                    should_exit = True
                
                # 조건 B: APY가 마이너스인 경우 (긴급 탈출)
                elif apy < 0:
                    logging.info(f"Exit Condition (Emergency): Negative APY for {symbol} ({apy:.2f}%)")
                    should_exit = True
            
            if should_exit:
                to_exit.append(symbol)
                    
        # 실제 청산 실행
        for symbol in to_exit:
            if self.is_real_trading and self.api:
                try:
                    # 1. 수량 확인 (거래소에서 직접 조회)
                    user_state = await self.api.get_user_state()
                    amount = 0
                    for p in user_state.get('assetPositions', []):
                        if p['position']['coin'] == symbol:
                            amount = abs(float(p['position']['szi']))
                            break
                    
                    if amount > 0:
                        # 2. 가격 데이터 가져오기
                        p_data = perp_data.get(symbol, {})
                        s_data = spot_data.get(symbol, {})
                        
                        # STEP 1: 선물(Perp) 먼저 매수 (숏 청산) - 펀딩비 차단
                        logging.info(f"EXIT STEP 1: Buying Perp {symbol} | {amount}")
                        # 공격적인 가격으로 IoC 주문 (시장가 효과)
                        await self.api.place_order(symbol, amount, p_data['midPrice'] * 1.02, True, is_perp=True, sz_decimals=p_data.get('szDecimals', 0))
                        
                        # STEP 2: 현물(Spot) 매도
                        spot_name = s_data.get('spot_name')
                        if spot_name:
                            logging.info(f"EXIT STEP 2: Selling Spot {spot_name} | {amount}")
                            await self.api.place_order(spot_name, amount, s_data['midPrice'] * 0.98, False, is_perp=False, sz_decimals=s_data.get('szDecimals', 0))
                        
                        await self.notifier.send_message(f"✅ *[REAL EXIT COMPLETED]*\n• {symbol} 청산 완료 (수량: {amount})")
                    else:
                        logging.warning(f"Exit triggered but no position found on exchange for {symbol}")
                except Exception as e:
                    logging.error(f"Real exit error for {symbol}: {e}")
                    continue
            
            self.total_realized_profit += self.positions[symbol].get('profit', 0.0)
            if not self.is_real_trading:
                await self.notifier.send_exit_notification(symbol, "Low APY / Target Reached")
            
            del self.positions[symbol]
        
        if to_exit: self._save_state()

        # 2. 신규 진입 로직
        if len(self.positions) < self.max_positions:
            targets = self.get_targets(perp_data, spot_data)
            
            for t in targets:
                if len(self.positions) >= self.max_positions:
                    break
                
                if t['symbol'] not in self.positions:
                    # 가상 가격 (슬리피지 포함)
                    virtual_spot_buy_px = t['spot_px'] * (1 + self.slippage_rate)
                    virtual_perp_sell_px = t['perp_px'] * (1 - self.slippage_rate)
                    
                    # --- 실전 진입 로직 (Safety First: Spot -> Perp) ---
                    if self.is_real_trading and self.api:
                        try:
                            # 1. 사전 검증
                            spot_name = spot_data.get(t['symbol'], {}).get('spot_name')
                            if not spot_name:
                                logging.error(f"[PRE-CHECK] No spot mapping for {t['symbol']}")
                                continue
                            
                            actual_balance = await self.api.get_balance()
                            if actual_balance < 10:
                                logging.error(f"Insufficient balance (${actual_balance:.2f})")
                                continue
                            
                            usable_balance = actual_balance * 0.95
                            size_usd = min(usable_balance / (self.max_positions - len(self.positions)), usable_balance)
                            if size_usd < 10.5:
                                if actual_balance >= 10.5: size_usd = 10.5
                                else: continue
                                
                            perp_amount = size_usd / t['perp_px']
                            perp_sz_dec = t.get('perp_sz_dec', 0)
                            spot_sz_dec = t.get('spot_sz_dec', 0)

                            # STEP 1: 현물(Spot) 먼저 매수
                            logging.info(f"STEP 1: Buying Spot {spot_name} | {perp_amount} @ {virtual_spot_buy_px}")
                            r_spot = await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px, True, is_perp=False, sz_decimals=spot_sz_dec)
                            
                            if not r_spot:
                                logging.error(f"STEP 1 FAILED: Spot buy failed for {t['symbol']}. Aborting entry.")
                                continue

                            # STEP 2: 현물 체결 확인 후 선물(Perp) 숏 진입
                            logging.info(f"STEP 2: Selling Perp {t['symbol']} | {perp_amount} @ {virtual_perp_sell_px}")
                            r_perp = await self.api.place_order(t['symbol'], perp_amount, virtual_perp_sell_px, False, is_perp=True, sz_decimals=perp_sz_dec)
                            
                            if not r_perp:
                                logging.error(f"STEP 2 FAILED: Perp sell failed for {t['symbol']}. Rolling back Spot.")
                                # 현물 롤백 (매도)
                                await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px * 0.9, False, is_perp=False, sz_decimals=spot_sz_dec)
                                await self.notifier.send_message(f"⚠️ *[ENTRY FAILED]*\n• {t['symbol']} 선물 진입 실패 (현물 롤백 완료)")
                                continue
                                
                            logging.info(f"[REAL ENTRY] {t['symbol']} successful!")
                        except Exception as e:
                            logging.error(f"Real entry error for {t['symbol']}: {e}")
                            continue
                    # ------------------------------------

                    self.positions[t['symbol']] = {
                        'entry_time': current_time.isoformat(),
                        'last_update': current_time.isoformat(),
                        'spot_px': virtual_spot_buy_px,
                        'perp_px': virtual_perp_sell_px,
                        'entry_apy': t['apy'],
                        'size': perp_amount if self.is_real_trading else 0,
                        'profit': 0.0
                    }
                    logging.info(f"[ENTRY] {t['symbol']} | APY: {t['apy']:.2f}%")
                    await self.notifier.send_entry_notification(t['symbol'], t['apy'], virtual_spot_buy_px, virtual_perp_sell_px)

        self._save_state()

    def get_targets(self, perp_data, spot_data):
        """진입 가능한 타겟 종목 스캔"""
        candidates = []
        for symbol, p_data in perp_data.items():
            s_data = spot_data.get(symbol)
            if not s_data: continue
            
            # APY 계산 (1시간 펀딩비 * 24 * 365)
            apy = p_data['funding'] * 24 * 365 * 100
            
            # 베이시스 프리미엄 계산 (선물/현물 가격차)
            premium = (p_data['midPrice'] - s_data['midPrice']) / s_data['midPrice'] * 100
            
            # 진입 조건: APY 10% 이상 & 프리미엄이 너무 과하지 않음
            if apy >= self.entry_apy_threshold and premium >= -0.1:
                # [추가] 수량 정밀도 체크 - 현재 잔고로 최소 1개는 살 수 있는지 확인
                if self.is_real_trading:
                    actual_balance = 50.0 # 기본값 (나중에 실제 fetch)
                    usable = actual_balance * 0.95
                    size_usd = (usable / 2) / 11 # 대략적인 사이즈
                    perp_amount = size_usd / p_data['midPrice']
                    if round(perp_amount, p_data['szDecimals']) <= 0:
                        continue # 너무 소액이라 주문 불가

                candidates.append({
                    'symbol': symbol,
                    'apy': apy,
                    'spot_px': s_data['midPrice'],
                    'perp_px': p_data['midPrice'],
                    'perp_sz_dec': p_data['szDecimals'],
                    'spot_sz_dec': s_data['szDecimals']
                })
        
        # APY 높은 순 정렬
        candidates.sort(key=lambda x: x['apy'], reverse=True)
        return candidates[:self.max_positions]

    def get_status_summary(self):
        """봇 가동 상태 요약 반환"""
        if self.is_real_trading and not self.is_testnet:
            mode_text = "🔴 Mainnet Real Trading"
        elif self.is_real_trading and self.is_testnet:
            mode_text = "🟡 Testnet Real Trading"
        else:
            mode_text = "📄 Paper Trading"
        
        return (
            f"📊 *[HLQuant Bot Status]*\n\n"
            f"• *Mode*: {mode_text}\n"
            f"• *Target Count*: {self.max_positions} Pairs\n"
            f"• *Active Positions*: {len(self.positions)}/{self.max_positions}\n"
            f"• *Strategy*: Delta-Neutral Arbitrage\n"
            f"• *Last Scan*: {datetime.now().strftime('%H:%M:%S')}"
        )

    async def get_balance_summary(self):
        """잔고 및 수익률 상세 요약 반환 (UI 스타일)"""
        if self.is_real_trading and self.api:
            try:
                # 1. 선물(Perp) 상태 가져오기
                user_state = await self.api.get_user_state()
                margin = user_state.get('marginSummary', {})
                perp_value = float(margin.get('accountValue', 0.0))
                unrealized_pnl = float(margin.get('totalUnrealizedPnl', 0.0))
                margin_used = float(margin.get('totalMarginUsed', 0.0))
                
                # 2. 현물(Spot) 상태 가져오기
                spot_state = self.api.info.spot_user_state(self.api.wallet_address)
                spot_value = 0.0
                spot_assets = []
                
                for b in spot_state.get('balances', []):
                    total = float(b.get('total', 0.0))
                    if total > 0:
                        coin = b.get('coin')
                        if coin == 'USDC':
                            spot_value += total
                        else:
                            # 코인 가치 계산 (현재가 필요)
                            # 간단하게 하기 위해 현재 스캔된 spot_data가 있다면 연동 가능
                            spot_assets.append(f"    - {coin}: {total:.4f}")
                
                total_portfolio = perp_value + spot_value
                
                # 3. 메시지 구성
                status_icon = "🟢" if unrealized_pnl >= 0 else "🔴"
                msg = (
                    f"💰 *[HLQuant Unified Portfolio]*\n\n"
                    f"• *Total Value*: ${total_portfolio:,.2f}\n"
                    f"• *Unrealized PNL*: {status_icon} ${unrealized_pnl:,.2f}\n\n"
                    f"📊 *Perpetual (Futures)*\n"
                    f"  - Equity: ${perp_value:,.2f}\n"
                    f"  - Margin Used: ${margin_used:,.2f}\n\n"
                    f"💎 *Spot (Holdings)*\n"
                    f"  - Cash: ${spot_value:,.2f} USDC\n"
                )
                if spot_assets:
                    msg += "\n".join(spot_assets) + "\n"
                
                msg += f"\n✨ *Account Status*: Live Connected"
                return msg
            except Exception as e:
                logging.error(f"Balance Summary Error: {e}")
                return "⚠️ 잔고 데이터를 가져오는 중 오류가 발생했습니다."
        
        return "💰 *Paper Balance Mode*"

    def get_positions_summary(self):
        """보유 포지션 요약"""
        if not self.positions: return "📭 No active positions."
        text = "📍 *[Active Positions]*\n\n"
        for sym, d in self.positions.items():
            text += f"• *{sym}*: APY {d['entry_apy']:.2f}% | {d['entry_time'][:16]}\n"
        return text