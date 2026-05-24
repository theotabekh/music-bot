import os
import asyncio
import aiohttp
import json
import random
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = ["@eng_sara_yangiliklar"]

DATA_FILE = "/tmp/bot_data.json"

def load_data() -> dict:
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "top_songs": {}, "search_count": 0}

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_lang(user_id: int) -> str:
    data = load_data()
    return data["users"].get(str(user_id), {}).get("lang", "uz")

def set_user_lang(user_id: int, lang: str):
    data = load_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {}
    data["users"][str(user_id)]["lang"] = lang
    save_data(data)

def add_user(user_id: int):
    data = load_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"lang": "uz"}
        save_data(data)

def add_search(query: str):
    data = load_data()
    data["search_count"] = data.get("search_count", 0) + 1
    songs = data.get("top_songs", {})
    songs[query] = songs.get(query, 0) + 1
    data["top_songs"] = songs
    save_data(data)

TEXTS = {
    "uz": {
        "welcome": "👋 Salom, *{name}*!\n\n🎵 *Musiqa Bot* ga xush kelibsiz!\n\nQuyidagi tugmalardan foydalaning yoki qo'shiq nomini yozing 👇",
        "subscribe": "⚠️ Botdan foydalanish uchun avval kanalga obuna bo'ling:",
        "subscribed": "✅ *Rahmat! Obuna bo'ldingiz!*\n\nEndi qo'shiq nomi yozing 🎵",
        "not_subscribed": "❌ Hali obuna bo'lmadingiz!",
        "searching": "🔍 Qidirilmoqda: *{query}*...",
        "found": "✅ *{count} ta natija topildi!*",
        "not_found": "❌ Hech narsa topilmadi. Boshqa so'z bilan urinib ko'ring.",
        "preview": "🎵 _(30 soniyalik namuna)_\n👆 To'liq versiya uchun yuqoridagi tugmani bosing",
        "deezer_btn": "🎧 Deezer'da to'liq tinglash",
        "choose_lang": "🌐 Tilni tanlang:",
        "lang_set": "✅ Til o'zgartirildi!",
        "stats": "📊 *Statistika*\n\n👥 Foydalanuvchilar: *{users}* ta\n🔍 Jami qidiruvlar: *{searches}* ta",
        "top": "🔝 *Eng ko'p qidirilgan qo'shiqlar:*\n\n{list}",
        "top_empty": "📭 Hali qidiruvlar yo'q.",
        "random": "🎲 *Tasodifiy qo'shiq qidirilmoqda...*",
        "voice_msg": "🎤 Qo'shiq nomini *matn* ko'rinishida yuboring 👇",
        "subscribed_btn": "✅ Obuna bo'ldim",
        "type_song": "🎵 Qo'shiq nomi yoki artist yozing:",
        "btn_search": "🎵 Musiqa qidirish",
        "btn_random": "🎲 Random musiqa",
        "btn_top": "🔝 Top qo'shiqlar",
        "btn_stats": "📊 Statistika",
        "btn_lang": "🌐 Til tanlash",
    },
    "ru": {
        "welcome": "👋 Привет, *{name}*!\n\n🎵 Добро пожаловать в *Музыкальный Бот*!\n\nИспользуйте кнопки ниже или напишите название песни 👇",
        "subscribe": "⚠️ Подпишитесь на канал, чтобы использовать бота:",
        "subscribed": "✅ *Спасибо! Вы подписались!*\n\nТеперь напишите название песни 🎵",
        "not_subscribed": "❌ Вы ещё не подписались!",
        "searching": "🔍 Поиск: *{query}*...",
        "found": "✅ *Найдено {count} результатов!*",
        "not_found": "❌ Ничего не найдено. Попробуйте другой запрос.",
        "preview": "🎵 _(30-секундный превью)_\n👆 Нажмите выше для полной версии",
        "deezer_btn": "🎧 Слушать на Deezer",
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык изменён!",
        "stats": "📊 *Статистика*\n\n👥 Пользователей: *{users}*\n🔍 Всего поисков: *{searches}*",
        "top": "🔝 *Самые популярные запросы:*\n\n{list}",
        "top_empty": "📭 Запросов ещё нет.",
        "random": "🎲 *Ищем случайную песню...*",
        "voice_msg": "🎤 Напишите название песни текстом 👇",
        "subscribed_btn": "✅ Я подписался",
        "type_song": "🎵 Напишите название песни или артиста:",
        "btn_search": "🎵 Поиск музыки",
        "btn_random": "🎲 Случайная",
        "btn_top": "🔝 Топ песен",
        "btn_stats": "📊 Статистика",
        "btn_lang": "🌐 Язык",
    },
    "en": {
        "welcome": "👋 Hello, *{name}*!\n\n🎵 Welcome to *Music Bot*!\n\nUse the buttons below or type a song name 👇",
        "subscribe": "⚠️ Please subscribe to the channel to use the bot:",
        "subscribed": "✅ *Thank you! You're subscribed!*\n\nNow type a song name 🎵",
        "not_subscribed": "❌ You haven't subscribed yet!",
        "searching": "🔍 Searching: *{query}*...",
        "found": "✅ *Found {count} results!*",
        "not_found": "❌ Nothing found. Try another query.",
        "preview": "🎵 _(30-second preview)_\n👆 Press above for full version",
        "deezer_btn": "🎧 Listen on Deezer",
        "choose_lang": "🌐 Choose language:",
        "lang_set": "✅ Language changed!",
        "stats": "📊 *Statistics*\n\n👥 Users: *{users}*\n🔍 Total searches: *{searches}*",
        "top": "🔝 *Most searched songs:*\n\n{list}",
        "top_empty": "📭 No searches yet.",
        "random": "🎲 *Finding a random song...*",
        "voice_msg": "🎤 Please type the song name as text 👇",
        "subscribed_btn": "✅ I subscribed",
        "type_song": "🎵 Type a song name or artist:",
        "btn_search": "🎵 Search music",
        "btn_random": "🎲 Random",
        "btn_top": "🔝 Top songs",
        "btn_stats": "📊 Statistics",
        "btn_lang": "🌐 Language",
    }
}

