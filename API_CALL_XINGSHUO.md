# VOICEVOX OneStepAPI 调用手册（完整版）

> 更新时间：2026-02-11 06:16:54（基于当前服务实时接口）

## 1. 服务信息
- 线上地址：`https://co2.de5.net`
- 鉴权方式：请求头 `X-API-Key: YOUR_API_KEY`
- API 风格：REST + WAV 二进制返回
- 文档目标：给第三方直接接入，减少试错成本

## 2. 你必须先理解的 3 个关键点
1. `speaker` 是最终音色开关，必须从 `/voices` 实时获取，不能写死猜测。
2. `mode=raw` 与 `mode=pseudo_jp` 会明显影响听感。
3. 中文优化当前只控制“拟读策略”，不会改速度、音高、抑扬等参数。

## 3. 接口清单
| 方法 | 路径 | 用途 | 鉴权 |
|---|---|---|---|
| `GET` | `/voices` | 角色+声线+speaker 编号 | 否 |
| `GET` | `/character_info?uuid=...` | 角色头像/试听信息 | 否 |
| `GET` | `/public_config` | 前端默认公开配置 | 否 |
| `GET` | `/check_key?key=...` | 检查 key 与额度 | 否 |
| `POST` | `/tts` | JSON 合成（常用） | 是 |
| `POST` | `/tts_custom` | multipart 合成（支持上传 BGM） | 是 |
| `GET` | `/debug_convert?mode=...&text=...` | 查看文本转换结果（调试） | 否 |

## 4. `mode` 参数（核心）
- `mode=raw`：原文直接送入引擎，适合日语文本。
- `mode=pseudo_jp`：中文先做拟日语转换再合成，适合中文“日式发音”场景。
- 前端策略：检测到日文假名时自动优先 `raw`。

## 5. 参数总表（`/tts` 与 `/tts_custom`共通）
| 参数 | 类型 | 说明 | 推荐范围/值 |
|---|---|---|---|
| `text` | `string` | 待合成文本 | 必填 |
| `speaker` | `int` | 声线编号 | 来自 `/voices` |
| `mode` | `string` | `raw` / `pseudo_jp` | 日语`raw`，中文`pseudo_jp` |
| `speedScale` | `float` | 语速 | `0.8 ~ 1.4` |
| `pitchScale` | `float` | 音高 | `-0.15 ~ 0.15` |
| `intonationScale` | `float` | 抑扬 | `0.8 ~ 1.3` |
| `volumeScale` | `float` | 人声音量 | `0.8 ~ 1.4` |
| `prePhonemeLength` | `float` | 前静音 | `0.0 ~ 0.3` |
| `postPhonemeLength` | `float` | 后静音 | `0.0 ~ 0.3` |
| `outputSamplingRate` | `int` | 采样率 | `24000` 或 `48000` |
| `outputStereo` | `bool` | 是否立体声 | `false/true` |
| `kana` | `string` | 可选读音覆盖 | 通常留空 |
| `bgmEnabled` | `bool` | 开关 BGM | `false/true` |
| `bgmVolume` | `float` | BGM 音量 | `0.2 ~ 0.45` |

## 6. 中文优化规则（最新）
- 中文优化只影响“文本是否走拟读转换”，不再改任何合成参数。
- 不会自动修改：`speedScale`、`pitchScale`、`intonationScale`、`volumeScale`、`prePhonemeLength`、`postPhonemeLength`。

## 7. 推荐预设模板
### 7.1 日语对齐官方网页听感
- `mode=raw`
- `speedScale=1.0`
- `pitchScale=0.0`
- `intonationScale=1.0`
- `outputSamplingRate=24000`
- `outputStereo=false`
- `bgmEnabled=false`

### 7.2 中文拟读（日式发音）
- `mode=pseudo_jp`
- 其他参数按业务需求保持不变（建议先从 1.0 基准开始）

## 8. 调用示例
### 8.1 `/tts`（JSON）
```bash
curl -sS -X POST 'https://co2.de5.net/tts' \
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

### 8.2 `/tts_custom`（上传自定义 BGM）
```bash
curl -sS -X POST 'https://co2.de5.net/tts_custom' \
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

### 8.3 Python 示例
```python
import requests
url = "https://co2.de5.net/tts"
headers = {"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"}
payload = {
    "text": "これはテストです。",
    "speaker": 3,
    "mode": "raw",
    "speedScale": 1.0,
    "pitchScale": 0.0,
    "intonationScale": 1.0,
    "volumeScale": 1.0,
    "prePhonemeLength": 0.1,
    "postPhonemeLength": 0.1,
    "outputSamplingRate": 24000,
    "outputStereo": False,
    "bgmEnabled": False,
}
r = requests.post(url, headers=headers, json=payload, timeout=120)
r.raise_for_status()
open("out.wav", "wb").write(r.content)
print("saved out.wav")
```

