import logging
import json
import os
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
        self.max_positions = 5  # $50 / 5슬롯 = 포지션당 ~$9.5
        state = self._load_state()
        self.positions = state.get("positions", {})
        self.total_realized_profit = state.get("total_realized_profit", 0.0)
        self.notifier = notifier or TelegramNotifier()
        
        self.min_hold_hours = 8
        self.slippage_rate = 0.005  # 0.5% (mainnet 유동성 개선으로 testnet보다 낙춤)
        self.entry_apy_threshold = 10.0  # mainnet에서 APY 10% 이상만 진입
        self.exit_apy_threshold = 3.0
        self.rebalance_gap = 10.0

    async def sync_with_exchange(self):
        """실제 거래소의 포지션을 확인하여 내부 상태와 동기화"""
        try:
            logging.info("🔄 거래소 포지션과 내부 상태 동기화 시도 중...")
            # get_user_state가 내부적으로 정보를 가져옴
            user_state = await self.api.get_user_state()
            asset_positions = user_state.get('assetPositions', [])
            
            new_positions = {}
            for pos in asset_positions:
                p = pos.get('position', {})
                symbol = p.get('coin')
                size = float(p.get('szi', 0))
                if abs(size) > 0:
                    # 기존에 관리하던 포지션이면 유지, 없으면 신규 등록
                    if symbol in self.positions:
                        new_positions[symbol] = self.positions[symbol]
                    else:
                        new_positions[symbol] = {
                            "entry_time": datetime.now().isoformat(),
                            "last_update": datetime.now().isoformat(),
                            "spot_px": float(p.get('entryPx', 0)),
                            "perp_px": float(p.get('entryPx', 0)),
                            "entry_apy": 10.95, # 기본값
                            "profit": 0.0
                        }
            
            self.positions = new_positions
            self._save_state()
            logging.info(f"✅ {len(new_positions)}개의 포지션을 성공적으로 동기화했습니다.")
        except Exception as e:
            logging.error(f"❌ 동기화 중 오류 발생: {e}")

    def get_status_summary(self):
        """현재 시장 상태 및 상위 APY 요약 (메모리상의 최근 데이터 기준)"""
        # 이 메서드는 perp_data와 spot_data가 로컬 변수로만 존재하므로, 
        # 마지막으로 확인된 상위 리스트를 저장해두거나 직접 정보를 생성해야 함.
        # 여기서는 현재 포지션 개수와 간단한 안내를 반환하도록 설계.
        pos_count = len(self.positions)
        text = (
            "📊 *HLQuant 시장 요약*\n\n"
            f"• 가동 모드: Paper Trading\n"
            f"• 보유 포지션: {pos_count}/3\n"
            "• 현재 시장의 상세 상위 리스트는 bot.log를 참조하거나 다음 스캔 결과를 기다려주세요."
        )
        return text

    def get_positions_summary(self):
        """보유 중인 포지션의 상세 내역 요약"""
        if not self.positions:
            return "📭 현재 보유 중인 가상 포지션이 없습니다."
        
        text = "📝 *현재 가상 포지션 내역*\n\n"
        for sym, pos in self.positions.items():
            entry_time = datetime.fromisoformat(pos['entry_time']).strftime('%m/%d %H:%M')
            text += (
                f"• *{sym}*\n"
                f"  - 진입: {entry_time}\n"
                f"  - 진입APY: {pos['entry_apy']:.2f}%\n"
                f"  - Spot진입가: {pos['spot_px']:.4f}\n"
                f"  - Perp진입가: {pos['perp_px']:.4f}\n\n"
            )
        return text

    def get_balance_summary(self):
        """가상 장부의 수익률 현황 요약"""
        if not self.positions:
            return "💰 현재 운용 중인 자산이 없습니다."
        
        # 실제 현재가를 반영하려면 perp_data가 필요하지만, 
        # 여기서는 진입가 정보와 가동 시간 위주로 보고.
        text = "💰 *가상 장부 수익률 보고*\n\n"
        for sym, pos in self.positions.items():
            text += f"• {sym}: 진입 APY {pos['entry_apy']:.2f}%\n"
        
        text += "\n*참고*: 현재 수익률은 펀딩비 적립 주기에 따라 계산되며, 상세 미실현 손익은 다음 버전에서 지원될 예정입니다."
        return text

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    # 하위 호환성 유지
                    if "positions" not in data:
                        return {"positions": data, "total_realized_profit": 0.0}
                    return data
            except:
                return {"positions": {}, "total_realized_profit": 0.0}
        return {"positions": {}, "total_realized_profit": 0.0}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump({
                "positions": self.positions,
                "total_realized_profit": self.total_realized_profit
            }, f, indent=4)

    def calculate_apy(self, funding_rate):
        """
        하이퍼리퀴드 1시간 펀딩비를 연환산(APY)으로 변환
        """
        # funding_rate가 0.0001 이면 0.01%
        return funding_rate * 24 * 365 * 100

    def get_targets(self, perp_data, spot_data):
        """
        진입 후보 종목 스캔 및 필터링
        현물 시장이 존재하는 종목만 대상으로 합니다.
        """
        candidates = []
        for symbol, p_data in perp_data.items():
            # 1. 현물 시장 존재 여부 확인
            s_data = spot_data.get(symbol)
            if not s_data:
                continue
                
            # 2. APY 계산
            apy = self.calculate_apy(p_data['funding'])
            
            # 3. 프리미엄(Basis) 계산
            spot_px = s_data['midPrice']
            if spot_px == 0: continue
            
            perp_px = p_data['midPrice']
            premium = abs(perp_px - spot_px) / spot_px * 100
            
            # 필터링 조건: APY 15% 이상, Premium 0.1% 이내
            if apy >= self.entry_apy_threshold and premium <= 0.1:
                candidates.append({
                    'symbol': symbol,
                    'apy': apy,
                    'premium': premium,
                    'spot_px': spot_px,
                    'perp_px': perp_px
                })
        
        # 디버깅: 현재 시장의 상위 5개 APY 및 프리미엄 출력 (현물 있는 것만)
        all_candidates = []
        for symbol, p_data in perp_data.items():
            apy = self.calculate_apy(p_data['funding'])
            s_data = spot_data.get(symbol)
            if s_data:
                spot_px = s_data['midPrice']
                premium = abs(p_data['midPrice'] - spot_px) / spot_px * 100 if spot_px != 0 else 999
            else:
                premium = 999 # 현물 없음
            all_candidates.append((symbol, apy, premium))
        
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        top_list = ", ".join([f"{s}(APY:{a:.1f}%, Prem:{'N/A' if p==999 else f'{p:.2f}%'})" for s, a, p in all_candidates[:5]])
        logging.info(f"Market Top: {top_list}")

        # APY 기준 내림차순 정렬 후 상위 max_positions개 선정
        candidates.sort(key=lambda x: x['apy'], reverse=True)
        return candidates[:self.max_positions]

    async def execute_logic(self, perp_data, spot_data):
        """
        전략 실행 메인 루프 (진입, 청산, 리밸런싱 판단 및 수익 정산)
        """
        current_time = datetime.now()
        
        # 실제 거래 시 가용 잔고에 따라 최대 포지션 수 동적 조절 ($10 제한 대비)
        if self.is_real_trading and self.api:
            actual_balance = await self.api.get_balance()
            # 최소 $11 할당 기준 (슬리피지 고려)
            dynamic_max = max(1, int(actual_balance // 11))
            if dynamic_max < self.max_positions:
                logging.info(f"Adjusting max_positions from {self.max_positions} to {dynamic_max} due to balance (${actual_balance:.2f})")
                self.max_positions = dynamic_max

        # 1. 기존 포지션 수익 업데이트 및 청산 판단
        symbols_to_exit = []
        for symbol, pos in list(self.positions.items()):
            if symbol not in perp_data: continue
            
            p_data = perp_data[symbol]
            curr_funding = p_data['funding']
            curr_apy = self.calculate_apy(curr_funding)
            
            # --- 수익 정산 로직 ---
            # 마지막 업데이트 이후 경과 시간 계산
            last_update = datetime.fromisoformat(pos.get('last_update', pos['entry_time']))
            elapsed_seconds = (current_time - last_update).total_seconds()
            
            # 펀딩비 수익 누적
            size_per_pos = (actual_balance / self.max_positions) if (self.is_real_trading and 'actual_balance' in locals()) else (self.initial_capital / self.max_positions)
            funding_profit = size_per_pos * curr_funding * (elapsed_seconds / 3600)
            pos['profit'] = pos.get('profit', 0.0) + funding_profit
            pos['last_update'] = current_time.isoformat()
            # --------------------

            entry_time = datetime.fromisoformat(pos['entry_time'])
            hold_duration = (current_time - entry_time).total_seconds() / 3600
            
            # 청산 조건 판단
            exit_reason = None
            if curr_apy <= self.exit_apy_threshold:
                exit_reason = f"Low APY ({curr_apy:.2f}%)"
            
            if not exit_reason and hold_duration >= self.min_hold_hours:
                targets = self.get_targets(perp_data, spot_data)
                if targets and targets[0]['apy'] > curr_apy + self.rebalance_gap:
                    exit_reason = f"Rebalancing (Better opportunity: {targets[0]['symbol']} @ {targets[0]['apy']:.2f}%)"
            
            if exit_reason:
                # 청산 시 미실현 손익(가격차이) 정산
                curr_spot_px = spot_data.get(symbol, {}).get('midPrice', p_data['indexPrice'])
                curr_perp_px = p_data['midPrice']
                
                spot_pnl_pct = (curr_spot_px - pos['spot_px']) / pos['spot_px']
                perp_pnl_pct = (pos['perp_px'] - curr_perp_px) / pos['perp_px']
                price_diff_profit = size_per_pos * (spot_pnl_pct + perp_pnl_pct)
                
                final_pos_profit = pos['profit'] + price_diff_profit
                
                # --- 실전 청산 로직 ---
                if self.is_real_trading and self.api:
                    try:
                        # 포지션 크기 재계산 (현재가 기준)
                        size_amount = size_per_pos / curr_perp_px
                        
                        r1 = await self.api.place_order(symbol, size_amount, curr_perp_px * 1.01, True, is_perp=True)
                        
                        spot_name = spot_data.get(symbol, {}).get('spot_name')
                        if not spot_name:
                            logging.error(f"Cannot find spot name for exit {symbol}")
                            continue
                            
                        r2 = await self.api.place_order(spot_name, size_amount, curr_spot_px * 0.99, False, is_perp=False)
                        
                        if not r1 or not r2:
                            logging.error(f"Real exit failed for {symbol}. Keeping position state.")
                            continue
                            
                        logging.info(f"[REAL EXIT] {symbol} execution successful.")
                    except Exception as e:
                        logging.error(f"Real exit failed for {symbol}: {e}")
                        continue
                # --------------------

                self.total_realized_profit += final_pos_profit
                logging.info(f"[VIRTUAL EXIT] {symbol} | Profit: ${final_pos_profit:.2f} | Reason: {exit_reason}")
                await self.notifier.send_exit_notification(symbol, f"{exit_reason} (Final Profit: ${final_pos_profit:.2f})")
                symbols_to_exit.append(symbol)

        # 포지션 제거
        for symbol in symbols_to_exit:
            del self.positions[symbol]
        
        # 2. 신규 진입 판단
        if len(self.positions) < self.max_positions:
            targets = self.get_targets(perp_data, spot_data)
            for t in targets:
                if len(self.positions) >= self.max_positions: break
                if t['symbol'] not in self.positions:
                    # 슬리피지 반영
                    virtual_spot_buy_px = t['spot_px'] * (1 + self.slippage_rate)
                    virtual_perp_sell_px = t['perp_px'] * (1 - self.slippage_rate)
                    
                    # --- 실전 진입 로직 ---
                    if self.is_real_trading and self.api:
                        try:
                            # [사전 검증 1] 현물 심볼 존재 여부
                            spot_name = spot_data.get(t['symbol'], {}).get('spot_name')
                            if not spot_name:
                                logging.error(f"[PRE-CHECK FAIL] No spot market for {t['symbol']} on this network")
                                continue
                            
                            actual_balance = await self.api.get_balance()
                            usable_balance = actual_balance * 0.95
                            size_usd = usable_balance / self.max_positions
                            
                            # [사전 검증 2] 최소 주문 금액($10) 체크
                            if size_usd < 10.1:
                                logging.warning(f"Skipping {t['symbol']} - Size ${size_usd:.2f} too small for $10 limit.")
                                continue
                                
                            perp_amount = size_usd / t['perp_px']
                            
                            # [사전 검증 3] 수량 정밀도 체크 (제로 사이즈 방지)
                            if perp_amount <= 0:
                                logging.warning(f"Skipping {t['symbol']} - Calculated size is zero.")
                                continue

                            # 1. 선물 숏 진입
                            r1 = await self.api.place_order(t['symbol'], perp_amount, virtual_perp_sell_px, False, is_perp=True)
                            
                            # 2. 현물 롱 진입
                            r2 = await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px, True, is_perp=False)
                            
                            if not r1 or not r2:
                                logging.error(f"Real entry failed for {t['symbol']}. Rolling back.")
                                if r1: await self.api.place_order(t['symbol'], perp_amount, virtual_perp_sell_px * 1.05, True, is_perp=True)
                                if r2: await self.api.place_order(spot_name, perp_amount, virtual_spot_buy_px * 0.95, False, is_perp=False)
                                await self.notifier.send_message(f"⚠️ *[ENTRY FAILED]*\n• {t['symbol']} 진입 실패")
                                continue
                                
                            logging.info(f"[REAL ENTRY] {t['symbol']} successful with size ${size_usd:.2f}")
                        except Exception as e:
                            logging.error(f"Real entry failed for {t['symbol']}: {e}")
                            continue
                    # --------------------

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

        self._save_state()

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
        """수익률 요약 반환 (현재 가상 매매 기준 또는 실전 잔고)"""
        if self.is_real_trading and self.api:
            try:
                # 1. Perp 계정 가치
                user_state = await self.api.get_user_state()
                margin_summary = user_state.get('marginSummary', {})
                perp_value = float(margin_summary.get('accountValue', 0.0))
                
                # 2. Spot 계정 잔고 합산
                spot_value = 0.0
                spot_state = self.api.info.spot_user_state(self.api.wallet_address)
                for balance in spot_state.get('balances', []):
                    # 간략화를 위해 USDC 현금 잔고만 합산 (실제 코인 가치는 생략하거나 나중에 고도화)
                    if balance.get('coin') == 'USDC':
                        spot_value += float(balance.get('total', 0.0))
                        
                account_value = perp_value + spot_value
                
                text = (
                    f"💰 *[HLQuant Live Portfolio Report]*\n\n"
                    f"• *Real Portfolio Value*: ${account_value:,.2f}\n"
                    f"  - Spot USDC: ${spot_value:,.2f}\n"
                    f"  - Perp Equity: ${perp_value:,.2f}\n\n"
                    f"📝 *Virtual Paper Ledger Status*\n"
                    f"• *Paper Initial*: ${self.initial_capital:,.2f}\n"
                    f"• *Paper Realized PnL*: ${self.total_realized_profit:+,.2f}\n\n"
                    f"• *Status*: 🟢 Live API Connected"
                )
                return text
            except Exception as e:
                logging.error(f"Error getting live portfolio value: {e}")
                pass
                
        unrealized_profit = sum(p.get('profit', 0.0) for p in self.positions.values())
        total_equity = self.initial_capital + self.total_realized_profit + unrealized_profit
        total_pnl = self.total_realized_profit + unrealized_profit
        roi = (total_pnl / self.initial_capital) * 100

        status_emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        text = (
            f"💰 *[HLQuant Virtual Portfolio Report]*\n\n"
            f"• *Initial Capital*: ${self.initial_capital:,.2f}\n"
            f"• *Total Equity*: ${total_equity:,.2f}\n"
            f"• *Total PnL*: ${total_pnl:+,.2f}\n"
            f"• *ROI*: {roi:+.3f}%\n\n"
            f"📈 *Details*\n"
            f"• Realized: ${self.total_realized_profit:+,.2f}\n"
            f"• Unrealized (Accruing): ${unrealized_profit:+,.2f}\n\n"
            f"• *Status*: {status_emoji} Stable Monitoring"
        )
        return text

    def get_positions_summary(self):
        """현재 보유 포지션 상세 반환"""
        if not self.positions:
            return "📍 현재 보유 중인 가상 포지션이 없습니다."
        
        text = "📍 *[Active Virtual Positions]*\n\n"
        for sym, d in self.positions.items():
            text += (
                f"• *{sym}*\n"
                f"  - Entry APY: {d['entry_apy']:.2f}%\n"
                f"  - Entry Time: {d['entry_time'][:16]}\n"
                f"  - Status: Holding\n\n"
            )
        return text
