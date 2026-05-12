import aiohttp
import logging
import os
import psutil
import socket
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드 (시스템 환경 변수가 있더라도 .env 내용을 우선 적용)
load_dotenv(override=True)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        self.cmd_url = f"https://api.telegram.org/bot{self.token}/setMyCommands"
        self.last_update_id = 0

    async def set_commands(self):
        if not self.token: return
        
        commands = [
            {"command": "server", "description": "서버 하드웨어 상태 확인"},
            {"command": "status", "description": "현재 봇 상태 및 시장 요약"},
            {"command": "balance", "description": "가상 장부 수익률 확인"},
            {"command": "positions", "description": "현재 보유 포지션 확인"},
            {"command": "help", "description": "명령어 도움말"}
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.cmd_url, json={"commands": commands}) as response:
                    if response.status == 200:
                        logging.info("Telegram commands menu set successfully")
                    else:
                        logging.error(f"Failed to set Telegram commands: {await response.text()}")
        except Exception as e:
            logging.error(f"Error setting Telegram commands: {e}")

    async def send_message(self, text):
        if not self.token or not self.chat_id:
            logging.warning("Telegram token or chat_id is missing in .env")
            return

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send Telegram message: {await response.text()}")
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")

    async def send_entry_notification(self, symbol, apy, spot_px, perp_px):
        text = (
            f"🚀 *[VIRTUAL ENTRY]*\n\n"
            f"• *Symbol*: {symbol}\n"
            f"• *APY*: {apy:.2f}%\n"
            f"• *Spot Buy*: {spot_px:.4f}\n"
            f"• *Perp Sell*: {perp_px:.4f}\n"
            f"• *Time*: {logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', None, None))}"
        )
        await self.send_message(text)

    async def send_exit_notification(self, symbol, reason):
        text = (
            f"📉 *[VIRTUAL EXIT]*\n\n"
            f"• *Symbol*: {symbol}\n"
            f"• *Reason*: {reason}\n"
        )
        await self.send_message(text)

    async def get_system_stats(self):
        """서버 리소스 상태를 텍스트로 반환"""
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')
        
        hostname = socket.gethostname()
        
        external_ip = os.getenv("SERVER_IP", "Unknown")
        text = (
            f"🚀 *[Alpha Professional Dashboard - HLQ]*\n\n"
            f"🌐 *Network & Info*\n"
            f"• External IP: {external_ip}\n"
            f"• Host: {hostname}\n\n"
            f"💻 *Hardware Stats*\n"
            f"• CPU Usage: {cpu_usage}% {'🟢' if cpu_usage < 70 else '🔴'}\n"
            f"• RAM Usage: {ram.percent}% ({ram.used/1024**3:.1f}G/{ram.total/1024**3:.1f}G)\n"
            f"• SWAP Usage: {swap.percent}% ({swap.used/1024**3:.1f}G/{swap.total/1024**3:.1f}G)\n"
            f"• DISK Usage: {disk.percent}% ({disk.used/1024**3:.1f}G/{disk.total/1024**3:.1f}G)\n\n"
            f"🤖 *Bot Version*: V1.0.0 [HLQuant]\n"
            f"⏰ *Server Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return text

    async def check_commands(self):
        """텔레그램 메시지를 확인하고 명령어가 있으면 응답"""
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        
        # 처음 실행 시, 현재 시점 이후의 메시지만 가져오도록 설정
        if self.last_update_id == 0:
            params = {"offset": -1}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("result"):
                                # 가장 최근 메시지 ID + 1로 설정하여 그 이후 메시지만 받음
                                self.last_update_id = data["result"][0]["update_id"]
                                logging.info(f"Telegram listener initialized. Starting from ID: {self.last_update_id}")
                            else:
                                # 메시지가 하나도 없는 경우 (새 봇)
                                self.last_update_id = 1
            except Exception as e:
                logging.error(f"Error initializing Telegram listener: {e}")
            return

        params = {"offset": self.last_update_id + 1, "timeout": 1} # 롱 폴링 흉내
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            msg = update.get("message", {})
                            text = msg.get("text", "").strip()
                            chat_id = msg.get("chat", {}).get("id")
                            
                            # 보낸 사람이 나인지 확인 (보안)
                            if str(chat_id) != str(self.chat_id):
                                logging.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
                                continue

                            logging.info(f"Command received: {text}")

                            if text == "/server":
                                stats = await self.get_system_stats()
                                await self.send_message(stats)
                            elif text == "/help":
                                await self.send_message("사용 가능한 명령어:\n/server - 서버 상태 확인")
                            elif text == "/start":
                                await self.send_message("HLQuant 봇이 준비되었습니다. /server 명령어를 입력해보세요.")
        except Exception as e:
            logging.error(f"Error checking Telegram commands: {e}")
