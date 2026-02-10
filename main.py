import os
import re
import json
import logging
import requests
import uuid
import subprocess
import tempfile
import hashlib
import secrets
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Header, Depends, Request, File, UploadFile, Form
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypinyin import pinyin, Style
from sqlalchemy import Column, String, Integer, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- 汉化字典 ---
CN_NAME_MAP = {
    "四国めたん": "四国美谈",
    "ずんだもん": "俊达萌",
    "春日部つむぎ": "春日部紬",
    "雨晴はう": "雨晴羽",
    "波音リツ": "波音律",
    "玄野武宏": "玄野武宏",
    "白上虎太郎": "白上虎太郎",
    "青山龍星": "青山龙星",
    "冥鳴ひまり": "冥鸣向日葵",
    "九州そら": "九州空",
    "もち子さん": "饼子小姐",
    "剣崎雌雄": "剑崎雌雄",
    "WhiteCUL": "WhiteCUL",
    "後鬼": "后鬼",
    "No.7": "No.7",
    "ちび式じい": "智备爷爷",
    "櫻歌ミコ": "樱歌美子",
    "小夜/SAYO": "小夜/SAYO",
    "ナースロボ＿タイプＴ": "护士机器人Type-T",
    "†聖騎士 紅桜†": "†圣骑士 红樱†",
    "雀松朱司": "雀松朱司",
    "麒ヶ島宗麟": "麒岛宗麟",
    "春歌ナナ": "春歌七七",
    "猫使アル": "猫使阿露",
    "猫使ビィ": "猫使薇",
    "中国うさぎ": "中国兔",
    "栗田まろん": "栗田栗子",
    "あいえるたん": "IL-Tan",
    "满别花丸": "满别花丸",
    "琴詠ニア": "琴咏妮娅",
    "Voidoll": "Voidoll",
    "ぞん子": "僵尸子",
    "中部つるぎ": "中部剑"
}

CN_STYLE_MAP = {
    "ノーマル": "标准", "あまあま": "甜甜", "ツンツン": "傲娇", "セクシー": "性感",
    "ささやき": "低语", "ヒソヒソ": "悄悄话", "喜び": "喜悦", "悲しみ": "悲伤",
    "怒り": "愤怒", "のんびり": "悠哉", "熱血": "热血", "不機嫌": "不爽",
    "囁き": "私语", "たのしい": "快乐", "かなしい": "难过", "びえーん": "哭泣",
    "おこ": "生气", "びくびく": "害怕", "ヘロヘロ": "筋疲力尽", "なみだめ": "含泪",
    "ツンギレ": "暴走", "しっとり": "湿润", "ふつう": "普通", "わーい": "开心",
    "読み聞かせ": "讲故事", "アナウンス": "广播风", "第二形態": "第二形态",
    "ロリ": "萝莉", "楽々": "乐呵呵", "恐怖": "恐怖", "内緒话": "秘密话",
    "おちつき": "沉稳", "うきうき": "雀跃", "人見知り": "怕生", "おどろき": "惊讶",
    "こわがり": "胆小", "元気": "元气", "ぶりっ子": "装可爱", "ボーイ": "少年",
    "低血圧": "低血压", "覚醒": "觉醒", "実況風": "实况风", "おどおど": "战战兢兢"
}

# --- 数据库配置 ---
DB_URL = "sqlite:///./tts_management.db"
Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

class APIKeyRecord(Base):
    __tablename__ = "api_keys"
    key = Column(String, primary_key=True, index=True)
    credits = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    salt = Column(String)
    api_key = Column(String, unique=True, index=True)
    balance = Column(Integer, default=300) # Default trial: 300 chars
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    out_trade_no = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Integer) # In cents (fen)
    status = Column(String, default="PENDING") # PENDING, SUCCESS, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

def hash_password(password: str, salt: str = None) -> (str, str):
    if not salt:
        salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest(), salt

def verify_password(stored_password: str, stored_salt: str, provided_password: str) -> bool:
    return stored_password == hashlib.sha256((provided_password + stored_salt).encode()).hexdigest()

Base.metadata.create_all(bind=engine)

# --- 配置 ---
VOICEVOX_URL = os.getenv("VOICEVOX_BASE_URL", "https://voicevox.kira.de5.net").rstrip("/")
ADMIN_KEY = "xingshuo_admin"
BGM_FILE = "/data/voicevox/1.mp3"

