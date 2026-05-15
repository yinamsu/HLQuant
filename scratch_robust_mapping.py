import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def build_robust_mapping():
    info = Info(constants.MAINNET_API_URL)
    
    # 1. 선물(Perp) 메타데이터
    perp_meta = info.meta()
    perp_symbols = {asset['name'] for asset in perp_meta['universe']}
    
    # 2. 현물(Spot) 메타데이터
    spot_meta = info.spot_meta()
    tokens = {t['index']: t for t in spot_meta['tokens']}
    
    mapping = {}
    print(f"{'Ticker':<10} | {'Spot Market ID':<15} | {'Note'}")
    print("-" * 45)
    
    for pair in spot_meta['universe']:
        # 현물 마켓의 토큰 인덱스 확인
        token_indices = pair.get('tokens', [])
        if len(token_indices) < 2: continue
        
        base_token = tokens.get(token_indices[0])
        quote_token = tokens.get(token_indices[1])
        
        if not base_token or not quote_token: continue
        
        # USDC 마켓만 거래 (우리의 전략)
        if quote_token['name'] != 'USDC': continue
        
        ticker = base_token['name']
        market_id = pair['name']
        
        # 만약 이 티커가 선물(Perp) 시장에도 존재한다면? -> 우리에겐 훌륭한 타겟!
        if ticker in perp_symbols:
            mapping[ticker] = market_id
            print(f"{ticker:<10} | {market_id:<15} | Verified Match")
        elif f"k{ticker}" in perp_symbols:
            # kSHIB 처럼 1000배 단위 차이가 있는 경우 대응
            mapping[f"k{ticker}"] = market_id
            print(f"k{ticker:<9} | {market_id:<15} | Multiplier Match (k)")
        else:
            # 선물 시장엔 없지만 현물에만 있는 경우
            # mapping[ticker] = market_id
            # print(f"{ticker:<10} | {market_id:<15} | Spot Only")
            pass

    # 3. 자동 생성된 매핑 저장
    with open("spot_mapping_auto.json", "w") as f:
        json.dump(mapping, f, indent=4)
        
    print(f"\n✅ Total {len(mapping)} robust mappings saved to spot_mapping_auto.json")

if __name__ == "__main__":
    asyncio.run(build_robust_mapping())
