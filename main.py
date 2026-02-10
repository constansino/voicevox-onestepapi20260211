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
import io
import wave
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Header, Depends, Request, File, UploadFile, Form
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypinyin import pinyin, Style, load_phrases_dict
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICEVOX_URL = os.getenv("VOICEVOX_BASE_URL", "https://voicevox.kira.de5.net").rstrip("/")
ADMIN_KEY = os.getenv("VOICEVOX_ADMIN_KEY", "change_me_admin_key")
PUBLIC_API_KEY = os.getenv("VOICEVOX_ADAPTER_KEY", "public_demo_key")
BGM_FILE = os.getenv("VOICEVOX_BGM_FILE", os.path.join(BASE_DIR, "1.mp3"))

# --- Translations ---
TRANSLATIONS = {}
try:
    translations_file = os.getenv("VOICEVOX_TRANSLATIONS_FILE", os.path.join(BASE_DIR, "voicevox_translations.json"))
    with open(translations_file, "r", encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    logging.error(f"Failed to load translations: {e}")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"])
static_dir = os.getenv("VOICEVOX_STATIC_DIR", os.path.join(BASE_DIR, "static"))
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def normalize_api_key(x_api_key: Optional[str]) -> str:
    key = (x_api_key or "").strip()
    return key if key else PUBLIC_API_KEY

def ensure_public_api_key():
    if not PUBLIC_API_KEY:
        return
    db = SessionLocal()
    try:
        record = db.query(APIKeyRecord).filter(APIKeyRecord.key == PUBLIC_API_KEY).first()
        if not record:
            db.add(APIKeyRecord(key=PUBLIC_API_KEY, credits=10_000_000))
            db.commit()
    finally:
        db.close()

ensure_public_api_key()

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

@app.get("/public_config")
def public_config():
    return {"default_api_key": PUBLIC_API_KEY}

@app.get("/debug_convert")
def debug_convert(text: str, mode: str = "pseudo_jp"):
    converted = converter.convert(text) if mode == "pseudo_jp" else text
    return {"mode": mode, "input": text, "output": converted}

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
    "ba": "バー", "bai": "バイ", "ban": "バン", "bang": "バン", "bao": "バオ", "bei": "ベイ", "ben": "ベン", "beng": "ベン", "bi": "ビー", "bian": "ビェン", "biao": "ビャオ", "bie": "ビェ", "bin": "ビン", "bing": "ビン", "bo": "ボ", "bu": "ブー",
    "ca": "ツァ", "cai": "ツァイ", "can": "ツァン", "cang": "ツァン", "cao": "ツァオ", "ce": "ツァ", "cen": "ツェン", "ceng": "ツェン", "ci": "ツー", "cong": "ツォン", "cou": "ツォウ", "cu": "ツー", "cuan": "ツァン", "cui": "ツイ", "cun": "ツン", "cuo": "ツォ",
    "cha": "チャー", "chai": "チャイ", "chan": "チャン", "chang": "チャン", "chao": "チャオ", "che": "チャー", "chen": "チェン", "cheng": "チェン", "chi": "チー", "chong": "チョン", "chou": "チョウ", "chu": "チュー", "chua": "チュア", "chuai": "チュアイ", "chuan": "チュアン", "chuang": "チュアン", "chui": "チュイ", "chun": "チュン", "chuo": "チュオ",
    "da": "ダー", "dai": "ダイ", "dan": "ダン", "dang": "ダン", "dao": "ダオ", "de": "ダ", "dei": "デイ", "den": "デン", "deng": "デン", "di": "ディー", "dia": "ディア", "dian": "ディェン", "diao": "ディアオ", "die": "ディェ", "ding": "ディン", "diu": "ディウ", "dong": "ドン", "dou": "ドウ", "du": "ドゥー", "duan": "ドゥアン", "dui": "ドゥイ", "dun": "ドゥン", "duo": "ドゥオ",
    "e": "アー", "ei": "エイ", "en": "エン", "eng": "エン", "er": "アル",
    "fa": "ファー", "fan": "ファン", "fang": "ファン", "fei": "フェイ", "fen": "フェン", "feng": "フェン", "fo": "フォ", "fou": "フォウ", "fu": "フー",
    "ga": "ガー", "gai": "ガイ", "gan": "ガン", "gang": "ガン", "gao": "ガオ", "ge": "ガ", "gei": "ゲイ", "gen": "ゲン", "geng": "ゲン", "gong": "ゴン", "gou": "ゴウ", "gu": "グー", "gua": "グア", "guai": "グアイ", "guan": "グアン", "guang": "グアン", "gui": "グイ", "gun": "グン", "guo": "グオ",
    "ha": "ハー", "hai": "ハイ", "han": "ハン", "hang": "ハン", "hao": "ハオ", "he": "ハ", "hei": "ヘイ", "hen": "ヘン", "heng": "ヘン", "hong": "ホン", "hou": "ホウ", "hu": "フー", "hua": "ファ", "huai": "ファイ", "huan": "ファン", "huang": "ファン", "hui": "フェイ", "hun": "フン", "huo": "フォ",
    "ji": "ジー", "jia": "ジャ", "jian": "ジェン", "jiang": "ジャン", "jiao": "ジャオ", "jie": "ジェ", "jin": "ジン", "jing": "ジン", "jiong": "ジォン", "jiu": "ジウ", "ju": "ジュー", "juan": "ジュェン", "jue": "ジュェ", "jun": "ジュン",
    "ka": "カー", "kai": "カイ", "kan": "カン", "kang": "カン", "kao": "カオ", "ke": "カ", "kei": "ケイ", "ken": "ケン", "keng": "ケン", "kong": "コン", "kou": "コウ", "ku": "クー", "kua": "クア", "kuai": "クアイ", "kuan": "クアン", "kuang": "クアン", "kui": "クイ", "kun": "クン", "kuo": "クオ",
    "la": "ラー", "lai": "ライ", "lan": "ラン", "lang": "ラン", "lao": "ラオ", "le": "ラ", "lei": "レイ", "leng": "レン", "li": "リー", "lia": "リア", "lian": "リェン", "liang": "リャン", "liao": "リャオ", "lie": "リェ", "lin": "リン", "ling": "リン", "liu": "リウ", "long": "ロン", "lou": "ロウ", "lu": "ルー", "lv": "リュー", "luan": "ルアン", "lue": "ルェ", "lun": "ルン", "luo": "ルオ",
    "ma": "マー", "mai": "マイ", "man": "マン", "mang": "マン", "mao": "マオ", "me": "マ", "mei": "メイ", "men": "メン", "meng": "メン", "mi": "ミー", "mian": "ミェン", "miao": "ミャオ", "mie": "ミェ", "min": "ミン", "ming": "ミン", "miu": "ミウ", "mo": "モ", "mou": "モウ", "mu": "ムー",
    "na": "ナー", "nai": "ナイ", "nan": "ナン", "nang": "ナン", "nao": "ナオ", "ne": "ナ", "nei": "ネイ", "nen": "ネン", "neng": "ネン", "ni": "ニー", "nian": "ニェン", "niang": "ニャン", "niao": "ニャオ", "nie": "ニェ", "nin": "ニン", "ning": "ニン", "niu": "ニウ", "nong": "ノン", "nou": "ノウ", "nu": "ヌー", "nv": "ニュー", "nuan": "ヌアン", "nue": "ニュェ", "nuo": "ヌオ",
    "o": "オー", "ou": "オウ",
    "pa": "パー", "pai": "パイ", "pan": "パン", "pang": "パン", "pao": "パオ", "pei": "ペイ", "pen": "ペン", "peng": "ペン", "pi": "ピー", "pian": "ピェン", "piao": "ピャオ", "pie": "ピェ", "pin": "ピン", "ping": "ピン", "po": "ポ", "pou": "ポウ", "pu": "プー",
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

load_phrases_dict({
    # Common polyphonic words/phrases
    "重庆": [["chong"], ["qing"]],
    "银行": [["yin"], ["hang"]],
    "行长": [["hang"], ["zhang"]],
    "重启": [["chong"], ["qi"]],
    "重复": [["chong"], ["fu"]],
    "重要": [["zhong"], ["yao"]],
    "音乐": [["yin"], ["yue"]],
    "乐器": [["yue"], ["qi"]],
    "快乐": [["kuai"], ["le"]],
    "长大": [["zhang"], ["da"]],
    "成长": [["cheng"], ["zhang"]],
})

CN_DIGITS = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"
}

