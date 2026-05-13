import os
import asyncio
import json
from dotenv import load_dotenv
from hyperliquid_api import HyperliquidAPI

async def inspect_spot_meta():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    print("Fetching Spot Meta...")
    meta, _ = api.info.spot_meta_and_asset_ctxs()
    
    tokens = meta['tokens']
    universe = meta['universe']
    
    # "ETH"가 포함된 자산 찾기
    print("\n--- ETH 관련 자산 검색 ---")
    eth_tokens = [t for t in tokens if "ETH" in t['name']]
    print(f"Tokens containing 'ETH': {eth_tokens}")
    
    eth_universe = [u for u in universe if "ETH" in u['name']]
    print(f"Universe items containing 'ETH': {eth_universe}")

    # "SOL" 관련 자산 찾기
    print("\n--- SOL 관련 자산 검색 ---")
    sol_tokens = [t for t in tokens if "SOL" in t['name']]
    print(f"Tokens containing 'SOL': {sol_tokens}")
    
    sol_universe = [u for u in universe if "SOL" in u['name']]
    print(f"Universe items containing 'SOL': {sol_universe}")

    # 전체 유니버스 이름 10개만 출력
    print("\n--- Universe Names (Top 10) ---")
    for u in universe[:10]:
        print(u['name'])

if __name__ == "__main__":
    asyncio.run(inspect_spot_meta())
