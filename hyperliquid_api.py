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
        이름 기반 매칭을 최우선으로 하며, 유닛 토큰(U+Symbol) 및 알려진 에일리어스를 처리합니다.
        """
        try:
            # 1. 현물 메타데이터 및 시세 데이터 가져오기
            result = self.info.spot_meta_and_asset_ctxs()
            if not result: return None
            
            meta, asset_ctxs = result
            tokens = meta['tokens']
            universe = meta['universe']
            token_map = {t['index']: t for t in tokens}
            
            spot_data = {}
            
            # 각 유니버스(페어)를 순회하며 베이스 토큰 정보를 분석
            for i, pair in enumerate(universe):
                token_indices = pair.get('tokens', [])
                if not token_indices: continue
                
                base_token = token_map.get(token_indices[0])
                if not base_token: continue
                
                raw_symbol = base_token['name']
                # 매칭 로직: 
                # 1. 이름이 직접 일치 (예: HYPE, PURR)
                # 2. 'U'로 시작하는 유닛 토큰 (예: UBTC -> BTC)
                # 3. 알려진 특수 매핑 (예: AVAX0 -> AVAX)
                
                symbol = raw_symbol
                if raw_symbol.startswith('U') and len(raw_symbol) > 3:
                    symbol = raw_symbol[1:]
                elif raw_symbol == 'AVAX0':
                    symbol = 'AVAX'
                
                mid_px = float(asset_ctxs[i].get('midPx') or 0)
                if mid_px <= 0: continue

                # 동일 심볼에 대해 여러 페어가 있을 경우 (예: @142, @234)
                # 가격이 0이 아닌 유효한 페어를 우선하며, 이미 등록된 경우 스킵하거나 덮어씀
                # 여기서는 처음 발견된 유효한 페어를 사용
                if symbol not in spot_data:
                    spot_data[symbol] = {
                        'midPrice': mid_px,
                        'spot_name': pair['name'],
                        'universe_index': i,
                        'szDecimals': base_token['szDecimals']
                    }
                    
            return spot_data
        except Exception as e:
            logging.error(f"Error fetching spot mapping by name: {e}")
            return None

    async def place_order(self, symbol, size, price, is_buy, is_perp=True):
        """
        실제 주문을 전송합니다.
        하이퍼리퀴드 규정: 가격은 최대 5유효숫자, 수량은 szDecimals 준수.
        """
        if not self.exchange:
            logging.error("Exchange not initialized.")
            return None
        
        try:
            # 자산별 정밀도 가져오기
            sz_decimals = 0
            if is_perp:
                meta, _ = self.info.meta_and_asset_ctxs()
                for asset in meta['universe']:
                    if asset['name'] == symbol:
                        sz_decimals = asset.get('szDecimals', 0)
                        break
            else:
                # 현물의 경우 spot_name(예: @226)으로 symbol이 들어옴
                meta, _ = self.info.spot_meta_and_asset_ctxs()
                for i, asset in enumerate(meta['universe']):
                    if asset['name'] == symbol:
                        base_token_idx = asset['tokens'][0]
                        for token in meta['tokens']:
                            if token['index'] == base_token_idx:
                                sz_decimals = token.get('szDecimals', 0)
                                break
                        break
            
            # 1. 수량 정밀도 조정 (szDecimals)
            rounded_size = round(float(size), sz_decimals)
            if rounded_size <= 0:
                logging.error(f"Rounded size is 0 for {symbol} (Size: {size}, Decimals: {sz_decimals})")
                return None
                
            # 2. 가격 정밀도 조정 (5 Significant Figures)
            # 1234.56 -> 1234.6 (5 sig figs)
            # 0.000123456 -> 0.00012346 (5 sig figs)
            import math
            p_float = float(price)
            if p_float > 0:
                precision = 5
                rounded_price = round(p_float, -int(math.floor(math.log10(p_float))) + (precision - 1))
                # 불필요한 소수점 제거 (정수일 경우 .0 등)
                if rounded_price == int(rounded_price):
                    rounded_price = int(rounded_price)
            else:
                rounded_price = p_float

            logging.info(f"Placing {'Buy' if is_buy else 'Sell'} order for {symbol}: {rounded_size} @ {rounded_price} (szDec: {sz_decimals})")
            
            response = self.exchange.order(
                symbol, 
                is_buy, 
                rounded_size, 
                rounded_price, 
                {"limit": {"tif": "Ioc"}}
            )
            
            if response.get('status') == 'ok':
                # 내부 에러 체크
                statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                for status in statuses:
                    if 'error' in status:
                        logging.error(f"Order rejected: {status['error']}")
                        return None
                    if 'filled' in status:
                        return response
                return None
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