## 9. 调试接口
```bash
curl -sS 'https://co2.de5.net/debug_convert?mode=pseudo_jp&text=中国有句古话，识时务者为俊杰'
```
用途：先看文本转换结果，再决定是否改词典或改 `mode`。

## 10. 错误码与排障
| 状态码 | 常见原因 | 处理建议 |
|---|---|---|
| `401` | API Key 错误或无额度 | 校验 `X-API-Key` |
| `402` | 用户余额不足 | 充值/更换 key |
| `404` | 路径错误或静态资源不存在 | 校验 URL / UUID |
| `5xx` | 引擎瞬时异常或后端故障 | 退避重试 + 看日志 |

## 11. 性能与稳定性建议
- 尽量避免超长单句，长文建议按自然语义分句。
- 批量任务建议并发控制，避免把引擎打满。
- 日语文本优先 `raw`，中文拟读再用 `pseudo_jp`。
- 对外接口调用建议设置超时（例如 60~120 秒）。

## 12. 俊达萌（ずんだもん）常用声线
- 标准：`speaker=3`
- 低语：`speaker=22`
- 悄悄话：`speaker=38`
- 筋疲力尽：`speaker=75`
- 含泪：`speaker=76`

## 13. 全量角色-声线编号（实时）

### 四国美谈（四国めたん）
- UUID：`7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `2` |
| 甜甜 | あまあま | `0` |
| 傲娇 | ツンツン | `6` |
| 性感 | セクシー | `4` |
| 低语 | ささやき | `36` |
| 悄悄话 | ヒソヒソ | `37` |

### 俊达萌（ずんだもん）
- UUID：`388f246b-8c41-4ac1-8e2d-5d79f3ff56d9`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `3` |
| 甜甜 | あまあま | `1` |
| 傲娇 | ツンツン | `7` |
| 性感 | セクシー | `5` |
| 低语 | ささやき | `22` |
| 悄悄话 | ヒソヒソ | `38` |
| 筋疲力尽 | ヘロヘロ | `75` |
| 含泪 | なみだめ | `76` |

### 春日部紬（春日部つむぎ）
- UUID：`35b2c544-660e-401e-b503-0e14c635303a`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `8` |

### 雨晴羽（雨晴はう）
- UUID：`3474ee95-c274-47f9-aa1a-8322163d96f1`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `10` |

### 波音律（波音リツ）
- UUID：`b1a81618-b27b-40d2-b0ea-27a9ad408c4b`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `9` |
| クイーン | クイーン | `65` |

### 玄野武宏（玄野武宏）
- UUID：`c30dc15a-0992-4f8d-8bb8-ad3b314e6a6f`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `11` |
| 喜悦 | 喜び | `39` |
| 暴走 | ツンギレ | `40` |
| 悲伤 | 悲しみ | `41` |

### 白上虎太郎（白上虎太郎）
- UUID：`e5020595-5c5d-4e87-b849-270a518d0dcf`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 普通 | ふつう | `12` |
| 开心 | わーい | `32` |
| 害怕 | びくびく | `33` |
| 生气 | おこ | `34` |
| 哭泣 | びえーん | `35` |

### 青山龙星（青山龍星）
- UUID：`4f51116a-d9ee-4516-925d-21f183e2afad`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `13` |
| 热血 | 熱血 | `81` |
| 不爽 | 不機嫌 | `82` |
| 喜悦 | 喜び | `83` |
| 湿润 | しっとり | `84` |
| かなしみ | かなしみ | `85` |
| 私语 | 囁き | `86` |

### 冥鸣向日葵（冥鳴ひまり）
- UUID：`8eaad775-3119-417e-8cf4-2a10bfd592c8`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `14` |

### 九州空（九州そら）
- UUID：`481fb609-6446-4870-9f46-90c4dd623403`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `16` |
| 甜甜 | あまあま | `15` |
| 傲娇 | ツンツン | `18` |
| 性感 | セクシー | `17` |
| 低语 | ささやき | `19` |

### 饼子小姐（もち子さん）
- UUID：`9f3ee141-26ad-437e-97bd-d22298d02ad2`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `20` |
| セクシー／あん子 | セクシー／あん子 | `66` |
| 泣き | 泣き | `77` |
| 愤怒 | 怒り | `78` |
| 喜悦 | 喜び | `79` |
| 悠哉 | のんびり | `80` |

### 剑崎雌雄（剣崎雌雄）
- UUID：`1a17ca16-7ee5-4ea5-b191-2f02ace24d21`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `21` |

### WhiteCUL（WhiteCUL）
- UUID：`67d5d8da-acd7-4207-bb10-b5542d3a663b`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `23` |
| 快乐 | たのしい | `24` |
| 难过 | かなしい | `25` |
| 哭泣 | びえーん | `26` |

### 后鬼（後鬼）
- UUID：`0f56c2f2-644c-49c9-8989-94e11f7129d0`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 人間ver. | 人間ver. | `27` |
| ぬいぐるみver. | ぬいぐるみver. | `28` |
| 人間（怒り）ver. | 人間（怒り）ver. | `87` |
| 鬼ver. | 鬼ver. | `88` |

### No.7（No.7）
- UUID：`044830d2-f23b-44d6-ac0d-b5d733caa900`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `29` |
| 广播风 | アナウンス | `30` |
| 讲故事 | 読み聞かせ | `31` |

### 智备爷爷（ちび式じい）
- UUID：`468b8e94-9da4-4f7a-8715-a22a48844f9e`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `42` |

### 樱歌美子（櫻歌ミコ）
- UUID：`0693554c-338e-4790-8982-b9c6d476dc69`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `43` |
| 第二形态 | 第二形態 | `44` |
| 萝莉 | ロリ | `45` |

### 小夜/SAYO（小夜/SAYO）
- UUID：`a8cc6d22-aad0-4ab8-bf1e-2f843924164a`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `46` |

### 护士机器人Type-T（ナースロボ＿タイプＴ）
- UUID：`882a636f-3bac-431a-966d-c5e6bba9f949`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `47` |
| 乐呵呵 | 楽々 | `48` |
| 恐怖 | 恐怖 | `49` |
| 内緒話 | 内緒話 | `50` |

### †圣骑士 红樱†（†聖騎士 紅桜†）
- UUID：`471e39d2-fb11-4c8c-8d89-4b322d2498e0`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `51` |

### 雀松朱司（雀松朱司）
- UUID：`0acebdee-a4a5-4e12-a695-e19609728e30`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `52` |

### 麒岛宗麟（麒ヶ島宗麟）
- UUID：`7d1e7ba7-f957-40e5-a3fc-da49f769ab65`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `53` |

### 春歌七七（春歌ナナ）
- UUID：`ba5d2428-f7e0-4c20-ac41-9dd56e9178b4`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `54` |

### 猫使阿露（猫使アル）
- UUID：`00a5c10c-d3bd-459f-83fd-43180b521a44`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `55` |
| 沉稳 | おちつき | `56` |
| 雀跃 | うきうき | `57` |

### 猫使薇（猫使ビィ）
- UUID：`c20a2254-0349-4470-9fc8-e5c0f8cf3404`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `58` |
| 沉稳 | おちつき | `59` |
| 怕生 | 人見知り | `60` |

### 中国兔（中国うさぎ）
- UUID：`1f18ffc3-47ea-4ce0-9829-0576d03a7ec8`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `61` |
| 惊讶 | おどろき | `62` |
| 胆小 | こわがり | `63` |
| へろへろ | へろへろ | `64` |

### 栗田栗子（栗田まろん）
- UUID：`04dbd989-32d0-40b4-9e71-17c920f2a8a9`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `67` |

### IL-Tan（あいえるたん）
- UUID：`dda44ade-5f9c-4a3a-9d2c-2a976c7476d9`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `68` |

### 満別花丸（満別花丸）
- UUID：`287aa49f-e56b-4530-a469-855776c84a8d`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `69` |
| 元气 | 元気 | `70` |
| 低语 | ささやき | `71` |
| 装可爱 | ぶりっ子 | `72` |
| 少年 | ボーイ | `73` |

### 琴咏妮娅（琴詠ニア）
- UUID：`97a4af4b-086e-4efd-b125-7ae2da85e697`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `74` |

### Voidoll（Voidoll）
- UUID：`0ebe2c7d-96f3-4f0e-a2e3-ae13fe27c403`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `89` |

### 僵尸子（ぞん子）
- UUID：`0156da66-4300-474a-a398-49eb2e8dd853`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `90` |
| 低血压 | 低血圧 | `91` |
| 觉醒 | 覚醒 | `92` |
| 实况风 | 実況風 | `93` |

### 中部剑（中部つるぎ）
- UUID：`4614a7de-9829-465d-9791-97eb8a5f9b86`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `94` |
| 愤怒 | 怒り | `95` |
| 悄悄话 | ヒソヒソ | `96` |
| 战战兢兢 | おどおど | `97` |
| 絶望と敗北 | 絶望と敗北 | `98` |

### 離途（離途）
- UUID：`3b91e034-e028-4acb-a08d-fbdcd207ea63`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `99` |

### 黒沢冴白（黒沢冴白）
- UUID：`0b466290-f9b6-4718-8d37-6c0c81e824ac`
| 声线名 | 原名 | speaker |
|---|---|---:|
| 标准 | ノーマル | `100` |

## 14. 快速导出编号表（给第三方）
```bash
curl -sS 'https://co2.de5.net/voices' | jq -r '.[] as $c | $c.styles[] | [$c.uuid,$c.name,.name,.id] | @csv' > vox_list.csv
```

## 15. 变更记录（本轮）
- 中文优化不再改速度/音高/抑扬，只控制拟读策略。
- 新增 `mode` 明确语义与推荐使用场景。
- 新增日语对齐官方网页的参数模板。
- 新增 `/debug_convert` 调试说明。
- 同步了当前服务的全量角色声线表。