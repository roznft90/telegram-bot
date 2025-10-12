import re
import logging
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError

# === BOT TOKENİNİ BURAYA YAZ ===
BOT_TOKEN = "8380176620:AAHDSNJIsg-04gETMQNOHEnh7N7Bot5fA9k"

# Liste formatında ilanlar
ilanlar = []

# Kullanıcı bazlı cooldown (spam önleme)
cooldown = {}
COOLDOWN_SECONDS = 5  # aynı kullanıcı 5 saniyede bir ilan girebilir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex: tam format
pattern = re.compile(
    r'^\s*([A-Za-zÇÖÜĞİŞçöüğış0-9\s]+?)\s+alınır\s*[-–]\s*([A-Za-zÇÖÜĞİŞçöüğış0-9\s]+?)\s+verilir\s*$',
    re.IGNORECASE
)

def start(update, context):
    update.message.reply_text(
        "Hoş geldiniz!\n\n"
        "İlan girmek için *tam* şu formatı kullanın:\n"
        "Bursa Merkez alınır - Sinop Gerze verilir\n\n"
        "Not: Bot grupta yalnızca bu formattaki mesajlara cevap verir."
    )

def ilan_kaydet(update, context):
    msg = update.message
    if msg is None:
        return

    text = msg.text or ""
    user = msg.from_user
    user_id = user.id
    chat_id = msg.chat_id
    now = time.time()

    # Cooldown kontrolü
    if user_id in cooldown and now - cooldown[user_id] < COOLDOWN_SECONDS:
        return
    cooldown[user_id] = now

    # Regex ile format kontrolü
    m = pattern.match(text.strip())
    if not m:
        return  # hatalı formata cevap yok

    alinacak_kisim = m.group(1).strip().lower()
    verilecek_kisim = m.group(2).strip().lower()

    # 1 yıl = 365 gün * 24 saat * 3600 saniye
    ONE_YEAR_SECONDS = 365 * 24 * 3600
    # Eski ilanları temizle
    ilanlar[:] = [i for i in ilanlar if now - i["timestamp"] <= ONE_YEAR_SECONDS]

    # Yeni ilanı listeye ekle
    ilanlar.append({
        "user_id": user_id,
        "alinacak": alinacak_kisim,
        "verilecek": verilecek_kisim,
        "chat_id": chat_id,
        "first_name": user.first_name or "",
        "username": user.username or "",
        "timestamp": now
    })

    # Grup içinde onay mesajı
    try:
        context.bot.send_message(chat_id=chat_id, text="✅ İlanınız kaydedildi. Eşleşme aranıyor...")
    except TelegramError as e:
        logger.warning("Onay mesajı gönderilemedi: %s", e)

    # Eşleşmeleri kontrol et
    eslesmeler = []
    for other in list(ilanlar):
        if other["user_id"] == user_id:
            continue
        if other["alinacak"] == verilecek_kisim and other["verilecek"] == alinacak_kisim:
            eslesmeler.append(other)

    for other in eslesmeler:
        emoji_msg = (
            f"🎯 Eşleşme Bulundu! 🎯\n\n"
            f"{user.first_name} ↔ {other['first_name']}\n"
            f"{alinacak_kisim.title()} alınır - {verilecek_kisim.title()} verilir"
        )
        try:
            context.bot.send_message(chat_id=chat_id, text=emoji_msg)
        except TelegramError as e:
            logger.warning("Grup bildirimi gönderilemedi: %s", e)

        # Eşleşen ilanları sil
        if other in ilanlar:
            ilanlar.remove(other)

    # Kullanıcının kendi ilanını sil
    ilanlar[:] = [i for i in ilanlar if i["user_id"] != user_id]

def list_ilanlar(update, context):
    if not ilanlar:
        update.message.reply_text("Aktif ilan bulunmuyor.")
        return

    lines = []
    for i, v in enumerate(ilanlar, 1):
        lines.append(f"{i}. {v.get('first_name','Kullanıcı')}: {v['alinacak'].title()} alınır - {v['verilecek'].title()} verilir")
    update.message.reply_text("\n".join(lines))

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ilanlar", list_ilanlar))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, ilan_kaydet))

    updater.start_polling()
    logger.info("Bot çalışıyor...")
    updater.idle()

if __name__ == "__main__":
    main()
