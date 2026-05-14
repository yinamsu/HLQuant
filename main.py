import asyncio
import logging
import logging.handlers
import sys
from hyperliquid_api import HyperliquidAPI
from strategy import DeltaNeutralStrategy
from notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler("bot.log", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    ]
)

async def telegram_worker(notifier):
    while True:
        try:
            await notifier.check_commands()
            await asyncio.sleep(0.5)
        except: await asyncio.sleep(5)

async def main():
    IS_TESTNET = False
    IS_REAL_TRADING = True
    
    api = HyperliquidAPI(is_testnet=IS_TESTNET)
    notifier = TelegramNotifier()
    strategy = DeltaNeutralStrategy(api=api, notifier=notifier, is_real_trading=IS_REAL_TRADING)
    notifier.strategy = strategy
    
    await notifier.set_commands()
    await notifier.send_message("🚀 *HLQuant Bot 가동 시작*")
    asyncio.create_task(telegram_worker(notifier))
    
    try:
        while True:
            perp_data = await api.get_all_perp_data()
            spot_data = await api.get_all_spot_data()
            
            if perp_data and spot_data:
                if IS_REAL_TRADING: await strategy.sync_with_exchange()
                await strategy.execute_logic(perp_data, spot_data)
                logging.info(f"Scan Complete. Positions: {len(strategy.positions)}")
            
            await asyncio.sleep(60)
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(main())