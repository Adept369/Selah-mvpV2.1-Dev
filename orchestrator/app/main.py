# orchestrator/app/main.py

import logging
import os
import tempfile

from fastapi import FastAPI, Request, Header, HTTPException
from telegram import Bot
from telegram.error import TelegramError
from gtts import gTTS

from app.core.config import settings
from app.orchestration.master_agent import MasterAgent
from app.llm.clients import LLMClient
from app.agents.file_conversion_agent.file_conversion_agent import FileConversionAgent
from app.agents.memory.buffer_memory import BufferMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# — Initialize Telegram, LLM, Agents, and in-memory buffer —
bot = Bot(token=settings.TELEGRAM_TOKEN)
llm_client = LLMClient(settings)
master = MasterAgent(llm_client=llm_client)
audio_agent = FileConversionAgent(llm_client=None)  # only uses audio_to_text()
memory = BufferMemory()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "✅ Inter-Tribal Chambers bot is live!"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    secret: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    # 1) Secret check
    if settings.WEBHOOK_SECRET and secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 2) Parse update JSON
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"status": "ignored"}

    chat_id = msg["chat"]["id"]

    # 3) Voice vs text
    if msg.get("voice") or msg.get("audio"):
        file_id = (msg.get("voice") or msg.get("audio"))["file_id"]
        tg_file = await bot.get_file(file_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".oga", delete=False)
        await tg_file.download(custom_path=tmp.name)
        tmp.close()

        try:
            user_input = audio_agent.audio_to_text(tmp.name)
        except Exception as e:
            logger.error("Audio agent error: %s", e)
            user_input = f"⚠️ Audio processing failed: {e}"

        # immediately reply with transcript
        try:
            await bot.send_message(chat_id=chat_id, text=user_input)
        except TelegramError as e:
            logger.error("Telegram send_message failed: %s", e)
        finally:
            os.unlink(tmp.name)

        return {"status": "ok", "voice_transcript": user_input}

    # 4) It’s text
    user_input = msg.get("text", "").strip()
    if not user_input:
        return {"status": "ok", "reply": "🤖 Please send some text."}

    # 5) Save to in-memory buffer
    memory.add(chat_id, "user", user_input)

    # 6) Route through MasterAgent
    #    MasterAgent.run will pick up buffer via Redis or in-memory as configured
    fake_update = {
        "message": {"chat": {"id": chat_id}, "text": user_input}
    }
    reply_text = await master.run(fake_update)

    # 7) Save bot reply in buffer
    memory.add(chat_id, "bot", reply_text)

    # 8) Send the full-text reply
    if reply_text:
        try:
            await bot.send_message(chat_id=chat_id, text=reply_text)
        except TelegramError as e:
            logger.error("Failed to send text reply: %s", e)

    # 9) (Optional) Send a witty TTS voice-note
    try:
        witty = llm_client.generate(
            prompt=f"Give me a short, witty one-liner about: {user_input}",
            max_tokens=50,
            temperature=0.8
        ).strip()
        tts = gTTS(witty)
        mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.write_to_fp(mp3)
        mp3.flush()
        mp3.close()
        with open(mp3.name, "rb") as f:
            await bot.send_voice(chat_id=chat_id, voice=f)
    except Exception:
        # swallow any errors here
        pass
    finally:
        if 'mp3' in locals() and os.path.exists(mp3.name):
            os.unlink(mp3.name)

    return {"status": "ok", "reply": reply_text}
