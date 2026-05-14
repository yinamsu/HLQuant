import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    # 1. Perp Universe
    perp_meta = api.info.meta()
    perp_symbols = {asset['name'] for asset in perp_meta['universe']}
    
    # 2. Spot Universe
    spot_meta, _ = api.info.spot_meta_and_asset_ctxs()
    spot_data = []
    for pair in spot_meta['universe']:
        token_indices = pair.get('tokens', [])
        if not token_indices: continue
        base_token = spot_meta['tokens'][token_indices[0]]
        spot_data.append({
            'symbol': base_token['name'],
            'id': pair['name']
        })
    
    print("--- Common Assets (Exact Name Match) ---")
    for s in spot_data:
        if s['symbol'] in perp_symbols:
            print(f"Match: {s['symbol']} | Spot ID: {s['id']}")
            
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
