import asyncio
import json
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def update_mappings():
    info = Info(constants.MAINNET_API_URL)
    
    # 1. 선물 종목 리스트 (Perp)
    meta = info.meta()
    perp_symbols = {asset['name'] for asset in meta['universe']}
    
    # 2. 현물 종목 리스트 (Spot)
    spot_meta = info.spot_meta()
    token_map = {t['index']: t for t in spot_meta['tokens']}
    
    mapping = {}
    for pair in spot_meta['universe']:
        tokens = pair.get('tokens', [])
        if not tokens: continue
        
        base_token = token_map.get(tokens[0])
        quote_token = token_map.get(tokens[1])
        
        if not base_token or not quote_token: continue
        
        # USDC 마켓만 취급
        if quote_token['name'] != 'USDC': continue
        
        symbol = base_token['name']
        pair_name = pair['name']
        
        # 선물이 존재하는 종목만 추가
        if symbol in perp_symbols:
            mapping[symbol] = pair_name
            print(f"Found Match: {symbol} -> {pair_name}")

    # 3. 파일 저장
    with open("spot_mapping.json", "w") as f:
        json.dump(mapping, f, indent=4)
    
    print(f"\nDone: Total {len(mapping)} pairs mapped to spot_mapping.json")

if __name__ == "__main__":
    asyncio.run(update_mappings())
