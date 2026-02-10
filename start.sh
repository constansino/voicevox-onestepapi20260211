#!/bin/bash
cd /root/voicevox-onestepapi-cn-en-pseudo-jp-tts
export VOICEVOX_BASE_URL="https://voicevox.kira.de5.net"
# 在本机环境变量中设置真实 Key；此处只提供默认占位，避免泄露
export VOICEVOX_ADAPTER_KEY="${VOICEVOX_ADAPTER_KEY:-public_demo_key}"
nohup python3 main.py > adapter.log 2>&1 &
echo "Voicevox OneStepAPI started on port 8000 with private key"
