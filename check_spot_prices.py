
import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    meta, asset_ctxs = api.info.spot_meta_and_asset_ctxs()
    tokens = meta['tokens']
    universe = meta['universe']
    token_map = {t['index']: t for t in tokens}
    
    for i, u in enumerate(universe):
        token_indices = u['tokens']
        t0 = token_map.get(token_indices[0])
        symbol = t0['name']
        price = asset_ctxs[i].get('midPx', 'N/A')
        
        if symbol in ['UBTC', 'UETH', 'USOL', 'AVAX0', 'UAVAX', 'BNB0', 'BNB1', 'LINK0']:
            print(f"Pair: {u['name']} (Base: {symbol}) -> Price: {price}")

if __name__ == "__main__":
    asyncio.run(main())
