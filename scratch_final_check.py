import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def final_check():
    info = Info(constants.MAINNET_API_URL)
    all_mids = info.all_mids()
    result = info.spot_meta_and_asset_ctxs()
    
    meta = result[0]
    contexts = result[1]
    
    # 우리가 의심하는 매핑 후보들
    candidates = {
        "PURR": "PURR/USDC",
        "HYPE": "@271",
        "SOL": "@160",
        "ETH": "@250",
        "BTC": "@249"
    }

    spot_data = {pair['name']: float(contexts[i].get('midPx') or 0) for i, pair in enumerate(meta['universe'])}

    print(f"{'Symbol':<10} | {'Perp Price':<12} | {'Spot Price':<12} | {'Gap %':<10} | {'Status'}")
    print("-" * 60)

    for sym, spot_id in candidates.items():
        perp_px = float(all_mids.get(sym, 0))
        spot_px = spot_data.get(spot_id, 0)
        
        if spot_px > 0:
            gap = abs(perp_px - spot_px) / spot_px * 100
            status = "VERIFIED" if gap < 1.0 else "REJECTED"
            print(f"{sym:<10} | {perp_px:<12.4f} | {spot_px:<12.4f} | {gap:<10.2f} | {status}")
        else:
            print(f"{sym:<10} | {perp_px:<12.4f} | {'MISSING':<12} | {'N/A':<10} | FAILED")

if __name__ == "__main__":
    asyncio.run(final_check())
