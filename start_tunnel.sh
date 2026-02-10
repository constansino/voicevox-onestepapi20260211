#!/bin/bash
# 启动 Quick Tunnel 指向本地 8000 端口
nohup cloudflared tunnel --url http://localhost:8000 > /root/voicevox-adapter/tunnel.log 2>&1 &
echo "Tunnel starting..."
sleep 5
# 提取域名
grep -o 'https://.*\.trycloudflare.com' /root/voicevox-adapter/tunnel.log | head -n 1
