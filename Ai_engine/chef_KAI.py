"""
دستیار هوش مصنوعی آشپزی ایرانی
ورودی: پیام متنی کاربر (فارسی), conversation_id
خروجی: پیشنهاد غذا به همراه امکان امتیازدهی و یادگیری
"""

import os, json, re, math, datetime, random, urllib.parse
from collections import defaultdict, Counter
import numpy as np
import requests
from bs4 import BeautifulSoup

# ---------- 1. پردازش زبان فارسی ----------
class PersianNLP:
    def __init__(self):
        self.stop_words = set([
            "و", "در", "به", "از", "با", "که", "را", "های", "ها", "این", "آن", "یک",
            "برای", "تا", "هر", "هم", "نیز", "اگر", "اما", "یا", "بود", "هست",
            "می‌شود", "کرد", "کنید", "باید", "داشته", "باشد"
        ])
        self.synonyms = {
            "آبدار": ["خورش", "خورشت", "سوپ", "آش"],
            "تند": ["فلفلی", "تند", "ادویه‌ای"],
            "سریع": ["آسان", "فوری", "زودپز"],
            "مجلس": ["فانتزی", "لاکچری"],
            "رژیمی": ["سالم", "کم‌کالری", "بدون روغن"],
            "گوشت": ["گوشت قرمز", "گوساله", "گوسفند"],
            "مرغ": ["جوجه", "مرغابی"],
            "پلو": ["چلو", "ته‌دیگ"],
            "خامه": ["خامه‌ای", "کرمی"],
            "سبزی": ["سبزیجات", "گیاهی", "وگان"],
        }
        self.suffixes = [
            "ها", "ان", "ات", "ی", "تر", "ترین", "مند", "وار", "اش", "ام", "مان", "شان",
            "هامان", "هایشان", "مان", "تان", "شان", "ای", "ست", "است"
        ]

    def normalize(self, text: str) -> str:
        text = text.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
        text = text.replace("ؤ", "و").replace("إ", "ا").replace("أ", "ا")
        text = text.replace("\u200c", " ")
        return text

    def tokenize(self, text: str) -> list:
        text = re.sub(r'[،,.!?؛:()«»""]', ' ', text)
        return text.split()

    def remove_stopwords(self, tokens: list) -> list:
        return [t for t in tokens if t not in self.stop_words and len(t) > 1]

    def stem(self, word: str) -> str:
        for suf in sorted(self.suffixes, key=len, reverse=True):
            if word.endswith(suf) and len(word) - len(suf) >= 2:
                return word[:-len(suf)]
        return word

    def process_query(self, text: str) -> list:
        text = self.normalize(text.lower())
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        stems = [self.stem(t) for t in tokens]
        expanded = set(stems)
        for t in stems:
            for base, syns in self.synonyms.items():
                if t == base or t in syns:
                    expanded.add(base)
                    for s in syns:
                        expanded.add(s)
        return list(expanded)

nlp = PersianNLP()

