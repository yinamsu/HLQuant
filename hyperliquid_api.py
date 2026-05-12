import asyncio
import aiohttp
import logging
import json
from datetime import datetime

# 하이퍼리퀴드 테스트넷 API 베이스 URL
BASE_URL = "https://api.hyperliquid-testnet.xyz"
INFO_URL = f"{BASE_URL}/info"

class HyperliquidAPI:
    """
    Hyperliquid API와 통신하여 시장 데이터를 가져오는 래퍼 클래스입니다.
    Rate Limit을 고려하여 백오프 로직을 포함합니다.
    """
    
    def __init__(self):
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            # aiodns 이슈 방지를 위해 ThreadedResolver를 사용하여 시스템 리졸버를 강제합니다.
            resolver = aiohttp.ThreadedResolver()
            connector = aiohttp.TCPConnector(resolver=resolver)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def post_request(self, data):
        """
        공통 POST 요청 처리 함수 (Rate Limit 대응 포함)
        """
        session = await self._get_session()
        for attempt in range(3):
            try:
                async with session.post(INFO_URL, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        logging.warning(f"Rate limit hit (429). Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error(f"API Error: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                logging.error(f"Request failed: {e}")
                await asyncio.sleep(1)
        return None

    async def get_all_perp_data(self):
        """
        모든 선물(Perp) 자산의 메타데이터와 컨텍스트(펀딩비, 가격 등)를 가져옵니다.
        """
        data = {"type": "metaAndAssetCtxs"}
        result = await self.post_request(data)
        if not result:
            return None
        
        # metaAndAssetCtxs는 [meta, assetCtxs] 형태의 리스트를 반환함
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

    async def get_all_spot_data(self):
        """
        모든 현물(Spot) 자산의 데이터를 가져옵니다.
        """
        data = {"type": "spotMetaAndAssetCtxs"}
        result = await self.post_request(data)
        if not result:
            return None
        
        meta, asset_ctxs = result
        tokens = meta['tokens']
        universe = meta['universe']
        
        spot_data = {}
        # 토큰 인덱스 -> 이름 매핑 생성
        token_map = {t['index']: t['name'] for t in tokens}
        
        for i, asset in enumerate(universe):
            # universe[i]의 tokens[0]이 해당 자산의 토큰 인덱스
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

    async def close(self):
        if self.session:
            await self.session.close()
