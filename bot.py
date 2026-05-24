import os
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# ─── Helpers ────────────────────────────────────────────────────────────────

async def search_music_by_text(query: str) -> list[dict]:
    """Deezer API orqali musiqa qidiradi (bepul, API key shart emas)."""
    url = "https://api.deezer.com/search"
    params = {"q": query, "limit": 5}
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
                    "preview_url": track.get("preview"),   # 30 soniyalik mp3
                    "cover": track["album"].get("cover_medium"),
                    "deezer_url": track.get("link", ""),
                })
            return results


async def recognize_audio_shazam(file_path: str) -> dict | None:
    """ShazamCore RapidAPI orqali ovozli xabarni aniqlaydi."""
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
                "artist": track.get("subtitle", "Noma'lum artist"),
            }


async def download_and_send_preview(update: Update,
                                    preview_url: str,
                                    title: str,
                                    artist: str):
    """30 soniyalik preview mp3 ni yuklab foydalanuvchiga yuboradi."""
    async with aiohttp.ClientSession() as session:
        async with session.get(preview_url) as resp:
            if resp.status != 200:
                return False
            audio_data = await resp.read()

    tmp_path = Path(f"/tmp/{title[:30]}.mp3")
    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(audio_data)

    with open(tmp_path, "rb") as audio_file:
        await update.message.reply_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            caption=f"🎵 *{title}*\n👤 {artist}\n\n_(30 soniyalik namuna)_",
            parse_mode="Markdown",
        )
    tmp_path.unlink(missing_ok=True)
    return True


# ─── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎶 *Musiqa Bot ga xush kelibsiz!*\n\n"
        "Men sizga musiqa topishda yordam beraman:\n\n"
        "📝 *Matn yuboring* — qo'shiq nomi yoki artist\n"
        "🎤 *Ovozli xabar* — qo'shiq parchasi (Shazam aniqlaydi)\n"
        "🎧 *Audio fayl* — musiqani aniqlash uchun\n\n"
        "Bosing va musiqa qidiring! 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Yordam*\n\n"
        "• Qo'shiq nomi yozing → men topaman\n"
        "• Artist nomi yozing → eng mashhur qo'shiqlarini topaman\n"
        "• Ovozli xabar yuboring → Shazam orqali aniqlayman\n"
        "• Audio fayl yuboring → aniqlab, o'xshashlarini topaman\n\n"
        "_Masalan: `Dua Lipa Levitating` deb yozing_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    msg = await update.message.reply_text(f"🔍 *{query}* qidirilmoqda...",
                                          parse_mode="Markdown")

    results = await search_music_by_text(query)
    if not results:
        await msg.edit_text("❌ Hech narsa topilmadi. Boshqa so'z bilan urinib ko'ring.")
        return

    await msg.edit_text(f"✅ *{len(results)} ta natija topildi!*", parse_mode="Markdown")

    for track in results:
        title = track["title"]
        artist = track["artist"]
        preview = track.get("preview_url")
        cover = track.get("cover")
        deezer = track.get("deezer_url", "")

        caption = f"🎵 *{title}*\n👤 _{artist}_"
        buttons = []
        if deezer:
            buttons.append([InlineKeyboardButton("🎧 Deezer'da tinglash", url=deezer)])

        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        # Muqova rasmi bilan yuborish
        if cover:
            await update.message.reply_photo(
                photo=cover,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(caption, parse_mode="Markdown",
                                            reply_markup=keyboard)

        # 30 soniyalik preview audio
        if preview:
            await download_and_send_preview(update, preview, title, artist)

        await asyncio.sleep(0.5)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Audio fayl yoki ovozli xabar."""
    msg = await update.message.reply_text("🎧 Audio tahlil qilinmoqda...")

    # Faylni yuklab olish
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

    if RAPIDAPI_KEY:
        await msg.edit_text("🔎 Shazam orqali aniqlanmoqda...")
        track_info = await recognize_audio_shazam(tmp_path)
    else:
        track_info = None

    # Faylni o'chirish
    Path(tmp_path).unlink(missing_ok=True)

    if track_info:
        title = track_info["title"]
        artist = track_info["artist"]
        await msg.edit_text(
            f"✅ *Topildi!*\n\n🎵 *{title}*\n👤 _{artist}_\n\n"
            "🔍 Endi Deezer'dan qidirilyapti...",
            parse_mode="Markdown"
        )
        results = await search_music_by_text(f"{artist} {title}")
        if results:
            track = results[0]
            preview = track.get("preview_url")
            cover = track.get("cover")
            deezer = track.get("deezer_url", "")
            buttons = []
            if deezer:
                buttons.append([InlineKeyboardButton("🎧 Deezer'da tinglash", url=deezer)])
            keyboard = InlineKeyboardMarkup(buttons) if buttons else None
            caption = f"🎵 *{track['title']}*\n👤 _{track['artist']}_"
            if cover:
                await update.message.reply_photo(photo=cover, caption=caption,
                                                  parse_mode="Markdown",
                                                  reply_markup=keyboard)
            if preview:
                await download_and_send_preview(update, preview,
                                                track["title"], track["artist"])
        else:
            await update.message.reply_text(
                f"ℹ️ Deezer'da '{title}' topilmadi, lekin qo'shiq aniqlanadi:\n"
                f"🎵 *{title}* — _{artist}_",
                parse_mode="Markdown"
            )
    else:
        # Shazam yo'q yoki aniqlay olmadi — matn izlash taklif qilish
        await msg.edit_text(
            "⚠️ Audio aniqlanmadi.\n\n"
            "Qo'shiq nomini *matn* ko'rinishida yuboring, men topaman! 🎵",
            parse_mode="Markdown"
        )


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida yo'q!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
