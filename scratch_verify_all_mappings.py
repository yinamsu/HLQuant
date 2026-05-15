import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def verify_mappings():
    info = Info(constants.MAINNET_API_URL)
    
    with open("spot_mapping.json", "r") as f:
        mapping = json.load(f)
        
    all_mids = info.all_mids()
    spot_meta = info.spot_meta()
    
    # 현물 원시 데이터 매핑 (Pair Name -> Mid Price)
    # spot_meta_and_asset_ctxs 사용
    result = info.spot_meta_and_asset_ctxs()
    spot_prices = {}
    for i, pair in enumerate(result[0]['universe']):
        spot_prices[pair['name']] = float(result[1][i].get('midPx') or 0)

    print(f"{'Symbol':<10} | {'Perp Price':<12} | {'Spot Price':<12} | {'Gap (%)':<10} | {'Status'}")
    print("-" * 65)

    for symbol, spot_id in mapping.items():
        perp_px = float(all_mids.get(symbol, 0))
        spot_px = spot_prices.get(spot_id, 0)
        
        if spot_px > 0:
            gap = abs(perp_px - spot_px) / spot_px * 100
            status = "OK" if gap < 5 else "ERROR (Price Mismatch)"
            print(f"{symbol:<10} | {perp_px:<12.6f} | {spot_px:<12.6f} | {gap:<10.2f} | {status}")
        else:
            print(f"{symbol:<10} | {perp_px:<12.6f} | {'N/A':<12} | {'N/A':<10} | WARNING: Spot Price Missing")

if __name__ == "__main__":
    asyncio.run(verify_mappings())
