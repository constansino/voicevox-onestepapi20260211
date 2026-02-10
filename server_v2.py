import os
import re
import json
import logging
import requests
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypinyin import pinyin, Style
from sqlalchemy import create_all_commands, Column, String, Integer, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- 数据库配置 ---
DB_URL = "sqlite:///./tts_management.db"
Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class APIKey(Base):
    __tablename__ = "api_keys"
    key = Column(String, primary_key=True, index=True)
    credits = Column(Integer, default=100) # 剩余额度
    created_at = Column(DateTime, default=datetime.utcnow)
    memo = Column(String, nullable=True) # 备注（如买家信息）

Base.metadata.create_all(bind=engine)

# --- FastAPI 配置 ---
VOICEVOX_URL = os.getenv("VOICEVOX_BASE_URL", "http://127.0.0.1:800").rstrip("/")
ADMIN_SECRET = "xingshuo_admin" # 管理员密码，用于生成 Key

app = FastAPI(title="Voicevox OneStep API & Web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 依赖项：获取数据库会话 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 鉴权与扣费逻辑 ---
async def verify_and_bill(db: Session = Depends(get_db), x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    db_key = db.query(APIKey).filter(APIKey.key == x_api_key).first()
    if not db_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    if db_key.credits <= 0:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    # 执行扣费
    db_key.credits -= 1
    db.commit()
    return db_key

# --- 拼音转换逻辑 (保持之前的高质量映射) ---
# ... (此处省略 PINYIN_TO_KANA 字典，实际代码中我会补全) ...
