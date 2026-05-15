import asyncio
from hyperliquid_api import HyperliquidAPI

async def main():
    api = HyperliquidAPI(is_testnet=False)
    meta, ctxs = api.info.spot_meta_and_asset_ctxs()
    
    print("Pairs with HYPE in name:")
    for i, p in enumerate(meta['universe']):
        if 'HYPE' in p['name']:
            print(f"{i} | {p['name']} | Price: {ctxs[i].get('midPx')}")
            
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