# ---------- 2. دیتابیس اولیه (۵۰ غذای ایرانی) ----------
SEED_RECIPES = [
    {
        "title": "پیتزا مخلوط خانگی",
        "ingredients": ["آرد ۲ پیمانه", "خمیرمایه ۱ قاشق چایخوری", "آب ولرم نصف پیمانه", "نمک و شکر", "روغن زیتون", "گوجه فرنگی ۴ عدد", "پنیر پیتزا ۲۰۰ گرم", "قارچ ۱۰۰ گرم", "کالباس یا ژامبون ۱۰۰ گرم", "فلفل دلمه‌ای ۱ عدد", "زیتون", "آویشن", "فلفل سیاه"],
        "steps": ["خمیرمایه و شکر را در آب ولرم حل کرده ۱۰ دقیقه بگذارید.", "آرد، نمک، روغن را با خمیرمایه مخلوط کرده خمیر نرمی بسازید، ۱ ساعت استراحت دهید.", "خمیر را روی سینی پهن کنید و با چنگال سوراخ کنید.", "گوجه‌ها را رنده کنید و با نمک، فلفل و آویشن بپزید تا سس غلیظ شود.", "سس را روی خمیر بمالید، پنیر، قارچ، کالباس، فلفل دلمه و زیتون بچینید.", "در فر ۲۰۰ درجه به مدت ۲۰ دقیقه بپزید تا طلایی شود."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "خورشت قیمه",
        "ingredients": ["گوشت خورشتی ۳۰۰ گرم", "لپه ۱ پیمانه", "پیاز ۲ عدد", "رب گوجه فرنگی ۲ قاشق غذاخوری", "لیمو عمانی ۴ عدد", "سیب زمینی برای خلال", "زعفران دم‌کرده", "نمک، فلفل، زردچوبه"],
        "steps": ["لپه را ۲ ساعت خیس کنید و بعد نیم‌پز کنید.", "پیاز را سرخ کنید، گوشت و ادویه‌ها را اضافه و تفت دهید.", "رب گوجه و لپه پخته را اضافه کنید، آب جوش بریزید و لیمو عمانی را بیندازید.", "۲ ساعت با حرارت ملایم بپزید تا جا بیفتد.", "سیب‌زمینی خلالی را سرخ کرده هنگام سرو روی خورش بریزید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "کباب کوبیده",
        "ingredients": ["گوشت چرخ‌کرده ۵۰۰ گرم (گوساله + گوسفند)", "پیاز ۲ عدد درشت", "نمک، فلفل سیاه، زردچوبه", "زعفران دم‌کرده ۱ قاشق", "کره"],
        "steps": ["پیاز را رنده کرده و آب آن را بگیرید.", "گوشت را با پیاز، نمک، فلفل و زعفران خوب ورز دهید.", "۱ ساعت در یخچال استراحت دهید.", "سیخ‌های پهن بردارید، مواد را دور سیخ بکوبید.", "روی زغال مرتب بچرخانید تا مغزپخت شود، با کره داغ سرو کنید."],
        "rating": 4.9, "url": ""
    },
    {
        "title": "قرمه سبزی",
        "ingredients": ["گوشت خورشتی ۴۰۰ گرم", "سبزی قرمه (تره، جعفری، گشنیز، شنبلیله) ۵۰۰ گرم", "لوبیا چیتی ۱ پیمانه", "لیمو عمانی ۴ عدد", "پیاز ۱ عدد", "روغن", "نمک، فلفل، زردچوبه"],
        "steps": ["لوبیا را از شب قبل خیس کنید و بپزید.", "سبزی را خرد کرده و با روغن تفت دهید تا رنگش تیره شود.", "پیاز را سرخ کنید، گوشت و ادویه را اضافه کنید.", "سبزی سرخ‌شده، لوبیا و لیمو عمانی را به گوشت بیفزایید و آب جوش بریزید.", "۳–۴ ساعت با حرارت کم بپزید تا جا بیفتد."],
        "rating": 4.9, "url": ""
    },
    {
        "title": "زرشک پلو با مرغ",
        "ingredients": ["برنج ۳ پیمانه", "مرغ ۴ تکه", "زرشک ۱ پیمانه", "زعفران دم‌کرده", "شکر ۲ قاشق", "کره ۵۰ گرم", "پیاز ۱ عدد", "نمک، فلفل، زردچوبه"],
        "steps": ["برنج را آبکش کنید و دم بگذارید.", "مرغ را با پیاز و ادویه بپزید تا مغزپخت شود.", "زرشک را با کره و شکر کمی تفت دهید.", "زعفران را روی برنج بدهید.", "برنج را در دیس کشیده و مرغ و زرشک را کنار آن بچینید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "کباب برگ",
        "ingredients": ["راسته گوساله یا فیله مرغ ۵۰۰ گرم", "ماست ۱ پیمانه", "پیاز ۱ عدد", "زعفران", "روغن زیتون", "نمک، فلفل سیاه"],
        "steps": ["گوشت را به قطعات یکسان خرد کنید.", "ماست، پیاز رنده‌شده، زعفران و ادویه را مخلوط کرده گوشت را ۴ ساعت مزه‌دار کنید.", "گوشت را به سیخ بکشید.", "روی ذغال داغ کباب کنید و مرتب بچرخانید.", "با برنج یا نان سرو کنید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "آش رشته",
        "ingredients": ["رشته آشی ۲۰۰ گرم", "نخود و لوبیا چیتی هرکدام نصف پیمانه", "عدس نصف پیمانه", "سبزی آش (تره، جعفری، گشنیز، اسفناج) ۵۰۰ گرم", "پیاز داغ ۳ قاشق", "سیر داغ ۱ قاشق", "کشک ۱ پیمانه", "نمک، فلفل، زردچوبه", "نعنا داغ"],
        "steps": ["حبوبات را از شب قبل خیس کرده و بپزید.", "پیاز را سرخ کنید، زردچوبه بزنید، آب بریزید.", "سبزی خردشده را اضافه کنید تا بپزد.", "رشته را اضافه کنید و هم بزنید تا نچسبد.", "وقتی رشته نرم شد، کشک را اضافه کنید.", "با پیاز داغ، سیر داغ و نعنا داغ تزئین کنید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "فسنجان",
        "ingredients": ["گوشت مرغ یا گوشت قرمز ۵۰۰ گرم", "گردو ۳۰۰ گرم", "رب انار ۱ پیمانه", "شکر ۲ قاشق (اختیاری)", "پیاز ۱ عدد", "زعفران", "نمک، فلفل"],
        "steps": ["گردو را آسیاب کرده و با آب سرد مخلوط کنید.", "پیاز را تفت دهید، گوشت را اضافه کنید.", "رب انار را به گردو اضافه کرده و روی گوشت بریزید.", "۲–۳ ساعت با حرارت بسیار کم بپزید تا روغن بیندازد.", "در انتها شکر و زعفران را اضافه کنید."],
        "rating": 4.9, "url": ""
    },
    {
        "title": "باقالی پلو با ماهیچه",
        "ingredients": ["برنج ۳ پیمانه", "باقالا ۱ پیمانه", "شوید خشک ۲ قاشق", "ماهیچه گوساله ۴ عدد", "پیاز", "زعفران", "روغن", "نمک"],
        "steps": ["باقالا را با کمی نمک بپزید.", "برنج را آبکش کرده، باقالا و شوید را لابه‌لا بریزید و دم کنید.", "ماهیچه را با پیاز و ادویه و آب بپزید تا کاملاً نرم شود.", "برنج را در دیس بکشید و ماهیچه‌ها را روی آن بچینید.", "با زعفران تزئین کنید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "کوکو سبزی",
        "ingredients": ["سبزی کوکو (تره، جعفری، شوید، گشنیز) ۳۰۰ گرم", "تخم مرغ ۴ عدد", "آرد ۲ قاشق", "زرشک و گردو (اختیاری)", "نمک، فلفل، زردچوبه", "روغن برای سرخ کردن"],
        "steps": ["سبزی را شسته و ریز خرد کنید.", "تخم مرغ‌ها را با آرد و ادویه بزنید.", "سبزی و مواد اختیاری را اضافه کنید.", "در تابه روغن داغ بریزید و مواد را پهن کنید.", "دو طرف را سرخ کنید تا طلایی شود."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "میرزا قاسمی",
        "ingredients": ["بادمجان ۴ عدد", "گوجه فرنگی ۳ عدد", "سیر ۴ حبه", "تخم مرغ ۲ عدد", "رب گوجه فرنگی ۱ قاشق", "روغن", "نمک، فلفل، زردچوبه"],
        "steps": ["بادمجان‌ها را کبابی کنید و پوست بگیرید.", "سیر را خرد کرده و در روغن تفت دهید.", "گوجه رنده‌شده و رب را اضافه کنید.", "بادمجان‌های له‌شده را بیفزایید و تفت دهید.", "تخم مرغ‌ها را روی مواد بشکنید و هم بزنید تا ببندد."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "کله جوش",
        "ingredients": ["کشک ۱ پیمانه", "پیاز ۲ عدد", "گردو خردشده ۳ قاشق", "نعنا خشک ۱ قاشق", "روغن", "نمک، فلفل"],
        "steps": ["پیاز را خلالی خرد کرده و سرخ کنید.", "نعنا خشک را اضافه و تفت دهید.", "کشک را با کمی آب رقیق کرده و به تابه بیفزایید.", "گردو را اضافه کنید و چند دقیقه بجوشانید.", "با نان سرو کنید."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "حلیم بادمجان",
        "ingredients": ["بادمجان ۴ عدد", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "سیر ۲ حبه", "نمک، فلفل", "روغن"],
        "steps": ["بادمجان‌ها را کبابی و پوست بگیرید.", "پیاز و سیر را تفت دهید، گوشت را اضافه کنید.", "رب گوجه و ادویه را بیفزایید.", "بادمجان له‌شده را مخلوط کنید.", "کمی آب بریزید تا جا بیفتد."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "دلمه برگ مو",
        "ingredients": ["برگ مو ۳۰ عدد", "برنج ۱ پیمانه", "لپه نیم‌پز نصف پیمانه", "سبزی دلمه (تره، شوید، گشنیز، جعفری) ۲۰۰ گرم", "پیاز ۱ عدد", "روغن", "نمک، فلفل", "آبلیمو"],
        "steps": ["برگ‌ها را در آب گرم بگذارید تا نرم شوند.", "پیاز را تفت دهید، برنج و لپه و سبزی را اضافه کنید.", "مواد را داخل برگ‌ها بپیچید.", "کف قابلمه برگ بچینید، دلمه‌ها را منظم بگذارید.", "آب و روغن و آبلیمو بریزید و ۱ ساعت دم کنید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "کباب تابه‌ای",
        "ingredients": ["گوشت چرخ‌کرده ۳۰۰ گرم", "گوجه فرنگی ۲ عدد", "فلفل دلمه‌ای ۱ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "نمک، فلفل، زردچوبه"],
        "steps": ["پیاز را نگینی خرد کرده و تفت دهید.", "گوشت را اضافه کنید و هم بزنید.", "فلفل دلمه‌ای خردشده و گوجه را اضافه کنید.", "رب گوجه و ادویه‌ها را بریزید.", "با حرارت ملایم بپزید تا آبش کشیده شود."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "شامی کباب",
        "ingredients": ["گوشت چرخ‌کرده ۳۰۰ گرم", "سیب زمینی پخته ۲ عدد", "تخم مرغ ۱ عدد", "پیاز ۱ عدد", "آرد نخودچی ۲ قاشق", "نمک، فلفل، زردچوبه"],
        "steps": ["سیب زمینی را رنده کنید.", "گوشت، پیاز رنده‌شده، تخم مرغ و ادویه را مخلوط کنید.", "آرد نخودچی را اضافه و ورز دهید.", "به شکل گرد یا بیضی درآورید.", "در روغن داغ سرخ کنید تا طلایی شوند."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "کوکو سیب زمینی",
        "ingredients": ["سیب زمینی پخته ۴ عدد", "تخم مرغ ۳ عدد", "پیاز ۱ عدد", "نمک، فلفل", "زردچوبه", "روغن"],
        "steps": ["سیب زمینی‌ها را رنده کنید.", "پیاز رنده‌شده و تخم مرغ‌ها را اضافه کنید.", "ادویه را زده و مواد را مخلوط کنید.", "در تابه روغن داغ بریزید و مواد را پهن کنید.", "دو طرف را سرخ کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "خورشت کرفس",
        "ingredients": ["گوشت خورشتی ۳۰۰ گرم", "کرفس ۱ بوته", "سبزی خورشتی (نعنا، جعفری) ۲۰۰ گرم", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "لیمو عمانی", "نمک، فلفل"],
        "steps": ["کرفس را خرد کرده و کمی تفت دهید.", "پیاز را سرخ کنید، گوشت را اضافه کنید.", "رب گوجه و ادویه را بیفزایید.", "سبزی خردشده و کرفس را اضافه کنید.", "آب جوش بریزید و لیمو عمانی بیندازید، ۲ ساعت بپزید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "خورشت بادمجان",
        "ingredients": ["گوشت خورشتی ۳۰۰ گرم", "بادمجان ۴ عدد", "گوجه فرنگی ۲ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "زعفران", "نمک، فلفل", "روغن برای سرخ کردن بادمجان"],
        "steps": ["بادمجان‌ها را پوست کنده و سرخ کنید.", "پیاز را سرخ کنید، گوشت را اضافه کنید.", "رب گوجه و گوجه‌های خردشده را بیفزایید.", "آب جوش بریزید و ادویه را اضافه کنید.", "بادمجان‌ها را روی خورش بگذارید و ۱.۵ ساعت بپزید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "ته‌چین مرغ",
        "ingredients": ["برنج ۲ پیمانه", "مرغ پخته و ریش‌ریش‌شده ۲ پیمانه", "ماست ۱ پیمانه", "تخم مرغ ۲ عدد", "زعفران", "کره", "نمک"],
        "steps": ["برنج را آبکش کنید.", "ماست، تخم مرغ، زعفران و نمک را مخلوط کرده با برنج بیامیزید.", "کف قابلمه را چرب کنید، نیمی از برنج را بریزید.", "مرغ ریش‌ریش‌شده را وسط بگذارید و بقیه برنج را روی آن بریزید.", "دم کنید تا ته‌دیگ طلایی شود."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "سبزی پلو با ماهی",
        "ingredients": ["برنج ۳ پیمانه", "سبزی پلویی (شوید، تره، جعفری، گشنیز) ۲۰۰ گرم", "ماهی قزل‌آلا یا سفید ۴ تکه", "سیر ۴ حبه", "رب انار یا آبلیمو", "نمک، فلفل", "روغن"],
        "steps": ["برنج را با سبزی خردشده مخلوط و آبکش کنید.", "ماهی را با سیر، نمک، فلفل و آبلیمو مزه‌دار کنید.", "ماهی را در تابه سرخ کنید.", "برنج را دم کنید.", "در دیس، برنج را کشیده و ماهی را کنار آن بگذارید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "شیرین پلو",
        "ingredients": ["برنج ۳ پیمانه", "مرغ یا گوشت ۳۰۰ گرم", "هویج ۲ عدد", "کشمش و خلال بادام و پسته", "زعفران", "شکر ۲ قاشق", "کره", "نمک"],
        "steps": ["هویج را خلال کرده و با کره و شکر کمی تفت دهید.", "کشمش و خلال‌ها را تفت دهید.", "گوشت را با پیاز و ادویه بپزید.", "برنج را آبکش کرده و دم بگذارید.", "هنگام کشیدن، هویج و خلال و گوشت را لای برنج بچینید و زعفران بدهید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "رشته پلو",
        "ingredients": ["برنج ۲ پیمانه", "رشته پلویی ۱۰۰ گرم", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "کشمش و خرما", "زعفران", "روغن", "نمک"],
        "steps": ["پیاز را تفت دهید، گوشت را اضافه و سرخ کنید.", "کشمش و خرما را تفت دهید.", "برنج را آبکش کنید و رشته را اضافه کنید.", "دم بگذارید.", "هنگام کشیدن، گوشت و کشمش و خرما را لای برنج بریزید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "عدس پلو",
        "ingredients": ["برنج ۲ پیمانه", "عدس ۱ پیمانه", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "کشمش و خرما", "زعفران", "نمک، فلفل"],
        "steps": ["عدس را بپزید.", "پیاز و گوشت را تفت دهید.", "کشمش و خرما را تفت دهید.", "برنج را آبکش کنید و عدس را مخلوط کنید.", "دم بگذارید و موقع کشیدن گوشت و کشمش را اضافه کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "مورچه پلو",
        "ingredients": ["برنج ۲ پیمانه", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "زعفران", "نمک، فلفل"],
        "steps": ["گوشت را با پیاز تفت دهید و رب گوجه اضافه کنید.", "برنج را آبکش کنید.", "گوشت را لای برنج بریزید.", "دم کنید.", "با زعفران تزئین کنید."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "کلم پلو شیرازی",
        "ingredients": ["برنج ۲ پیمانه", "کلم برگ ۲ پیمانه خردشده", "گوشت چرخ‌کرده ۲۰۰ گرم", "سبزی (شوید، ترخون، ریحان) ۱۰۰ گرم", "پیاز ۱ عدد", "رب گوجه", "نمک، فلفل"],
        "steps": ["کلم را خرد کرده و تفت دهید.", "پیاز و گوشت را تفت دهید، رب گوجه اضافه کنید.", "سبزی خردشده را اضافه کنید.", "برنج را آبکش کرده و با مواد مخلوط کنید.", "دم بگذارید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "دمی گوجه",
        "ingredients": ["برنج ۲ پیمانه", "گوجه فرنگی ۴ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "کره", "نمک، فلفل"],
        "steps": ["پیاز را تفت دهید، گوجه خردشده و رب را اضافه کنید.", "آب را اضافه کنید تا جوش بیاید.", "برنج شسته را بریزید.", "اجازه دهید آب کشیده شود.", "دم کنید."],
        "rating": 4.3, "url": ""
    },
    {
        "title": "استامبولی",
        "ingredients": ["برنج ۲ پیمانه", "گوجه فرنگی ۳ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "سیب زمینی ۱ عدد", "کره", "نمک، فلفل"],
        "steps": ["پیاز و گوجه را تفت دهید.", "سیب زمینی خردشده و رب را اضافه کنید.", "آب و برنج را اضافه کنید.", "بگذارید جوشیده و آب کشیده شود.", "دم کنید."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "خاگینه",
        "ingredients": ["تخم مرغ ۴ عدد", "آرد ۲ قاشق", "ماست ۱ قاشق", "شکر ۲ قاشق", "زعفران", "کره", "پودر هل"],
        "steps": ["تخم مرغ‌ها را با آرد، ماست، شکر و زعفران مخلوط کنید.", "کره را در تابه داغ کنید.", "مواد را در تابه بریزید.", "دو طرف را سرخ کنید.", "با پودر هل و پسته تزئین کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "املت ایرانی",
        "ingredients": ["تخم مرغ ۴ عدد", "گوجه فرنگی ۳ عدد", "پیاز ۱ عدد", "فلفل دلمه‌ای", "نمک، فلفل", "روغن"],
        "steps": ["پیاز را تفت دهید.", "گوجه و فلفل خردشده را اضافه کنید.", "تخم مرغ‌ها را بشکنید و هم بزنید.", "بگذارید ببندد.", "با نان تازه سرو کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "حلیم گندم",
        "ingredients": ["گندم پوست‌کنده ۱ پیمانه", "گوشت بوقلمون یا گوساله ۳۰۰ گرم", "پیاز ۱ عدد", "دارچین", "شکر", "کره", "نمک"],
        "steps": ["گندم را از شب قبل خیس کنید.", "گوشت و پیاز را با گندم بپزید تا کاملاً نرم شود.", "با گوشت‌کوب له کنید تا کشدار شود.", "کره و نمک را اضافه کنید.", "با دارچین و شکر سرو کنید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "شله زرد",
        "ingredients": ["برنج ۱ پیمانه", "شکر ۲ پیمانه", "زعفران", "گلاب نصف پیمانه", "کره ۵۰ گرم", "خلال بادام و پسته", "دارچین"],
        "steps": ["برنج را با آب زیاد بپزید تا باز شود.", "شکر را اضافه کنید و هم بزنید.", "زعفران و گلاب را بریزید.", "کره را اضافه کنید.", "در ظرف بکشید و با دارچین و خلال تزئین کنید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "فرنی",
        "ingredients": ["شیر ۲ پیمانه", "آرد برنج ۲ قاشق", "شکر ۳ قاشق", "گلاب ۲ قاشق", "پودر هل", "پسته"],
        "steps": ["آرد برنج را با شیر سرد حل کنید.", "روی حرارت ملایم هم بزنید تا غلیظ شود.", "شکر و گلاب را اضافه کنید.", "در ظرف بریزید.", "با پودر هل و پسته تزئین کنید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "سمنو",
        "ingredients": ["گندم ۱ پیمانه", "آرد سبوس‌دار ۳ پیمانه", "آب", "شکر (اختیاری)", "بادام"],
        "steps": ["گندم را خیس کرده و جوانه بزنید.", "جوانه را آسیاب و صاف کنید.", "شیرهٔ به‌دست‌آمده را با آرد مخلوط کنید.", "روی حرارت ملایم ساعت‌ها هم بزنید.", "تا قوام بیاید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "آش دوغ",
        "ingredients": ["دوغ ۱ لیتر", "نخود و لوبیا نصف پیمانه", "سبزی آش (تره، جعفری، گشنیز) ۲۰۰ گرم", "برنج ۲ قاشق", "سیر", "نمک، فلفل"],
        "steps": ["حبوبات را بپزید.", "دوغ را با کمی آب بجوشانید.", "سبزی و برنج را اضافه کنید.", "مرتب هم بزنید تا ته نگیرد.", "با سیر داغ و نعنا سرو کنید."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "آش جو",
        "ingredients": ["جو پرک ۱ پیمانه", "گوشت چرخ‌کرده ۱۵۰ گرم", "سبزی آش ۲۰۰ گرم", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "نمک، فلفل", "آبلیمو"],
        "steps": ["پیاز را تفت دهید، گوشت را اضافه کنید.", "رب گوجه و ادویه را بریزید.", "جو و آب جوش اضافه کنید.", "سبزی خردشده را بریزید و بپزید.", "با آبلیمو سرو کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "اشکنه",
        "ingredients": ["تخم مرغ ۲ عدد", "پیاز ۲ عدد", "آرد ۱ قاشق", "زردچوبه", "نعنا خشک", "نمک، فلفل", "آب جوش"],
        "steps": ["پیاز را خلالی سرخ کنید.", "زردچوبه و آرد را اضافه کنید.", "آب جوش بریزید.", "نعنا خشک را اضافه کنید.", "تخم مرغ‌ها را یکی یکی بشکنید و بگذارید ببندد."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "آبگوشت",
        "ingredients": ["گوشت گوساله ۳۰۰ گرم", "نخود و لوبیا سفید هرکدام نصف پیمانه", "سیب زمینی ۲ عدد", "گوجه فرنگی ۲ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "لیمو عمانی", "نمک، فلفل، زردچوبه"],
        "steps": ["حبوبات را از شب قبل خیس کنید.", "همه مواد را در قابلمه ریخته و با آب بپزید.", "بعد از ۲ ساعت سیب زمینی‌ها را اضافه کنید.", "وقتی پخت، آب آن را جدا کرده و نان ترید کنید.", "گوشت و سیب زمینی و حبوبات را بکوبید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "دلمه فلفل دلمه‌ای",
        "ingredients": ["فلفل دلمه‌ای ۴ عدد", "گوشت چرخ‌کرده ۲۰۰ گرم", "برنج ۱ پیمانه", "لپه نیم‌پز نصف پیمانه", "سبزی دلمه ۱۰۰ گرم", "پیاز", "رب گوجه", "نمک، فلفل"],
        "steps": ["فلفل‌ها را از سر خالی کنید.", "مواد را مخلوط و داخل فلفل‌ها بریزید.", "کف قابلمه کمی رب گوجه و آب بریزید.", "دلمه‌ها را بچینید.", "با حرارت ملایم ۴۵ دقیقه بپزید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "کتلت",
        "ingredients": ["گوشت چرخ‌کرده ۳۰۰ گرم", "سیب زمینی پخته ۲ عدد", "تخم مرغ ۲ عدد", "پیاز ۱ عدد", "آرد سوخاری", "نمک، فلفل", "زردچوبه"],
        "steps": ["سیب زمینی را رنده کرده و با گوشت مخلوط کنید.", "پیاز رنده‌شده، تخم مرغ و ادویه را اضافه کنید.", "ورز دهید و به شکل بیضی درآورید.", "در آرد سوخاری بغلتانید.", "در روغن داغ سرخ کنید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "فلافل",
        "ingredients": ["نخود ۱ پیمانه (خیس‌خورده)", "سیر ۳ حبه", "جعفری تازه ۱ پیمانه", "پیاز ۱ عدد", "بکینگ پودر ۱ قاشق", "ادویه فلافل (زیره، گشنیز، فلفل)", "نمک", "روغن برای سرخ‌کردن"],
        "steps": ["نخود خیس‌خورده را با سیر، پیاز و جعفری چرخ کنید.", "ادویه و بکینگ پودر را اضافه کنید.", "به شکل گرد درآورید.", "در روغن داغ سرخ کنید تا طلایی شود.", "با نان پیتا و سس ارده سرو کنید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "سمبوسه",
        "ingredients": ["لواش یا خمیر یوفکا", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "سیب زمینی پخته ۱ عدد", "سبزیجات معطر", "نمک، فلفل", "زردچوبه", "روغن"],
        "steps": ["پیاز را تفت دهید، گوشت را اضافه کنید.", "سیب زمینی رنده‌شده و ادویه را بیفزایید.", "مواد را داخل خمیر بپیچید.", "لبه‌ها را با چسب آرد ببندید.", "در روغن داغ سرخ کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "پیراشکی گوشت",
        "ingredients": ["خمیر پای (آرد، کره، آب)", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "قارچ", "فلفل دلمه‌ای", "پنیر پیتزا", "نمک، فلفل"],
        "steps": ["خمیر را پهن و قالب بزنید.", "مواد را داخل خمیر بگذارید.", "کمی پنیر پیتزا روی آن بریزید.", "خمیر را ببندید.", "در فر ۱۸۰ درجه به مدت ۲۵ دقیقه بپزید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "نرگسی",
        "ingredients": ["اسفناج ۳۰۰ گرم", "تخم مرغ ۴ عدد", "پیاز ۱ عدد", "سیر ۲ حبه", "نمک، فلفل", "روغن"],
        "steps": ["اسفناج را بشویید و خرد کنید.", "پیاز و سیر را تفت دهید، اسفناج را اضافه کنید.", "وقتی اسفناج نرم شد، تخم مرغ‌ها را بشکنید.", "در تابه را بگذارید تا تخم مرغ‌ها ببندند.", "با نان سرو کنید."],
        "rating": 4.4, "url": ""
    },
    {
        "title": "بورانی اسفناج",
        "ingredients": ["اسفناج ۳۰۰ گرم", "ماست ۱ پیمانه", "سیر ۲ حبه", "گردو", "نمک، فلفل", "نعنا خشک"],
        "steps": ["اسفناج را پخته و آب آن را بگیرید.", "سیر را له کنید.", "ماست را با اسفناج، سیر و ادویه مخلوط کنید.", "گردو و نعنا خشک روی آن بپاشید.", "با نان سرو کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "کشک بادمجان",
        "ingredients": ["بادمجان ۴ عدد", "کشک ۱ پیمانه", "سیر ۳ حبه", "پیاز داغ", "نعنا داغ", "گردو", "نمک، فلفل"],
        "steps": ["بادمجان‌ها را کبابی و پوست بگیرید.", "سیر را له کرده و با بادمجان تفت دهید.", "کشک رقیق‌شده را اضافه کنید.", "نمک و فلفل بزنید.", "با پیاز داغ، نعنا داغ و گردو تزئین کنید."],
        "rating": 4.7, "url": ""
    },
    {
        "title": "حمص",
        "ingredients": ["نخود پخته ۱ پیمانه", "ارده ۳ قاشق", "سیر ۲ حبه", "آبلیمو ۲ قاشق", "روغن زیتون", "نمک"],
        "steps": ["نخود را با کمی آب و سیر میکس کنید.", "ارده و آبلیمو را اضافه کنید.", "نمک بزنید و هم بزنید تا نرم شود.", "در ظرف بریزید و روی آن روغن زیتون بدهید.", "با نان تازه سرو کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "مرصع پلو",
        "ingredients": ["برنج ۳ پیمانه", "مرغ ۴ تکه", "خلال بادام و پسته", "زرشک", "هویج خلال‌شده", "پوست پرتقال", "زعفران", "شکر", "کره"],
        "steps": ["برنج را آبکش کنید و دم بگذارید.", "مرغ را با پیاز و ادویه بپزید.", "هویج را با شکر و کره تفت دهید.", "زرشک و خلال‌ها را تفت دهید.", "برنج را در دیس بکشید و مرغ و خلال و زرشک را تزئین کنید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "لوبیا پلو",
        "ingredients": ["برنج ۲ پیمانه", "لوبیا سبز ۲۰۰ گرم", "گوشت چرخ‌کرده ۲۰۰ گرم", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "زعفران", "نمک، فلفل"],
        "steps": ["لوبیا سبز را خرد کرده و تفت دهید.", "پیاز و گوشت را تفت دهید، رب گوجه اضافه کنید.", "برنج را آبکش کرده و با مواد مخلوط کنید.", "دم کنید.", "با زعفران تزئین کنید."],
        "rating": 4.5, "url": ""
    },
    {
        "title": "کوفته تبریزی",
        "ingredients": ["گوشت چرخ‌کرده ۳۰۰ گرم", "لپه پخته ۱ پیمانه", "برنج نیم‌پز ۱ پیمانه", "پیاز ۱ عدد", "تخم مرغ ۱ عدد", "سبزی معطر", "آلو و گردو برای مغز", "رب گوجه", "نمک، فلفل"],
        "steps": ["گوشت، لپه، برنج، پیاز و تخم مرغ را مخلوط کنید.", "از مواد گلوله‌های بزرگ درست کنید.", "وسط هر کوفته یک آلو و گردو بگذارید.", "در قابلمه رب گوجه و آب جوش بریزید.", "کوفته‌ها را بگذارید و ۱.۵ ساعت بپزید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "تاس کباب",
        "ingredients": ["گوشت خورشتی ۳۰۰ گرم", "سیب زمینی ۲ عدد", "هویج ۲ عدد", "پیاز ۱ عدد", "رب گوجه ۱ قاشق", "نمک، فلفل", "زردچوبه"],
        "steps": ["پیاز را تفت دهید، گوشت را اضافه کنید.", "رب گوجه و ادویه را بریزید.", "سیب زمینی و هویج خردشده را اضافه کنید.", "کمی آب بریزید.", "با حرارت ملایم بپزید تا گوشت نرم شود."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "جوجه کباب",
        "ingredients": ["تکه‌های مرغ ۵۰۰ گرم", "ماست ۱ پیمانه", "زعفران", "آبلیمو", "پیاز", "نمک، فلفل", "روغن زیتون"],
        "steps": ["مرغ را با ماست، آبلیمو، زعفران و ادویه مزه‌دار کنید.", "۲-۴ ساعت استراحت دهید.", "به سیخ بکشید.", "روی ذغال کباب کنید.", "با برنج زعفرانی سرو کنید."],
        "rating": 4.8, "url": ""
    },
    {
        "title": "خورش خلال بادام",
        "ingredients": ["گوشت خورشتی ۳۰۰ گرم", "خلال بادام ۱ پیمانه", "زرشک ۲ قاشق", "زعفران", "پیاز", "رب گوجه", "نمک، فلفل"],
        "steps": ["پیاز را تفت دهید، گوشت را اضافه کنید.", "رب گوجه و ادویه را بریزید.", "خلال بادام و زرشک را اضافه کنید.", "آب جوش بریزید و بپزید.", "با زعفران تزئین کنید."],
        "rating": 4.6, "url": ""
    },
    {
        "title": "بریانی اصفهان",
        "ingredients": ["گوشت چرخ‌کرده ۳۰۰ گرم", "جگر سفید گوسفندی ۱۰۰ گرم", "پیاز ۲ عدد", "زعفران", "دارچین", "نمک، فلفل", "نعنا خشک"],
        "steps": ["پیاز را تفت دهید، گوشت و جگر را اضافه کنید.", "دارچین و نعنا و ادویه را بریزید.", "کاملاً تفت دهید تا سرخ شود.", "با نان سنگک و سبزی خوردن سرو کنید."],
        "rating": 4.7, "url": ""
    }
]

# ---------- 3. پایگاه داده رسپی‌ها ----------
DB_DIR = os.path.join(os.path.dirname(__file__), 'chef_data')
os.makedirs(DB_DIR, exist_ok=True)

class RecipeDB:
    def __init__(self):
        self.recipes_file = os.path.join(DB_DIR, "recipes.json")
        self.next_id = 1
        self.recipes = self.load_recipes()
        if self.recipes:
            self.next_id = max(r['id'] for r in self.recipes) + 1
        self.id_to_idx = {r['id']: i for i, r in enumerate(self.recipes)}
        self.vocab = set()
        self.idf = {}
        self.recipe_vectors = []
        self._dirty = False
        self.build_index()

    def load_recipes(self):
        if os.path.exists(self.recipes_file):
            with open(self.recipes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        recipes = []
        for r in SEED_RECIPES:
            new_r = r.copy()
            new_r["id"] = self.next_id
            self.next_id += 1
            new_r["added_date"] = datetime.date.today().isoformat()
            recipes.append(new_r)
        self.save_recipes_to_disk(recipes)
        return recipes

    def save_recipes_to_disk(self, recipes=None):
        if recipes is None:
            recipes = self.recipes
        with open(self.recipes_file, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)

    def save_recipes(self):
        self.save_recipes_to_disk(self.recipes)

    def add_recipe(self, title, ingredients, steps, url, rating=None):
        if url and any(r['url'] == url for r in self.recipes):
            return None
        rid = self.next_id
        self.next_id += 1
        recipe = {
            "id": rid,
            "title": title,
            "ingredients": ingredients,
            "steps": steps,
            "url": url,
            "rating": rating,
            "added_date": datetime.date.today().isoformat()
        }
        self.recipes.append(recipe)
        self.id_to_idx[rid] = len(self.recipes) - 1
        self.update_index_for_recipe(recipe)
        self.save_recipes()
        return rid

    def build_index(self):
        self.vocab = set()
        all_terms = []
        self.recipe_vectors = []
        for r in self.recipes:
            terms = self._recipe_to_terms(r)
            all_terms.append(terms)
            self.vocab.update(terms)
        N = len(self.recipes)
        self.idf = {}
        for term in self.vocab:
            df = sum(1 for terms in all_terms if term in terms)
            self.idf[term] = math.log((N + 1) / (df + 1)) + 1
        for terms in all_terms:
            vec = self._compute_tfidf_vector(terms)
            self.recipe_vectors.append(vec)
        self._dirty = False

    def update_index_for_recipe(self, recipe):
        terms = self._recipe_to_terms(recipe)
        vec = self._compute_tfidf_vector(terms)
        self.recipe_vectors.append(vec)
        for term in set(terms):
            if term not in self.vocab:
                self.vocab.add(term)
            df = sum(1 for v in self.recipe_vectors if term in v)
            N = len(self.recipe_vectors)
            self.idf[term] = math.log((N + 1) / (df + 1)) + 1
        self._dirty = True

    def _recipe_to_terms(self, recipe):
        text = recipe['title'] + ' ' + ' '.join(recipe['ingredients'])
        return list(set(nlp.process_query(text)))

    def _compute_tfidf_vector(self, terms):
        vec = defaultdict(float)
        term_counts = Counter(terms)
        for term, count in term_counts.items():
            if term in self.idf:
                vec[term] = (math.log(1 + count)) * self.idf[term]
            else:
                vec[term] = (math.log(1 + count)) * 1.0
        norm = math.sqrt(sum(v ** 2 for v in vec.values()))
        if norm > 0:
            for term in vec:
                vec[term] /= norm
        return dict(vec)

    def search(self, query_terms, exclude_ids=None):
        if self._dirty:
            self.build_index()
        exclude_ids = exclude_ids or []
        query_vec = defaultdict(float)
        counts = Counter(query_terms)
        for term, cnt in counts.items():
            if term in self.idf:
                query_vec[term] = (math.log(1 + cnt)) * self.idf[term]
        norm = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        if norm > 0:
            for term in query_vec:
                query_vec[term] /= norm
        scores = []
        for i, rvec in enumerate(self.recipe_vectors):
            if self.recipes[i]['id'] in exclude_ids:
                continue
            dot = sum(query_vec.get(t, 0) * rvec.get(t, 0) for t in set(query_vec) | set(rvec))
            scores.append((dot, self.recipes[i]))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores

# ---------- 4. پروفایل کاربر ----------
TASTY_SPICES = ["زعفران", "دارچین", "زیره", "هل", "جوز هندی", "فلفل سیاه", "پاپریکا", "تخم گشنیز", "زردچوبه", "نعنا خشک"]
FOOD_KEYWORDS = {
    "protein": ["مرغ", "گوشت", "ماهی", "میگو", "تخم مرغ", "حبوبات", "عدس", "لوبیا", "تن ماهی"],
    "veg": ["بادمجان", "کدو", "اسفناج", "قارچ", "کلم", "هویج", "گوجه", "سیب زمینی", "پیاز"],
    "taste": ["تند", "شیرین", "ترش", "شور", "ملس", "ادویه‌ای", "فلفلی"],
    "style": ["سریع", "آسان", "مجلس", "سنتی", "فانتزی", "رژیمی", "سالم", "خوشمزه"],
}

class UserProfile:
    def __init__(self, filepath):
        self.file = filepath
        self.data = self.load()
        self.weights = self.data.get("weights", {
            "tfidf_sim": 0.25, "pref_match": 0.20, "rating": 0.15,
            "ing_count": 0.10, "spices": 0.10, "season": 0.05, "exploration": 0.15
        })
        self.ratings = self.data.get("ratings", {})
        self.preferences = self.data.get("preferences", {"protein": [], "taste": [], "style": [], "veg": []})
        self.beta_params = self.data.get("beta_params", {})

    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save(self):
        self.data["weights"] = self.weights
        self.data["ratings"] = self.ratings
        self.data["preferences"] = self.preferences
        self.data["beta_params"] = self.beta_params
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def record_rating(self, recipe_id, rating):
        self.ratings[str(recipe_id)] = rating
        if str(recipe_id) not in self.beta_params:
            self.beta_params[str(recipe_id)] = [1, 1]
        alpha, beta = self.beta_params[str(recipe_id)]
        if rating >= 7:
            alpha += 1
        elif rating <= 4:
            beta += 1
        self.beta_params[str(recipe_id)] = [alpha, beta]
        self.save()

    def update_preferences(self, recipe, rating):
        if rating >= 7:
            ing_text = ' '.join(recipe['ingredients']).lower()
            for p in FOOD_KEYWORDS["protein"]:
                if p in ing_text and p not in self.preferences["protein"]:
                    self.preferences["protein"].append(p)
            for t in FOOD_KEYWORDS["taste"]:
                if t in recipe['title'].lower() or t in ing_text:
                    if t not in self.preferences["taste"]:
                        self.preferences["taste"].append(t)
            for k in self.preferences:
                self.preferences[k] = self.preferences[k][-10:]

    def online_learn(self, features, predicted_score, rating):
        target = rating / 10.0
        error = target - predicted_score
        lr = 0.02
        for key in self.weights:
            grad = error * features[key]
            self.weights[key] += lr * grad
        total = sum(self.weights.values())
        for key in self.weights:
            self.weights[key] /= total
        self.save()

# ---------- 5. امتیازدهی ----------
class Scorer:
    def __init__(self, user_profile, recipe_db):
        self.user = user_profile
        self.db = recipe_db

    def compute_features(self, recipe, query_terms=None):
        feat = {}
        if query_terms:
            query_set = set(query_terms)
            rec_terms = set(self.db._recipe_to_terms(recipe))
            feat['tfidf_sim'] = len(query_set & rec_terms) / max(len(query_set), 1)
        else:
            feat['tfidf_sim'] = 0.5
        pref_score = 0
        ing_text = ' '.join(recipe['ingredients']).lower()
        title = recipe['title'].lower()
        for p in self.user.preferences.get("protein", []):
            if p in ing_text:
                pref_score += 0.4
        for t in self.user.preferences.get("taste", []):
            if t in title or t in ing_text:
                pref_score += 0.3
        feat['pref_match'] = min(pref_score, 1.0)
        feat['rating'] = min(recipe.get('rating', 0) or 0, 5) / 5.0
        feat['ing_count'] = min(len(recipe['ingredients']) / 15.0, 1.0)
        spice_count = sum(1 for s in TASTY_SPICES if s in ing_text)
        feat['spices'] = min(spice_count / 5.0, 1.0)
        now = datetime.datetime.now()
        month = now.month
        if month in [1, 2, 12]:
            feat['season'] = 0.8 if any(x in recipe['title'] for x in ["آش", "سوپ", "حلیم"]) else 0.3
        elif month in [6, 7, 8]:
            feat['season'] = 0.8 if any(x in recipe['title'] for x in ["سالاد", "بستنی", "شربت"]) else 0.3
        else:
            feat['season'] = 0.5
        rid = str(recipe['id'])
        if rid in self.user.beta_params:
            a, b = self.user.beta_params[rid]
            feat['exploration'] = np.random.beta(a, b)
        else:
            feat['exploration'] = np.random.beta(1, 1)
        return feat

    def score(self, recipe, query_terms=None):
        features = self.compute_features(recipe, query_terms)
        score = 0.0
        for key, w in self.user.weights.items():
            score += w * features.get(key, 0)
        return score, features

# ---------- 6. توابع کمکی ----------
CALORIE_DB = {"برنج": 130, "مرغ": 165, "گوشت چرخ‌کرده": 250, "روغن": 884, "پیاز": 40,
              "سیر": 149, "رب گوجه": 82, "زعفران": 310, "نمک": 0, "فلفل": 251,
              "سیب زمینی": 77, "گوجه فرنگی": 18, "بادمجان": 25, "عدس": 116, "لوبیا": 127}
def estimate_calories(ingredients):
    total = 0
    for ing in ingredients:
        for key, cal in CALORIE_DB.items():
            if key in ing:
                total += cal * 0.5
    return f"{int(total)} کیلوکالری (تخمینی)"

def shopping_link(ingredients):
    base = "https://www.digikala.com/search/?q="
    return base + "+".join(ingredients[:5]).replace(" ", "+")

def search_web_recipes(query, max_results=5):
    encoded_query = urllib.parse.quote_plus(f"{query} دستور پخت")
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = []
        for a in soup.select('a.result__a, a.result__url, a[class*="result"]'):
            href = a.get('href')
            if href and href.startswith('http') and 'duckduckgo.com' not in href:
                if href not in links:
                    links.append(href)
                    if len(links) >= max_results:
                        return links
        return links
    except:
        return []

def extract_recipe_from_url(url):
    try:
        html = requests.get(url, timeout=10).content
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "بدون عنوان"
        ingredients = [li.get_text(strip=True) for li in soup.find_all('li')] if soup.find('ul') else []
        steps = [li.get_text(strip=True) for li in soup.find_all('li')] if soup.find('ol') else []
        rating = None
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    rating = data.get('aggregateRating', {}).get('ratingValue')
                elif isinstance(data, list):
                    for item in data:
                        r = item.get('aggregateRating', {}).get('ratingValue')
                        if r: rating = r
            except:
                pass
        return {'title': title, 'ingredients': ingredients, 'steps': steps, 'rating': float(rating) if rating else None, 'url': url}
    except:
        return None

# ---------- 7. حالت‌های مکالمه ----------
conversation_states = {}

def get_or_create_state(conversation_id):
    if conversation_id not in conversation_states:
        profile_path = os.path.join(DB_DIR, f"user_{conversation_id}.json")
        profile = UserProfile(profile_path)
        db = RecipeDB()
        scorer = Scorer(profile, db)
        conversation_states[conversation_id] = {
            'profile': profile,
            'db': db,
            'scorer': scorer,
            'last_suggested': None,
            'selected_recipe': None,
            'awaiting_rating': False
        }
    return conversation_states[conversation_id]

def format_recipe(recipe, score=None):
    cal = estimate_calories(recipe['ingredients'])
    steps = recipe['steps'][:5]
    steps_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
    return (
        f"🍲 **{recipe['title']}** (امتیاز: {score:.2f})\n"
        f"📋 مواد: {', '.join(recipe['ingredients'][:10])}{'...' if len(recipe['ingredients']) > 10 else ''}\n"
        f"🔥 کالری تقریبی: {cal}\n"
        f"🛒 خرید مواد: {shopping_link(recipe['ingredients'])}\n"
        f"👨‍🍳 دستور پخت:\n{steps_str}"
    )

# ---------- 8. تابع اصلی process ----------
def process(message: str, conversation_id: str = None, is_new: bool = False) -> str:
    if not message.strip():
        return "لطفاً پیام خود را وارد کنید."

    if conversation_id is None:
        return "خطا: شناسه گفت‌وگو یافت نشد."

    state = get_or_create_state(conversation_id)
    db = state['db']
    profile = state['profile']
    scorer = state['scorer']
    msg = message.strip()

    if is_new:
        return "سلام! 🌟 امشب دوست داری چی بخوری؟ (هر چی دوست داری بگو؛ مثلاً «یه غذای تند»، «خوراک مرغ»، «چیزای گیاهی»...)"

    # حالت انتظار امتیاز
    if state['awaiting_rating'] and state['selected_recipe']:
        if msg.isdigit() and 1 <= int(msg) <= 10:
            rating = int(msg)
            recipe = state['selected_recipe']
            profile.record_rating(recipe['id'], rating)
            profile.update_preferences(recipe, rating)
            if state['last_suggested']:
                for s, r, f in state['last_suggested']:
                    if r['id'] == recipe['id']:
                        profile.online_learn(f, s, rating)
                        break
            state['awaiting_rating'] = False
            state['selected_recipe'] = None
            return f"👍 امتیاز {rating} با موفقیت ثبت شد. هر زمان غذای دیگری خواستی، فقط بگو. 😊"
        else:
            return "لطفاً یک عدد از ۱ تا ۱۰ برای امتیاز وارد کنید."

    # انتخاب غذا (۱-۳) از آخرین پیشنهادها
    if msg.isdigit() and state['last_suggested'] and 1 <= int(msg) <= 3:
        idx = int(msg) - 1
        if idx < len(state['last_suggested']):
            selected = state['last_suggested'][idx]
            state['selected_recipe'] = selected[1]
            state['awaiting_rating'] = True
            return f"شما «{selected[1]['title']}» را انتخاب کردید. لطفاً از ۱ تا ۱۰ امتیاز دهید."
        else:
            return "عدد وارد شده معتبر نیست."

    # جستجوی جدید
    terms = nlp.process_query(msg)
    results = db.search(terms)
    if not results:
        web_query = " ".join(terms[:4])
        urls = search_web_recipes(web_query)
        if urls:
            for url in urls:
                rec = extract_recipe_from_url(url)
                if rec and rec['ingredients'] and rec['steps']:
                    db.add_recipe(rec['title'], rec['ingredients'], rec['steps'], url, rec.get('rating'))
            db.build_index()
            results = db.search(terms)
    if not results:
        return "متأسفانه برای این درخواست دستور پختی پیدا نشد. لطفاً عبارت دیگری را جستجو کنید. 🙁"

    top_recipes = []
    for sim, recipe in results[:5]:
        score, features = scorer.score(recipe, terms)
        top_recipes.append((score, recipe, features))
    top_recipes.sort(key=lambda x: x[0], reverse=True)
    state['last_suggested'] = top_recipes[:3]

    response = "🔥 بهترین پیشنهادها برای شما:\n"
    for i, (sc, rec, _) in enumerate(top_recipes[:3], 1):
        response += f"\n--- گزینه {i} ---\n"
        response += format_recipe(rec, sc)
    response += "\n\n📥 لطفاً شماره غذای مورد نظر (۱-۳) را وارد کنید تا امتیاز دهید، یا درخواست جدیدی بدهید."
    return response

# ---------- 9. رابط ربات ----------
def generate_response(user_message, conv_id=None):
    """تابعی که ربات صدا می‌زند. شناسه گفتگو را به عنوان conversation_id استفاده می‌کند."""
    if conv_id is None:
        conv_id = "default"
    conv_id = str(conv_id)
    profile_path = os.path.join(DB_DIR, f"user_{conv_id}.json")
    is_new = not os.path.exists(profile_path)
    return process(user_message, conv_id, is_new)