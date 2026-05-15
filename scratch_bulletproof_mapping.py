import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def build_safe_mapping():
    info = Info(constants.MAINNET_API_URL)
    
    # 1. 모든 가격 데이터 가져오기
    all_mids = info.all_mids()
    spot_result = info.spot_meta_and_asset_ctxs()
    spot_meta, spot_ctxs = spot_result
    
    spot_prices = {pair['name']: float(spot_ctxs[i].get('midPx') or 0) for i, pair in enumerate(spot_meta['universe'])}
    tokens = {t['index']: t for t in spot_meta['tokens']}
    
    mapping = {}
    print(f"{'Ticker':<10} | {'Spot ID':<10} | {'Perp Px':<10} | {'Spot Px':<10} | {'Status'}")
    print("-" * 65)
    
    for pair in spot_meta['universe']:
        token_indices = pair.get('tokens', [])
        if len(token_indices) < 2: continue
        
        base_token = tokens.get(token_indices[0])
        quote_token = tokens.get(token_indices[1])
        if not base_token or not quote_token or quote_token['name'] != 'USDC': continue
        
        ticker = base_token['name']
        market_id = pair['name']
        spot_px = spot_prices.get(market_id, 0)
        
        if spot_px == 0: continue

        # 선물 시장에서 짝꿍 찾기 (가격 기반)
        for perp_sym, perp_px in all_mids.items():
            perp_px = float(perp_px)
            if perp_px == 0: continue
            
            gap = abs(perp_px - spot_px) / spot_px * 100
            
            # 1. 직접 매칭 (이름이 같고 가격이 비슷)
            if ticker == perp_sym and gap < 5.0:
                mapping[perp_sym] = market_id
                print(f"{perp_sym:<10} | {market_id:<10} | {perp_px:<10.4f} | {spot_px:<10.4f} | VERIFIED")
                break
                
            # 2. k-단위 매칭 (이름이 같거나 k가 붙었고, 가격이 1000배 차이)
            if (ticker == perp_sym or f"k{ticker}" == perp_sym) and abs(gap - 99900) < 1000: # 대략 1000배 차이
                # 이 경우는 선물 가격이 현물의 1000배인 경우 (예: kSHIB)
                mapping[perp_sym] = market_id
                print(f"{perp_sym:<10} | {market_id:<10} | {perp_px:<10.4f} | {spot_px:<10.4f} | VERIFIED (k)")
                break

    # 3. 마지막으로 아까 우리가 수동으로 찾았던 예외 케이스(HYPE -> @271 등)가 있는지 가격으로만 전수조사
    for perp_sym, perp_px in all_mids.items():
        if perp_sym in mapping: continue
        perp_px = float(perp_px)
        for market_id, spot_px in spot_prices.items():
            if spot_px == 0: continue
            gap = abs(perp_px - spot_px) / spot_px * 100
            if gap < 0.5: # 이름은 달라도 가격이 0.5% 미만으로 똑같다면? 99% 짝꿍!
                mapping[perp_sym] = market_id
                print(f"{perp_sym:<10} | {market_id:<10} | {perp_px:<10.4f} | {spot_px:<10.4f} | VERIFIED (Price Match)")
                break

    with open("spot_mapping.json", "w") as f:
        json.dump(mapping, f, indent=4)
    
    print(f"\nTotal {len(mapping)} safe mappings saved.")

if __name__ == "__main__":
    asyncio.run(build_safe_mapping())
