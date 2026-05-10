"""
سیستم دستیار پزشکی هوشمند 
تشخیص بیماری‌های شایع، پارکینسون و تفسیر آزمایش‌ها
 مبتنی بر قواعد و کلیدواژه‌های فارسی
هشدار: این نرم‌افزار جایگزین پزشک نیست.
"""

import re
import numpy as np
import warnings
warnings.filterwarnings("ignore")

import re
from typing import Dict, List, Tuple

# -------------------------------------------------------------------
# ۱. استخراج علائم مبتنی بر قواعد (Rule‑Based) – سریع و بدون نیاز به مدل
# -------------------------------------------------------------------
class RuleBasedSymptomExtractor:
    """
    استخراج علائم از متن فارسی با استفاده از کلیدواژه‌ها و قواعد نفی و شدت.
    این نسخه برای پوشش طیف بسیار گسترده‌ای از بیماری‌ها (حتی نادر) توسعه یافته است.
    """

    def __init__(self):
        # دیکشنری جامع علائم: هر کلید یک علامت بالینی و مقدار لیست عبارات فارسی است.
        self.symptom_keywords = {
            # عمومی و عفونی
            "fever": ["تب", "درجه حرارت بالا", "حرارت بدن", "تب شدید", "تب خفیف"],
            "chills": ["لرز", "سرما", "سرد شدن بدن", "لرزش سرد"],
            "cough": ["سرفه", "سرفه‌های خشک", "سرفه می‌کنم", "سرفم"],
            "cough_productive": ["سرفه خلط دار", "خلط", "سرفه با خلط", "سرفه چرکی", "بلغم"],
            "shortness_of_breath": ["تنگی نفس", "نفس تنگی", "نمی‌تونم نفس بکشم", "کمبود نفس", "نفس کم"],
            "chest_pain": ["درد قفسه سینه", "درد سینه", "قلبم درد می‌کنه", "سینه درد"],
            "left_arm_pain": ["درد دست چپ", "دست چپم درد می‌کنه", "درد بازوی چپ"],
            "palpitations": ["تپش قلب", "ضربان قلب بالا", "قلبم تند می‌زنه", "تپش", "تپش تند"],
            "fatigue": ["خستگی مفرط", "خستگی زیاد", "بی حالی", "بی‌حال", "بی‌رمق", "ضعف عمومی"],
            "weight_loss": ["کاهش وزن", "وزن کم کردم", "لاغر شدم بی‌دلیل", "وزن از دست دادم"],
            "weight_gain": ["افزایش وزن", "وزن اضافه کردم", "چاق شدم", "وزن زیاد"],
            "night_sweats": ["تعریق شبانه", "عرق شب", "شبها عرق می‌کنم", "عرق شبانه"],
            "loss_of_appetite": ["بی اشتهایی", "اشتها ندارم", "میل به غذا ندارم", "بی‌میل به غذا"],
            "general_malaise": ["کسالت", "بی‌حالی", "درد بدن", "خستگی دائمی"],
            # گوارشی
            "abdominal_pain": ["درد شکم", "دل درد", "شکم درد", "دل پیچه"],
            "lower_abdominal_pain": ["درد زیر شکم", "درد پایین شکم", "درد لگن"],
            "nausea": ["تهوع", "حالت تهوع", "بالا آوردن", "دل به هم خوردگی"],
            "vomiting": ["استفراغ", "بالا آوردم", "استفراغ کردم", "تهوع و استفراغ"],
            "diarrhea": ["اسهال", "شکم روش", "مدفوع شل", "اسهال آبکی"],
            "constipation": ["یبوست", "گرفتگی شکم", "دفع سخت", "شکم کار نمیکنه"],
            "heartburn": ["سوزش سر دل", "ترش کردن", "ریفلاکس", "سوزش معده"],
            "dysphagia": ["مشکل در بلع", "نمی‌تونم قورت بدم", "بلع سخت", "غذا گیر می‌کنه"],
            "odynophagia": ["بلع دردناک", "موقع بلع درد دارم", "گلو درد هنگام قورت"],
            # عصبی
            "headache": ["سردرد", "سر درد", "کله درد", "سردرد شدید"],
            "dizziness": ["سرگیجه", "گیجی", "منگی", "عدم تعادل"],
            "neck_stiffness": ["سفتی گردن", "گردن خشک", "گردنم سفت شده"],
            "photophobia": ["حساسیت به نور", "نور اذیتم می‌کنه", "چشم درد با نور", "نور ترسی"],
            "facial_droop": ["کج شدن صورت", "افتادگی صورت", "صورتم کج شده"],
            "arm_weakness": ["ضعف دست", "دستم ضعیف شده", "نمی‌تونم دستم رو بلند کنم"],
            "arm_numbness": ["بی حسی دست", "دستم بی حس شده", "گزگز دست"],
            "speech_difficulty": ["اختلال تکلم", "نمی‌تونم حرف بزنم", "گفتار مشکل", "ناتوانی در صحبت"],
            "unilateral_weakness": ["ضعف نیمه بدن", "یک طرف بدنم ضعیف شده", "فلج نیمه"],
            "diplopia": ["دوبینی", "دو تا می‌بینم", "تاری دو بینی"],
            "seizure": ["تشنج", "غش کردن", "حرکات تشنجی", "صرع"],
            "paresthesia": ["گزگز", "سوزن سوزن شدن", "پارستزی", "مور مور"],
            "memory_loss": ["فراموشی", "کاهش حافظه", "یادم می‌ره", "آلزایمر"],
            "tremor": ["لرزش", "دست هام می‌لرزه", "لرزیدن", "لرزش دست"],
            "rest_tremor": ["لرزش در استراحت", "لرزش دست موقع استراحت"],
            "bradykinesia": ["کندی حرکت", "حرکاتم کند شده", "کند حرکت می‌کنم"],
            "rigidity": ["سفتی عضلات", "عضلاتم سفت شده", "سفتی بدن"],
            "gait_disturbance": ["اختلال راه رفتن", "راه رفتنم مشکل داره", "تلوتلو می‌خورم"],
            "early_falls": ["افتادن های مکرر", "زمین خوردن زیاد", "مدام می‌افتم"],
            "visual_hallucinations": ["توهم بینایی", "چیزایی می‌بینم که نیستن", "توهم دیداری"],
            "depression_anxiety": ["افسردگی و اضطراب", "افسرده", "مضطرب", "نگرانی مداوم"],
            # تنفسی / گوش و حلق و بینی
            "sore_throat": ["گلو درد", "گلودرد", "گلویم درد می‌کنه"],
            "runny_nose": ["آبریزش بینی", "آب بینی", "زکام", "سرماخوردگی"],
            "hemoptysis": ["خون بالا آوردن", "خلط خونی", "سرفه خونی", "خون در خلط"],
            "wheezing": ["خس‌خس سینه", "خس خس", "نفس خس خس دار", "صدای خس"],
            "stridor": ["صدای استریدور", "صدای بلند تنفسی", "خس‌خس حنجره"],
            # ادراری
            "dysuria": ["سوزش ادرار", "ادرار سوزش داره", "سوزش موقع ادرار"],
            "polyuria": ["تکرر ادرار", "ادرار زیاد", "زیاد دستشویی می‌رم"],
            "oliguria": ["کم ادراری", "ادرار کم", "تعداد دفعات کم ادرار"],
            "nocturia": ["شب ادراری", "بیدار شدن برای ادرار", "ادرار شبانه"],
            "flank_pain": ["درد پهلو", "درد کلیه", "درد پهلوها"],
            # پوست و خون
            "pruritus": ["خارش پوست", "خارش بدن", "پوستم می‌خاره"],
            "jaundice": ["زردی پوست", "زرد شدن پوست", "یرقان", "زردی چشم"],
            "abnormal_bleeding": ["خونریزی غیرعادی", "خونریزی بی‌دلیل", "خونریزی زیاد"],
            "easy_bruising": ["کبودی سریع", "زود کبود می‌شم", "کبودی بی‌دلیل"],
            "petechiae": ["پتشي", "دانه‌های قرمز زیرپوستی", "لکه‌های خونریزی"],
            "purpura": ["پورپورا", "کبودی‌های سطحی", "لکه‌های بنفش"],
            "rash": ["بثورات پوستی", "جوش", "دانه های پوستی", "راش"],
            "mouth_ulcers": ["زخم دهان", "آفت دهان", "زخم‌های دهانی"],
            "alopecia": ["ریزش مو", "موهام می‌ریزه", "کم پشت شدن مو", "طاسی"],
            # متابولیک
            "polydipsia": ["تشنگی زیاد", "تشنگی مفرط", "زیاد تشنه می‌شم"],
            "polyphagia": ["گرسنگی زیاد", "پرخوری بی‌دلیل", "همیشه گرسنه ام"],
            "blurred_vision": ["تاری دید", "تار می‌بینم", "دید تار"],
            "dry_mouth": ["خشکی دهان", "دهان خشک", "دهنم خشک می‌شه"],
            "cold_intolerance": ["عدم تحمل سرما", "سردم میشه همیشه", "نمی‌تونم سرما رو تحمل کنم"],
            "heat_intolerance": ["عدم تحمل گرما", "گرمم میشه زیاد", "از گرما بدم میاد"],
            "excessive_sweating": ["تعریق زیاد", "عرق کردن بی‌دلیل", "همیشه عرق می‌کنم"],
            # عضلانی-اسکلتی
            "back_pain": ["کمر درد", "درد کمر", "پشت درد", "درد ستون فقرات"],
            "joint_pain": ["درد مفاصل", "مفاصل درد", "زانو درد", "دست درد مفصلی"],
            "joint_swelling": ["تورم مفاصل", "مفصل باد کرده", "زانو ورم کرده"],
            "morning_stiffness": ["سفتی صبحگاهی", "صبح‌ها خشکم", "خشکی مفاصل صبح"],
            "muscle_pain": ["درد عضلانی", "عضله درد", "بدن درد", "گرفتگی عضلات"],
            "muscle_weakness": ["ضعف عضلانی", "نمی‌تونم بلند شم", "پاهام ضعیف شده"],
            # چشمی
            "red_eye": ["قرمزی چشم", "چشم قرمز", "چشم قرمز شده"],
            "eye_pain": ["درد چشم", "چشمم درد می‌کنه", "درد حدقه چشم"],
            "vision_loss": ["کاهش بینایی", "بیناییم کم شده", "نمی‌بینم خوب"],
            # گوش
            "hearing_loss": ["کم شنوایی", "گوشم سنگین شده", "نمی‌شنوم"],
            "tinnitus": ["وزوز گوش", "صدای زنگ تو گوش", "صدای سوت در گوش"],
            # قلبی-عروقی
            "edema": ["ورم پاها", "پاهام ورم کرده", "ادم", "تورم پا"],
            "claudication": ["درد ساق پا هنگام راه رفتن", "پا درد موقع راه", "درد عضلانی پا با فعالیت"],
            "cold_extremities": ["دست و پای سرد", "انگشتان سرد", "پاهای سرد"],
            # سایر
            "insomnia": ["بی خوابی", "نمی‌تونم بخوابم", "خوابم نمی‌بره"],
            "swollen_lymph_nodes": ["تورم غدد لنفاوی", "غدد لنفاوی متورم", "گره های لنفاوی"],
            "ascites": ["آسیت", "شکم باد کرده", "بزرگی شکم"],
            "cyanosis": ["کبودی لب و ناخن", "کبودی انگشتان", "تغییر رنگ آبی"],
            "clubbing": ["چماقی شدن انگشتان", "انگشتان چماقی", "پهن شدن ناخن"],
            "hyperpigmentation": ["تیره شدن پوست", "لکه‌های تیره", "پوست تیره شده"],
            "vitiligo": ["برص", "لکه‌های سفید", "پیسی"],
            "gynecomastia": ["بزرگی پستان در مردان", "سینه‌های برجسته در مرد"],
            "galactorrhea": ["ترشح شیر از پستان", "شیر از سینه میاد"],
            "erectile_dysfunction": ["ناتوانی جنسی", "اختلال نعوظ", "نمی‌تونم نعوظ داشته باشم"],
        }

        # عبارات نفی – اگر قبل از کلیدواژه بیایند، علامت را باطل می‌کنند
        self.negation_words = [
            "ندارم", "نیست", "نمیکنم", "نشده", "بدون", "خوب است", "طبیعی است",
            "نمی", "نه", "عدم", "فاقد", "خوبم", "سالم", "مشکلی ندارم", "طبیعی",
            "عارضی ندارم", "نبوده", "نکردم"
        ]

        # الگوهای تشخیص شدت (high)
        self.severity_patterns = [
            r"\bشدید\b", r"\bزیاد\b", r"\bوحشتناک\b", r"\bطاقت‌فرسا\b",
            r"\bخیلی\b", r"\bبه‌شدت\b", r"\bمهیب\b", r"\bدائمی\b",
            r"\bقوی\b", r"\bطاقت‌فرسا\b", r"\bوحشت\b"
        ]

    def _split_sentences(self, text: str):
        sentences = re.split(r'[،,\.\n؛;]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    def _detect_negation(self, sentence: str, phrase: str, phrase_start: int) -> bool:
        before_text = sentence[:phrase_start].strip()
        if not before_text:
            return False
        tokens_before = before_text.split()
        window = tokens_before[-5:] if len(tokens_before) >= 5 else tokens_before
        for token in window:
            clean_token = token.strip(" \t،.؛:")
            if clean_token in self.negation_words:
                return True
        return False

    def _detect_severity(self, sentence: str) -> str:
        for pat in self.severity_patterns:
            if re.search(pat, sentence):
                return "high"
        return "normal"

    def extract(self, text: str) -> dict:
        sentences = self._split_sentences(text)
        symptoms = {}
        for sent in sentences:
            severity = self._detect_severity(sent)
            for symptom_key, phrases in self.symptom_keywords.items():
                for phrase in phrases:
                    pattern = r'(?<!\S)' + re.escape(phrase) + r'(?!\S)'
                    match = re.search(pattern, sent)
                    if match:
                        start_idx = match.start()
                        if self._detect_negation(sent, phrase, start_idx):
                            if symptom_key in symptoms:
                                del symptoms[symptom_key]
                            continue
                        if symptom_key in symptoms:
                            if severity == "high":
                                symptoms[symptom_key] = "high"
                        else:
                            symptoms[symptom_key] = severity
                        break
        return symptoms


# -------------------------------------------------------------------
# ۲. پایگاه دانش بیماری‌ها (بسیار گسترده – بیش از ۱۰۰ بیماری)
# -------------------------------------------------------------------
DISEASE_DB = {
    # ===================== اورژانسی و قلبی-عروقی =====================
    "Myocardial Infarction (سکته قلبی)": {
        "prior": 0.002, "urgency": "high",
        "symptoms": {
            ("chest_pain", "high"): 0.92, ("chest_pain", "normal"): 0.5,
            ("left_arm_pain", None): 0.7, ("shortness_of_breath", "high"): 0.85,
            ("shortness_of_breath", "normal"): 0.4, ("nausea", None): 0.4,
            ("vomiting", None): 0.3, ("palpitations", None): 0.5
        },
        "advice": ["فوراً با اورژانس (۱۱۵) تماس بگیرید.",
                   "آسپرین ۳۲۵ میلی‌گرم بجوید (در صورت تأیید اپراتور)."]
    },
    "Stroke (سکته مغزی)": {
        "prior": 0.002, "urgency": "high",
        "symptoms": {
            ("facial_droop", None): 0.95, ("arm_weakness", None): 0.9,
            ("speech_difficulty", None): 0.95, ("unilateral_weakness", None): 0.95,
            ("dizziness", None): 0.4
        },
        "advice": ["زمان طلایی را از دست ندهید! فوراً با اورژانس تماس بگیرید."]
    },
    "Aortic Dissection (دایسکشن آئورت)": {
        "prior": 0.0001, "urgency": "high",
        "symptoms": {
            ("chest_pain", "high"): 0.95, ("back_pain", "high"): 0.8,
            ("shortness_of_breath", None): 0.5, ("facial_droop", None): 0.2
        },
        "advice": ["اورژانس پزشکی فوری! احتمال پارگی آئورت."]
    },
    "Pulmonary Embolism (آمبولی ریه)": {
        "prior": 0.0005, "urgency": "high",
        "symptoms": {
            ("shortness_of_breath", "high"): 0.9, ("chest_pain", "high"): 0.8,
            ("cough", None): 0.3, ("hemoptysis", None): 0.3,
            ("palpitations", None): 0.4
        },
        "advice": ["فوراً به اورژانس مراجعه کنید."]
    },
    "Cardiac Tamponade (تامپوناد قلبی)#": {
        "prior": 0.00005, "urgency": "high",
        "symptoms": {
            ("shortness_of_breath", "high"): 0.9, ("chest_pain", None): 0.7,
            ("dizziness", None): 0.6, ("palpitations", None): 0.5
        },
        "advice": ["فوراً به بیمارستان مراجعه کنید."]
    },

    # ===================== عفونی =====================
    "Sepsis (سپسیس)": {
        "prior": 0.001, "urgency": "high",
        "symptoms": {
            ("fever", "high"): 0.8, ("chills", None): 0.7,
            ("shortness_of_breath", None): 0.6, ("fatigue", None): 0.9,
            ("dizziness", None): 0.5
        },
        "advice": ["فوراً به بیمارستان مراجعه کنید."]
    },
    "Meningitis (مننژیت)": {
        "prior": 0.0003, "urgency": "high",
        "symptoms": {
            ("fever", "high"): 0.8, ("neck_stiffness", None): 0.95,
            ("headache", "high"): 0.9, ("photophobia", None): 0.8
        },
        "advice": ["بلافاصله به اورژانس مراجعه کنید."]
    },
    "Pneumonia (ذات‌الریه)": {
        "prior": 0.01, "urgency": "medium",
        "symptoms": {
            ("cough", None): 0.9, ("cough_productive", None): 0.8,
            ("fever", "high"): 0.7, ("shortness_of_breath", None): 0.6,
            ("fatigue", None): 0.7
        },
        "advice": ["به پزشک مراجعه کنید، احتمال آنتی‌بیوتیک."]
    },
    "Tuberculosis (سل)": {
        "prior": 0.003, "urgency": "high",
        "symptoms": {
            ("cough", None): 0.95, ("cough_productive", None): 0.9,
            ("fever", None): 0.6, ("night_sweats", None): 0.8,
            ("weight_loss", None): 0.7, ("fatigue", None): 0.7
        },
        "advice": ["آزمایش خلط و مراجعه فوری به متخصص ریه."]
    },
    "Malaria (مالاریا)": {
        "prior": 0.0005, "urgency": "high",
        "symptoms": {
            ("fever", "high"): 0.95, ("chills", None): 0.9,
            ("headache", None): 0.8, ("vomiting", None): 0.4,
            ("jaundice", None): 0.3
        },
        "advice": ["فوراً به بیمارستان؛ تست مالاریا ضروری است."]
    },
    "Dengue Fever (تب دنگی)": {
        "prior": 0.001, "urgency": "high",
        "symptoms": {
            ("fever", "high"): 0.9, ("headache", "high"): 0.8,
            ("joint_pain", None): 0.9, ("rash", None): 0.6,
            ("fatigue", None): 0.8
        },
        "advice": ["نوشیدن مایعات زیاد، مراجعه به پزشک."]
    },
    "HIV Acute Infection (عفونت حاد HIV)": {
        "prior": 0.0005, "urgency": "medium",
        "symptoms": {
            ("fever", None): 0.8, ("sore_throat", None): 0.7,
            ("rash", None): 0.5, ("swollen_lymph_nodes", None): 0.8,
            ("fatigue", None): 0.8
        },
        "advice": ["آزمایش HIV در اسرع وقت."]
    },
    "Hepatitis B (هپاتیت ب)": {
        "prior": 0.003, "urgency": "medium",
        "symptoms": {
            ("jaundice", None): 0.7, ("fatigue", None): 0.8,
            ("abdominal_pain", None): 0.5, ("nausea", None): 0.6,
            ("loss_of_appetite", None): 0.7
        },
        "advice": ["آزمایش‌های کبدی و HBsAg انجام دهید."]
    },
    "COVID-19 Severe (کرونا شدید)": {
        "prior": 0.02, "urgency": "high",
        "symptoms": {
            ("fever", None): 0.8, ("cough", None): 0.9,
            ("shortness_of_breath", "high"): 0.7, ("fatigue", None): 0.8,
            ("loss_of_appetite", None): 0.5
        },
        "advice": ["قرنطینه و تماس با مراکز بهداشت."]
    },
    "Typhoid Fever (حصبه)": {
        "prior": 0.0008, "urgency": "medium",
        "symptoms": {
            ("fever", "high"): 0.9, ("headache", None): 0.7,
            ("abdominal_pain", None): 0.6, ("constipation", None): 0.4,
            ("fatigue", None): 0.8
        },
        "advice": ["آزمایش خون و کشت مدفوع."]
    },

    # ===================== گوارش =====================
    "Appendicitis (آپاندیسیت)": {
        "prior": 0.0007, "urgency": "high",
        "symptoms": {
            ("abdominal_pain", "high"): 0.9, ("nausea", None): 0.8,
            ("vomiting", None): 0.7, ("fever", None): 0.5
        },
        "advice": ["فوراً به اورژانس جراحی."]
    },
    "Pancreatitis Acute (پانکراتیت حاد)": {
        "prior": 0.0003, "urgency": "high",
        "symptoms": {
            ("abdominal_pain", "high"): 0.95, ("back_pain", None): 0.5,
            ("nausea", None): 0.8, ("vomiting", None): 0.7,
            ("fever", None): 0.4
        },
        "advice": ["بیمارستان، ناشتا باشید."]
    },
    "Bowel Obstruction (انسداد روده)": {
        "prior": 0.0004, "urgency": "high",
        "symptoms": {
            ("abdominal_pain", "high"): 0.9, ("vomiting", None): 0.8,
            ("constipation", None): 0.9, ("abdominal_distention", None): 0.8
        },
        "advice": ["فوراً به جراح مراجعه کنید."]
    },
    "Crohn's Disease (کرون)": {
        "prior": 0.001, "urgency": "medium",
        "symptoms": {
            ("abdominal_pain", None): 0.8, ("diarrhea", None): 0.9,
            ("weight_loss", None): 0.6, ("fatigue", None): 0.7
        },
        "advice": ["کولونوسکوپی و مشاوره گوارش."]
    },
    "Ulcerative Colitis (کولیت اولسراتیو)": {
        "prior": 0.0008, "urgency": "medium",
        "symptoms": {
            ("diarrhea", None): 0.9, ("bloody_diarrhea", None): 0.8,
            ("abdominal_pain", None): 0.7, ("fatigue", None): 0.5
        },
        "advice": ["کولونوسکوپی و درمان دارویی."]
    },
    "Irritable Bowel Syndrome (سندروم روده تحریک‌پذیر)": {
        "prior": 0.1, "urgency": "low",
        "symptoms": {
            ("abdominal_pain", None): 0.9, ("diarrhea", None): 0.5,
            ("constipation", None): 0.5, ("bloating", None): 0.8
        },
        "advice": ["اصلاح رژیم غذایی و کاهش استرس."]
    },

    # ===================== کلیه و مجاری ادراری =====================
    "Chronic Kidney Disease (نارسایی مزمن کلیه)": {
        "prior": 0.03, "urgency": "medium",
        "symptoms": {
            ("fatigue", None): 0.8, ("edema", None): 0.6,
            ("hypertension", None): 0.7, ("oliguria", None): 0.4,
            ("pruritus", None): 0.5
        },
        "advice": ["آزمایش کراتینین و مشاوره نفرولوژی."]
    },
    "Glomerulonephritis (گلومرولونفریت)": {
        "prior": 0.0005, "urgency": "medium",
        "symptoms": {
            ("edema", None): 0.7, ("hypertension", None): 0.6,
            ("fatigue", None): 0.5, ("flank_pain", None): 0.3
        },
        "advice": ["آزمایش ادرار و کلیه."]
    },
    "Kidney Stone (سنگ کلیه)": {
        "prior": 0.02, "urgency": "medium",
        "symptoms": {
            ("flank_pain", "high"): 0.95, ("abdominal_pain", None): 0.5,
            ("nausea", None): 0.6, ("dysuria", None): 0.4
        },
        "advice": ["مصرف مایعات بالا، مراجعه به اورولوژیست."]
    },
    "Urinary Tract Infection (عفونت ادراری)": {
        "prior": 0.07, "urgency": "medium",
        "symptoms": {
            ("dysuria", None): 0.95, ("polyuria", None): 0.8,
            ("fever", None): 0.4, ("abdominal_pain", None): 0.3
        },
        "advice": ["آزمایش کامل ادرار، آنتی‌بیوتیک."]
    },

    # ===================== غدد =====================
    "Diabetes Mellitus Type 1 (دیابت نوع ۱)": {
        "prior": 0.005, "urgency": "high",
        "symptoms": {
            ("polydipsia", None): 0.9, ("polyuria", None): 0.9,
            ("weight_loss", None): 0.8, ("fatigue", None): 0.8,
            ("blurred_vision", None): 0.5
        },
        "advice": ["فوراً قند خون چک کنید، خطر کتواسیدوز."]
    },
    "Diabetes Mellitus Type 2 (دیابت نوع ۲)": {
        "prior": 0.08, "urgency": "low",
        "symptoms": {
            ("polydipsia", None): 0.8, ("polyuria", None): 0.8,
            ("polyphagia", None): 0.7, ("fatigue", None): 0.7,
            ("blurred_vision", None): 0.5, ("weight_loss", None): 0.3
        },
        "advice": ["قند خون ناشتا و HbA1c را چک کنید."]
    },
    "Hypothyroidism (کم‌کاری تیروئید)": {
        "prior": 0.04, "urgency": "low",
        "symptoms": {
            ("fatigue", None): 0.9, ("weight_gain", None): 0.6,
            ("cold_intolerance", None): 0.8, ("constipation", None): 0.5,
            ("hair_loss", None): 0.4
        },
        "advice": ["آزمایش TSH و T4."]
    },
    "Hyperthyroidism (پرکاری تیروئید)": {
        "prior": 0.01, "urgency": "medium",
        "symptoms": {
            ("weight_loss", None): 0.7, ("palpitations", None): 0.9,
            ("heat_intolerance", None): 0.8, ("tremor", None): 0.7,
            ("fatigue", None): 0.5
        },
        "advice": ["آزمایش TSH، T3، T4 و اسکن تیروئید."]
    },
    "Cushing's Syndrome (سندروم کوشینگ)": {
        "prior": 0.0002, "urgency": "medium",
        "symptoms": {
            ("weight_gain", None): 0.8, ("fatigue", None): 0.7,
            ("hypertension", None): 0.5, ("hyperpigmentation", None): 0.3,
            ("depression_anxiety", None): 0.6
        },
        "advice": ["آزمایش کورتیزول و مراجعه به غدد."]
    },
    "Addison's Disease (بیماری آدیسون)": {
        "prior": 0.0001, "urgency": "high",
        "symptoms": {
            ("fatigue", None): 0.9, ("weight_loss", None): 0.7,
            ("nausea", None): 0.6, ("hyperpigmentation", None): 0.5,
            ("dizziness", None): 0.6
        },
        "advice": ["فوراً به متخصص غدد؛ بحران آدرنال خطرناک است."]
    },

    # ===================== روماتولوژی =====================
    "Rheumatoid Arthritis (آرتریت روماتوئید)": {
        "prior": 0.01, "urgency": "medium",
        "symptoms": {
            ("joint_pain", None): 0.9, ("joint_swelling", None): 0.8,
            ("morning_stiffness", None): 0.9, ("fatigue", None): 0.6,
            ("low_grade_fever", None): 0.3
        },
        "advice": ["آزمایش RF و anti-CCP, مراجعه به روماتولوژی."]
    },
    "Systemic Lupus Erythematosus (لوپوس)": {
        "prior": 0.001, "urgency": "medium",
        "symptoms": {
            ("joint_pain", None): 0.8, ("rash", None): 0.7,
            ("fever", None): 0.5, ("fatigue", None): 0.9,
            ("mouth_ulcers", None): 0.4, ("kidney_involvement", None): 0.3
        },
        "advice": ["آزمایش ANA و ENA, مراجعه به روماتولوژی."]
    },
    "Sjogren's Syndrome (شوگرن)": {
        "prior": 0.003, "urgency": "low",
        "symptoms": {
            ("dry_mouth", None): 0.9, ("dry_eyes", None): 0.9,
            ("joint_pain", None): 0.5, ("fatigue", None): 0.7
        },
        "advice": ["آزمایش SS-A/SS-B و چشم‌پزشکی."]
    },
    "Ankylosing Spondylitis (اسپوندیلیت آنکیلوزان)": {
        "prior": 0.002, "urgency": "medium",
        "symptoms": {
            ("back_pain", "high"): 0.9, ("morning_stiffness", None): 0.8,
            ("fatigue", None): 0.5
        },
        "advice": ["عکس ستون فقرات و آزمایش HLA-B27."]
    },
    "Gout (نقرس)": {
        "prior": 0.02, "urgency": "medium",
        "symptoms": {
            ("joint_pain", "high"): 0.95, ("joint_swelling", None): 0.9,
            ("redness", None): 0.8
        },
        "advice": ["کولشی‌سین و محدودیت پورین."]
    },

    # ===================== هماتولوژی =====================
    "Iron Deficiency Anemia (کم‌خونی فقر آهن)": {
        "prior": 0.06, "urgency": "low",
        "symptoms": {
            ("fatigue", None): 0.9, ("dizziness", None): 0.6,
            ("hair_loss", None): 0.5, ("shortness_of_breath", "normal"): 0.3,
            ("palpitations", None): 0.4
        },
        "advice": ["آزمایش CBC و فریتین."]
    },
    "Sickle Cell Disease (بیماری سلول داسی شکل)": {
        "prior": 0.0003, "urgency": "high",
        "symptoms": {
            ("joint_pain", "high"): 0.9, ("bone_pain", None): 0.9,
            ("fatigue", None): 0.8, ("jaundice", None): 0.4
        },
        "advice": ["بستری فوری، کنترل درد و مایعات."]
    },
    "Hemophilia (هموفیلی)": {
        "prior": 0.00005, "urgency": "high",
        "symptoms": {
            ("abnormal_bleeding", None): 0.95, ("easy_bruising", None): 0.9,
            ("joint_swelling", None): 0.5
        },
        "advice": ["فوراً به مرکز درمانی، تزریق فاکتور انعقادی."]
    },
    "Leukemia (لوسمی حاد)": {
        "prior": 0.0002, "urgency": "high",
        "symptoms": {
            ("fatigue", None): 0.9, ("fever", None): 0.7,
            ("swollen_lymph_nodes", None): 0.6, ("easy_bruising", None): 0.5,
            ("night_sweats", None): 0.5
        },
        "advice": ["فوراً CBC و مشاوره هماتولوژی."]
    },
    "Lymphoma (لنفوم)": {
        "prior": 0.0003, "urgency": "medium",
        "symptoms": {
            ("swollen_lymph_nodes", None): 0.9, ("night_sweats", None): 0.7,
            ("weight_loss", None): 0.6, ("fatigue", None): 0.7
        },
        "advice": ["بیوپسی غده لنفاوی و آزمایش خون."]
    },

    # ===================== نورولوژی =====================
    "Multiple Sclerosis (ام‌اس)": {
        "prior": 0.001, "urgency": "medium",
        "symptoms": {
            ("fatigue", None): 0.8, ("paresthesia", None): 0.7,
            ("vision_loss", None): 0.6, ("diplopia", None): 0.5,
            ("dizziness", None): 0.6, ("unilateral_weakness", None): 0.4
        },
        "advice": ["MRI مغز و نخاع، مراجعه به نورولوژی."]
    },
    "Epilepsy (صرع)": {
        "prior": 0.005, "urgency": "medium",
        "symptoms": {
            ("seizure", None): 0.95, ("aura", None): 0.4,
            ("fatigue", None): 0.5
        },
        "advice": ["نوار مغز و مشاوره نورولوژی."]
    },
    "Guillain-Barre Syndrome (گیلن باره)": {
        "prior": 0.0001, "urgency": "high",
        "symptoms": {
            ("muscle_weakness", None): 0.9, ("paresthesia", None): 0.7,
            ("dysphagia", None): 0.3, ("shortness_of_breath", None): 0.5
        },
        "advice": ["بستری فوری در ICU، درمان IVIG."]
    },
    "Myasthenia Gravis (میاستنی گراویس)": {
        "prior": 0.0003, "urgency": "high",
        "symptoms": {
            ("muscle_weakness", None): 0.9, ("diplopia", None): 0.7,
            ("dysphagia", None): 0.5, ("fatigue", None): 0.8
        },
        "advice": ["آزمایش آنتی‌بادی AChR و نورولوژی."]
    },
    "ALS (اسکلروز جانبی آمیوتروفیک)": {
        "prior": 0.00005, "urgency": "high",
        "symptoms": {
            ("muscle_weakness", None): 0.95, ("dysphagia", None): 0.6,
            ("speech_difficulty", None): 0.7, ("shortness_of_breath", None): 0.4
        },
        "advice": ["مراجعه فوری به نورولوژیست."]
    },

    # ===================== سایر =====================
    "Parkinson's Disease (پارکینسون)": {
        "prior": 0.003, "urgency": "low",
        "symptoms": {
            ("bradykinesia", None): 0.95, ("rest_tremor", None): 0.85,
            ("rigidity", None): 0.9, ("gait_disturbance", None): 0.8
        },
        "advice": ["به نورولوژی مراجعه کنید."]
    },
    "Common Cold (سرماخوردگی)": {
        "prior": 0.3, "urgency": "low",
        "symptoms": {
            ("runny_nose", None): 0.9, ("sore_throat", None): 0.8,
            ("cough", None): 0.6, ("fever", "normal"): 0.4
        },
        "advice": ["استراحت و مایعات گرم."]
    },
    "Migraine (میگرن)": {
        "prior": 0.12, "urgency": "low",
        "symptoms": {
            ("headache", "high"): 0.9, ("photophobia", None): 0.7,
            ("nausea", None): 0.6, ("dizziness", None): 0.5
        },
        "advice": ["در اتاق تاریک استراحت کنید."]
    },
    "Anxiety Disorder (اختلال اضطراب)": {
        "prior": 0.1, "urgency": "low",
        "symptoms": {
            ("palpitations", None): 0.7, ("fatigue", None): 0.5,
            ("insomnia", None): 0.8, ("depression_anxiety", "high"): 0.9
        },
        "advice": ["تکنیک‌های تنفسی و مشاور روانشناس."]
    },
    "Chronic Fatigue Syndrome (سندروم خستگی مزمن)": {
        "prior": 0.005, "urgency": "low",
        "symptoms": {
            ("fatigue", "high"): 0.95, ("insomnia", None): 0.5,
            ("muscle_pain", None): 0.6, ("fatigue_post_exertion", None): 0.9
        },
        "advice": ["مراجعه به پزشک و درمان حمایتی."]
    },
    "Depression (افسردگی اساسی)": {
        "prior": 0.1, "urgency": "medium",
        "symptoms": {
            ("depression_anxiety", "high"): 0.95, ("fatigue", None): 0.8,
            ("loss_of_appetite", None): 0.6, ("insomnia", None): 0.7
        },
        "advice": ["مشاوره با روان‌پزشک."]
    },
    # بیماری‌های نادر اضافی
    "Ehlers-Danlos Syndrome (سندروم اهلرز-دانلوس)": {
        "prior": 0.00002, "urgency": "low",
        "symptoms": {
            ("joint_pain", None): 0.8, ("easy_bruising", None): 0.7,
            ("skin_hyperelasticity", None): 0.9, ("fatigue", None): 0.6
        },
        "advice": ["مشاوره ژنتیک."]
    },
    "Marfan Syndrome (سندروم مارفان)": {
        "prior": 0.00003, "urgency": "medium",
        "symptoms": {
            ("tall_stature", None): 0.8, ("chest_pain", None): 0.5,
            ("vision_loss", None): 0.5, ("joint_laxity", None): 0.7
        },
        "advice": ["اکوکاردیوگرافی سالانه."]
    },
    "Pheochromocytoma (فئوکروموسیتوم)": {
        "prior": 0.00001, "urgency": "high",
        "symptoms": {
            ("headache", "high"): 0.9, ("palpitations", None): 0.9,
            ("excessive_sweating", None): 0.9, ("hypertension", None): 0.8
        },
        "advice": ["اندازه‌گیری متانفرین و مراجعه به غدد."]
    },
    "Acute Intermittent Porphyria (پورفیری حاد متناوب)": {
        "prior": 0.000005, "urgency": "high",
        "symptoms": {
            ("abdominal_pain", "high"): 0.9, ("vomiting", None): 0.7,
            ("seizure", None): 0.2, ("psychiatric_symptoms", None): 0.5
        },
        "advice": ["آزمایش پورفوبیلینوژن."]
    },
    "Cystic Fibrosis (فیبروز کیستیک)": {
        "prior": 0.0001, "urgency": "medium",
        "symptoms": {
            ("cough_productive", None): 0.9, ("shortness_of_breath", None): 0.6,
            ("weight_loss", None): 0.5, ("diarrhea", None): 0.4,
            ("clubbing", None): 0.5
        },
        "advice": ["تست کلر عرق و مشاوره ژنتیک."]
    },
    "Hemochromatosis (هموکروماتوز)": {
        "prior": 0.0005, "urgency": "medium",
        "symptoms": {
            ("fatigue", None): 0.8, ("joint_pain", None): 0.7,
            ("hyperpigmentation", None): 0.5, ("diabetes", None): 0.4
        },
        "advice": ["آزمایش فریتین و درصد اشباع ترنسفرین."]
    },
    # موارد تکمیلی برای پوشش گسترده
    "Endometriosis (اندومتریوز)": {
        "prior": 0.015, "urgency": "medium",
        "symptoms": {
            ("dysmenorrhea", None): 0.9, ("dyspareunia", None): 0.6,
            ("lower_abdominal_pain", None): 0.8, ("infertility", None): 0.3
        },
        "advice": ["سونوگرافی و مراجعه به زنان."]
    },
    "Polycystic Ovary Syndrome (سندروم تخمدان پلی‌کیستیک)": {
        "prior": 0.05, "urgency": "low",
        "symptoms": {
            ("irregular_menses", None): 0.9, ("hirsutism", None): 0.6,
            ("weight_gain", None): 0.5, ("acne", None): 0.5
        },
        "advice": ["سونوگرافی تخمدان و آزمایش هورمونی."]
    }
    # در یک پیاده‌سازی واقعی می‌توان صدها بیماری دیگر افزود.
}


# -------------------------------------------------------------------
# ۳. موتور تفسیر آزمایش‌ها (Lab Result Interpreter) – توسعه‌یافته
# -------------------------------------------------------------------
class LabInterpreter:
    def __init__(self):
        self.tests = {
            "fbs": {
                "names": ["قند ناشتا", "FBS", "گلوکز ناشتا", "قند خون"],
                "unit": "mg/dL",
                "normal": (70, 100),
                "interpret": {
                    "low": "هیپوگلیسمی – نیاز به بررسی فوری.",
                    "normal": "قند ناشتا طبیعی.",
                    "prediabetes": "پیش‌دیابت (۱۰۰-۱۲۵) – اصلاح سبک زندگی.",
                    "diabetes": "دیابت: ≥۱۲۶. آزمایش تکمیلی لازم است."
                },
                "ranges": {
                    "low": (0, 70),
                    "normal": (70, 100),
                    "prediabetes": (100, 126),
                    "diabetes": (126, 1000)
                }
            },
            "hba1c": {
                "names": ["هموگلوبین گلیکوزیله", "HbA1c", "گلیکوهموگلوبین"],
                "unit": "%",
                "normal": (4.0, 5.7),
                "interpret": {
                    "normal": "کنترل عالی قند خون.",
                    "prediabetes": "پیش‌دیابت (۵.۷-۶.۴%).",
                    "diabetes": "کنترل ضعیف دیابت (≥۶.۵%)."
                },
                "ranges": {
                    "normal": (4.0, 5.7),
                    "prediabetes": (5.7, 6.5),
                    "diabetes": (6.5, 20.0)
                }
            },
            "tsh": {
                "names": ["تی‌اس‌اچ", "TSH", "هورمون محرک تیروئید"],
                "unit": "mIU/L",
                "normal": (0.4, 4.0),
                "interpret": {
                    "low": "پرکاری تیروئید محتمل.",
                    "normal": "عملکرد طبیعی تیروئید.",
                    "high": "کم‌کاری تیروئید محتمل."
                },
                "ranges": {"low": (0, 0.4), "normal": (0.4, 4.0), "high": (4.0, 100)}
            },
            "creatinine": {
                "names": ["کراتینین", "Creatinine"],
                "unit": "mg/dL",
                "normal": (0.6, 1.2),
                "interpret": {
                    "normal": "عملکرد کلیه طبیعی.",
                    "high": "افزایش کراتینین – کاهش عملکرد کلیه."
                },
                "ranges": {"normal": (0.6, 1.2), "high": (1.2, 30)}
            },
            "vitamin_d": {
                "names": ["ویتامین دی", "Vitamin D"],
                "unit": "ng/mL",
                "normal": (30, 100),
                "interpret": {
                    "low": "کمبود ویتامین D.",
                    "normal": "میزان کافی ویتامین D."
                },
                "ranges": {"low": (0, 30), "normal": (30, 100)}
            },
            "ldl": {
                "names": ["LDL", "کلسترول بد", "ال‌دی‌ال"],
                "unit": "mg/dL",
                "normal": (0, 100),
                "interpret": {
                    "normal": "LDL مطلوب.",
                    "borderline": "مرزی (۱۰۰-۱۲۹).",
                    "high": "بالا (≥۱۳۰) – ریسک قلبی."
                },
                "ranges": {"normal": (0, 100), "borderline": (100, 130), "high": (130, 500)}
            },
            "hdl": {
                "names": ["HDL", "کلسترول خوب", "اچ‌دی‌ال"],
                "unit": "mg/dL",
                "normal": (40, 100),
                "interpret": {
                    "low": "HDL پایین – عامل خطر.",
                    "normal": "HDL مناسب."
                },
                "ranges": {"low": (0, 40), "normal": (40, 100)}
            },
            "triglycerides": {
                "names": ["تری‌گلیسیرید", "Triglycerides"],
                "unit": "mg/dL",
                "normal": (0, 150),
                "interpret": {
                    "normal": "طبیعی.",
                    "borderline": "مرزی (۱۵۰-۱۹۹).",
                    "high": "بالا (≥۲۰۰) – خطر پانکراتیت."
                },
                "ranges": {"normal": (0, 150), "borderline": (150, 200), "high": (200, 1000)}
            },
            "alt": {
                "names": ["ALT", "آلانین آمینوترانسفراز", "SGPT"],
                "unit": "U/L",
                "normal": (7, 56),
                "interpret": {
                    "normal": "کبد سالم.",
                    "high": "افزایش آنزیم کبد – احتمال آسیب کبدی."
                },
                "ranges": {"normal": (7, 56), "high": (56, 5000)}
            },
            "ast": {
                "names": ["AST", "آسپارتات آمینوترانسفراز", "SGOT"],
                "unit": "U/L",
                "normal": (10, 40),
                "interpret": {
                    "normal": "طبیعی.",
                    "high": "افزایش AST – بررسی کبد و عضلات."
                },
                "ranges": {"normal": (10, 40), "high": (40, 5000)}
            },
            "bilirubin_total": {
                "names": ["بیلی‌روبین کل", "Total Bilirubin"],
                "unit": "mg/dL",
                "normal": (0.1, 1.2),
                "interpret": {
                    "normal": "طبیعی.",
                    "high": "زردی – همولیز یا مشکل کبدی."
                },
                "ranges": {"normal": (0.1, 1.2), "high": (1.2, 30)}
            },
            "uric_acid": {
                "names": ["اسید اوریک", "Uric Acid"],
                "unit": "mg/dL",
                "normal": (2.4, 6.0),
                "interpret": {
                    "normal": "طبیعی.",
                    "high": "افزایش – خطر نقرس و سنگ کلیه."
                },
                "ranges": {"normal": (2.4, 6.0), "high": (6.0, 20)}
            },
            "ferritin": {
                "names": ["فریتین", "Ferritin"],
                "unit": "ng/mL",
                "normal": (20, 250),
                "interpret": {
                    "low": "کمبود آهن.",
                    "normal": "ذخایر آهن طبیعی.",
                    "high": "افزایش آهن – هموکروماتوز یا التهاب."
                },
                "ranges": {"low": (0, 20), "normal": (20, 250), "high": (250, 2000)}
            }
        }
        self.number_pattern = r"(\d+\.?\d*)\s*(mg/dL|%|mIU/L|ng/mL|U/L|میلی‌گرم|واحد|%)?"

    def extract_number_and_unit(self, text: str):
        """استخراج عدد از متن (بدون واحد اجباری)."""
        match = re.search(self.number_pattern, text)
        if match:
            return float(match.group(1)), match.group(2) or None
        # جستجوی عدد تنها
        match2 = re.search(r"(\d+\.?\d*)", text)
        if match2:
            return float(match2.group(1)), None
        return None, None

    def interpret_lab(self, input_text: str):
        """
        تفسیر نتیجه یک آزمایش.
        ورودی می‌تواند مانند "قند ناشتا ۱۲۰" یا "TSH 4.5" باشد.
        خروجی: دیکشنری شامل نام تست، مقدار، واحد، وضعیت و تفسیر.
        """
        input_text = input_text.strip()
        # پیدا کردن نام تست
        for test_key, test_info in self.tests.items():
            for name in test_info["names"]:
                if name.lower() in input_text.lower():
                    value, unit = self.extract_number_and_unit(input_text)
                    if value is None:
                        return {"error": "مقدار عددی یافت نشد."}
                    # تعیین محدوده
                    result_status = "unknown"
                    for status, (low, high) in test_info["ranges"].items():
                        if low <= value < high:
                            result_status = status
                            break
                    interpret_text = test_info["interpret"].get(result_status, "تفسیر نامشخص")
                    return {
                        "test_name": test_info["names"][0],
                        "value": value,
                        "unit": unit or test_info["unit"],
                        "status": result_status,
                        "interpretation": interpret_text
                    }
        return {"error": "آزمایش تشخیص داده نشد."}

    def find_test(self, user_text: str):
        """تشخیص نام آزمایش و عدد ذکر شده در متن کاربر."""
        text = user_text.replace("،", " ").replace("؛", " ")
        for test_key, info in self.tests.items():
            for name in info["names"]:
                if name.lower() in text.lower():
                    # جستجوی عدد با الگوی loose
                    matches = re.findall(self.number_pattern, text)
                    for num_str, unit in matches:
                        try:
                            value = float(num_str)
                            return test_key, value, unit if unit else info["unit"]
                        except:
                            continue
                    # اگر عدد با الگو پیدا نشد، ساده‌تر فقط یک عدد بگیریم
                    simple_num = re.search(r"(\d+)", text)
                    if simple_num:
                        return test_key, float(simple_num.group(1)), info["unit"]
        return None, None, None

    def interpret_result(self, test_key: str, value: float, unit: str) -> str:
        """تفسیر نتیجه بر اساس بازه‌های تعریف‌شده."""
        test = self.tests[test_key]
        ranges = test["ranges"]
        for range_name, (low, high) in ranges.items():
            # بازه‌های باز از سمت راست (به جز بازه‌های بی‌نهایت)
            if low <= value < high or (high == 1000 and value >= low) or (high == 500 and value >= low):
                return test["interpret"][range_name]
        return "مقدار خارج از محدوده‌های تعریف‌شده، لطفاً با پزشک مشورت کنید."

    def generate_lab_response(self, user_text: str):
        """تولید پاسخ کامل تفسیر آزمایش."""
        test_key, value, unit = self.find_test(user_text)
        if not test_key:
            return None

        interpretation = self.interpret_result(test_key, value, unit)
        test_name = self.tests[test_key]["names"][0]
        normal_range = self.tests[test_key]["normal"]
        response = f"🔬 نتیجه آزمایش {test_name} شما:\n"
        response += f"• مقدار: {value} {unit}\n"
        response += f"• محدوده نرمال: {normal_range[0]} - {normal_range[1]} {unit}\n"
        response += f"• تفسیر: {interpretation}\n"
        response += "⚠️ این تفسیر خودکار است و نیاز به تأیید پزشک دارد."
        return response


# -------------------------------------------------------------------
# ۴. موتور تشخیص بیماری (بیز ساده)
# -------------------------------------------------------------------
def compute_disease_probabilities(symptoms_severity: dict):
    """
    محاسبه احتمال بیماری‌ها با روش بیز ساده (Naïve Bayes)
    از log-prob ها برای جلوگیری از underflow استفاده می‌کند.
    ورودی: دیکشنری {علامت: شدت} (مانند {'fever':'high'})
    خروجی: لیست مرتب‌شده از (نام بیماری، احتمال، فوریت، توصیه‌ها)
    """
    scores = {}
    for disease, info in DISEASE_DB.items():
        prob = np.log(info["prior"])
        for (sym, req_sev), likelihood in info["symptoms"].items():
            if sym in symptoms_severity:
                sev = symptoms_severity[sym]
                # اگر بیماری نیاز به شدت خاصی دارد و شدت بیمار مطابقت نداشته باشد،
                # احتمال را با یک ضریب جریمه ضرب می‌کنیم.
                if req_sev and req_sev != sev:
                    prob += np.log(0.3)  # احتمال کاهش‌یافته
                else:
                    prob += np.log(likelihood)
            else:
                # اگر علامت وجود نداشته باشد، از مکمل احتمال استفاده می‌کنیم
                if likelihood < 1:
                    prob += np.log(1 - likelihood)
                else:
                    prob += np.log(0.01)  # عدد کوچک برای جلوگیری از log(0)
        scores[disease] = prob

    # تبدیل log-scale به احتمال نرمال‌شده
    max_log = max(scores.values())
    exp_scores = {d: np.exp(s - max_log) for d, s in scores.items()}
    total = sum(exp_scores.values())
    probs = {d: v / total for d, v in exp_scores.items() if v / total > 0.01}
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    return [
        (d, p, DISEASE_DB[d]["urgency"], DISEASE_DB[d]["advice"])
        for d, p in sorted_probs
    ]


# -------------------------------------------------------------------
# ۵. مسیر اصلی پردازش – تلفیق آزمایش و علائم
# -------------------------------------------------------------------
def process_medical_query(message: str, model_id: str = None) -> str:
    """
    پردازش پرسش پزشکی کاربر.
    ابتدا بررسی می‌کند که آیا متن حاوی نتیجه‌ی آزمایش است یا خیر.
    در غیر این صورت، علائم را استخراج کرده و تشخیص افتراقی ارائه می‌دهد.
    """
    if not message or len(message.strip()) < 10:
        return ("🙏 لطفاً شرح دقیق‌تری از علائم یا آزمایش خود ارائه دهید.\n"
                "مثال: «از دیشب تب و سرفه دارم، تنگی نفس هم دارم»\n"
                "یا اگر نتیجه آزمایش دارید: «قند ناشتام ۱۳۵ شده»")

    # ۱) بررسی آزمایش
    lab_interpreter = LabInterpreter()
    lab_response = lab_interpreter.generate_lab_response(message)
    if lab_response:
        return "🔍 تحلیل آزمایش شما:\n" + lab_response

    # ۲) استخراج علائم با سیستم قاعده‌ای (سریع)
    extractor = RuleBasedSymptomExtractor()
    symptoms_sev = extractor.extract(message)

    if not symptoms_sev:
        return (
            "❓ متأسفانه از متن شما علائم واضحی استخراج نشد.\n"
            "لطفاً دقیق‌تر بیان کنید، مثلاً:\n"
            "• «سردرد شدید دارم و نور اذیتم می‌کنه»\n"
            "• «دست چپم بی‌حس شده و صورتم کج شده»\n"
            "• یا نتیجه آزمایش خود را با عدد ذکر کنید."
        )

    # ۳) محاسبه احتمال بیماری‌ها
    disease_list = compute_disease_probabilities(symptoms_sev)

    if not disease_list:
        resp = "🩺 با علائم فعلی، تشخیص قطعی ممکن نیست، اما مراجعه به پزشک توصیه می‌شود.\n"
        resp += "علائم شناسایی‌شده: " + "، ".join(symptoms_sev.keys())
        return resp

    top = disease_list[0]
    conf = int(top[1] * 100)
    urgency = top[2]
    advice = top[3]

    urgency_text = {
        "high": "🔴 وضعیت اورژانسی! فوراً به مرکز درمانی مراجعه کنید.",
        "medium": "🟡 نیمه‌اورژانسی – طی ۲۴ ساعت به پزشک مراجعه نمایید.",
        "low": "🟢 غیراورژانسی – می‌توانید با برنامه‌ریزی به پزشک مراجعه کنید."
    }

    # ساخت پاسخ
    response = "🩺 تحلیل بالینی هوشمند:\n"
    response += f"محتمل‌ترین تشخیص: **{top[0]}** (اطمینان {conf}%)\n"
    response += urgency_text.get(urgency, "") + "\n"
    response += "💡 توصیه‌ها:\n"
    for i, a in enumerate(advice, 1):
        response += f"  {i}. {a}\n"

    if len(disease_list) > 1:
        response += "\n⚠️ تشخیص‌های افتراقی دیگر:\n"
        for d, p, _, _ in disease_list[1:4]:
            response += f" • {d} ({int(p * 100)}%)\n"

    response += (
        "\n──────────────────────────────\n"
        "🚨 این تحلیل خودکار و مستقل از معاینه پزشک است.\n"
        "در موارد اورژانسی هرگز به این نرم‌افزار اکتفا نکنید."
    )
    return response

# ======================= اتصال به ربات بله =======================
def generate_response(user_message: str, conversation_id=None) -> str:
    """
    تابع استاندارد برای فراخوانی توسط ربات.
    conversation_id در این ماژول کاربردی ندارد (تشخیص‌ها مستقل از نشست هستند).
    """
    return process_medical_query(user_message)