import asyncio
import os
from hyperliquid_api import HyperliquidAPI
from strategy import DeltaNeutralStrategy
from notifier import TelegramNotifier
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api = HyperliquidAPI(is_testnet=False)
    strategy = DeltaNeutralStrategy(api=api)
    
    print("--- [Account Status Check] ---")
    # 1. 가용 USDC 잔고
    balance = await api.get_balance()
    print(f"Available USDC: ${balance:.2f}")
    
    # 2. 선물 포지션
    perp_data = await api.info.user_state(api.wallet_address)
    print("\n[Perp Positions]")
    for pos in perp_data.get('assetPositions', []):
        p = pos['position']
        if float(p['szi']) != 0:
            print(f"Symbol: {p['coin']} | Size: {p['szi']} | Value: ${float(p['szi']) * float(p['entryPx']):.2f}")
            
    # 3. 현물 잔고
    spot_data = await api.info.spot_user_state(api.wallet_address)
    print("\n[Spot Balances]")
    for bal in spot_data.get('balances', []):
        if float(bal['total']) > 0:
            print(f"Coin: {bal['coin']} | Total: {bal['total']}")

    print("\n--- [Log Check] ---")
    log_path = "bot.log"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print("Last 10 lines of bot.log:")
            for line in lines[-10:]:
                print(line.strip())
    else:
        print("Log file not found.")

    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
