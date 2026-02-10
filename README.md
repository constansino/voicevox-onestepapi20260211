# VOICEVOX OneStepAPI (CN/EN/Pseudo-JP TTS)

[English](#english) | [日本語](#japanese) | [中文](#chinese)

---

<a name="english"></a>
## 🇬🇧 English

### Introduction
This is a lightweight middleware server (FastAPI) that acts as a bridge between your application and the **VOICEVOX** engine. It enables VOICEVOX characters (like Zundamon) to read **Chinese** (and English) text by converting it into "Pseudo-Japanese" (Pseudo-Chinese / 偽中国語) pronunciation using Katakana.

### Authentication
All API requests require an API Key passed in the request header.
*   **Header Name**: `X-API-Key`
*   **Value**: `YOUR_API_KEY` (Configured via environment variable on the server)

### API Usage

#### 1. Get Voices
**Endpoint**: `GET /voices`  
**Header**: `X-API-Key: YOUR_API_KEY`

#### 2. Synthesize Speech
**Endpoint**: `POST /tts`  
**Header**: `X-API-Key: YOUR_API_KEY`  
**Request Body (JSON)**:
```json
{
  "text": "Hello world, 你好世界。",
  "speaker": 3,
  "mode": "pseudo_jp",
  "speedScale": 1.1,
  "pitchScale": 0.0,
  "intonationScale": 1.2,
  "volumeScale": 1.0
}
```
**Parameters**:
*   `text` (string, required): The text to be spoken.
*   `speaker` (int, required): The ID of the speaker (get from `/voices`).
*   `mode` (string): `pseudo_jp` (default, converts to Katakana) or `raw` (sends text directly).
*   `speedScale` (float): Speed (0.5 to 2.0).
*   `pitchScale` (float): Pitch (-0.15 to 0.15).
*   `intonationScale` (float): Intonation (0.0 to 2.0).
*   `volumeScale` (float): Volume level.

---

<a name="japanese"></a>
## 🇯🇵 日本語

### 認証
すべてのAPIリクエストには、リクエストヘッダーにAPIキーを含める必要があります。
*   **ヘッダー名**: `X-API-Key`
*   **値**: `YOUR_API_KEY`

### API の使い方

#### 1. 話者リストの取得
**エンドポイント**: `GET /voices`  
**ヘッダー**: `X-API-Key: YOUR_API_KEY`

#### 2. 音声合成
**エンドポイント**: `POST /tts`  
**リクエストボディ (JSON)**:
```json
{
  "text": "こんにちは、你好世界。",
  "speaker": 3,
  "mode": "pseudo_jp",
  "speedScale": 1.1,
  "pitchScale": 0.0,
  "intonationScale": 1.2
}
```

---

<a name="chinese"></a>
## 🇨🇳 中文

### 简介
这是一个为 **VOICEVOX** 引擎设计的轻量级中间件（基于 FastAPI）。它让 Zundamon（ずんだもん）等角色能够通过“伪日语”（Pseudo-Japanese）的方式朗读**中文**。

### 鉴权说明
所有 API 请求均需要在 Header 中携带 API Key。
*   **Header 名称**: `X-API-Key`
*   **默认 Key**: `YOUR_API_KEY` (服务器端通过环境变量配置)

### 接口调用指南

#### 1. 获取音色列表
**接口**: `GET /voices`  
**Header**: `X-API-Key: YOUR_API_KEY`
返回所有可用的角色及其对应的 `speaker_id`。

#### 2. 语音合成接口
**接口**: `POST /tts`  
**Header**: `X-API-Key: YOUR_API_KEY`
**请求体 (JSON)**:
```json
{
  "text": "你好世界，这才是正宗的伪中国语！",
  "speaker": 3,
  "mode": "pseudo_jp",
  "speedScale": 1.1,
  "pitchScale": 0.0,
  "intonationScale": 1.2,
  "volumeScale": 1.0
}
```
**详细参数说明**:
*   `text` (字符串, 必填): 需要合成的文本。
*   `speaker` (整数, 必填): 角色 ID（从 `/voices` 获取）。
*   `mode` (字符串): `pseudo_jp`（默认，开启拟音转换）或 `raw`（不转换）。
*   `speedScale` (浮点数): 语速（建议 0.5 - 2.0）。
*   `pitchScale` (浮点数): 音高（建议 -0.15 - 0.15）。
*   `intonationScale` (浮点数): 语调抑扬（建议 0.0 - 2.0）。
*   `volumeScale` (浮点数): 音量。

**JavaScript 调用示例**:
```javascript
const response = await fetch("https://your-domain.com/tts", {
  method: "POST",
  headers: { 
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY" 
  },
  body: JSON.stringify({
    text: "你好世界",
    speaker: 3
  })
});
const blob = await response.blob();
new Audio(URL.createObjectURL(blob)).play();
```
