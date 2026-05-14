
import asyncio
import os
import sys
from hyperliquid.info import Info
from hyperliquid.utils import constants
from dotenv import load_dotenv

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    load_dotenv()
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    result = info.spot_meta_and_asset_ctxs()
    meta, asset_ctxs = result
    tokens = meta['tokens']
    universe = meta['universe']
    token_map = {t['index']: t for t in tokens}
    
    print(f"{'Index':<6} | {'Pair Name':<15} | {'Base Token':<10} | {'Price':<12} | {'Full Name'}")
    print("-" * 100)
    for i, pair in enumerate(universe):
        token_indices = pair['tokens']
        name = pair['name']
        t0 = token_map.get(token_indices[0])
        t0_name = t0['name'] if t0 else "Unknown"
        t0_full = t0.get('fullName', 'N/A') if t0 else "N/A"
        price = asset_ctxs[i].get('midPx', 'N/A')
        print(f"{i:<6} | {name:<15} | {t0_name:<10} | {str(price):<12} | {t0_full}")

if __name__ == "__main__":
    asyncio.run(main())