# --- Translations ---
TRANSLATIONS = {}
try:
    with open("/root/voicevox_translations.json", "r", encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    logging.error(f"Failed to load translations: {e}")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"])
app.mount("/static", StaticFiles(directory="/data/voicevox/webui"), name="static")

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class RechargeRequest(BaseModel):
    username: str
    amount_cny: int
    admin_secret: str

@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    pwd_hash, salt = hash_password(user.password)
    api_key = "vv-" + secrets.token_urlsafe(16)
    new_user = User(username=user.username, password_hash=pwd_hash, salt=salt, api_key=api_key)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Registration successful", "api_key": api_key, "balance": new_user.balance}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(db_user.password_hash, db_user.salt, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"api_key": db_user.api_key, "balance": db_user.balance, "username": db_user.username}

@app.post("/recharge")
def recharge(req: RechargeRequest, db: Session = Depends(get_db)):
    if req.admin_secret != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    credits_to_add = req.amount_cny * 1000
    user.balance += credits_to_add
    db.commit()
    return {"message": "Recharge successful", "new_balance": user.balance}

@app.get("/check_key")
def check_key(key: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == key).first()
    if user: return {"credits": user.balance, "type": "user", "username": user.username}
    record = db.query(APIKeyRecord).filter(APIKeyRecord.key == key).first()
    if not record: raise HTTPException(status_code=404, detail="Key not found")
    return {"credits": record.credits, "type": "legacy"}

# --- 缓存 ---
SPEAKER_STYLE_MAP = {} # { uuid: { name: id } }
STYLE_ID_TO_UUID = {} # { id: uuid }

def refresh_speaker_cache():
    global SPEAKER_STYLE_MAP, STYLE_ID_TO_UUID
    try:
        speakers = requests.get(f"{VOICEVOX_URL}/speakers", verify=False).json()
        for spk in speakers:
            uuid = spk["speaker_uuid"]
            styles = {}
            for st in spk["styles"]:
                s_name = st["name"]
                cn_name = CN_STYLE_MAP.get(s_name, s_name)
                styles[s_name] = st["id"]
                styles[cn_name] = st["id"]
                STYLE_ID_TO_UUID[st["id"]] = uuid
            SPEAKER_STYLE_MAP[uuid] = styles
    except Exception as e:
        logging.error(f"Failed to refresh cache: {e}")

refresh_speaker_cache()

# --- 核心：伪日语转换逻辑 (包含 PINYIN_TO_KANA) ---
PINYIN_TO_KANA = {
    "a": "アー", "ai": "アイ", "an": "アン", "ang": "アン", "ao": "アオ",
    "ba": "バー", "bai": "バイ", "ban": "バン", "bang": "バン", "bao": "バオ", "bei": "ベイ", "ben": "ベン", "beng": "ベン", "bi": "ビー", "bian": "ビェン", "biao": "ビャ奥", "bie": "ビェ", "bin": "ビン", "bing": "ビン", "bo": "ボ", "bu": "ブー",
    "ca": "ツァ", "cai": "ツァイ", "can": "ツァン", "cang": "ツァン", "cao": "ツァオ", "ce": "ツァ", "cen": "ツェン", "ceng": "ツェン", "ci": "ツー", "cong": "ツォン", "cou": "ツォウ", "cu": "ツー", "cuan": "ツァン", "cui": "ツイ", "cun": "ツン", "cuo": "ツォ",
    "cha": "チャー", "chai": "チャイ", "chan": "チャン", "chang": "チャン", "chao": "チャオ", "che": "チャー", "chen": "チェン", "cheng": "チェン", "chi": "チー", "chong": "チョン", "chou": "チョウ", "chu": "チュー", "chua": "チュア", "chuai": "チュアイ", "chuan": "チュアン", "chuang": "チュアン", "chui": "チュイ", "chun": "チュン", "chuo": "チュオ",
    "da": "ダー", "dai": "ダイ", "dan": "ダン", "dang": "ダン", "dao": "ダオ", "de": "ダ", "dei": "デイ", "den": "デン", "deng": "デン", "di": "ディー", "dia": "ディア", "dian": "ディェン", "diao": "ディアオ", "die": "ディェ", "ding": "ディン", "diu": "ディウ", "dong": "ドン", "dou": "ドウ", "du": "ドゥー", "duan": "ドゥアン", "dui": "ドゥイ", "dun": "ドゥン", "duo": "ドゥオ",
    "e": "アー", "ei": "エイ", "en": "エン", "eng": "エン", "er": "アル",
    "fa": "ファー", "fan": "ファン", "fang": "ファン", "fei": "フェイ", "fen": "フェン", "feng": "フェン", "fo": "フォ", "fou": "フォウ", "fu": "フー",
    "ga": "ガー", "gai": "ガイ", "gan": "ガン", "gang": "ガン", "gao": "ガオ", "ge": "ガ", "gei": "ゲイ", "gen": "ゲン", "geng": "ゲン", "gong": "ゴン", "gou": "ゴウ", "gu": "グー", "gua": "グ亚", "guai": "グアイ", "guan": "グアン", "guang": "グアン", "gui": "グイ", "gun": "グン", "guo": "グオ",
    "ha": "ハー", "hai": "ハイ", "han": "ハン", "hang": "ハン", "hao": "ハオ", "he": "ハ", "hei": "ヘイ", "hen": "ヘン", "heng": "ヘン", "hong": "ホン", "hou": "ホウ", "hu": "フー", "hua": "ファ", "huai": "ファイ", "huan": "ファン", "huang": "ファン", "hui": "フェイ", "hun": "フン", "huo": "フォ",
    "ji": "ジー", "jia": "ジャ", "jian": "ジェン", "jiang": "ジャン", "jiao": "ジャオ", "jie": "ジェ", "jin": "ジン", "jing": "ジン", "jiong": "ジォン", "jiu": "ジウ", "ju": "ジュー", "juan": "ジュェン", "jue": "ジュェ", "jun": "ジュン",
    "ka": "カー", "kai": "カイ", "kan": "カン", "kang": "カン", "kao": "カオ", "ke": "カ", "kei": "ケイ", "ken": "ケン", "keng": "ケン", "kong": "コン", "kou": "コウ", "ku": "クー", "kua": "クア", "kuai": "クアイ", "kuan": "クアン", "kuang": "クアン", "kui": "クイ", "kun": "クン", "kuo": "クオ",
    "la": "ラー", "lai": "ライ", "lan": "ラン", "lang": "ラン", "lao": "ラオ", "le": "ラ", "lei": "レイ", "leng": "レン", "li": "リー", "lia": "リア", "lian": "リェン", "liang": "リャン", "liao": "リャオ", "lie": "リェ", "lin": "リン", "ling": "リン", "liu": "リウ", "long": "ロン", "lou": "ロウ", "lu": "ルー", "lv": "リュー", "luan": "ルアン", "lue": "ルェ", "lun": "ルン", "luo": "ルオ",
    "ma": "マー", "mai": "マイ", "man": "マン", "mang": "マン", "mao": "マオ", "me": "マ", "mei": "メイ", "men": "メン", "meng": "メン", "mi": "ミー", "mian": "ミェン", "miao": "ミャオ", "mie": "ミェ", "min": "ミン", "ming": "ミン", "miu": "ミウ", "mo": "モ", "mou": "モウ", "mu": "ムー",
    "na": "ナー", "nai": "ナイ", "nan": "ナン", "nang": "ナン", "nao": "ナオ", "ne": "ナ", "nei": "ネイ", "nen": "ネン", "neng": "ネン", "ni": "ニー", "nian": "ニェン", "niang": "ニャン", "niao": "ニャオ", "nie": "ニェ", "nin": "ニン", "ning": "ニン", "niu": "ニウ", "nong": "ノン", "nou": "ノウ", "nu": "ヌー", "nv": "ニュー", "nuan": "ヌアン", "nue": "ニュェ", "nuo": "ヌオ",
    "o": "オー", "ou": "オウ",
    "pa": "パー", "pai": "パイ", "pan": "パン", "pang": "パン", "pao": "パ奥", "pei": "ペイ", "pen": "ペン", "peng": "ペン", "pi": "ピー", "pian": "ピェン", "piao": "ピャオ", "pie": "ピェ", "pin": "ピン", "ping": "ピン", "po": "ポ", "pou": "ポウ", "pu": "プー",
    "qi": "チー", "qia": "チャ", "qian": "チェン", "qiang": "チャン", "qiao": "チャオ", "qie": "チェ", "qin": "チン", "qing": "チン", "qiong": "チョン", "qiu": "チウ", "qu": "チュー", "quan": "チュェン", "que": "チュェ", "qun": "チュン",
    "ran": "ラン", "rang": "ラン", "rao": "ラオ", "re": "ラ", "ren": "レン", "reng": "レン", "ri": "リー", "rong": "ロン", "rou": "ロウ", "ru": "ルー", "ruan": "ルアン", "rui": "ルイ", "run": "ルン", "ruo": "ルオ",
    "sa": "サー", "sai": "サイ", "san": "サン", "sang": "サン", "sao": "サオ", "se": "サ", "sen": "セン", "seng": "セン", "si": "スー", "song": "ソン", "sou": "ソウ", "su": "スー", "suan": "スアン", "sui": "スイ", "sun": "スン", "suo": "スオ",
    "sha": "シャー", "shai": "シャイ", "shan": "シャン", "shang": "シャン", "shao": "シャオ", "she": "シェ", "shei": "シェイ", "shen": "シェン", "sheng": "シェン", "shi": "シー", "shou": "ショウ", "shu": "シュー", "shua": "シュア", "shuai": "シュアイ", "shuan": "シュアン", "shuang": "シュアン", "shui": "シュイ", "shun": "シュン", "shuo": "シュオ",
    "ta": "ター", "tai": "タイ", "tan": "タン", "tang": "タン", "tao": "タオ", "te": "タ", "teng": "テン", "ti": "ティー", "tian": "ティェン", "tiao": "ティアオ", "tie": "ティェ", "ting": "ティン", "tong": "トン", "tou": "トウ", "tu": "トゥー", "tuan": "トゥアン", "tui": "トゥイ", "tun": "トゥン", "tuo": "トゥオ",
    "wa": "ワー", "wai": "ワイ", "wan": "ワン", "wang": "ワン", "wei": "ウェイ", "wen": "ウェン", "weng": "ウェン", "wo": "ウォ", "wu": "ウー",
    "xi": "シー", "xia": "シア", "xian": "シェン", "xiang": "シャン", "xiao": "シャオ", "xie": "シェ", "xin": "シン", "xing": "シン", "xiong": "ション", "xiu": "シウ", "xu": "シュー", "xuan": "シュェン", "xue": "シュェ", "xun": "シュン",
    "ya": "ヤー", "yan": "イェン", "yang": "ヤン", "yao": "ヤオ", "ye": "イェ", "yi": "イー", "yin": "イン", "ying": "イン", "yong": "ヨン", "you": "ヨウ", "yu": "ユー", "yuan": "ユェン", "yue": "ユェ", "yun": "ユン",
    "za": "ザー", "zai": "ザイ", "zan": "ザン", "zang": "ザン", "zao": "ザオ", "ze": "ザ", "zei": "ゼイ", "zen": "ゼン", "zeng": "ゼン", "zi": "ツー", "zong": "ゾン", "zou": "ゾウ", "zu": "ズー", "zuan": "ズアン", "zui": "ズイ", "zun": "ズン", "zuo": "ズオ",
    "zha": "ジャー", "zhai": "ジャイ", "zhan": "ジャン", "zhang": "ジャン", "zhao": "ジャオ", "zhe": "ジャ", "zhei": "ジェイ", "zhen": "ジェン", "zheng": "ジェン", "zhi": "ジー", "zhong": "ジョン", "zhou": "ジョウ", "zhu": "ジュー", "zhua": "ジュア", "zhuai": "ジュアイ", "zhuan": "ジュアン", "zhuang": "ジュアン", "zhui": "ジュイ", "zhun": "ジュン", "zhuo": "ジュオ"
}

class PseudoConverter:
    def is_chinese(self, char): return '\u4e00' <= char <= '\u9fff'
    def process_chinese(self, text):
        py_list = pinyin(text, style=Style.NORMAL, errors='default')
        return "".join([PINYIN_TO_KANA.get(p[0].lower().replace("ü", "v"), p[0]) for p in py_list])
    def process_english(self, text):
        text = text.lower()
        replacements = [("th", "s"), ("ph", "f"), ("v", "b"), ("l", "r"), ("tion", "shon"), ("si", "shi"), ("tu", "chu"), ("ti", "chi")]
        for old, new in replacements: text = text.replace(old, new)
        if text[-1] not in "aeiou": text += "o" if text[-1] in "td" else "u"
        return text
    def convert(self, text):
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+|[^a-zA-Z0-9\u4e00-\u9fff]+', text)
        return "".join([self.process_chinese(t) if self.is_chinese(t[0]) else (self.process_english(t) if re.match(r'[a-zA-Z]+', t) else t) for t in tokens])

converter = PseudoConverter()

class TTSRequest(BaseModel):
    text: str
    speaker: int
    mode: Optional[str] = "pseudo_jp"
    speedScale: Optional[float] = 1.1
    pitchScale: Optional[float] = 0.0
    intonationScale: Optional[float] = 1.0
    volumeScale: Optional[float] = 1.0
    prePhonemeLength: Optional[float] = 0.1
    postPhonemeLength: Optional[float] = 0.1
    outputSamplingRate: Optional[int] = 24000
    outputStereo: Optional[bool] = False
    kana: Optional[str] = None
    pauseLength: Optional[float] = None
    pauseLengthScale: Optional[float] = 1.0
    bgmEnabled: Optional[bool] = False
    bgmVolume: Optional[float] = 0.5

def parse_segments(text, default_speaker_id):
    if not SPEAKER_STYLE_MAP:
        refresh_speaker_cache()
    current_uuid = STYLE_ID_TO_UUID.get(default_speaker_id)
    if not current_uuid:
        refresh_speaker_cache()
        current_uuid = STYLE_ID_TO_UUID.get(default_speaker_id)
    segments = []
    parts = text.replace("，", ",").split(",")
    for part in parts:
        part = part.strip()
        if not part: continue
        match = re.match(r"^\$([^$]+)\$:.(.*)$", part)
        if match:
            style_name = match.group(1)
            content = match.group(2)
            if current_uuid and current_uuid in SPEAKER_STYLE_MAP:
                style_id = SPEAKER_STYLE_MAP[current_uuid].get(style_name)
                if style_id is not None:
                    segments.append((style_id, content))
                else:
                    segments.append((default_speaker_id, content))
            else:
                segments.append((default_speaker_id, content))
        else:
            segments.append((default_speaker_id, part))
    return segments

def generate_combined_audio(segments, params):
    audio_files = []
    temp_files = []
    try:
        for spk_id, text in segments:
            if not text: continue
            target_text = converter.convert(text)
            q = requests.post(f"{VOICEVOX_URL}/audio_query", params={"text": target_text, "speaker": spk_id}, verify=False).json()
            q["speedScale"] = params.speedScale
            q["pitchScale"] = params.pitchScale
            q["intonationScale"] = params.intonationScale
            q["volumeScale"] = params.volumeScale
            q["prePhonemeLength"] = params.prePhonemeLength
            q["postPhonemeLength"] = params.postPhonemeLength
            if hasattr(params, 'outputSamplingRate') and params.outputSamplingRate:
                q["outputSamplingRate"] = params.outputSamplingRate
            if hasattr(params, 'outputStereo') and params.outputStereo is not None:
                q["outputStereo"] = params.outputStereo
            if hasattr(params, 'kana') and params.kana:
                q["kana"] = params.kana
            if hasattr(params, 'pauseLength') and params.pauseLength is not None:
                q["pauseLength"] = params.pauseLength
            if hasattr(params, 'pauseLengthScale') and params.pauseLengthScale is not None:
                q["pauseLengthScale"] = params.pauseLengthScale

            synth_res = requests.post(f"{VOICEVOX_URL}/synthesis", params={"speaker": spk_id}, json=q, verify=False)
            if synth_res.status_code != 200:
                logging.error(f"Synthesis failed: {synth_res.status_code} {synth_res.text[:200]}")
                continue
            wav = synth_res.content
            tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tf.write(wav)
            tf.close()
            temp_files.append(tf.name)
            audio_files.append(tf.name)
        if not audio_files: return b""
        if len(audio_files) == 1:
            with open(audio_files[0], "rb") as f: return f.read()
        list_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        for f in audio_files: list_file.write(f"file '{f}'\n")
        list_file.close()
        temp_files.append(list_file.name)
        out_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        temp_files.append(out_file)
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file.name, "-c", "copy", out_file], check=True, stderr=subprocess.PIPE)
        with open(out_file, "rb") as f: return f.read()
    except Exception as e:
        logging.error(f"Audio gen error: {e}")
        return b""
    finally:
        for f in temp_files:
            if os.path.exists(f): os.unlink(f)

