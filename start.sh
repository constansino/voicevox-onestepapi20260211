#!/bin/bash
cd /root/voicevox-onestepapi-cn-en-pseudo-jp-tts
export VOICEVOX_BASE_URL="https://voicevox.kira.de5.net"
# 在这里设置真实的鉴权 Key，不会被推送到 Git
export VOICEVOX_ADAPTER_KEY="xingshuo"
nohup python3 main.py > adapter.log 2>&1 &
echo "Voicevox OneStepAPI started on port 8000 with private key"
