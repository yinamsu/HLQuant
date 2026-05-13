import asyncio
import logging
import os
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
        """
        try:
            result = self.info.spot_meta_and_asset_ctxs()
            if not result: return None
            
            meta, asset_ctxs = result
            tokens = meta['tokens']
            universe = meta['universe']
            
            spot_data = {}
            token_map = {t['index']: t['name'] for t in tokens}
            
            for i, asset in enumerate(universe):
                token_indices = asset.get('tokens', [])
                if not token_indices: continue
                
                base_token_index = token_indices[0]
                name = token_map.get(base_token_index)
                
                if name:
                    ctx = asset_ctxs[i]
                    spot_data[name] = {
                        'midPrice': float(ctx.get('midPx') or 0)
                    }
            return spot_data
        except Exception as e:
            logging.error(f"Error fetching spot data: {e}")
            return None

    async def get_balance(self):
        """
        지갑의 가용 USDC 잔고를 조회합니다.
        """
        try:
            user_state = self.info.user_state(self.wallet_address)
            # 'cash'가 없으면 'withdrawable' 또는 'marginSummary'의 'accountValue' 사용
            cash = user_state.get('cash')
            if cash is None:
                cash = user_state.get('marginSummary', {}).get('accountValue', 0.0)
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
            meta, _ = self.info.meta_and_asset_ctxs()
            universe = meta['universe']
            sz_decimals = 0
            px_decimals = 0
            for asset in universe:
                if asset['name'] == symbol:
                    sz_decimals = asset['szDecimals']
                    # pxDecimals는 개별 에셋의 속성으로 존재하지 않을 수 있으므로 
                    # 기본 6자리 또는 특정 로직 필요 (보통 6자리이나 종목별로 다름)
                    # 실제 SDK에서는 정밀도를 알아내기 위해 다른 필드를 사용하거나 
                    # 고정된 규칙(Significant Figures)을 따르는 경우가 많음.
                    # 여기서는 안전하게 6자리로 하되, 오류 방지를 위해 정수 변환 로직 확인.
                    px_decimals = 6 # 기본값
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
                {"limit": {"tif": "Gtc"}}
            )
            
            if response['status'] == 'ok':
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