RANDOM_QUERIES = ["trending pop 2024", "best hits", "top songs", "popular music", "viral songs"]

def main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Pastki tugmalar (Reply Keyboard)."""
    t = TEXTS[lang]
    keyboard = [
        [KeyboardButton(t["btn_search"]), KeyboardButton(t["btn_random"])],
        [KeyboardButton(t["btn_top"]), KeyboardButton(t["btn_stats"])],
        [KeyboardButton(t["btn_lang"])],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def check_subscription(user_id: int, bot) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            return False
    return True

def subscription_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{channel[1:]}")])
    buttons.append([InlineKeyboardButton(TEXTS[lang]["subscribed_btn"], callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def check_and_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if not await check_subscription(user_id, context.bot):
        await update.message.reply_text(
            TEXTS[lang]["subscribe"],
            parse_mode="Markdown",
            reply_markup=subscription_keyboard(lang)
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

async def download_audio(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None

async def send_tracks(update: Update, results: list, lang: str):
    for track in results[:3]:
        title = track["title"]
        artist = track["artist"]
        preview = track["preview"]
        cover = track["cover"]
        deezer_url = track["deezer_url"]
        buttons = [[InlineKeyboardButton(TEXTS[lang]["deezer_btn"], url=deezer_url)]]
        keyboard = InlineKeyboardMarkup(buttons)
        caption = f"🎵 *{title}*\n👤 _{artist}_"
        if cover:
            await update.message.reply_photo(photo=cover, caption=caption,
                                              parse_mode="Markdown", reply_markup=keyboard)
        if preview:
            audio_data = await download_audio(preview)
            if audio_data:
                await update.message.reply_audio(
                    audio=audio_data,
                    filename=f"{artist} - {title}.mp3",
                    title=title, performer=artist,
                    caption=TEXTS[lang]["preview"],
                    parse_mode="Markdown"
                )
        await asyncio.sleep(0.5)

# ─── Handlers ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    lang = get_user_lang(user.id)
    is_subscribed = await check_subscription(user.id, context.bot)
    if not is_subscribed:
        await update.message.reply_text(
            f"👋 Salom, *{user.first_name}*!\n\n" + TEXTS[lang]["subscribe"],
            parse_mode="Markdown",
            reply_markup=subscription_keyboard(lang)
        )
        return
    await update.message.reply_text(
        TEXTS[lang]["welcome"].format(name=user.first_name),
        parse_mode="Markdown",
        reply_markup=main_keyboard(lang)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_sub":
        lang = get_user_lang(user_id)
        if await check_subscription(user_id, context.bot):
            await query.message.edit_text(TEXTS[lang]["subscribed"], parse_mode="Markdown")
            await context.bot.send_message(
                user_id,
                TEXTS[lang]["welcome"].format(name=query.from_user.first_name),
                parse_mode="Markdown",
                reply_markup=main_keyboard(lang)
            )
        else:
            await query.answer(TEXTS[lang]["not_subscribed"], show_alert=True)

    elif query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        set_user_lang(user_id, lang)
        await query.message.edit_text(TEXTS[lang]["lang_set"])
        await context.bot.send_message(user_id, TEXTS[lang]["welcome"].format(
            name=query.from_user.first_name),
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang)
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_and_notify(update, context):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text.strip()
    t = TEXTS[lang]

    # Pastki tugmalar bosilganda
    if text == t["btn_search"]:
        await update.message.reply_text(t["type_song"], parse_mode="Markdown",
                                        reply_markup=main_keyboard(lang))
        context.user_data["waiting_search"] = True
        return

    elif text == t["btn_random"]:
        msg = await update.message.reply_text(t["random"], parse_mode="Markdown")
        results = await search_deezer(random.choice(RANDOM_QUERIES))
        if not results:
            await msg.edit_text(t["not_found"])
            return
        track = random.choice(results)
        await msg.delete()
        await send_tracks(update, [track], lang)
        return

    elif text == t["btn_top"]:
        data = load_data()
        songs = data.get("top_songs", {})
        if not songs:
            await update.message.reply_text(t["top_empty"])
            return
        sorted_songs = sorted(songs.items(), key=lambda x: x[1], reverse=True)[:10]
        song_list = "\n".join([f"{i+1}. {s[0]} — *{s[1]} marta*" for i, s in enumerate(sorted_songs)])
        await update.message.reply_text(t["top"].format(list=song_list), parse_mode="Markdown")
        return

    elif text == t["btn_stats"]:
        data = load_data()
        await update.message.reply_text(
            t["stats"].format(users=len(data.get("users", {})), searches=data.get("search_count", 0)),
            parse_mode="Markdown"
        )
        return

    elif text == t["btn_lang"]:
        buttons = [
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
             InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        await update.message.reply_text(t["choose_lang"],
                                        reply_markup=InlineKeyboardMarkup(buttons))
        return

    # Oddiy matn — musiqa qidirish
    add_search(text)
    msg = await update.message.reply_text(t["searching"].format(query=text), parse_mode="Markdown")
    results = await search_deezer(text)
    if not results:
        await msg.edit_text(t["not_found"])
        return
    await msg.edit_text(t["found"].format(count=len(results)), parse_mode="Markdown")
    await send_tracks(update, results, lang)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_and_notify(update, context):
        return
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(TEXTS[lang]["voice_msg"], parse_mode="Markdown")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
