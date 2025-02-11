from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRecord(BaseModel):
    timestamp: str
    chatId: int
    userMessage: str
    botReasoning: str
    botResponse: str
    thinkingTime: str

@app.post("/save-record")
async def save_record(record: ChatRecord):
    try:
        # 格式化记录
        formatted_record = (
            f"\n=== 对话记录 ===\n"
            f"时间: {record.timestamp}\n"
            f"对话ID: {record.chatId}\n"
            f"用户: {record.userMessage}\n"
            f"思考过程: {record.botReasoning}\n"
            f"回复: {record.botResponse}\n"
            f"思考用时: {record.thinkingTime}秒\n"
            f"===============\n"
        )
        
        # 将记录追加到文件
        with open("record.txt", "a", encoding="utf-8") as f:
            f.write(formatted_record)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))