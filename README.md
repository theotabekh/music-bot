# 🎵 Telegram Musiqa Bot — O'rnatish Qo'llanmasi

## Bot nima qila oladi?

| Funksiya | Tavsif |
|---|---|
| 📝 Matn qidirish | Qo'shiq yoki artist nomi yozing |
| 🎤 Ovozli xabar | Shazam orqali aniqlaydi |
| 🎧 30s namuna | Topilgan qo'shiqni preview sifatida yuboradi |
| 🖼️ Muqova | Albom rasmi bilan chiqadi |
| 🔗 Deezer link | To'liq tinglash uchun havola |

---

## 1-qadam — Python o'rnatish

Python 3.10+ bo'lishi kerak:
```bash
python --version
```

---

## 2-qadam — Botni yaratish (@BotFather)

1. Telegramda `@BotFather` ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `My Music Bot`)
4. Username kiriting (masalan: `mymusicfinder_bot`)
5. **Token** ni nusxalab oling — u shunday ko'rinadi:
   ```
   7123456789:AAHdqTcvCH1vGWJxfSeofSs0K5PALDsaw
   ```

---

## 3-qadam — Fayllarni sozlash

```bash
# Papkaga o'tish
cd music_bot

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# .env fayl yaratish
cp .env.example .env
```

`.env` faylini oching va tokenni kiriting:
```
BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSs0K5PALDsaw
```

---

## 4-qadam — Shazam (ixtiyoriy, ovoz uchun)

Ovozli xabardan musiqa aniqlash uchun:

1. https://rapidapi.com ga kiring (bepul ro'yxatdan o'ting)
2. `Shazam Core` API ni qidiring
3. **Subscribe** (bepul Basic plan — 500 so'rov/oy)
4. API key ni nusxalab `.env` ga qo'shing:
   ```
   RAPIDAPI_KEY=abc123...
   ```

> ⚠️ RAPIDAPI_KEY bo'lmasa ham bot ishlaydi — faqat matn qidirish bilan.

---

## 5-qadam — Botni ishga tushirish

```bash
python bot.py
```

Konsolda quyidagi chiqsa, bot tayyor:
```
🤖 Bot ishga tushdi!
```

---

## Foydalanish

Botga Telegramdan yozing:

```
Dua Lipa Levitating
```
yoki
```
Coldplay Yellow
```

Yoki ovozli xabar yuboring (qo'shiq parchasi) — Shazam aniqlaydi!

---

## Server (24/7 ishlashi uchun)

### Variant A — Bepul (Railway.app)
1. https://railway.app ga kiring
2. GitHub repo yarating va fayllarni yuklang
3. Environment variable sifatida `BOT_TOKEN` ni qo'shing
4. Deploy qiling

### Variant B — VPS (DigitalOcean, Hetzner)
```bash
# Screen yoki systemd bilan fonga yuborish
screen -S musicbot
python bot.py
# Ctrl+A, D — fonga o'tkazish
```

### Variant C — Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

---

## Muammolar

| Xato | Yechim |
|---|---|
| `BOT_TOKEN not found` | `.env` faylini tekshiring |
| `Unauthorized` | Token noto'g'ri, @BotFather dan qayta oling |
| `Shazam aniqlamadi` | RAPIDAPI_KEY ni tekshiring yoki bepul limitni |
| Audio yuklanmaydi | Fayl hajmi 20MB dan oshmasligi kerak |
