import sqlite3
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# ------------------------- بارگذاری متغیرهای محیطی -------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# ------------------------- ثابت‌های وضعیت مکالمه -------------------------
CHAT_CONTACT, CHAT_MODEL, CHAT_MSG = range(3)
PROJ_TITLE, PROJ_DESC, PROJ_TIME, PROJ_AMOUNT, PROJ_PHONE = range(3, 8)

# ------------------------- دیتابیس -------------------------
def init_db():
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            name TEXT,
            message_text TEXT,
            role TEXT,
            model TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            proposed_time TEXT,
            amount TEXT,
            phone_number TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ------------------------- مدل‌های هوش مصنوعی (نمونه) -------------------------
def get_ai_response(model_name, user_message):
    """
    این تابع را با مدل‌های واقعی خود جایگزین کنید.
    """
    if model_name == "مدل ۱":
        return f"پاسخ مدل ۱ به پیام شما: {user_message[::-1]}"
    elif model_name == "مدل ۲":
        return f"مدل ۲ می‌گوید: {user_message.upper()}"
    else:
        return f"مدل انتخاب شده ({model_name}) در حال حاضر در دسترس نیست."

# ------------------------- منوی اصلی -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎨 گالری هنرمندان", url="https://your-gallery-link.com")],
        [InlineKeyboardButton("🌐 سایت اصلی هوش مصنوعی", url="https://your-ai-site.com")],
        [InlineKeyboardButton("💬 گفت‌وگو با چت‌بات", callback_data="start_chat")],
        [InlineKeyboardButton("📬 پیشنهاد پروژه", callback_data="start_project")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 به ربات من خوش آمدید! یکی از گزینه‌ها را انتخاب کنید:", reply_markup=reply_markup)

# ------------------------- بخش چت با هوش مصنوعی -------------------------
async def chat_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """درخواست شماره تماس از کاربر"""
    contact_button = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    await update.callback_query.message.reply_text(
        "برای شروع گفت‌وگو، لطفاً دکمهٔ زیر را بزنید تا شمارهٔ شما دریافت شود.",
        reply_markup=reply_markup
    )
    return CHAT_CONTACT

async def chat_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره شماره و درخواست انتخاب مدل"""
    contact = update.message.contact
    phone = contact.phone_number
    user_id = update.effective_user.id
    name = contact.first_name or update.effective_user.first_name
    context.user_data["phone"] = phone
    context.user_data["name"] = name

    await update.message.reply_text("✅ شماره شما ثبت شد.", reply_markup=ReplyKeyboardRemove())

    keyboard = [
        [InlineKeyboardButton("مدل ۱", callback_data="model_1")],
        [InlineKeyboardButton("مدل ۲", callback_data="model_2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 لطفاً مدل هوش مصنوعی مورد نظر را انتخاب کنید:", reply_markup=reply_markup)
    return CHAT_MODEL

async def chat_model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره مدل و شروع چت"""
    query = update.callback_query
    await query.answer()
    model_map = {
        "model_1": "مدل ۱",
        "model_2": "مدل ۲"
    }
    model_name = model_map.get(query.data, "مدل ناشناخته")
    context.user_data["model"] = model_name
    await query.edit_message_text(f"✅ مدل انتخاب شده: {model_name}\nحالا می‌توانید پیام خود را بنویسید. برای پایان /cancel را بفرستید.")
    return CHAT_MSG

async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به پیام کاربر و ذخیره تاریخچه"""
    user = update.effective_user
    user_id = user.id
    name = context.user_data.get("name", user.full_name)
    phone = context.user_data.get("phone", "")
    model = context.user_data.get("model", "نامشخص")
    user_msg = update.message.text

    # ذخیره پیام کاربر در دیتابیس
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, phone_number, name, message_text, role, model) VALUES (?,?,?,?,?,?)",
              (user_id, phone, name, user_msg, "user", model))
    conn.commit()
    conn.close()

    # گرفتن پاسخ از هوش مصنوعی
    bot_reply = get_ai_response(model, user_msg)

    # ذخیره پاسخ بات
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, phone_number, name, message_text, role, model) VALUES (?,?,?,?,?,?)",
              (user_id, phone, name, bot_reply, "bot", model))
    conn.commit()
    conn.close()

    await update.message.reply_text(bot_reply)
    return CHAT_MSG

async def cancel_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو با چت‌بات پایان یافت. برای بازگشت به منوی اصلی /start را بزنید.",
                                    reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ------------------------- بخش پیشنهاد پروژه -------------------------
async def project_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📌 لطفاً **عنوان پروژه** را وارد کنید:")
    return PROJ_TITLE

async def project_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 حالا **متن پیشنهاد** (توضیحات کامل پروژه) را بنویسید:")
    return PROJ_DESC

async def project_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("⏱ **زمان پیشنهادی** برای انجام پروژه (مثلاً ۳ روز، یک هفته) را وارد کنید:")
    return PROJ_TIME

async def project_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["proposed_time"] = update.message.text
    await update.message.reply_text("💰 **مبلغ پروژه** را به تومان وارد کنید (فقط عدد):")
    return PROJ_AMOUNT

async def project_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    contact_button = KeyboardButton("📱 ارسال شماره همراه", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📞 لطفاً شماره همراه خود را از طریق دکمهٔ زیر ارسال کنید:", reply_markup=reply_markup)
    return PROJ_PHONE

async def project_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("لطفاً از دکمهٔ اشتراک‌گذاری مخاطب استفاده کنید.")
        return PROJ_PHONE

    phone = contact.phone_number
    user_id = update.effective_user.id
    title = context.user_data.get("title")
    desc = context.user_data.get("description")
    time = context.user_data.get("proposed_time")
    amount = context.user_data.get("amount")

    # ذخیره در دیتابیس
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("INSERT INTO projects (user_id, title, description, proposed_time, amount, phone_number) VALUES (?,?,?,?,?,?)",
              (user_id, title, desc, time, amount, phone))
    conn.commit()
    conn.close()

    # ارسال به ادمین
    admin_msg = (
        f"📬 **پیشنهاد پروژه جدید**\n"
        f"👤 کاربر: {user_id}\n"
        f"📌 عنوان: {title}\n"
        f"📝 شرح: {desc}\n"
        f"⏱ زمان: {time}\n"
        f"💰 مبلغ: {amount} تومان\n"
        f"📞 شماره: {phone}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

    await update.message.reply_text(
        "✅ پروژه شما با موفقیت ثبت شد و برای فریلنسر ارسال گردید. به‌زودی با شما تماس گرفته خواهد شد.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ارسال پروژه لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ------------------------- تابع اصلی -------------------------
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).base_url("https://tapi.bale.ai/bot").build()

    app.add_handler(CommandHandler("start", start))

    # مکالمه چت با هوش مصنوعی
    chat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(chat_contact_start, pattern="^start_chat$")],
        states={
            CHAT_CONTACT: [MessageHandler(filters.CONTACT, chat_contact_received)],
            CHAT_MODEL: [CallbackQueryHandler(chat_model_selected, pattern="^model_")],
            CHAT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel_chat)]
    )
    app.add_handler(chat_conv)

    # مکالمه پیشنهاد پروژه
    proj_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(project_start, pattern="^start_project$")],
        states={
            PROJ_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_title)],
            PROJ_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_desc)],
            PROJ_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_time)],
            PROJ_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_amount)],
            PROJ_PHONE: [MessageHandler(filters.CONTACT, project_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_project)]
    )
    app.add_handler(proj_conv)

    print("✅ ربات شروع به کار کرد...")
    app.run_polling()

if __name__ == "__main__":
    main()