EN_LETTER_TO_KATA = {
    "a": "エー", "b": "ビー", "c": "シー", "d": "ディー", "e": "イー", "f": "エフ",
    "g": "ジー", "h": "エイチ", "i": "アイ", "j": "ジェー", "k": "ケー", "l": "エル",
    "m": "エム", "n": "エヌ", "o": "オー", "p": "ピー", "q": "キュー", "r": "アール",
    "s": "エス", "t": "ティー", "u": "ユー", "v": "ブイ", "w": "ダブリュー", "x": "エックス",
    "y": "ワイ", "z": "ゼット"
}


class PseudoConverter:
    def is_chinese(self, char): return '\u4e00' <= char <= '\u9fff'

    def process_number(self, text):
        cn = "".join(CN_DIGITS.get(ch, ch) for ch in text)
        return self.process_chinese(cn)

    def process_chinese(self, text):
        py_list = pinyin(text, style=Style.NORMAL, errors='default')
        kana_list = []
        for p in py_list:
            py = p[0].lower().replace("ü", "v")
            kana_list.append(PINYIN_TO_KANA.get(py, p[0]))
        # Keep natural flow: do not force per-syllable separators.
        return "".join(kana_list)

    def process_english(self, text):
        if text.isupper() and text.isalpha() and len(text) <= 8:
            return "・".join(EN_LETTER_TO_KATA.get(ch.lower(), ch) for ch in text.lower())
        text = text.lower().replace("-", " ")
        replacements = [("th", "s"), ("ph", "f"), ("v", "b"), ("l", "r"), ("tion", "shon"), ("si", "shi"), ("tu", "chu"), ("ti", "chi")]
        for old, new in replacements: text = text.replace(old, new)
        if text and text[-1] not in "aeiou":
            text += "o" if text[-1] in "td" else "u"
        return text

    def convert(self, text):
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|[0-9]+|[^a-zA-Z0-9\u4e00-\u9fff]+', text)
        out = []
        for t in tokens:
            if not t:
                continue
            if self.is_chinese(t[0]):
                out.append(self.process_chinese(t))
            elif re.match(r'^[a-zA-Z]+$', t):
                out.append(self.process_english(t))
            elif re.match(r'^[0-9]+$', t):
                out.append(self.process_number(t))
            else:
                out.append(t)
        return "".join(out)

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
    text = text.strip()
    if not text:
        return []
    # No style tag: keep full sentence (including punctuation) as one segment,
    # so prosody stays consistent.
    if "$" not in text:
        return [(default_speaker_id, text)]

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

