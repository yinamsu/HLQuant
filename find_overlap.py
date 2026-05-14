
import asyncio
import os
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    print("--- Fetching Perp Universe ---")
    perp_meta, _ = api.info.meta_and_asset_ctxs()
    perp_names = {u['name'] for u in perp_meta['universe']}
    
    print("--- Fetching Spot Universe ---")
    result = api.info.spot_meta_and_asset_ctxs()
    if not result:
        print("Failed to fetch spot meta")
        return
    meta, asset_ctxs = result
    tokens = meta['tokens']
    spot_universe = meta['universe']
    token_map = {t['index']: t['name'] for t in tokens}
    
    spot_names = set()
    for pair in spot_universe:
        token_indices = pair['tokens']
        base_token_name = token_map.get(token_indices[0])
        if base_token_name:
            spot_names.add(base_token_name)
    
    common = perp_names.intersection(spot_names)
    print(f"\nFound {len(common)} assets existing in both Perp and Spot:")
    for name in sorted(common):
        print(f"- {name}")

    print("\n--- Detailed Spot Pair Search for Major Assets ---")
    major = ['BTC', 'ETH', 'SOL', 'BNB', 'AVAX', 'MATIC', 'POL', 'XRP', 'LINK']
    for m in major:
        matches = [p['name'] for p in spot_universe if m in p['name'].upper()]
        if matches:
            print(f"{m} matches in Spot Universe: {matches}")
        else:
            print(f"{m} has NO matches in Spot Universe")

if __name__ == "__main__":
    asyncio.run(main())
