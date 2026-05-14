import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    meta, _ = api.info.spot_meta_and_asset_ctxs()
    
    print(f"{'Index':<8} | {'ID':<8} | {'Name':<12} | {'szDec':<6}")
    print("-" * 40)
    for i, pair in enumerate(meta['universe']):
        token_indices = pair.get('tokens', [])
        if not token_indices: continue
        base_token = meta['tokens'][token_indices[0]]
        print(f"{i:<8} | {pair['name']:<8} | {base_token['name']:<12} | {base_token['szDecimals']:<6}")
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
