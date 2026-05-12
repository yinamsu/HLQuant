import logging
import json
import os
from datetime import datetime, timedelta
from notifier import TelegramNotifier

class DeltaNeutralStrategy:
    """
    델타 중립 펀딩비 체리피킹 전략 클래스
    """
    def __init__(self, notifier=None, state_file="paper_balance.json"):
        self.state_file = state_file
        self.positions = self._load_state()
        self.min_hold_hours = 8
        self.slippage_rate = 0.0005  # 0.05%
        self.entry_apy_threshold = 3.0
        self.exit_apy_threshold = 1.0
        self.rebalance_gap = 10.0  # 타 종목 APY가 10% 이상 높을 때
        self.notifier = notifier or TelegramNotifier()

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
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.positions, f, indent=4)

    def calculate_apy(self, funding_rate):
        """
        하이퍼리퀴드 1시간 펀딩비를 연환산(APY)으로 변환
        """
        # funding_rate가 0.0001 이면 0.01%
        return funding_rate * 24 * 365 * 100

    def get_targets(self, perp_data, spot_data):
        """
        진입 후보 종목 스캔 및 필터링
        """
        candidates = []
        for symbol, p_data in perp_data.items():
            # 1. APY 계산
            apy = self.calculate_apy(p_data['funding'])
            
            # 2. 프리미엄(Basis) 계산
            # 현물 데이터가 없으면 오라클 가격(indexPrice)을 대용으로 사용
            spot_px = spot_data.get(symbol, {}).get('midPrice', p_data['indexPrice'])
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
        
        # 디버깅: 현재 시장의 상위 5개 APY 및 프리미엄 출력
        all_candidates = []
        for symbol, p_data in perp_data.items():
            apy = self.calculate_apy(p_data['funding'])
            spot_px = spot_data.get(symbol, {}).get('midPrice', p_data['indexPrice'])
            premium = abs(p_data['midPrice'] - spot_px) / spot_px * 100 if spot_px != 0 else 999
            all_candidates.append((symbol, apy, premium))
        
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        top_list = ", ".join([f"{s}(APY:{a:.1f}%, Prem:{p:.2f}%)" for s, a, p in all_candidates[:5]])
        logging.info(f"Market Top: {top_list}")

        # APY 기준 내림차순 정렬 후 상위 3개 선정
        candidates.sort(key=lambda x: x['apy'], reverse=True)
        return candidates[:3]

    async def execute_logic(self, perp_data, spot_data):
        """
        전략 실행 메인 루프 (진입, 청산, 리밸런싱 판단)
        """
        current_time = datetime.now()
        
        # 1. 기존 포지션 체크 및 청산/리밸런싱 판단
        symbols_to_exit = []
        for symbol, pos in list(self.positions.items()):
            if symbol not in perp_data: continue
            
            curr_apy = self.calculate_apy(perp_data[symbol]['funding'])
            entry_time = datetime.fromisoformat(pos['entry_time'])
            hold_duration = (current_time - entry_time).total_seconds() / 3600
            
            # 청산 조건 1: APY 5% 이하
            exit_reason = None
            if curr_apy <= self.exit_apy_threshold:
                exit_reason = f"Low APY ({curr_apy:.2f}%)"
            
            # 리밸런싱 조건: 타 종목 APY가 현재보다 20% 이상 높고 최소 유지시간 경과
            if not exit_reason and hold_duration >= self.min_hold_hours:
                targets = self.get_targets(perp_data, spot_data)
                if targets and targets[0]['apy'] > curr_apy + self.rebalance_gap:
                    exit_reason = f"Rebalancing (Better opportunity: {targets[0]['symbol']} @ {targets[0]['apy']:.2f}%)"
            
            if exit_reason:
                logging.info(f"[VIRTUAL EXIT] {symbol} | Reason: {exit_reason}")
                await self.notifier.send_exit_notification(symbol, exit_reason)
                symbols_to_exit.append(symbol)

        # 포지션 제거
        for symbol in symbols_to_exit:
            del self.positions[symbol]
        
        # 2. 신규 진입 판단
        if len(self.positions) < 3:
            targets = self.get_targets(perp_data, spot_data)
            for t in targets:
                if len(self.positions) >= 3: break
                if t['symbol'] not in self.positions:
                    # 슬리피지 반영 (현물 매수는 높게, 선물 매도는 낮게 체결 가정)
                    virtual_spot_buy_px = t['spot_px'] * (1 + self.slippage_rate)
                    virtual_perp_sell_px = t['perp_px'] * (1 - self.slippage_rate)
                    
                    self.positions[t['symbol']] = {
                        'entry_time': current_time.isoformat(),
                        'spot_px': virtual_spot_buy_px,
                        'perp_px': virtual_perp_sell_px,
                        'entry_apy': t['apy']
                    }
                    logging.info(f"[VIRTUAL ENTRY] {t['symbol']} | APY: {t['apy']:.2f}% | SpotPx: {virtual_spot_buy_px:.4f} | PerpPx: {virtual_perp_sell_px:.4f}")
                    await self.notifier.send_entry_notification(t['symbol'], t['apy'], virtual_spot_buy_px, virtual_perp_sell_px)

        self._save_state()

    def get_status_summary(self):
        """봇 가동 상태 요약 반환"""
        return (
            f"📊 *[HLQuant Bot Status]*\n\n"
            f"• *Mode*: Paper Trading\n"
            f"• *Target Count*: 3 Pairs\n"
            f"• *Active Positions*: {len(self.positions)}/3\n"
            f"• *Strategy*: Delta-Neutral Arbitrage\n"
            f"• *Last Scan*: {datetime.now().strftime('%H:%M:%S')}"
        )

    def get_balance_summary(self):
        """수익률 요약 반환 (현재 가상 매매 기준)"""
        # 가상 원금 $10,000 기준 (추후 실거래 연동 가능)
        total_profit = sum(p.get('profit', 0) for p in self.positions.values())
        return (
            f"💰 *[Virtual Balance]*\n\n"
            f"• *Initial Equity*: $10,000.00\n"
            f"• *Current Profit*: ${total_profit:.2f}\n"
            f"• *ROI*: {(total_profit/10000)*100:.2f}%\n"
            f"• *Status*: Stable 🟢"
        )

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
