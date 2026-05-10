"""
مربی مکالمه انگلیسی KAI
- مناسب برای استفاده در ربات بله
- از SQLite مشترک برای ذخیره‌سازی وضعیت هر مکالمه استفاده می‌کند.
- برای شروع اولین پیام کاربر را نادیده گرفته و سؤال اول را می‌فرستد.
- نیاز به نصب: pip install spellchecker
"""

import sqlite3
import re
import random
from difflib import SequenceMatcher

# مسیر دیتابیس (همان bot_data.db در کنار bot.py)
DB_PATH = "bot_data.db"

# -------------------------------
# ۱. بارگذاری اسپل‌چکر (بدون مدل سنگین)
# -------------------------------

# -------------------------------
# ۲. الگوهای اشتباه گرامری رایج
# -------------------------------
GRAMMAR_PATTERNS = [
    (r"\bI is\b", "I am", "فاعل I با am می‌آید، نه is"),
    (r"\bhe go\b", "he goes", "برای سوم شخص مفرد فعل s می‌گیرد"),
    (r"\bshe don't\b", "she doesn't", "برای سوم شخص doesn't استفاده می‌شود"),
    (r"\bI doesn't\b", "I don't", "برای I از don't استفاده می‌کنیم"),
    (r"\bthey is\b", "they are", "فاعل جمع با are می‌آید"),
    (r"\bHe are\b", "He is", "برای he/she/it از is استفاده می‌شود"),
    (r"\bcan to\b", "can", "بعد از can فعل بدون to می‌آید"),
    (r"\bI have been go\b", "I have been going", "بعد از have been فعل ing دار می‌آید"),
    (r"\byou was\b", "you were", "you/were – not was"),
    (r"\bI didn't went\b", "I didn't go", "بعد از did فعل ساده می‌آید"),
]

# -------------------------------
# ۳. دیالوگ‌های آموزشی (۱۰ مرحله)
# -------------------------------
TEACHING_DIALOGS = [
    ("Hello! How are you?", "سلام! حال شما چطور است؟"),
    ("What is your name?", "اسم شما چیست؟"),
    ("Where are you from?", "اهل کجا هستید؟"),
    ("What do you do?", "شغل شما چیست؟"),
    ("Do you like learning English?", "آیا یادگیری انگلیسی را دوست دارید؟"),
    ("How old are you?", "چند سالته؟"),
    ("What time do you usually wake up?", "معمولاً چه ساعتی بیدار می‌شی؟"),
    ("What is your favorite food?", "غذای مورد علاقه‌ات چیه؟"),
    ("Do you have any hobbies?", "آیا سرگرمی داری؟"),
    ("What is your goal in learning English?", "هدف از یادگیری انگلیسی چیه؟"),
]

# -------------------------------
# ۴. توابع ارزیابی پاسخ برای ۱۰ سؤال
# -------------------------------
def check_q0(answer: str):
    positive = ['fine', 'good', 'well', 'okay', 'great', 'not bad', 'wonderful', 'happy']
    if any(w in answer.lower() for w in positive):
        return True, ""
    return False, "I'm fine, thank you."

def check_q1(answer: str):
    if re.search(r"\bmy name is\b", answer.lower()):
        return True, ""
    return False, "My name is [your name]."

def check_q2(answer: str):
    if re.search(r"\b(i am from|i come from)\b", answer.lower()):
        return True, ""
    return False, "I'm from [your country]."

def check_q3(answer: str):
    patterns = [r"\bi am a\b", r"\bi work as\b", r"\bi'm a\b", r"\bi work in\b"]
    if any(re.search(p, answer.lower()) for p in patterns):
        return True, ""
    return False, "I'm a student./I work as a [job]."

def check_q4(answer: str):
    if re.search(r"\b(yes|no|i like|i love|i don't like|i hate)\b", answer.lower()):
        return True, ""
    return False, "Yes, I like it very much. / No, I don't like it."

def check_q5(answer: str):
    if re.search(r"\b(i am|i'm)\s+\d+", answer.lower()):
        return True, ""
    return False, "I am [number] years old."

def check_q6(answer: str):
    if re.search(r"\b(at|around)\s+\d", answer.lower()) or re.search(r"\d\s*(am|pm|o'clock)", answer.lower()):
        return True, ""
    return False, "I usually wake up at [time]."

def check_q7(answer: str):
    food_words = ['pizza', 'pasta', 'rice', 'burger', 'sushi', 'kebab', 'chicken', 'food']
    if any(w in answer.lower() for w in food_words) or re.search(r"\bmy favorite food is\b", answer.lower()):
        return True, ""
    return False, "My favorite food is [food]."

