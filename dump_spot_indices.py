
import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    meta, _ = api.info.spot_meta_and_asset_ctxs()
    tokens = meta['tokens']
    universe = meta['universe']
    token_map = {t['index']: t for t in tokens}
    
    mapping = {}
    for i, u in enumerate(universe):
        token_indices = u['tokens']
        t0 = token_map.get(token_indices[0])
        symbol = t0['name']
        # If it's a unit token like UBTC, map it to BTC
        clean_symbol = symbol[1:] if symbol.startswith('U') and len(symbol) > 3 else symbol
        if symbol == 'AVAX0': clean_symbol = 'AVAX'
        
        mapping[clean_symbol] = u['name']
        print(f"Symbol: {clean_symbol} (Original: {symbol}) -> Spot Pair Name: {u['name']}, Index: {i}")

if __name__ == "__main__":
    asyncio.run(main())
