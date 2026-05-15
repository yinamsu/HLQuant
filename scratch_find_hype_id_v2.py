import asyncio
from hyperliquid_api import HyperliquidAPI

async def main():
    api = HyperliquidAPI(is_testnet=False)
    meta, asset_ctxs = api.info.spot_meta_and_asset_ctxs()
    
    print(f"{'Index':<6} | {'Name':<10} | {'Token':<10} | {'Price':<10}")
    for i, pair in enumerate(meta['universe']):
        token_indices = pair.get('tokens', [])
        if not token_indices: continue
        base_token = meta['tokens'][token_indices[0]]
        if base_token['name'] == 'HYPE':
            price = asset_ctxs[i].get('midPx')
            print(f"{i:<6} | {pair['name']:<10} | {base_token['name']:<10} | {price}")
            
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
