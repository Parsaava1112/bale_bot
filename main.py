import sqlite3
import os
import logging
import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes, PreCheckoutQueryHandler
)
from Ai_engine.english_KAI import init_tutor_db
init_tutor_db()

# ====== بارگذاری متغیرهای محیطی ======
load_dotenv()
BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")

# ====== تنظیم لاگ ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== ثابت‌های وضعیت مکالمه ======
CHAT_CONTACT, CHAT_MODEL, CHAT_CONVERSATION, CHAT_MSG = range(4)
PROJ_TITLE, PROJ_DESC, PROJ_TIME, PROJ_AMOUNT, PROJ_PHONE = range(4, 9)
SUB_PLAN, SUB_CUSTOM_AMOUNT = range(9, 11)

# ====== دیتابیس ======
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
            conversation_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        c.execute("ALTER TABLE chat_history ADD COLUMN conversation_id INTEGER")
    except sqlite3.OperationalError:
        pass

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            model_key TEXT,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS free_messages (
            user_id INTEGER PRIMARY KEY,
            messages_used INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            plan_name TEXT,
            message_limit INTEGER,
            messages_used INTEGER DEFAULT 0,
            start_date TEXT,
            expiration_date TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()

# ====== بارگذاری مدل‌های هوش مصنوعی ======
def load_ai_models():
    models = {}
    ai_dir = Path(__file__).parent / "Ai_engine"
    if not ai_dir.exists():
        logger.warning("پوشه Ai_engine یافت نشد.")
        return models

    if str(ai_dir.parent) not in sys.path:
        sys.path.insert(0, str(ai_dir.parent))

    for file in ai_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        model_key = file.stem
        display_name = model_key.replace("_", " ").replace("-", " ").title()
        try:
            module = importlib.import_module(f"Ai_engine.{model_key}")
            if hasattr(module, "generate_response"):
                models[model_key] = {"name": display_name, "module": module}
                logger.info(f"مدل '{display_name}' بارگذاری شد.")
            else:
                logger.warning(f"ماژول {model_key} تابع generate_response ندارد.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری مدل {model_key}: {e}")
    return models

AI_MODELS = load_ai_models()

# ====== تابع پاسخ‌دهی ======
def get_ai_response(model_key, user_message, conv_id=None):
    if model_key not in AI_MODELS:
        return "مدل انتخاب شده در دسترس نیست."
    try:
        module = AI_MODELS[model_key]["module"]
        if hasattr(module, 'generate_response'):
            # اگر تابع سه آرگومان بگیرد (مثل مربی)
            import inspect
            sig = inspect.signature(module.generate_response)
            if len(sig.parameters) >= 2:
                return module.generate_response(user_message, conv_id)
            else:
                return module.generate_response(user_message)
        else:
            return "مدل فاقد تابع generate_response است."
    except Exception as e:
        logger.error(f"خطا در generate_response: {e}")
        return "خطایی در تولید پاسخ رخ داد."

# ====== مدیریت دسترسی پیام ======
def get_user_access(user_id, phone_number):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, plan_name, message_limit, messages_used, expiration_date
        FROM subscriptions
        WHERE user_id = ? AND is_active = 1
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    sub = c.fetchone()
    if sub:
        sub_id, plan_name, limit, used, exp_date = sub
        if exp_date:
            if datetime.now() > datetime.fromisoformat(exp_date):
                c.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ?", (sub_id,))
                conn.commit()
                conn.close()
                return False, "اشتراک شما منقضی شده است."
        if limit is not None and used >= limit:
            conn.close()
            return False, "تعداد پیام‌های مجاز به پایان رسیده است."
        conn.close()
        return True, "active_sub"

    c.execute("SELECT messages_used FROM free_messages WHERE user_id = ?", (user_id,))
    free = c.fetchone()
    if free:
        if free[0] < 25:
            conn.close()
            return True, "free"
        else:
            conn.close()
            return False, "۲۵ پیام رایگان شما تمام شده است."
    else:
        c.execute("INSERT INTO free_messages (user_id, messages_used) VALUES (?, 0)", (user_id,))
        conn.commit()
        conn.close()
        return True, "free"

def consume_message(user_id, phone_number):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, message_limit, messages_used FROM subscriptions
        WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1
    """, (user_id,))
    sub = c.fetchone()
    if sub:
        sub_id, limit, used = sub
        if limit is not None:
            c.execute("UPDATE subscriptions SET messages_used = messages_used + 1 WHERE id = ?", (sub_id,))
        conn.commit()
        conn.close()
        return
    c.execute("UPDATE free_messages SET messages_used = messages_used + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ====== مدیریت گفتگوها ======
def get_user_conversations(user_id, model_key, limit=5):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, title, created_at
        FROM conversations
        WHERE user_id = ? AND model_key = ?
        ORDER BY updated_at DESC LIMIT ?
    """, (user_id, model_key, limit))
    convs = c.fetchall()
    conn.close()
    return convs