@app.get("/voices")
def get_voices():
    try:
        r = requests.get(f"{VOICEVOX_URL}/speakers", verify=False).json()
    except: return []
    grouped = {}
    for char in r:
        raw_name = char["name"]
        display_name = CN_NAME_MAP.get(raw_name, raw_name)
        styles = []
        for s in char["styles"]:
            styles.append({"id": s["id"], "name": CN_STYLE_MAP.get(s["name"], s["name"]), "raw_name": s["name"]})
        uuid = char["speaker_uuid"]
        grouped[raw_name] = {"name": display_name, "uuid": uuid, "styles": styles, "raw_name": raw_name, "icon_url": f"/static/{uuid}_icon.png"}
    return list(grouped.values())

@app.get("/character_info")
def get_character_info(uuid: str):
    return {"portrait_url": f"/static/{uuid}_portrait.png", "sample_urls": [f"/static/{uuid}_sample_{i}.wav" for i in range(1, 4)]}

@app.post("/tts")
def tts(req: TTSRequest, x_api_key: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if user:
        cost = len(req.text)
        if user.balance < cost: raise HTTPException(status_code=402, detail="Insufficient balance")
        user.balance -= cost
    else:
        record = db.query(APIKeyRecord).filter(APIKeyRecord.key == x_api_key).first()
        if not record or record.credits <= 0: raise HTTPException(status_code=401, detail="Invalid key or no credits")
        record.credits -= 1
    segments = parse_segments(req.text, req.speaker)
    audio = generate_combined_audio(segments, req)
    db.commit()
    return Response(content=audio, media_type="audio/wav")

@app.post("/tts_custom")
async def tts_custom(
    text: str = Form(...), speaker: int = Form(...), mode: str = Form("pseudo_jp"),
    speedScale: float = Form(1.1), pitchScale: float = Form(0.0), intonationScale: float = Form(1.0),
    volumeScale: float = Form(1.0), prePhonemeLength: float = Form(0.1), postPhonemeLength: float = Form(0.1),
    outputSamplingRate: int = Form(24000), outputStereo: bool = Form(False), kana: Optional[str] = Form(None),
    bgmEnabled: bool = Form(False), bgmVolume: float = Form(0.5), bgmFile: UploadFile = File(None),
    x_api_key: str = Header(...), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if user:
        cost = len(text)
        if user.balance < cost: raise HTTPException(status_code=402, detail="Insufficient balance")
        user.balance -= cost
    else:
        record = db.query(APIKeyRecord).filter(APIKeyRecord.key == x_api_key).first()
        if not record or record.credits <= 0: raise HTTPException(status_code=401, detail="Invalid key or no credits")
        record.credits -= 1
    class Params: pass
    p = Params()
    p.speedScale = speedScale
    p.pitchScale = pitchScale
    p.intonationScale = intonationScale
    p.volumeScale = volumeScale
    p.prePhonemeLength = prePhonemeLength
    p.postPhonemeLength = postPhonemeLength
    p.outputSamplingRate = outputSamplingRate
    p.outputStereo = outputStereo
    p.kana = kana
    
    segments = parse_segments(text, speaker)
    audio = generate_combined_audio(segments, p)
    db.commit()
    return Response(content=audio, media_type="audio/wav")

# --- Payment Logic ---
@app.post("/api/recharge/create")
async def create_recharge_order(amount_type: str = Form(...), x_api_key: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user: raise HTTPException(401, "Invalid User")
    if amount_type != "0.99_1000": raise HTTPException(400, "Invalid package")
    amount = 0.99
    out_trade_no = datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(4)
    pay = Payment(out_trade_no=out_trade_no, user_id=user.id, amount=int(amount*100), status="PENDING")
    db.add(pay)
    db.commit()
    return {"url": f"/mock_pay?order={out_trade_no}&amount={amount}", "mock": True}

@app.get("/mock_pay", response_class=HTMLResponse)
def mock_pay_page(order: str, amount: str):
    return f"<h1>Mock Alipay</h1><p>Order: {order}</p><form action='/api/recharge/mock_confirm' method='post'><input type='hidden' name='order_id' value='{order}'><button type='submit'>Confirm</button></form>"

@app.post("/api/recharge/mock_confirm")
def mock_confirm(order_id: str = Form(...), db: Session = Depends(get_db)):
    pay = db.query(Payment).filter(Payment.out_trade_no == order_id).first()
    if not pay: return "Order not found"
    if pay.status == "PENDING":
        pay.status = "SUCCESS"
        user = db.query(User).filter(User.id == pay.user_id).first()
        user.balance += 1000
        db.commit()
    return HTMLResponse("Success! <a href='/'>Back</a>")

@app.get("/", response_class=HTMLResponse)
def index():
    trans_json = json.dumps(TRANSLATIONS, ensure_ascii=False)
    try:
        with open("/root/voicevox-onestepapi-cn-en-pseudo-jp-tts/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return html.replace('[[TRANS_JSON]]', trans_json)
    except Exception as e:
        return f"Error loading index.html: {e}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
