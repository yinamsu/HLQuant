import asyncio
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def find_clean_names():
    info = Info(constants.MAINNET_API_URL)
    spot_meta = info.spot_meta()
    tokens = {t['index']: t for t in spot_meta['tokens']}
    
    targets = ["BTC", "ETH", "SOL", "HYPE", "PURR"]
    mapping = {}
    
    for pair in spot_meta['universe']:
        indices = pair.get('tokens', [])
        if len(indices) < 2: continue
        base = tokens.get(indices[0])
        quote = tokens.get(indices[1])
        
        if base and quote and quote['name'] == 'USDC':
            if base['name'] in targets:
                mapping[base['name']] = pair['name']
                print(f"Found: {base['name']} -> {pair['name']}")

if __name__ == "__main__":
    asyncio.run(find_clean_names())
