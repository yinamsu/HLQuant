import asyncio
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    perp_data = await api.get_all_perp_data()
    _, asset_ctxs = api.info.spot_meta_and_asset_ctxs()
    
    # Common assets to check
    checks = [
        ("PURR", 0), # PURR is often index 0 or similar
        ("HYPE", 207),
        ("TRUMP", 9),
        ("PUMP", 20),
    ]
    
    print(f"{'Symbol':<10} | {'Perp Price':<12} | {'Spot Price':<12}")
    for sym, idx in checks:
        p_px = perp_data.get(sym, {}).get('midPrice')
        # We need to find the spot index correctly.
        # Actually, let's just dump the mapping first.
        s_px = asset_ctxs[idx].get('midPx') if idx < len(asset_ctxs) else "N/A"
        print(f"{sym:<10} | {p_px:<12} | {s_px:<12}")
        
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
