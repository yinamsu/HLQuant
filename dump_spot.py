import asyncio
import logging
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def dump_all_spot():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    print("Fetching ALL spot metadata and prices...")
    meta, asset_ctxs = api.info.spot_meta_and_asset_ctxs()
    
    tokens = meta['tokens']
    universe = meta['universe']
    token_map = {t['index']: t['name'] for t in tokens}
    
    print(f"\n{'Index':<6} | {'Univ Name':<12} | {'Base':<8} | {'Price':<12} | {'Tokens'}")
    print("-" * 60)
    
    for i, pair in enumerate(universe):
        token_indices = pair.get('tokens', [])
        base_name = token_map.get(token_indices[0], "Unknown")
        ctx = asset_ctxs[i]
        price = ctx.get('midPx', '0')
        
        # 가격이 있는 놈들이나 우리가 찾는 놈들 위주로 출력
        if base_name in ['BTC', 'ETH', 'SOL', 'AVAX', 'UBTC', 'UETH', 'USOL', 'UAVAX'] or float(price or 0) > 0:
            print(f"{i:<6} | {pair['name']:<12} | {base_name:<8} | {price:<12} | {token_indices}")

if __name__ == "__main__":
    asyncio.run(dump_all_spot())