def create_conversation(user_id, phone_number, model_key, title):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO conversations (user_id, phone_number, model_key, title, created_at, updated_at) VALUES (?,?,?,?,?,?)",
              (user_id, phone_number, model_key, title, now, now))
    conv_id = c.lastrowid
    conn.commit()
    conn.close()
    return conv_id

# ====== توابع راهنمایی کاربر (بدون خروج از حالت) ======
async def remind_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 لطفاً از دکمهٔ «ارسال شماره تماس» استفاده کنید.")
    return CHAT_CONTACT

async def remind_model_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 لطفاً یکی از مدل‌ها را با دکمه‌های بالا انتخاب کنید.")
    return CHAT_MODEL

async def remind_conversation_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 لطفاً از دکمه‌های بالا یک گفتگو را انتخاب کنید یا گفتگوی جدید بسازید.")
    return CHAT_CONVERSATION

async def remind_text_only(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💬 لطفاً پیام خود را به صورت متن بنویسید.")
    return CHAT_MSG

async def remind_sub_plan_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛒 لطفاً یکی از پلن‌های اشتراک را با دکمه انتخاب کنید.")
    return SUB_PLAN

async def remind_custom_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔢 لطفاً فقط یک عدد (تعداد پیام) وارد کنید.")
    return SUB_CUSTOM_AMOUNT

# ====== منوی اصلی ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎨 گالری هنرمندان", url="https://persiarts.runflare.run")],
        [InlineKeyboardButton("💬 گفت‌وگو با چت‌بات", callback_data="start_chat")],
        [InlineKeyboardButton("📬 پیشنهاد پروژه", callback_data="start_project")],
        [InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_subscription")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 به ربات AiClass خوش آمدید! یکی از گزینه‌ها را انتخاب کنید:", reply_markup=reply_markup)

# ====== بخش چت ======
async def chat_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    await update.callback_query.message.reply_text("برای شروع، لطفاً روی دکمه زیر بزنید و شماره خود را ارسال کنید:", reply_markup=reply_markup)
    return CHAT_CONTACT

async def chat_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = contact.phone_number
    name = contact.first_name or update.effective_user.first_name
    context.user_data["phone"] = phone
    context.user_data["name"] = name
    context.user_data["user_id"] = update.effective_user.id

    await update.message.reply_text("✅ شماره ثبت شد.", reply_markup=ReplyKeyboardRemove())

    if not AI_MODELS:
        await update.message.reply_text("❌ هیچ مدلی فعال نیست.")
        return ConversationHandler.END

    keyboard = []
    for key, info in AI_MODELS.items():
        keyboard.append([InlineKeyboardButton(info["name"], callback_data=f"model_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")])
    await update.message.reply_text("🤖 یک مدل انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHAT_MODEL

async def chat_model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text("به منوی اصلی بازگشتید. /start")
        return ConversationHandler.END

    if not data.startswith("model_"):
        await query.edit_message_text("انتخاب نامعتبر.")
        return CHAT_MODEL

    model_key = data[len("model_"):]
    if model_key not in AI_MODELS:
        await query.edit_message_text("مدل یافت نشد.")
        return CHAT_MODEL

    context.user_data["model_key"] = model_key
    model_name = AI_MODELS[model_key]["name"]
    user_id = context.user_data["user_id"]

    conversations = get_user_conversations(user_id, model_key)
    keyboard = [[InlineKeyboardButton("🆕 شروع گفتگوی جدید", callback_data="conv_new")]]
    for conv_id, title, created in conversations:
        date_str = created[:10] if created else ""
        keyboard.append([InlineKeyboardButton(f"{title} ({date_str})", callback_data=f"conv_{conv_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به انتخاب مدل", callback_data="back_to_models")])

    await query.edit_message_text(f"مدل: {model_name}\nیک گفتگو را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHAT_CONVERSATION

async def conversation_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = context.user_data["user_id"]
    model_key = context.user_data["model_key"]

    if data == "back_to_models":
        keyboard = []
        for key, info in AI_MODELS.items():
            keyboard.append([InlineKeyboardButton(info["name"], callback_data=f"model_{key}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")])
        await query.edit_message_text("🤖 یک مدل انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CHAT_MODEL

    if data == "conv_new":
        title = f"گفتگوی {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        conv_id = create_conversation(user_id, context.user_data.get("phone", ""), model_key, title)
        context.user_data["conversation_id"] = conv_id
        context.user_data["conversation_title"] = title
        await query.edit_message_text(f"✅ گفتگوی جدید آغاز شد.\nمدل: {AI_MODELS[model_key]['name']}\nمی‌توانید پیام خود را بنویسید. /cancel برای پایان")
        return CHAT_MSG

    if data.startswith("conv_"):
        try:
            conv_id = int(data[5:])
        except ValueError:
            await query.edit_message_text("شناسه گفتگو نامعتبر.")
            return CHAT_CONVERSATION
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("SELECT id, title FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
        row = c.fetchone()
        conn.close()
        if row:
            context.user_data["conversation_id"] = row[0]
            context.user_data["conversation_title"] = row[1]
            await query.edit_message_text(f"📂 ادامه گفتگو: {row[1]}\nمدل: {AI_MODELS[model_key]['name']}\nپیام خود را بنویسید. /cancel برای پایان")
            return CHAT_MSG
        else:
            await query.edit_message_text("گفتگوی انتخاب شده معتبر نیست.")
            return CHAT_CONVERSATION

    return CHAT_CONVERSATION

async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    phone = context.user_data.get("phone", "")
    name = context.user_data.get("name", user.full_name)
    model_key = context.user_data.get("model_key", "")
    conv_id = context.user_data.get("conversation_id")
    user_msg = update.message.text

    can_send, reason = get_user_access(user_id, phone)
    if not can_send:
        keyboard = [[InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_subscription")]]
        await update.message.reply_text(f"⛔ {reason}\nبرای ادامه، لطفاً اشتراک تهیه کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CHAT_MSG

    try:
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, phone_number, name, message_text, role, model, conversation_id) VALUES (?,?,?,?,?,?,?)",
                  (user_id, phone, name, user_msg, "user", AI_MODELS[model_key]["name"], conv_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پیام کاربر: {e}")
        await update.message.reply_text("❌ مشکلی در ذخیره پیام پیش آمد. لطفاً دوباره تلاش کنید.")
        return CHAT_MSG

    try:
        bot_reply = get_ai_response(model_key, user_msg, conv_id=conv_id)
    except Exception as e:
        logger.error(f"خطا در get_ai_response: {e}")
        bot_reply = "❌ خطایی در تولید پاسخ رخ داد."

    try:
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, phone_number, name, message_text, role, model, conversation_id) VALUES (?,?,?,?,?,?,?)",
                  (user_id, phone, name, bot_reply, "bot", AI_MODELS[model_key]["name"], conv_id))
        c.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), conv_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پاسخ بات: {e}")

    try:
        consume_message(user_id, phone)
    except Exception as e:
        logger.error(f"خطا در consume_message: {e}")

    await update.message.reply_text(bot_reply)
    return CHAT_MSG

async def cancel_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفتگو پایان یافت. /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ====== بخش پروژه ======
async def project_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📌 عنوان پروژه را وارد کنید:")
    return PROJ_TITLE

async def project_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 توضیحات پروژه را بنویسید:")
    return PROJ_DESC

async def project_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("⏱ زمان پیشنهادی را وارد کنید:")
    return PROJ_TIME

async def project_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["proposed_time"] = update.message.text
    await update.message.reply_text("💰 مبلغ پروژه را به تومان وارد کنید:")
    return PROJ_AMOUNT

async def project_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    contact_button = KeyboardButton("📱 ارسال شماره همراه", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("📞 شماره همراه خود را ارسال کنید:", reply_markup=reply_markup)
    return PROJ_PHONE

async def project_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("لطفاً از دکمه اشتراک‌گذاری مخاطب استفاده کنید.")
        return PROJ_PHONE

    phone = contact.phone_number
    user_id = update.effective_user.id
    title = context.user_data.get("title")
    desc = context.user_data.get("description")
    time = context.user_data.get("proposed_time")
    amount = context.user_data.get("amount")

    try:
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO projects (user_id, title, description, proposed_time, amount, phone_number) VALUES (?,?,?,?,?,?)",
                  (user_id, title, desc, time, amount, phone))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ذخیره پروژه: {e}")
        await update.message.reply_text("❌ مشکلی در ثبت پروژه پیش آمد. لطفاً دوباره تلاش کنید.")
        return PROJ_PHONE

    admin_msg = (
        f"📬 پروژه جدید\n"
        f"👤 کاربر: {user_id}\n"
        f"📌 عنوان: {title}\n"
        f"📝 شرح: {desc}\n"
        f"⏱ زمان: {time}\n"
        f"💰 مبلغ: {amount} تومان\n"
        f"📞 شماره: {phone}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
    except Exception as e:
        logger.error(f"ارسال به ادمین ناموفق: {e}")

    await update.message.reply_text("✅ پروژه ثبت شد. به‌زودی تماس می‌گیریم.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ارسال پروژه لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ====== خرید اشتراک (پرداخت رسمی) ======
async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🥈 نقره‌ای - ۱۰۰ پیام (۹۰,۰۰۰ تومان، ۱ ماهه)", callback_data="sub_silver")],
        [InlineKeyboardButton("🥇 طلایی - ۳۰۰ پیام (۲۰۰,۰۰۰ تومان، ۳ ماهه)", callback_data="sub_gold")],
        [InlineKeyboardButton("💎 الماسی - بی‌نهایت (۵۰۰,۰۰۰ تومان، ۱ ساله)", callback_data="sub_diamond")],
        [InlineKeyboardButton("🔢 سفارشی - تعداد پیام دلخواه (هر پیام ۱,۰۰۰ تومان)", callback_data="sub_custom")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu_sub")],
    ]
    await query.edit_message_text("🛒 یک پلن اشتراک انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SUB_PLAN

async def sub_plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_menu_sub":
        await query.edit_message_text("به منوی اصلی بازگشتید. /start")
        return ConversationHandler.END

    if data == "sub_custom":
        await query.edit_message_text("🔢 تعداد پیام مورد نظر خود را وارد کنید:")
        return SUB_CUSTOM_AMOUNT

    plans = {
        "sub_silver": ("نقره‌ای", 100, 90000, 1),
        "sub_gold": ("طلایی", 300, 200000, 3),
        "sub_diamond": ("الماسی", None, 500000, 12),
    }
    if data not in plans:
        await query.edit_message_text("انتخاب نامعتبر.")
        return SUB_PLAN

    plan_name, limit, price, months = plans[data]
    context.user_data["sub_plan"] = (plan_name, limit, price, months)
    await send_invoice_for_plan(update.effective_chat.id, context)
    await query.edit_message_text("✅ فاکتور پرداخت ارسال شد. لطفاً پرداخت را انجام دهید.")
    return ConversationHandler.END

async def sub_custom_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("لطفاً یک عدد معتبر و بزرگتر از صفر وارد کنید:")
        return SUB_CUSTOM_AMOUNT
    count = int(text)
    total_price = count * 1000
    context.user_data["sub_plan"] = ("سفارشی", count, total_price, "نامحدود")
    await send_invoice_for_plan(update.effective_chat.id, context)
    await update.message.reply_text("✅ فاکتور سفارشی ارسال شد. لطفاً پرداخت را انجام دهید.")
    return ConversationHandler.END

async def send_invoice_for_plan(chat_id, context):
    plan_name, limit, price, months = context.user_data["sub_plan"]
    title = f"اشتراک {plan_name}"
    description = f"پلن {plan_name}: {'بی‌نهایت' if limit is None else limit} پیام، {months} ماهه"
    payload = f"{plan_name}_{chat_id}_{datetime.now().timestamp()}"
    prices = [LabeledPrice(title, price * 10)]  # ریال
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="IRR",
        prices=prices,
        need_phone_number=True
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment = update.message.successful_payment
    phone = update.message.contact.phone_number if update.message.contact else ""
    payload = payment.invoice_payload

    plan_name = "نامشخص"
    limit = None
    months = 0
    if "نقره‌ای" in payload:
        plan_name = "نقره‌ای"; limit = 100; months = 1
    elif "طلایی" in payload:
        plan_name = "طلایی"; limit = 300; months = 3
    elif "الماسی" in payload:
        plan_name = "الماسی"; limit = None; months = 12
    elif "سفارشی" in payload:
        plan_name = "سفارشی"
        total_tomans = payment.total_amount / 10
        limit = int(total_tomans / 1000)
        months = "نامحدود"

    now = datetime.now()
    expiration = (now + timedelta(days=30 * months)).isoformat() if months != "نامحدود" else None

    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
    c.execute("INSERT INTO subscriptions (user_id, phone_number, plan_name, message_limit, messages_used, start_date, expiration_date, is_active) VALUES (?,?,?,?,?,?,?,1)",
              (user_id, phone, plan_name, limit, 0, now.isoformat(), expiration))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🎉 پرداخت موفق!\n✅ اشتراک {plan_name} با {'بی‌نهایت' if limit is None else limit} پیام فعال شد.\nاز /start برای گفتگو استفاده کنید."
    )

# ====== مدیریت خطا ======
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="خطا در پردازش به‌روزرسانی:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید یا /start را بزنید.")

# ====== تابع اصلی ======
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).base_url("https://tapi.bale.ai/bot").build()
    app.add_error_handler(error_handler)

    # هندلرهای پرداخت
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", lambda u, c: buy_subscription(u, c)))

    # مکالمه چت
    chat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(chat_contact_start, pattern="^start_chat$")],
        states={
            CHAT_CONTACT: [
                MessageHandler(filters.CONTACT, chat_contact_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_contact),
            ],
            CHAT_MODEL: [
                CallbackQueryHandler(chat_model_selected, pattern="^(model_|back_to_menu)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_model_buttons),
            ],
            CHAT_CONVERSATION: [
                CallbackQueryHandler(conversation_selection, pattern="^(conv_|back_to_models)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_conversation_buttons),
            ],
            CHAT_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message),
                MessageHandler(~filters.COMMAND, remind_text_only),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_chat)],
    )
    app.add_handler(chat_conv)

    # مکالمه پروژه
    proj_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(project_start, pattern="^start_project$")],
        states={
            PROJ_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, project_title),
                MessageHandler(~filters.COMMAND, lambda u, c: (u.message.reply_text("📌 لطفاً عنوان را به صورت متن وارد کنید."), PROJ_TITLE)[-1]),
            ],
            PROJ_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, project_desc),
                MessageHandler(~filters.COMMAND, lambda u, c: (u.message.reply_text("📝 توضیحات را به صورت متن بنویسید."), PROJ_DESC)[-1]),
            ],
            PROJ_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, project_time),
                MessageHandler(~filters.COMMAND, lambda u, c: (u.message.reply_text("⏱ زمان را به صورت متن وارد کنید."), PROJ_TIME)[-1]),
            ],
            PROJ_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, project_amount),
                MessageHandler(~filters.COMMAND, lambda u, c: (u.message.reply_text("💰 مبلغ را به صورت عدد وارد کنید."), PROJ_AMOUNT)[-1]),
            ],
            PROJ_PHONE: [
                MessageHandler(filters.CONTACT, project_phone),
                MessageHandler(~filters.COMMAND, lambda u, c: (u.message.reply_text("📞 لطفاً از دکمهٔ ارسال شماره همراه استفاده کنید."), PROJ_PHONE)[-1]),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_project)],
    )
    app.add_handler(proj_conv)

    # مکالمه خرید اشتراک
    sub_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_subscription, pattern="^buy_subscription$")],
        states={
            SUB_PLAN: [
                CallbackQueryHandler(sub_plan_selected, pattern="^(sub_|back_to_menu_sub)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_sub_plan_buttons),
            ],
            SUB_CUSTOM_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sub_custom_amount_received),
                MessageHandler(~filters.COMMAND, remind_custom_number),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_project)],
    )
    app.add_handler(sub_conv)

    print("✅ ربات آمادهٔ کار است...")
    app.run_polling()

if __name__ == "__main__":
    main()