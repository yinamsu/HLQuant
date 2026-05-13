import asyncio
import logging
import os
import json
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

class HyperliquidAPI:
    """
    Hyperliquid 공식 SDK를 사용하여 시장 데이터 조회 및 주문 실행을 담당하는 클래스입니다.
    """
    
    def __init__(self, is_testnet=True):
        self.is_testnet = is_testnet
        self.base_url = constants.TESTNET_API_URL if is_testnet else constants.MAINNET_API_URL
        
        # .env에서 지갑 정보 로드
        self.wallet_address = os.getenv("HL_WALLET_ADDRESS")
        self.private_key = os.getenv("HL_AGENT_PRIVATE_KEY")
        
        # Info 객체 생성 (시장 데이터 조회용)
        self.info = Info(self.base_url, skip_ws=True)
        
        # Exchange 객체 생성 (주문 실행용)
        self.exchange = None
        if self.wallet_address and self.private_key:
            try:
                account = Account.from_key(self.private_key)
                self.exchange = Exchange(account, self.base_url, account_address=self.wallet_address)
                logging.info(f"Hyperliquid Exchange initialized for {self.wallet_address} ({'Testnet' if is_testnet else 'Mainnet'})")
            except Exception as e:
                logging.error(f"Failed to initialize Exchange: {e}")

    async def get_all_perp_data(self):
        """
        모든 선물(Perp) 자산의 데이터(펀딩비, 가격 등)를 가져옵니다.
        """
        try:
            # SDK의 meta_and_asset_ctxs는 동기 함수이므로 루프를 방해하지 않게 run_in_executor 사용 고려 가능하나
            # 여기서는 단순하게 호출 (성능 이슈 시 비동기 래퍼 사용)
            result = self.info.meta_and_asset_ctxs()
            if not result: return None
            
            meta, asset_ctxs = result
            universe = meta['universe']
            
            perp_data = {}
            for i, asset in enumerate(universe):
                name = asset['name']
                ctx = asset_ctxs[i]
                perp_data[name] = {
                    'funding': float(ctx.get('funding') or 0),
                    'midPrice': float(ctx.get('midPx') or 0),
                    'markPrice': float(ctx.get('markPx') or 0),
                    'indexPrice': float(ctx.get('oraclePx') or 0)
                }
            return perp_data
        except Exception as e:
            logging.error(f"Error fetching perp data: {e}")
            return None

    async def get_all_spot_data(self):
        """
        모든 현물(Spot) 자산의 데이터를 가져옵니다. 
        Precise Name & FullName Matching + spot_mapping.json 을 사용하여 정확도를 높입니다.
        """
        try:
            # 1. 현물 메타데이터 및 시세 데이터 가져오기
            result = self.info.spot_meta_and_asset_ctxs()
            if not result: return None
            
            meta, asset_ctxs = result
            tokens = meta['tokens']
            universe = meta['universe']
            token_map = {t['index']: t for t in tokens}
            
            # 2. spot_mapping.json 로드 (선택 사항)
            mapping_from_file = {}
            if os.path.exists("spot_mapping.json"):
                try:
                    with open("spot_mapping.json", "r") as f:
                        mapping_from_file = json.load(f)
                except Exception as e:
                    logging.warning(f"Failed to load spot_mapping.json: {e}")

            # 3. 선물 데이터 가져오기 (가격 대조용 보조)
            perp_meta, perp_asset_ctxs = self.info.meta_and_asset_ctxs()
            perp_universe = perp_meta['universe']
            perp_prices = {p['name']: float(perp_asset_ctxs[i].get('midPx') or 0) for i, p in enumerate(perp_universe)}
            
            spot_data = {}
            
            # 4. 각 선물 종목에 대해 가장 적합한 현물 시장 찾기
            for p_symbol, p_price in perp_prices.items():
                if p_price <= 0: continue
                
                best_match_idx = -1
                
                # 가. spot_mapping.json 우선 확인
                if p_symbol in mapping_from_file:
                    target_name = mapping_from_file[p_symbol]
                    for j, s_pair in enumerate(universe):
                        if s_pair['name'] == target_name:
                            best_match_idx = j
                            break
                
                # 나. 이름/풀네임 기반 매칭 (mapping 실패 시)
                if best_match_idx == -1:
                    for j, s_pair in enumerate(universe):
                        token_indices = s_pair.get('tokens', [])
                        if not token_indices: continue
                        
                        base_token = token_map.get(token_indices[0], {})
                        t_name = base_token.get('name', '')
                        f_name = (base_token.get('fullName') or '').upper()
                        
                        match = False
                        if t_name == p_symbol: match = True
                        elif t_name == f"U{p_symbol}": match = True # Unit tokens
                        elif p_symbol == "BTC" and "BITCOIN" in f_name: match = True
                        elif p_symbol == "ETH" and "ETHEREUM" in f_name: match = True
                        elif p_symbol == "SOL" and "SOLANA" in f_name: match = True
                        
                        if match:
                            best_match_idx = j
                            break
                            
                # 다. 가격 기반 매칭 (최후의 수단, 오차 0.5% 이내)
                if best_match_idx == -1:
                    min_diff = 0.005
                    for j, s_ctx in enumerate(asset_ctxs):
                        if j >= len(universe): break
                        s_price = float(s_ctx.get('midPx') or 0)
                        if s_price <= 0: continue
                        diff = abs(p_price - s_price) / p_price
                        if diff < min_diff:
                            min_diff = diff
                            best_match_idx = j

                if best_match_idx != -1:
                    s_pair = universe[best_match_idx]
                    s_ctx = asset_ctxs[best_match_idx]
                    mid_px = float(s_ctx.get('midPx') or 0)
                    
                    if mid_px > 0:
                        spot_data[p_symbol] = {
                            'midPrice': mid_px,
                            'spot_name': s_pair['name'],
                            'universe_index': best_match_idx
                        }
            
            # 5. 특수 자산 추가 보완 (PURR 등)
            for i, pair in enumerate(universe):
                token_indices = pair.get('tokens', [])
                if not token_indices: continue
                base_token = token_map.get(token_indices[0], {})
                base_name = base_token.get('name')
                if base_name and base_name in ['PURR', 'HYPE', 'HPL', 'VIRTUAL']:
                    spot_data[base_name] = {
                        'midPrice': float(asset_ctxs[i].get('midPx') or 0),
                        'spot_name': pair['name'],
                        'universe_index': i
                    }
                    
            return spot_data
        except Exception as e:
            logging.error(f"Error in robust spot mapping: {e}")
            return None

    async def get_balance(self):
        """
        지갑의 가용 USDC 잔고를 조회합니다. (Perp 및 Spot 통합 확인)
        """
        try:
            # 1. Perp 계정 잔고 (marginSummary)
            user_state = self.info.user_state(self.wallet_address)
            cash = user_state.get('withdrawable', 0.0)
            if float(cash) == 0.0:
                cash = user_state.get('marginSummary', {}).get('accountValue', 0.0)
                
            # 2. 만약 Perp 잔고가 0에 가깝다면 Spot 계정의 USDC 확인
            if float(cash) < 1.0:
                spot_state = self.info.spot_user_state(self.wallet_address)
                for balance in spot_state.get('balances', []):
                    if balance.get('coin') == 'USDC':
                        cash = float(balance.get('total', 0.0))
                        break
                        
            return float(cash)
        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            return 0.0

    async def place_order(self, symbol, size, price, is_buy, is_perp=True):
        """
        실제 주문을 전송합니다.
        """
        if not self.exchange:
            logging.error("Exchange not initialized. Private key might be missing.")
            return None
        
        try:
            # SDK 주문 전송 (Market Order 또는 Limit Order)
            # 여기서는 편의상 Limit Order로 전송 (slippage 고려된 가격)
            # is_perp가 False이면 Spot 주문 처리 로직 필요 (SDK 확인 필요)
            
            # 자산별 정밀도(szDecimals, pxDecimals) 가져오기
            if is_perp:
                meta, _ = self.info.meta_and_asset_ctxs()
                universe = meta['universe']
                sz_decimals = 0
                px_decimals = 6
                for asset in universe:
                    if asset['name'] == symbol:
                        sz_decimals = asset.get('szDecimals', 0)
                        break
            else:
                meta, _ = self.info.spot_meta_and_asset_ctxs()
                universe = meta['universe']
                tokens = meta['tokens']
                sz_decimals = 0
                px_decimals = 6
                for asset in universe:
                    if asset['name'] == symbol:
                        base_token_idx = asset.get('tokens', [0])[0]
                        for token in tokens:
                            if token['index'] == base_token_idx:
                                sz_decimals = token.get('szDecimals', 0)
                                break
                        break
            
            # 수량 및 가격 정밀도 조정
            rounded_size = round(float(size), sz_decimals)
            # Hyperliquid은 가격에 대해 유효숫자 5자리를 요구하는 경우가 많음
            rounded_price = float(f"{float(price):.5g}") 
            
            logging.info(f"Placing {'Buy' if is_buy else 'Sell'} order for {symbol}: {rounded_size} @ {rounded_price}")
            
            response = self.exchange.order(
                symbol, 
                is_buy, 
                rounded_size, 
                rounded_price, 
                {"limit": {"tif": "Ioc"}}
            )
            
            if response.get('status') == 'ok':
                # 내부 에러 체크 (마진 부족 등)
                statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                for status in statuses:
                    if 'error' in status:
                        logging.error(f"Order rejected by exchange: {status['error']}")
                        return None
                        
                    if 'filled' in status:
                        filled_sz = float(status['filled'].get('totalSz', 0))
                        if filled_sz == 0:
                            logging.error("IOC order filled 0 (Canceled due to slippage/spread)")
                            return None
                    elif 'canceled' in status:
                        logging.error("IOC order was canceled immediately")
                        return None
                        
                logging.info(f"Order successful: {response}")
                return response
            else:
                logging.error(f"Order failed: {response}")
                return None
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

    async def get_user_state(self):
        """
        지갑의 전체 상태(잔고, 포지션 등)를 조회합니다.
        """
        try:
            return self.info.user_state(self.wallet_address)
        except Exception as e:
            logging.error(f"Error fetching user state: {e}")
            return {}

    async def close(self):
        # SDK (requests 기반)은 별도의 close가 필요 없으나 구조 유지
        pass
