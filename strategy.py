import logging
import json
import os
from datetime import datetime
from notifier import TelegramNotifier

class DeltaNeutralStrategy:
    def __init__(self, api=None, notifier=None, state_file="paper_balance.json", is_real_trading=False, is_testnet=False):
        self.state_file = state_file
        self.api = api
        self.is_real_trading = is_real_trading
        self.is_testnet = is_testnet
        self.initial_capital = 1000.0
        self.max_positions = 5
        
        state = self._load_state()
        self.positions = state.get("positions", {})
        self.total_realized_profit = state.get("total_realized_profit", 0.0)
        self.notifier = notifier or TelegramNotifier()
        
        self.min_hold_hours = 8
        self.slippage_rate = 0.005
        self.entry_apy_threshold = 10.0
        self.exit_apy_threshold = 3.0
        self.rebalance_gap = 10.0

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f: return json.load(f)
            except: return {"positions": {}, "total_realized_profit": 0.0}
        return {"positions": {}, "total_realized_profit": 0.0}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump({"positions": self.positions, "total_realized_profit": self.total_realized_profit}, f, indent=4)

    async def sync_with_exchange(self):
        try:
            user_state = await self.api.get_user_state()
            asset_positions = user_state.get('assetPositions', [])
            new_positions = {}
            for pos in asset_positions:
                p = pos.get('position', {})
                symbol = p.get('coin')
                if abs(float(p.get('szi', 0))) > 0:
                    new_positions[symbol] = self.positions.get(symbol, {
                        "entry_time": datetime.now().isoformat(),
                        "spot_px": float(p.get('entryPx', 0)),
                        "perp_px": float(p.get('entryPx', 0)),
                        "entry_apy": 10.0, "profit": 0.0
                    })
            self.positions = new_positions
            self._save_state()
        except Exception as e:
            logging.error(f"Sync Error: {e}")

    async def execute_logic(self, perp_data, spot_data):
        current_time = datetime.now()
        actual_balance = 0.0
        
        if self.is_real_trading and self.api:
            actual_balance = await self.api.get_balance()
            dynamic_max = max(1, int(actual_balance // 11))
            self.max_positions = min(dynamic_max, 10)

        # 1. 청산 로직 생략 (기존과 동일)
        # 2. 진입 로직
        if len(self.positions) < self.max_positions:
            targets = self.get_targets(perp_data, spot_data)
            for t in targets:
                if len(self.positions) >= self.max_positions: break
                if t['symbol'] not in self.positions:
                    if self.is_real_trading:
                        # 실제 주문 로직 수행...
                        pass
                    self.positions[t['symbol']] = {
                        'entry_time': current_time.isoformat(),
                        'spot_px': t['spot_px'], 'perp_px': t['perp_px'],
                        'entry_apy': t['apy'], 'profit': 0.0
                    }
        self._save_state()

    def get_targets(self, perp_data, spot_data):
        candidates = []
        for symbol, p_data in perp_data.items():
            s_data = spot_data.get(symbol)
            if not s_data: continue
            
            apy = p_data['funding'] * 24 * 365 * 100
            premium = abs(p_data['midPrice'] - s_data['midPrice']) / s_data['midPrice'] * 100
            if apy >= self.entry_apy_threshold and premium <= 0.1:
                candidates.append({'symbol': symbol, 'apy': apy, 'spot_px': s_data['midPrice'], 'perp_px': p_data['midPrice']})
        candidates.sort(key=lambda x: x['apy'], reverse=True)
        return candidates[:self.max_positions]

    def get_status_summary(self):
        return f"📊 *HLQuant Bot Status*\n• Mode: {'Real' if self.is_real_trading else 'Paper'}\n• Positions: {len(self.positions)}/{self.max_positions}"

    async def get_balance_summary(self):
        if self.is_real_trading:
            balance = await self.api.get_balance()
            return f"💰 *Live Balance*: ${balance:,.2f}"
        return "💰 *Paper Balance Mode*"

    def get_positions_summary(self):
        if not self.positions: return "📭 No Positions"
        return "📍 Active Positions: " + ", ".join(self.positions.keys())