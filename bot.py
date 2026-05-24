import os
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")


async def download_from_youtube(query: str) -> tuple:
    import yt_dlp
    output_path = f"/tmp/{query[:30].replace(' ', '_')}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path.replace(".mp3", ".%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", query)
            artist = info.get("uploader", "Noma'lum")
            return title, artist

    try:
        title, artist = await loop.run_in_executor(None, _download)
        if Path(output_path).exists():
            return output_path, title, artist
        return None, query, "Noma'lum"
    except Exception as e:
        print(f"Xato: {e}")
        return None, query, "Noma'lum"


async def search_music_deezer(query: str) -> list:
    url = "https://api.deezer.com/search"
    params = {"q": query, "limit": 3}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            results = []
            for track in data.get("data", []):
                results.append({
                    "title": track["title"],
                    "artist": track["artist"]["name"],
                    "cover": track["album"].get("cover_medium"),
                    "deezer_url": track.get("link", ""),
                })
            return results


async def recognize_audio_shazam(file_path: str):
    if not RAPIDAPI_KEY:
        return None
    url = "https://shazam-core.p.rapidapi.com/v1/tracks/recognize"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "shazam-core.p.rapidapi.com",
    }
    async with aiofiles.open(file_path, "rb") as f:
        audio_bytes = await f.read()
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("upload_file", audio_bytes,
                       filename="audio.ogg", content_type="audio/ogg")
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                return None
            result = await resp.json()
            track = result.get("track")
            if not track:
                return None
            return {
                "title": track.get("title", "Noma'lum"),
                "artist": track.get("subtitle", "Noma'lum"),
            }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 *Musiqa Bot ga xush kelibsiz!*\n\n"
        "Qo'shiq nomi yoki artist yozing — men YouTube dan topib yuboraman!\n\n"
        "🎤 Ovozli xabar yuborsangiz ham aniqlayman!\n\n"
        "_Masalan: `Dua Lipa Levitating`_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    msg = await update.message.reply_text(
        f"🔍 *{query}* qidirilmoqda...\n⏳ Biroz kuting (10-20 sek)",
        parse_mode="Markdown"
    )

    results = await search_music_deezer(query)
    await msg.edit_text("⬇️ YouTube dan yuklanmoqda...")
    file_path, title, artist = await download_from_youtube(query)

    if file_path and Path(file_path).exists():
        cover = results[0]["cover"] if results else None
        deezer_url = results[0]["deezer_url"] if results else ""

        buttons = []
        if deezer_url:
            buttons.append([InlineKeyboardButton("🎧 Deezer'da tinglash", url=deezer_url)])
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        if cover:
            await update.message.reply_photo(
                photo=cover,
                caption=f"🎵 *{title}*\n👤 _{artist}_",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        with open(file_path, "rb") as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                caption=f"🎵 *{title}*\n👤 _{artist}_",
                parse_mode="Markdown",
            )

        await msg.delete()
        Path(file_path).unlink(missing_ok=True)
    else:
        await msg.edit_text(
            "❌ Yuklab bo'lmadi. Boshqa so'z bilan urinib ko'ring.\n"
            "_Masalan: `artist - qo'shiq nomi`_",
            parse_mode="Markdown"
        )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🎧 Aniqlanmoqda...")

    if update.message.voice:
        file_obj = update.message.voice
        ext = "ogg"
    elif update.message.audio:
        file_obj = update.message.audio
        ext = "mp3"
    else:
        await msg.edit_text("❌ Fayl tanilmadi.")
        return

    tmp_path = f"/tmp/recognize_{update.message.message_id}.{ext}"
    tg_file = await context.bot.get_file(file_obj.file_id)
    await tg_file.download_to_drive(tmp_path)

    track_info = None
    if RAPIDAPI_KEY:
        await msg.edit_text("🔎 Shazam orqali aniqlanmoqda...")
        track_info = await recognize_audio_shazam(tmp_path)

    Path(tmp_path).unlink(missing_ok=True)

    if track_info:
        title = track_info["title"]
        artist = track_info["artist"]
        await msg.edit_text(
            f"✅ Topildi!\n🎵 *{title}*\n👤 _{artist}_\n\n⬇️ Yuklanmoqda...",
            parse_mode="Markdown"
        )
        file_path, dl_title, dl_artist = await download_from_youtube(f"{artist} {title}")
        if file_path and Path(file_path).exists():
            with open(file_path, "rb") as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    title=title,
                    performer=artist,
                )
            await msg.delete()
            Path(file_path).unlink(missing_ok=True)
        else:
            await msg.edit_text(
                f"✅ Aniqlandi: *{title}* — _{artist}_\n❌ Lekin yuklab bo'lmadi.",
                parse_mode="Markdown"
            )
    else:
        await msg.edit_text(
            "⚠️ Aniqlanmadi.\n\nQo'shiq nomini *matn* ko'rinishida yuboring!",
            parse_mode="Markdown"
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida yo'q!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
