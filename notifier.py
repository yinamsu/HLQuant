import aiohttp
import logging
import os
import psutil
import socket
import time
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(override=True)

class TelegramNotifier:
    def __init__(self, strategy=None):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        self.cmd_url = f"https://api.telegram.org/bot{self.token}/setMyCommands"
        self.last_update_id = 0
        self.strategy = strategy
        self.bot_username = "HLQunatbot" # 봇 아이디 (명령어 뒤에 붙는 경우 대비)

    async def set_commands(self):
        if not self.token: return
        commands = [
            {"command": "server", "description": "서버 하드웨어 상태 확인"},
            {"command": "status", "description": "봇 가동 상태 요약"},
            {"command": "balance", "description": "가상 수익률 확인"},
            {"command": "positions", "description": "보유 포지션 상세"},
            {"command": "help", "description": "도움말"}
        ]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.cmd_url, json={"commands": commands}) as resp:
                    if resp.status == 200:
                        logging.info("Telegram commands menu updated.")
        except Exception as e:
            logging.error(f"Error setting commands: {e}")

    async def send_message(self, text):
        if not self.token or not self.chat_id: return
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as resp:
                    if resp.status != 200:
                        logging.error(f"Telegram send fail: {await resp.text()}")
        except Exception as e:
            logging.error(f"Telegram send error: {e}")

    async def send_entry_notification(self, symbol, apy, spot_px, perp_px):
        text = (f"🚀 *[VIRTUAL ENTRY]*\n\n• *Symbol*: {symbol}\n• *APY*: {apy:.2f}%\n"
                f"• *Spot Buy*: {spot_px:.4f}\n• *Perp Sell*: {perp_px:.4f}")
        await self.send_message(text)

    async def send_exit_notification(self, symbol, reason):
        text = f"📉 *[VIRTUAL EXIT]*\n\n• *Symbol*: {symbol}\n• *Reason*: {reason}"
        await self.send_message(text)

    async def get_system_stats(self):
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')
        hostname = socket.gethostname()
        ext_ip = os.getenv("SERVER_IP", "Unknown")
        return (
            f"🚀 *[Alpha Dashboard - HLQ]*\n\n"
            f"🌐 *Network*\n• IP: {ext_ip}\n• Host: {hostname}\n\n"
            f"💻 *Hardware*\n• CPU: {cpu}% {'🟢' if cpu < 70 else '🔴'}\n"
            f"• RAM: {ram.percent}% ({ram.used/1024**3:.1f}G/{ram.total/1024**3:.1f}G)\n"
            f"• SWAP: {swap.percent}% ({swap.used/1024**3:.1f}G/{swap.total/1024**3:.1f}G)\n"
            f"• DISK: {disk.percent}% ({disk.used/1024**3:.1f}G/{disk.total/1024**3:.1f}G)\n\n"
            f"🤖 *Version*: V1.1.0\n⏰ *Time*: {datetime.now().strftime('%H:%M:%S')}"
        )

    async def check_commands(self):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        
        # 1. 초기화 (동작 시작 시 최근 메시지 수집)
        if self.last_update_id == 0:
            params = {"offset": -10} # 최근 10개
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results = data.get("result", [])
                            if results:
                                now = time.time()
                                for update in results:
                                    self.last_update_id = update["update_id"]
                                    msg = update.get("message", {})
                                    # 최근 5분 이내의 메시지만 처리
                                    if now - msg.get("date", 0) < 300:
                                        await self._process_update(update)
                                logging.info(f"Initialized with ID: {self.last_update_id}")
                            else:
                                self.last_update_id = 1
            except Exception as e:
                logging.error(f"Init check fail: {e}")
            return

        # 2. 정기 폴링 (Long Polling)
        params = {"offset": self.last_update_id + 1, "timeout": 30}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            await self._process_update(update)
        except Exception as e:
            logging.error(f"Polling error: {e}")

    async def _process_update(self, update):
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = msg.get("chat", {}).get("id")
        
        if not text or chat_id is None: return

        # 보안 확인
        if str(chat_id) != str(self.chat_id):
            logging.warning(f"Access Denied: Got {chat_id}, Need {self.chat_id}")
            return

        # 명령어 정규화 (/status@BotName -> /status)
        cmd = text.split('@')[0].lower()
        logging.info(f"Processing command: {cmd}")

        try:
            if cmd == "/server":
                await self.send_message(await self.get_system_stats())
            elif cmd == "/status":
                await self.send_message(self.strategy.get_status_summary() if self.strategy else "전략 연결 안됨")
            elif cmd == "/positions":
                await self.send_message(self.strategy.get_positions_summary() if self.strategy else "전략 연결 안됨")
            elif cmd == "/balance":
                await self.send_message(self.strategy.get_balance_summary() if self.strategy else "전략 연결 안됨")
            elif cmd == "/help":
                await self.send_message("명령어: /server, /status, /positions, /balance, /help")
            elif cmd == "/start":
                await self.send_message("HLQuant 봇 시작! /help를 입력하세요.")
        except Exception as e:
            logging.error(f"Command execution error ({cmd}): {e}")
            await self.send_message(f"⚠️ 명령어 처리 중 오류 발생: {e}")
