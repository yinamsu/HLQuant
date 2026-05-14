import asyncio
import logging
import json
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def inspect_spot_meta():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    print("Fetching Spot Meta...")
    meta, _ = api.info.spot_meta_and_asset_ctxs()
    
    tokens = meta['tokens']
    universe = meta['universe']
    
    # "BTC"가 포함된 토큰 찾기
    print("\n--- BTC 관련 토큰 검색 ---")
    for t in tokens:
        if "BTC" in t['name'].upper() or (t.get('fullName') and "BITCOIN" in t['fullName'].upper()):
            print(f"Token Index: {t['index']} | Name: {t['name']} | FullName: {t['fullName']}")

    # "ETH" 관련 토큰 검색
    print("\n--- ETH 관련 토큰 검색 ---")
    for t in tokens:
        if "ETH" in t['name'].upper() or (t.get('fullName') and "ETHEREUM" in t['fullName'].upper()):
            print(f"Token Index: {t['index']} | Name: {t['name']} | FullName: {t['fullName']}")

    # 유니버스 상위 20개 매핑 확인
    print("\n--- Universe Mapping (Top 20) ---")
    token_map = {t['index']: t['name'] for t in tokens}
    for i, pair in enumerate(universe[:20]):
        token_indices = pair.get('tokens', [])
        base_name = token_map.get(token_indices[0], "Unknown") if token_indices else "None"
        print(f"Index: {i} | Pair Name: {pair['name']} | Base Token: {base_name}")

if __name__ == "__main__":
    asyncio.run(inspect_spot_meta())
