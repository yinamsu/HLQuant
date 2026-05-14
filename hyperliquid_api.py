import asyncio
import logging
import os
import json
import math
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

class HyperliquidAPI:
    def __init__(self, is_testnet=True):
        self.is_testnet = is_testnet
        self.base_url = constants.TESTNET_API_URL if is_testnet else constants.MAINNET_API_URL
        
        self.wallet_address = os.getenv("HL_WALLET_ADDRESS")
        self.private_key = os.getenv("HL_AGENT_PRIVATE_KEY")
        
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = None
        
        if self.wallet_address and self.private_key:
            try:
                account = Account.from_key(self.private_key)
                self.exchange = Exchange(account, self.base_url, account_address=self.wallet_address)
                logging.info(f"Hyperliquid API Initialized: {self.wallet_address}")
            except Exception as e:
                logging.error(f"Exchange Init Error: {e}")

    async def get_all_perp_data(self):
        try:
            result = self.info.meta_and_asset_ctxs()
            if not result: return None
            meta, asset_ctxs = result
            perp_data = {}
            for i, asset in enumerate(meta['universe']):
                ctx = asset_ctxs[i]
                perp_data[asset['name']] = {
                    'funding': float(ctx.get('funding') or 0),
                    'midPrice': float(ctx.get('midPx') or 0),
                    'indexPrice': float(ctx.get('oraclePx') or 0),
                    'szDecimals': asset['szDecimals']
                }
            return perp_data
        except Exception as e:
            logging.error(f"Perp Data Error: {e}"); return None

    async def get_all_spot_data(self):
        try:
            result = self.info.spot_meta_and_asset_ctxs()
            if not result: return None
            meta, asset_ctxs = result
            token_map = {t['index']: t for t in meta['tokens']}
            # spot_mapping.json 로드
            mapping = {}
            if os.path.exists("spot_mapping.json"):
                try:
                    with open("spot_mapping.json", "r") as f:
                        mapping = json.load(f)
                except: pass

            spot_data = {}
            for i, pair in enumerate(meta['universe']):
                token_indices = pair.get('tokens', [])
                if not token_indices: continue
                base_token = token_map.get(token_indices[0])
                if not base_token: continue
                
                raw_symbol = base_token['name']
                pair_name = pair['name']
                
                # 1. 매핑 파일 우선 확인
                symbol = None
                for s, m_name in mapping.items():
                    if m_name == pair_name:
                        symbol = s
                        break
                
                # 2. 매핑 없으면 기존 로직 적용
                if not symbol:
                    symbol = raw_symbol
                    if raw_symbol.startswith('U') and len(raw_symbol) > 3: symbol = raw_symbol[1:]
                    elif raw_symbol == 'AVAX0': symbol = 'AVAX'
                
                mid_px = float(asset_ctxs[i].get('midPx') or 0)
                if mid_px > 0 and symbol not in spot_data:
                    spot_data[symbol] = {
                        'midPrice': mid_px,
                        'spot_name': pair['name'],
                        'szDecimals': base_token['szDecimals']
                    }
            return spot_data
        except Exception as e:
            logging.error(f"Spot Data Error: {e}"); return None

    async def get_balance(self):
        """가용 자산 합산 반환 (무한 재부팅 방지 핵심)"""
        if not self.wallet_address:
            logging.error("Wallet address not set in environment.")
            return 0.0
        try:
            user_state = await self.get_user_state()
            perp_balance = float(user_state.get('marginSummary', {}).get('withdrawable', 0.0))
            
            spot_state = self.info.spot_user_state(self.wallet_address)
            spot_usdc = 0.0
            for b in spot_state.get('balances', []):
                if b.get('coin') == 'USDC':
                    spot_usdc = float(b.get('total', 0.0))
                    break
            return perp_balance + spot_usdc
        except Exception as e:
            logging.error(f"Balance Error: {e}"); return 0.0

    async def place_order(self, symbol, size, price, is_buy, is_perp=True, sz_decimals=0):
        if not self.exchange: return None
        try:
            # 1. 가격 정밀도 조정 (5유효숫자)
            p_float = float(price)
            rounded_price = round(p_float, -int(math.floor(math.log10(p_float))) + 4) if p_float > 0 else p_float
            
            # 2. 수량 정밀도 조정 (szDecimals)
            rounded_size = round(float(size), sz_decimals)
            if rounded_size <= 0:
                logging.warning(f"Order skipped: Rounded size is 0 (Original: {size}, Decimals: {sz_decimals})")
                return None

            logging.info(f"Sending {'Perp' if is_perp else 'Spot'} Order: {symbol} {'BUY' if is_buy else 'SELL'} {rounded_size} @ {rounded_price}")
            
            # 3. 주문 실행
            # is_spot 파라미터는 SDK 버전에 따라 다를 수 있음. 여기서는 symbol 이름으로 구분되거나 별도 처리가 필요할 수 있음.
            # SDK의 exchange.order는 기본적으로 perp. Spot은 별도 처리가 필요할 수 있으나 SDK 최신버전은 지원함.
            response = self.exchange.order(symbol, is_buy, rounded_size, rounded_price, {"limit": {"tif": "Ioc"}})
            
            if response.get('status') == 'ok':
                # 내부 상태 확인 (Margin, Price 등 에러 체크)
                statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                if statuses:
                    status = statuses[0]
                    if 'error' in status:
                        logging.error(f"Exchange Order Rejected: {status['error']}")
                        return None
                    if 'filled' in status or 'resting' in status:
                        return response
            
            logging.error(f"Order failed or no fill: {response}")
            return None
        except Exception as e:
            logging.error(f"Order Exception: {e}"); return None

    async def get_user_state(self):
        if not self.wallet_address: return {}
        try:
            return self.info.user_state(self.wallet_address)
        except Exception as e:
            logging.error(f"User State Error: {e}"); return {}

    async def spot_user_transfer(self, amount, to_perp=True):
        if not self.exchange: return None
        try:
            logging.info(f"Transferring {amount} USDC from {'Spot to Perp' if to_perp else 'Perp to Spot'}")
            # usd_class_transfer takes float amount and to_perp bool
            response = self.exchange.usd_class_transfer(float(amount), to_perp)
            return response
        except Exception as e:
            logging.error(f"Transfer Error: {e}"); return None

    async def close(self): pass