def concat_wavs(audio_files):
    if not audio_files:
        return b""
    out_buf = io.BytesIO()
    first_params = None
    with wave.open(out_buf, "wb") as out_wav:
        for idx, path in enumerate(audio_files):
            with wave.open(path, "rb") as in_wav:
                params = in_wav.getparams()
                if idx == 0:
                    first_params = params
                    out_wav.setnchannels(params.nchannels)
                    out_wav.setsampwidth(params.sampwidth)
                    out_wav.setframerate(params.framerate)
                else:
                    if (
                        params.nchannels != first_params.nchannels
                        or params.sampwidth != first_params.sampwidth
                        or params.framerate != first_params.framerate
                    ):
                        raise ValueError("WAV format mismatch while concatenating segments")
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
    return out_buf.getvalue()

def mix_with_bgm(tts_audio: bytes, bgm_volume: float = 0.5, bgm_path: Optional[str] = None) -> bytes:
    bgm_src = bgm_path or BGM_FILE
    if not tts_audio or not bgm_src or not os.path.exists(bgm_src):
        return tts_audio
    temp_files = []
    try:
        tts_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tts_file.write(tts_audio)
        tts_file.close()
        temp_files.append(tts_file.name)

        out_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        out_file.close()
        temp_files.append(out_file.name)

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", bgm_src,
                "-i", tts_file.name,
                "-filter_complex", f"[0:a]volume={bgm_volume}[bgm];[bgm][1:a]amix=inputs=2:duration=shortest:dropout_transition=2[out]",
                "-map", "[out]",
                "-ac", "1",
                out_file.name,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        with open(out_file.name, "rb") as f:
            return f.read()
    except Exception as e:
        logging.error(f"BGM mix failed: {e}")
        return tts_audio
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.unlink(f)

def generate_combined_audio(segments, params):
    audio_files = []
    temp_files = []
    try:
        for spk_id, text in segments:
            if not text: continue
            use_pseudo = getattr(params, "mode", "pseudo_jp") == "pseudo_jp"
            target_text = converter.convert(text) if use_pseudo else text
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
            with open(audio_files[0], "rb") as f:
                base_audio = f.read()
            if getattr(params, "bgmEnabled", False):
                return mix_with_bgm(base_audio, getattr(params, "bgmVolume", 0.5), getattr(params, "bgmFilePath", None))
            return base_audio
        list_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        for f in audio_files: list_file.write(f"file '{f}'\n")
        list_file.close()
        temp_files.append(list_file.name)
        out_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        temp_files.append(out_file)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file.name, "-c", "copy", out_file],
                check=True,
                stderr=subprocess.PIPE
            )
            with open(out_file, "rb") as f:
                merged_audio = f.read()
        except FileNotFoundError:
            merged_audio = concat_wavs(audio_files)
        if getattr(params, "bgmEnabled", False):
            return mix_with_bgm(merged_audio, getattr(params, "bgmVolume", 0.5), getattr(params, "bgmFilePath", None))
        return merged_audio
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
def tts(req: TTSRequest, x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)):
    x_api_key = normalize_api_key(x_api_key)
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
    x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    x_api_key = normalize_api_key(x_api_key)
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
    p.mode = mode
    p.bgmEnabled = bgmEnabled
    p.bgmVolume = bgmVolume
    temp_bgm_path = None
    if bgmFile is not None:
        content = await bgmFile.read()
        if content:
            suffix = os.path.splitext(bgmFile.filename or "")[1] or ".mp3"
            tf = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tf.write(content)
            tf.close()
            temp_bgm_path = tf.name
            p.bgmFilePath = temp_bgm_path
    
    try:
        segments = parse_segments(text, speaker)
        audio = generate_combined_audio(segments, p)
        db.commit()
        return Response(content=audio, media_type="audio/wav")
    finally:
        if temp_bgm_path and os.path.exists(temp_bgm_path):
            os.unlink(temp_bgm_path)

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
        index_file = os.getenv("VOICEVOX_INDEX_FILE", os.path.join(BASE_DIR, "index.html"))
        with open(index_file, "r", encoding="utf-8") as f:
            html = f.read()
        return html.replace('[[TRANS_JSON]]', trans_json)
    except Exception as e:
        return f"Error loading index.html: {e}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
