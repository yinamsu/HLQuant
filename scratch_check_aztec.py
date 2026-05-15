import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def check_aztec():
    info = Info(constants.MAINNET_API_URL)
    all_mids = info.all_mids()
    result = info.spot_meta_and_asset_ctxs()
    
    # AZTEC은 @302로 추정됨
    perp_px = float(all_mids.get("AZTEC", 0))
    
    spot_px = 0
    for i, pair in enumerate(result[0]['universe']):
        if pair['name'] == "@302":
            spot_px = float(result[1][i].get('midPx') or 0)
            break

    gap = abs(perp_px - spot_px) / spot_px * 100 if spot_px > 0 else 100
    print(f"AZTEC Check: Perp {perp_px} vs Spot(@302) {spot_px} | Gap: {gap:.2f}%")

if __name__ == "__main__":
    asyncio.run(check_aztec())
