# VOICEVOX API 调用手册（已同步）

> 这份文档已与当前线上行为同步（`https://co2.de5.net`）。

## 1. 基础信息
- 基础地址：`https://YOUR_DOMAIN`
- 鉴权头：`X-API-Key: YOUR_API_KEY`
- 角色与声线编号：以 `GET /voices` 实时返回为准

## 2. 核心接口
- `GET /voices`：获取全量角色/声线/speaker 编号
- `GET /check_key?key=...`：检查 key 可用性与额度
- `POST /tts`：JSON 合成
- `POST /tts_custom`：表单合成（支持上传自定义 BGM）
- `GET /debug_convert?mode=...&text=...`：查看“原文 -> 拟读”结果

## 3. `mode` 参数说明（重点）
- `mode=pseudo_jp`：启用中文拟日语读法（中文场景用）
- `mode=raw`：原文直送引擎（日文场景推荐）

说明：
- 当前前端在检测到日文假名时会自动走 `raw`，以贴近原版 VOICEVOX 网页听感。

## 4. 中文优化规则（已更新）
- 中文优化 **只做拟读策略**（`pseudo_jp`）
- **不会** 自动改这些参数：
  - `speedScale`
  - `pitchScale`
  - `intonationScale`
  - `volumeScale`
  - `prePhonemeLength`
  - `postPhonemeLength`

## 5. 标准 JSON 调用示例（/tts）
```bash
curl -sS -X POST 'https://YOUR_DOMAIN/tts' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  --data '{
    "text": "中国有句古话，识时务者为俊杰。",
    "speaker": 22,
    "mode": "pseudo_jp",
    "speedScale": 1.0,
    "pitchScale": 0.0,
    "intonationScale": 1.0,
    "volumeScale": 1.0,
    "prePhonemeLength": 0.1,
    "postPhonemeLength": 0.1,
    "outputSamplingRate": 24000,
    "outputStereo": false,
    "kana": "",
    "bgmEnabled": false,
    "bgmVolume": 0.35
  }' \
  -o out.wav
```

## 6. 自定义 BGM 调用示例（/tts_custom）
```bash
curl -sS -X POST 'https://YOUR_DOMAIN/tts_custom' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -F 'text=中国有句古话，识时务者为俊杰。' \
  -F 'speaker=22' \
  -F 'mode=pseudo_jp' \
  -F 'speedScale=1.0' \
  -F 'pitchScale=0.0' \
  -F 'intonationScale=1.0' \
  -F 'volumeScale=1.0' \
  -F 'prePhonemeLength=0.1' \
  -F 'postPhonemeLength=0.1' \
  -F 'outputSamplingRate=24000' \
  -F 'outputStereo=false' \
  -F 'kana=' \
  -F 'bgmEnabled=true' \
  -F 'bgmVolume=0.35' \
  -F 'bgmFile=@/absolute/path/to/your_bgm.mp3' \
  -o out_custom_bgm.wav
```

## 7. 日语对齐原版网页的推荐参数
用于和官方/网页默认听感更接近：
- `mode=raw`
- `speedScale=1.0`
- `pitchScale=0.0`
- `intonationScale=1.0`
- `outputSamplingRate=24000`
- `outputStereo=false`
- `bgmEnabled=false`

## 8. 快速查询声线编号
```bash
# 全量
curl -sS 'https://YOUR_DOMAIN/voices' | jq

# 仅看俊达萌
curl -sS 'https://YOUR_DOMAIN/voices' | jq '.[] | select(.name=="俊达萌")'

# 导出 角色-声线-speaker
curl -sS 'https://YOUR_DOMAIN/voices' | jq -r '.[] as $c | $c.styles[] | [$c.name, .name, .id] | @tsv'
```

## 9. 常见问题
- 听感和其它站点不一致：先统一 `mode` 和默认参数再对比。
- 中文“一个字一个字读”：避免强制逐音节分隔；当前已修复为自然连续读法。
- 同句前后语速不一致：不要把普通逗号文本拆成多段；当前默认整句一次合成。