def check_q8(answer: str):
    if re.search(r"\b(yes|no|i like|i enjoy|i love|my hobby)\b", answer.lower()):
        return True, ""
    return False, "Yes, I like [hobby]. / No, I don't have any hobbies."

def check_q9(answer: str):
    if re.search(r"\b(i want to|to travel|to work|to study|to communicate|for my job)\b", answer.lower()):
        return True, ""
    return False, "I want to [reason]."

ANSWER_CHECKS = [check_q0, check_q1, check_q2, check_q3, check_q4,
                 check_q5, check_q6, check_q7, check_q8, check_q9]

# -------------------------------
# ۵. ترجمه‌های فاز پیشرفته
# -------------------------------
ADVANCED_TRANSLATIONS = {
    "Let's talk about {topic}. What do you like about {topic}?":
        "بیایید دربارهٔ {topic} صحبت کنیم. چه چیزی را دوست داری؟",
    "Interesting! Tell me more.": "جالبه! بیشتر توضیح بده.",
    "Why do you think so?": "چرا اینطور فکر می‌کنی؟",
    "Can you give an example?": "می‌تونی مثال بزنی؟",
    "What about the opposite?": "برعکسش چطور؟",
    "Let's continue.": "ادامه بدهیم.",
    "Tell me something else about {topic}.": "یه چیز دیگه دربارهٔ {topic} بگو.",
    "How does {topic} make you feel?": "چه حسی بهت میده {topic}؟",
    "That's right! Well done.": "درسته! آفرین.",
    "Not exactly. Let me help you.": "دقیقاً نه، بذار کمکت کنم.",
    "I see. What else?": "می‌فهمم. چیز دیگه‌ای؟",
    "Really? Tell me more about that.": "واقعاً؟ بیشتر بگو.",
    "That's a great point!": "نکته‌ی خوبی بود!",
    "Can you tell me why?": "می‌تونی بگی چرا؟",
    "What do you mean by that?": "منظورت چیه؟",
}

def translate_advanced(english: str, topic: str = "") -> str:
    template = english.replace(topic, "{topic}") if topic else english
    return ADVANCED_TRANSLATIONS.get(template, english).replace("{topic}", topic)

# -------------------------------
# ۶. ابزارهای تصحیح املا و گرامر
# -------------------------------
def get_spelling_feedback(text: str) -> str:
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    lines = []
    for w in words:
        if w[0].isupper() and len(w) > 1 and (w[1:].islower() or w.isupper()):
            continue

        if w not in spell:
            correct = spell.correction(w)
            if not correct or correct == w:
                continue
            matcher = SequenceMatcher(None, w, correct)
            diffs = []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'replace':
                    diffs.append(f"جایگزینی '{w[i1:i2]}' با '{correct[j1:j2]}'")
                elif tag == 'delete':
                    diffs.append(f"حذف '{w[i1:i2]}'")
                elif tag == 'insert':
                    diffs.append(f"درج '{correct[j1:j2]}'")
            desc = "، ".join(diffs)
            lines.append(f"املای نادرست: «{w}» → «{correct}» ({desc})")
    return "\n".join(lines)

def get_grammar_feedback(text: str) -> str:
    lines = []
    for pattern, correction, explanation in GRAMMAR_PATTERNS:
        match = re.search(pattern, text)
        if match:
            lines.append(f"گرامر: «{match.group()}» نادرست. درست: «{correction}» ({explanation})")
    return "\n".join(lines)

