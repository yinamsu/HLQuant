
import asyncio
import os
import json
from hyperliquid_api import HyperliquidAPI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    
    print("--- 1. Perpetual Positions ---")
    user_state = await api.get_user_state()
    asset_positions = user_state.get('assetPositions', [])
    for pos in asset_positions:
        p = pos['position']
        print(f"Symbol: {p['coin']}, Size: {p['szi']}, EntryPx: {p['entryPx']}, PnL: {p['unrealizedPnl']}")

    print("\n--- 2. Spot Balances ---")
    spot_state = api.info.spot_user_state(api.wallet_address)
    balances = spot_state.get('balances', [])
    for b in balances:
        if float(b.get('total', 0)) > 0:
            print(f"Token: {b['coin']}, Total: {b['total']}, EntryPx: {b.get('entryPx', 'N/A')}")

    print("\n--- 3. Asset Indices (Mainnet) ---")
    # Perp Meta
    perp_meta, _ = api.info.meta_and_asset_ctxs()
    for i, u in enumerate(perp_meta['universe']):
        if u['name'] in ['LINK', 'AVAX', 'BNB', 'BTC', 'ETH']:
            print(f"[Perp] {u['name']} -> Index: {i}, szDecimals: {u['szDecimals']}")

    # Spot Meta
    spot_meta, _ = api.info.spot_meta_and_asset_ctxs()
    tokens = spot_meta['tokens']
    universe = spot_meta['universe']
    token_map = {t['index']: t for t in tokens}
    
    for i, u in enumerate(universe):
        token_indices = u['tokens']
        t0 = token_map.get(token_indices[0])
        t1 = token_map.get(token_indices[1])
        if t0['name'] in ['AVAX', 'AVAX0', 'LINK', 'BNB', 'BTC', 'ETH', 'PURR']:
            print(f"[Spot] Pair: {u['name']} (Index: {i}) -> Base: {t0['name']} (szDec: {t0['szDecimals']}), Quote: {t1['name']}")

if __name__ == "__main__":
    asyncio.run(main())
