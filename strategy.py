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
        self.min_hold_hours = 8        # 최소 8시간 보유 (펀딩비 수취 목적)
        self.slippage_rate = 0.005     # 0.5% 슬리피지 가드
        self.entry_apy_threshold = 10.0 # 연환산 APY 10% 이상 시 진입
        self.exit_apy_threshold = 3.0  # APY 3% 미만 시 청산 검토
        self.rebalance_gap = 10.0      # 타 종목 APY가 10% 이상 높을 때 리밸런싱

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
            
            # 청산 조건 확인
            entry_time = datetime.fromisoformat(pos_info['entry_time'])
            hold_time = current_time - entry_time
            
            # 조건 A: 최소 보유 시간 경과 + APY 하락
            if hold_time > timedelta(hours=self.min_hold_hours):
                if p_data and (p_data['funding'] * 24 * 365 * 100) < self.exit_apy_threshold:
                    logging.info(f"Exit Condition: Low APY for {symbol}")
                    to_exit.append(symbol)
                    
        # 실제 청산 실행
        for symbol in to_exit:
            if self.is_real_trading:
                # [실전] 청산 로직 (선물 Buy + 현물 Sell)
                # ... (구현 생략 - 필요시 추가)
                pass
            
            self.total_realized_profit += self.positions[symbol].get('profit', 0.0)
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
                    
                    # --- 실전 진입 로직 (Testnet/Mainnet) ---
                    if self.is_real_trading and self.api:
                        try:
                            # [사전 검증 1] 현물 심볼 존재 여부 확인
                            spot_name = spot_data.get(t['symbol'], {}).get('spot_name')
                            if not spot_name:
                                logging.error(f"[PRE-CHECK FAIL] No spot market for {t['symbol']} — skipping")
                                continue
                            
                            # [사전 검증 2] 실제 잔고 조회
                            actual_balance = await self.api.get_balance()
                            if actual_balance < 10:
                                logging.error(f"Insufficient balance (${actual_balance:.2f}) for entry.")
                                continue
                            
                            # 가용 자산의 95%만 사용하여 여유분 확보
                            usable_balance = actual_balance * 0.95
                            size_usd = min(usable_balance / (self.max_positions - len(self.positions)), usable_balance)
                            
                            # $10 미만 주문 방지
                            if size_usd < 10.5:
                                if actual_balance >= 10.5: size_usd = 10.5
                                else: continue
                                
                            perp_amount = size_usd / t['perp_px']
                            
                            # 1. 선물 숏 진입 (Sell)
                            perp_sz_dec = t.get('perp_sz_dec', 0)
                            spot_sz_dec = t.get('spot_sz_dec', 0)

                            logging.info(f"Placing Sell order for {t['symbol']}: {perp_amount} @ {virtual_perp_sell_px} (szDec: {perp_sz_dec})")
                            r1 = await self.api.place_order(t['symbol'], perp_amount, virtual_perp_sell_px, False, is_perp=True, sz_decimals=perp_sz_dec)
                            
                            # 2. 현물 롱 진입 (Buy)
                            logging.info(f"Placing Buy order for {spot_name}: {perp_amount} @ {virtual_spot_buy_px} (szDec: {spot_sz_dec})")
                            r2 = await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px, True, is_perp=False, sz_decimals=spot_sz_dec)
                            
                            if not r1 or not r2:
                                logging.error(f"Real entry failed for {t['symbol']}. Rolling back.")
                                # 롤백: 한쪽만 체결된 경우 반대 매매
                                if r1: await self.api.place_order(t['symbol'], perp_amount, virtual_perp_sell_px * 1.1, True, is_perp=True)
                                if r2: await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px * 0.9, False, is_perp=False)
                                await self.notifier.send_message(f"⚠️ *[ENTRY FAILED]*\n• {t['symbol']} 진입 실패 (롤백 수행)")
                                continue
                                
                            logging.info(f"[REAL ENTRY] {t['symbol']} successful with size ${size_usd:.2f}")
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
        """잔고 및 수익률 요약 반환"""
        if self.is_real_trading and self.api:
            try:
                user_state = await self.api.get_user_state()
                perp_value = float(user_state.get('marginSummary', {}).get('accountValue', 0.0))
                
                spot_value = 0.0
                spot_state = self.api.info.spot_user_state(self.api.wallet_address)
                for b in spot_state.get('balances', []):
                    if b.get('coin') == 'USDC':
                        spot_value = float(b.get('total', 0.0))
                        break
                        
                account_value = perp_value + spot_value
                return (
                    f"💰 *[HLQuant Live Portfolio]*\n\n"
                    f"• *Total Value*: ${account_value:,.2f}\n"
                    f"  - Spot USDC: ${spot_value:,.2f}\n"
                    f"  - Perp Equity: ${perp_value:,.2f}\n\n"
                    f"🟢 Live API Connected"
                )
            except: pass
        return "💰 *Paper Balance Mode*"

    def get_positions_summary(self):
        """보유 포지션 요약"""
        if not self.positions: return "📭 No active positions."
        text = "📍 *[Active Positions]*\n\n"
        for sym, d in self.positions.items():
            text += f"• *{sym}*: APY {d['entry_apy']:.2f}% | {d['entry_time'][:16]}\n"
        return text