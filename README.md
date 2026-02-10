# VOICEVOX OneStepAPI (2026-02-11 Snapshot)

本仓库是 VOICEVOX 一步式 API 服务快照，包含：
- FastAPI 适配层（`/tts`、`/tts_custom` 等）
- 中文拟日语读法（`mode=pseudo_jp`）
- 日语原文直送（`mode=raw`）
- 前端页面、BGM 混音、角色资源缓存
- Cloudflare Tunnel 可对外访问部署方案

## 文档入口
- 详细 API 手册（完整版，推荐先看）：`API_CALL_XINGSHUO.md`
- 通用版说明：`API_CALL.md`

## 当前线上状态
- 服务地址：`https://co2.de5.net`
- 角色列表接口：`GET /voices`
- 调试转换接口：`GET /debug_convert?mode=...&text=...`

## 核心行为说明
- `mode=raw`：原文直接合成（推荐用于日语）
- `mode=pseudo_jp`：中文先拟读再合成（推荐用于中文日式发音）
- 中文优化规则：只控制拟读策略，不自动修改速度/音高/抑扬等参数

## 快速启动（本机）
```bash
cd /Users/macbookm1air8g/voicevox-onestepapi-cn
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## 关键接口
- `GET /voices`：获取角色和 `speaker` 编号
- `POST /tts`：JSON 合成（常用）
- `POST /tts_custom`：自定义 BGM 上传合成
- `GET /check_key?key=...`：Key/额度检查
- `GET /character_info?uuid=...`：角色信息

## 典型调用（JSON）
```bash
curl -sS -X POST 'https://co2.de5.net/tts' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  --data '{
    "text":"中国有句古话，识时务者为俊杰。",
    "speaker":22,
    "mode":"pseudo_jp",
    "speedScale":1.0,
    "pitchScale":0.0,
    "intonationScale":1.0,
    "outputSamplingRate":24000,
    "outputStereo":false,
    "bgmEnabled":false
  }' -o out.wav
```

## 仓库说明
- 本仓库是生产快照，含静态角色资源（`static/`）与默认 BGM（`1.mp3`）。
- 若你做二次开发，请优先阅读 `API_CALL_XINGSHUO.md` 的参数和排障章节。
