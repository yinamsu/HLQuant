@echo off
ssh -i deploy_key -o StrictHostKeyChecking=no yinamsu@34.136.45.224 "tail -n 50 ~/HLQuant/bot.log"
