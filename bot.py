import os
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def search_and_download(query: str):
    """Deezer dan to'liq musiqa URL topadi."""
    # 1. Qidirish
    search_url = "https://api.deezer.com/search"
    params = {"q": query, "limit": 1}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            tracks = data.get("data", [])
            if not tracks:
                return None
            
            track = tracks[0]
            return {
                "title": track["title"],
                "artist": track["artist"]["name"],
                "preview_url": track.get("preview"),  # 30 soniya MP3
                "cover": track["album"].get("cover_medium"),
                "deezer_url": track.get("link", ""),
                "duration": track.get("duration", 0),
            }


async def download_audio(url: str) -> bytes | None:
    """Audio faylni yuklab oladi."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Musiqa Bot*\n\n"
        "Qo'shiq nomi yozing — topib yuboraman!\n\n"
        "_Masalan: Dua Lipa Levitating_",
        parse_mode="Markdown"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    msg = await update.message.reply_text(f"🔍 Qidirilmoqda: *{query}*...", parse_mode="Markdown")

    track = await search_and_download(query)

    if not track:
        await msg.edit_text("❌ Topilmadi. Boshqa nom bilan urinib ko'ring.")
        return

    title = track["title"]
    artist = track["artist"]
    preview_url = track["preview_url"]
    cover = track["cover"]

    await msg.edit_text(f"✅ Topildi! ⬇️ Yuklanmoqda...")

    # Muqova + ma'lumot
    if cover:
        await update.message.reply_photo(
            photo=cover,
            caption=f"🎵 *{title}*\n👤 _{artist}_",
            parse_mode="Markdown"
        )

    # Audio yuborish
    if preview_url:
        audio_data = await download_audio(preview_url)
        if audio_data:
            tmp = f"/tmp/{title[:20]}.mp3"
            with open(tmp, "wb") as f:
                f.write(audio_data)
            with open(tmp, "rb") as f:
                await update.message.reply_audio(
                    audio=f,
                    title=title,
                    performer=artist,
                    caption=f"🎵 *{title}* — _{artist}_",
                    parse_mode="Markdown"
                )
            Path(tmp).unlink(missing_ok=True)
            await msg.delete()
        else:
            await msg.edit_text("❌ Yuklab bo'lmadi.")
    else:
        await msg.edit_text(
            f"🎵 *{title}* — _{artist}_\n\n"
            "⚠️ Bu qo'shiq uchun yuklab bo'lmadi, boshqasini qidiring.",
            parse_mode="Markdown"
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN yo'q!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