# -------------------------------
# ۷. اطمینان از وجود ستون‌های وضعیت در جدول conversations
# -------------------------------
def init_tutor_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # افزودن ستون‌های جدید در صورت نبود
    for col, col_type in [("tutor_phase", "TEXT"),
                          ("tutor_step", "INTEGER DEFAULT 0"),
                          ("tutor_score", "INTEGER DEFAULT 0"),
                          ("tutor_topic", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE conversations ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # ستون از قبل وجود دارد
    conn.commit()
    conn.close()

# -------------------------------
# ۸. تابع اصلی generate_response
# -------------------------------
def generate_response(user_message: str, conversation_id: int = None) -> str:
    if conversation_id is None:
        return "⚠️ خطا: شناسه مکالمه دریافت نشد."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # خواندن وضعیت
    c.execute("SELECT tutor_phase, tutor_step, tutor_score, tutor_topic FROM conversations WHERE id = ?", (conversation_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "⚠️ مکالمه یافت نشد."

    phase, step, score, topic = row
    if phase is None:
        phase = 'teaching'
    if step is None:
        step = 0
    if score is None:
        score = 0

    # بررسی اولین پیام (اگر هنوز هیچ پیامی در تاریخچه نیست)
    c.execute("SELECT COUNT(*) FROM chat_history WHERE conversation_id = ?", (conversation_id,))
    msg_count = c.fetchone()[0]
    if msg_count == 0 and user_message.strip():
        conn.close()
        # اولین پیام کاربر را نادیده می‌گیریم و سؤال اول آموزش را می‌فرستیم
        eng, fa = TEACHING_DIALOGS[0]
        return f"🗣️ معلم: {eng}\n   🇮🇷 {fa}\n\nپاسخ شما:"

    if not user_message or user_message.strip() == "":
        conn.close()
        return "لطفاً یک پیام ارسال کنید."

    # بررسی املا و گرامر
    spell_fb = get_spelling_feedback(user_message)
    grammar_fb = get_grammar_feedback(user_message)
    fb_parts = []
    if spell_fb:
        fb_parts.append("🔴 اشکالات املایی:\n" + spell_fb)
    if grammar_fb:
        fb_parts.append("🟡 اشکالات گرامری:\n" + grammar_fb)
    feedback = "\n".join(fb_parts)

    # پردازش فاز
    if phase == 'teaching':
        response = _teaching_step(step, score, topic, user_message)
        new_phase, new_step, new_score, new_topic = response['state']
        reply = response['text']
    elif phase == 'test':
        response = _test_step(step, score, user_message)
        new_phase, new_step, new_score, new_topic = response['state']
        reply = response['text']
    elif phase == 'advanced':
        response = _advanced_step(step, score, topic, user_message)
        new_phase, new_step, new_score, new_topic = response['state']
        reply = response['text']
    else:
        conn.close()
        return "این مکالمه پایان یافته است."

    # ذخیره وضعیت جدید
    c.execute("UPDATE conversations SET tutor_phase=?, tutor_step=?, tutor_score=?, tutor_topic=? WHERE id=?",
              (new_phase, new_step, new_score, new_topic, conversation_id))
    conn.commit()
    conn.close()

    final = (feedback + "\n\n" + reply) if feedback else reply
    return final

# -------------------------------
# ۹. فاز آموزش
# -------------------------------
def _teaching_step(step, score, topic, user_msg):
    check_func = ANSWER_CHECKS[step]
    is_correct, example = check_func(user_msg)

    lines = []
    if is_correct:
        lines.append("✅ آفرین! پاسخ شما درست است.")
    else:
        eng_q, fa_q = TEACHING_DIALOGS[step]
        lines.append(f"❌ پاسخ شما کاملاً مناسب نیست.")
        lines.append(f"پاسخ پیشنهادی: «{example}»")
        fa_example = _translate_example(example)
        if fa_example:
            lines.append(f"معنی: {fa_example}")

    new_step = step + 1
    if new_step < len(TEACHING_DIALOGS):
        lines.append(_teaching_question_text(new_step))
        new_phase = 'teaching'
        new_score = score
        new_topic = topic
    else:
        lines.append("📝 آموزش تمام شد. حالا آزمون کوتاه (بدون ترجمه).")
        lines.append(_test_question_text(0))
        new_phase = 'test'
        new_step = 0
        new_score = 0
        new_topic = topic

    reply = "\n".join(lines)
    state = (new_phase, new_step, new_score, new_topic)
    return {'text': reply, 'state': state}

def _teaching_question_text(idx):
    eng, fa = TEACHING_DIALOGS[idx]
    return f"🗣️ معلم: {eng}\n   🇮🇷 {fa}\n\nپاسخ شما:"

def _translate_example(example):
    mapping = {
        "I'm fine, thank you.": "من خوبم، متشکرم.",
        "My name is [your name].": "اسم من [اسم شما] است.",
        "I'm from [your country].": "من اهل [کشور شما] هستم.",
        "I'm a student./I work as a [job].": "من دانشجو هستم / به عنوان [شغل] کار می‌کنم.",
        "Yes, I like it very much. / No, I don't like it.": "بله، خیلی دوست دارم. / نه، دوست ندارم.",
        "I am [number] years old.": "من [عدد] سال دارم.",
        "I usually wake up at [time].": "من معمولاً ساعت [زمان] بیدار می‌شم.",
        "My favorite food is [food].": "غذای مورد علاقه‌م [غذا] است.",
        "Yes, I like [hobby]. / No, I don't have any hobbies.": "بله [سرگرمی] رو دوست دارم. / نه سرگرمی ندارم.",
        "I want to [reason].": "می‌خوام [دلیل].",
    }
    return mapping.get(example, "")

# -------------------------------
# ۱۰. فاز آزمون
# -------------------------------
def _test_step(step, score, user_msg):
    keywords = {
        0: ['fine', 'good', 'well', 'okay'],
        1: ['my name'],
        2: ['from', 'come from'],
        3: ['student', 'work', 'job'],
        4: ['yes', 'no', 'like', 'dislike'],
        5: ['years old'],
        6: ['wake up', 'at', 'o\'clock'],
        7: ['favorite food', 'food'],
        8: ['hobby', 'like', 'enjoy'],
        9: ['goal', 'want to', 'travel', 'work', 'study'],
    }
    kw = keywords[step]
    if any(k in user_msg.lower() for k in kw):
        score += 1
        hint = "✅ درست بود."
    else:
        hint = f"❌ پاسخ مناسبی نبود. پاسخ نمونه: «{_expected_answer(step)}»"

    eng, _ = TEACHING_DIALOGS[step]
    response = f"{hint}\n📝 معلم: {eng}"

    new_step = step + 1
    if new_step < len(TEACHING_DIALOGS):
        response += "\n\n" + _test_question_text(new_step)
        new_phase = 'test'
        new_score = score
        new_topic = None
    else:
        total = len(TEACHING_DIALOGS)
        response += f"\n\n🏁 آزمون تمام شد. امتیاز: {score}/{total}"
        if score >= total * 0.6:
            response += "\n✅ قبول شدید! حالا چه موضوعی می‌خواهید تمرین کنید؟"
            new_phase = 'advanced'
            new_step = 0
            new_score = score
            new_topic = None
        else:
            response += "\n❌ قبول نشدید. یک مکالمهٔ جدید شروع کنید."
            new_phase = 'finished'
            new_step = 0
            new_score = score
            new_topic = None

    state = (new_phase, new_step, new_score, new_topic)
    return {'text': response, 'state': state}

def _expected_answer(idx):
    examples = [
        "I'm fine, thank you.",
        "My name is ...",
        "I'm from ...",
        "I'm a student.",
        "Yes, I like it.",
        "I am 25 years old.",
        "I wake up at 7 am.",
        "My favorite food is pizza.",
        "I like reading.",
        "I want to speak fluently.",
    ]
    return examples[idx] if idx < len(examples) else "..."

def _test_question_text(idx):
    eng, _ = TEACHING_DIALOGS[idx]
    return f"🗣️ معلم: {eng}\n\nپاسخ شما:"

# -------------------------------
# ۱۱. فاز پیشرفته
# -------------------------------
def _advanced_step(step, score, topic, user_msg):
    if not topic:
        new_topic = user_msg.strip()
        if not new_topic:
            return {
                'text': "لطفاً یک موضوع معتبر وارد کنید.\nپاسخ شما:",
                'state': ('advanced', 0, score, None)
            }
        eng = f"Let's talk about {new_topic}. What do you like about {new_topic}?"
        fa = translate_advanced(eng, new_topic)
        return {
            'text': f"🗣️ معلم: {eng}\n   🇮🇷 {fa}\n\nپاسخ شما:",
            'state': ('advanced', 0, score, new_topic)
        }

    positive = ['like', 'love', 'enjoy', 'good', 'great', 'awesome', 'yes', 'interesting']
    negative = ['dislike', 'hate', 'bad', 'terrible', 'no', 'boring']
    if any(w in user_msg.lower() for w in positive):
        pool = [
            "Interesting! Tell me more.",
            "That's great! Can you give an example?",
            "Why do you think so?",
            "Really? Tell me more about that.",
            "That's a great point!",
        ]
    elif any(w in user_msg.lower() for w in negative):
        pool = [
            "I see. What about the opposite?",
            "How does that make you feel?",
            "Tell me something you do like.",
            "I see. What else?",
        ]
    else:
        pool = [
            "Let's continue.",
            f"Tell me something else about {topic}.",
            "Can you explain more?",
            "What do you mean by that?",
            "Can you tell me why?",
        ]
    eng = random.choice(pool)
    fa = translate_advanced(eng, topic)
    return {
        'text': f"🗣️ معلم: {eng}\n   🇮🇷 {fa}\n\nپاسخ شما:",
        'state': ('advanced', 0, score, topic)
    }