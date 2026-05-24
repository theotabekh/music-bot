import os
import asyncio
import aiohttp
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNELS = ["@eng_sara_yangiliklar"]


async def check_subscription(user_id: int, bot) -> bool:
    """Foydalanuvchi kanallarga obuna bo'lganmi tekshiradi."""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            return False
    return True


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Obuna tugmalari."""
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{channel[1:]}")])
    buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


async def check_and_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Obuna tekshirib, agar yo'q bo'lsa xabar yuboradi."""
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context.bot)

    if not is_subscribed:
        await update.message.reply_text(
            "⚠️ *Botdan foydalanish uchun quyidagi kanalga obuna bo'ling:*\n\n"
            "Obuna bo'lgandan so'ng ✅ *Obuna bo'ldim* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=subscription_keyboard()
        )
        return False
    return True


async def search_deezer(query: str) -> list:
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
                    "cover": track["album"].get("cover_medium"),
                    "preview": track.get("preview"),
                    "deezer_url": track.get("link", ""),
                })
            return results


async def download_audio(url: str) -> bytes | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context.bot)

    if not is_subscribed:
        await update.message.reply_text(
            f"👋 Salom, *{user.first_name}*!\n\n"
            "🎵 *Musiqa Bot* ga xush kelibsiz!\n\n"
            "⚠️ Botdan foydalanish uchun avval quyidagi kanalga obuna bo'ling:",
            parse_mode="Markdown",
            reply_markup=subscription_keyboard()
        )
        return

    await update.message.reply_text(
        f"👋 Salom, *{user.first_name}*!\n\n"
        "🎵 *Musiqa Bot* ga xush kelibsiz!\n\n"
        "Qo'shiq nomi yoki artist yozing — topib yuboraman!\n\n"
        "_Masalan:_ `Dua Lipa Levitating`",
        parse_mode="Markdown"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obuna bo'ldim tugmasi bosilganda."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_subscribed = await check_subscription(user_id, context.bot)

    if is_subscribed:
        await query.message.edit_text(
            "✅ *Rahmat! Obuna bo'ldingiz!*\n\n"
            "Endi qo'shiq nomi yozing — topib yuboraman 🎵",
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌ Hali obuna bo'lmadingiz! Iltimos, kanalga obuna bo'ling.", show_alert=True)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Obuna tekshirish
    if not await check_and_notify(update, context):
        return

    query = update.message.text.strip()
    if not query:
        return

    msg = await update.message.reply_text(f"🔍 Qidirilmoqda: *{query}*...", parse_mode="Markdown")

    results = await search_deezer(query)

    if not results:
        await msg.edit_text("❌ Hech narsa topilmadi. Boshqa so'z bilan urinib ko'ring.")
        return

    await msg.edit_text(f"✅ *{len(results)} ta natija topildi!*", parse_mode="Markdown")

    for track in results[:3]:
        title = track["title"]
        artist = track["artist"]
        preview = track["preview"]
        cover = track["cover"]
        deezer_url = track["deezer_url"]

        buttons = [[InlineKeyboardButton("🎧 Deezer'da to'liq tinglash", url=deezer_url)]]
        keyboard = InlineKeyboardMarkup(buttons)
        caption = f"🎵 *{title}*\n👤 _{artist}_"

        if cover:
            await update.message.reply_photo(
                photo=cover,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        if preview:
            audio_data = await download_audio(preview)
            if audio_data:
                await update.message.reply_audio(
                    audio=audio_data,
                    filename=f"{artist} - {title}.mp3",
                    title=title,
                    performer=artist,
                    caption="🎵 _(30 soniyalik namuna)_\n👆 To'liq versiya uchun yuqoridagi tugmani bosing",
                    parse_mode="Markdown"
                )

        await asyncio.sleep(0.5)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_and_notify(update, context):
        return

    await update.message.reply_text(
        "🎤 Ovozli xabar qabul qilindi!\n\n"
        "Qo'shiq nomini *matn* ko'rinishida yuboring 👇",
        parse_mode="Markdown"
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    from telegram.ext import CallbackQueryHandler
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
