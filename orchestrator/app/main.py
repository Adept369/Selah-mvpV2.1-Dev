# orchestrator/app/main.py

import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, Header, HTTPException
from telegram import Bot
from telegram.error import TelegramError
from gtts import gTTS

from app.core.config import settings
from app.orchestration.master_agent import MasterAgent
from app.llm.clients import LLMClient
from app.agents.file_conversion_agent.file_conversion_agent import FileConversionAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# — Initialize clients & agents —
bot = Bot(token=settings.TELEGRAM_TOKEN)
llm_client = LLMClient(settings)
master = MasterAgent(llm_client=llm_client)
audio_agent = FileConversionAgent(llm_client=None)  # only uses audio_to_text()

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

    # 2) Parse update
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"status": "ignored"}

    chat_id = msg["chat"]["id"]

    # 3) Handle voice vs text
    if msg.get("voice") or msg.get("audio"):
        file_id = (msg.get("voice") or msg.get("audio"))["file_id"]
        # fetch and download the .oga/.ogg file
        tg_file = await bot.get_file(file_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".oga", delete=False)
        await tg_file.download(custom_path=tmp.name)
        tmp.close()

        # now let our agent handle it
        try:
            user_input = audio_agent.audio_to_text(tmp.name)
        except Exception as e:
            logger.error("Audio agent error: %s", e)
            user_input = f"⚠️ Audio processing failed: {e}"

        # and send back the transcript
        try:
            await bot.send_message(chat_id=chat_id, text=user_input)
        except TelegramError as e:
            logger.error("Telegram send_message failed: %s", e)

        # we're done for voice
        os.unlink(tmp.name)
        return {"status": "ok", "voice_transcript": user_input}

    # 4) Route the (possibly-transcribed) text through MasterAgent
    fake_update = {"message": {"chat": {"id": chat_id}, "text": user_input}}
    reply_text = await master.run(fake_update)

    # 5) Generate a short, witty one-liner about the user_input
    witty = None
    if user_input:
        try:
            witty = llm_client.generate(
                prompt=f"Give me a short, witty one-liner about: {user_input}",
                max_tokens=50,
                temperature=0.8
            ).strip()
            logger.info("Witty line: %r", witty)
        except Exception as e:
            logger.error("Failed to generate witty line: %s", e)

    
    


    # 6a) Send the full answer back as text
    if reply_text:
        try:
            await bot.send_message(chat_id=chat_id, text=reply_text)
        except TelegramError as e:
            logger.error("Failed to send text reply: %s", e)

    # 6b) If we have a witty line, TTS it and send as voice note
    if witty:
        mp3_file = None
        try:
            tts = gTTS(witty)
            mp3_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tts.write_to_fp(mp3_file)
            mp3_file.flush()
            mp3_file.close()

            with open(mp3_file.name, "rb") as f:
                await bot.send_voice(chat_id=chat_id, voice=f)
        except Exception as e:
            logger.error("Failed to send witty voice note: %s", e)
        finally:
            if mp3_file and os.path.exists(mp3_file.name):
                os.unlink(mp3_file.name)

    # 7) Always return non-null JSON
    return {"status": "ok", "reply": reply_text, "witty": witty}
