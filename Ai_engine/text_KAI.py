"""
نسخهٔ ۵ – تولید متن هوشمند فارسی (سازگار با بات بله)
"""

import sys
import os
import re
import json
import random
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Any, Tuple

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


class SmartPersianGenerator:
    def __init__(self):
        self._init_sentence_patterns()
        self._init_phrase_bank()
        self._init_knowledge_snippets()
        self._init_text_structures()
        self._init_tone_lexicon()
        self._init_topic_expander()
        self._init_synonyms()

        self.unigram_counts = Counter()
        self.bigram_counts = defaultdict(Counter)
        self.trigram_counts = defaultdict(Counter)
        self.vocabulary = set()
        self.total_tokens = 0
        self.is_ngram_ready = False
        self._train_from_corpus_if_exists()

        self.sessions: Dict[str, Dict[str, Any]] = {}

    # --------------- بانک‌های واژگانی ---------------
    def _init_sentence_patterns(self):
        self.sentence_patterns = {
            "general": [
                "امروزه {topic} به یکی از مباحث داغ محافل علمی و عمومی تبدیل شده است.",
                "شاید بارها نام {topic} به گوشتان خورده باشد؛ اما واقعاً چقدر با آن آشنایید؟",
                "اگر بخواهیم صادق باشیم، {topic} نقش بی‌بدیلی در زندگی مدرن ایفا می‌کند.",
                "نکتهٔ جالبی که کمتر به آن توجه می‌شود، اهمیت {topic} در {subtopic} است.",
                "با رشد روزافزون فناوری، {topic} بیش از پیش اهمیت پیدا کرده است.",
            ],
            "cause_effect": [
                "از آنجا که {topic} مستقیماً بر روی {subtopic} تأثیر می‌گذارد، بی‌توجهی به آن عواقب ناخوشایندی دارد.",
                "علت اصلی گرایش روزافزون به {topic} را می‌توان در {benefit} جستجو کرد.",
                "هرچه بیشتر به {topic} بها دهیم، {benefit} بیشتری نصیبمان خواهد شد.",
            ],
            "advice": [
                "توصیهٔ اکید کارشناسان این است که برای بهبود {topic}، از {method} شروع کنید.",
                "اگر به دنبال {benefit} هستید، بهتر است بیش از پیش به {topic} اهمیت بدهید.",
                "فراموش نکنید که حتی قدم‌های کوچک در مسیر {topic}، نتایج بزرگی به همراه دارد.",
            ],
            "question": [
                "آیا تاکنون از خود پرسیده‌اید که بدون {topic} دنیای امروز چگونه بود؟",
                "چرا برخی افراد هنوز ارزش واقعی {topic} را درک نکرده‌اند؟",
                "به نظر شما مهم‌ترین چالش پیش روی {topic} چیست؟",
            ],
            "comparison": [
                "در مقایسه با روش‌های سنتی، {topic} مزایای چشمگیری مانند {benefit} دارد.",
                "اگر {topic} را با {subtopic} مقایسه کنیم، تفاوت‌ها شگفت‌انگیز خواهد بود.",
            ],
            "example": [
                "برای روشن‌تر شدن مطلب، {example} را در نظر بگیرید.",
                "نمونهٔ بارز موفقیت در {topic}، داستان {example} است که الهام‌بخش بسیاری بوده.",
            ],
            "conclusion": [
                "در پایان باید اذعان داشت که {topic} نه یک گزینه، بلکه یک ضرورت اجتناب‌ناپذیر است.",
                "سخن آخر آنکه آینده از آن کسانی است که امروز برای {topic} سرمایه‌گذاری می‌کنند.",
            ],
            "story": [
                "تصور کنید {topic} را کاملاً نادیده می‌گرفتیم؛ زندگی‌مان چه شکلی بود؟",
                "روزی شخصی به نام {character} متوجه اهمیت {topic} شد و زندگیش دگرگون گشت.",
            ]
        }

    def _init_phrase_bank(self):
        self.connectors = {
            "addition": ["علاوه بر این", "همچنین", "از سوی دیگر", "به همین ترتیب"],
            "contrast": ["با این حال", "اما", "در مقابل", "هرچند که"],
            "cause": ["به همین دلیل", "از این رو", "در نتیجه", "بنابراین"],
            "example": ["برای مثال", "به عنوان نمونه", "شاهد این مدعا"],
            "emphasis": ["به جرأت می‌توان گفت", "باید تأکید کرد که", "نکتهٔ قابل توجه این است"],
            "conclusion": ["در نهایت", "خلاصه آنکه", "حاصل کلام", "پس می‌توان نتیجه گرفت"]
        }
        self.hashtags_pool = ["آموزش", "موفقیت", "خلاقیت", "نوآوری", "فناوری", "زندگی_بهتر", "کسب‌وکار", "انگیزه", "توسعه_فردی"]

    def _init_knowledge_snippets(self):
        self.wisdom_quotes = [
            "یادگیری هرگز متوقف نمی‌شود؛ هر روز فرصتی تازه است.",
            "موفقیت مجموعه‌ای از شکست‌های کوچک است که به یک پیروزی بزرگ ختم می‌شود.",
            "اگر می‌خواهید چیزی را تغییر دهید، اول خودتان شروع کنید.",
            "خلاقیت یعنی دیدن چیزی که همه دیده‌اند و اندیشیدن به چیزی که هیچ‌کس نیندیشیده.",
            "آینده به کسانی تعلق دارد که آن را باور دارند و برایش تلاش می‌کنند.",
            "بزرگ‌ترین ریسک، ریسک نکردن است.",
            "هر شکست، درس‌آموزتر از هزار موفقیت بی‌زحمت است.",
            "تنها راه انجام کار بزرگ، عشق به کاری است که انجام می‌دهید. – استیوجابز"
        ]
        self.general_facts = [
            "تحقیقات دانشگاه هاروارد نشان می‌دهد یادگیری یک مهارت جدید تراکم سیناپسی را افزایش می‌دهد.",
            "بر اساس گزارش مجمع جهانی اقتصاد، ۵۰٪ مشاغل تا سال ۲۰۳۰ به مهارت‌های جدید نیاز خواهند داشت.",
            "مطالعه‌ای در دانشگاه استنفورد نشان داد که پیاده‌روی روزانه، خلاقیت را تا ۶۰٪ افزایش می‌دهد.",
            "از هر ۵ نفر، ۴ نفر معتقدند که برنامه‌ریزی روزانه تأثیر مستقیمی بر موفقیتشان دارد.",
            "بر اساس آمار، افرادی که تفکر مثبت دارند، ۲۳٪ عمر طولانی‌تری دارند.",
            "شرکت‌هایی که نوآوری را در اولویت قرار می‌دهند، ۳ برابر سریع‌تر رشد می‌کنند."
        ]
        self.proverbs = [
            "از تو حرکت، از خدا برکت.",
            "کار نیکو کردن از پر کردن است.",
            "همان‌طور که کاشته‌ای، درو خواهی کرد.",
            "نابرده رنج، گنج میسر نمی‌شود.",
            "رهرو آن نیست که گه تند و گهی خسته رود، رهرو آن است که آهسته و پیوسته رود."
        ]

    def _init_text_structures(self):
        self.text_structures = {
            "ایمیل": {
                "opening": ["سلام و عرض ادب", "با سلام خدمت شما", "درود بر شما", "سلام {recipient} عزیز"],
                "body_patterns": [
                    "امیدوارم حالتان خوب باشد. در رابطه با «{topic}» خواستم {purpose} را عرض کنم.",
                    "پیرو گفت‌وگوی قبلی‌مان دربارهٔ {topic}، لطفاً {request}.",
                ],
                "closing": [
                    "با سپاس فراوان،\n{signature}",
                    "پیشاپیش از همکاری شما متشکرم.\nارادتمند،\n{signature}",
                    "منتظر پاسخ شما هستم.\nبا احترام،\n{signature}",
                ],
                "subject_default": "دربارهٔ {topic}"
            },
            "پست_اینستاگرام": {
                "intro": [
                    "✨ اینم یه نکتهٔ ناب دربارهٔ {topic}:",
                    "تا حالا فکر کردی {topic} چطور می‌تونه روزتو بسازه؟",
                ],
                "body_options": [
                    "{core_sentence} {extra_sentence}",
                    "{core_sentence} و واقعیت اینه که {extra_advice}",
                ],
                "outro": [
                    "نظرت چیه؟ برام کامنت بذار. 👇",
                    "تجربه‌ات رو با ما به اشتراک بذار. 💬",
                ]
            },
            "یادداشت_وبلاگ": {
                "title": "نگاهی عمیق به {topic}",
                "intro": [
                    "در دنیای پرشتاب امروز، {topic} به یکی از مسائل کلیدی تبدیل شده است.",
                    "همهٔ ما در بره‌ای از زندگی با مفهوم {topic} مواجه شده‌ایم؛ بیایید با هم بررسی‌اش کنیم.",
                ],
                "body_sections": [
                    ("چرا {topic} مهم است؟", "اهمیت {topic} را نمی‌توان انکار کرد. {reason}"),
                    ("چگونه می‌توانیم {topic} را بهبود بخشیم؟", "برای بهبود {topic}، {method}"),
                    ("نمونه‌های موفق", "نمونه‌های موفق نشان می‌دهند که با {approach} می‌توان به نتایج درخشانی رسید."),
                    ("چالش‌های پیش رو", "مهم‌ترین مانع در مسیر {topic}، {challenge} است."),
                ],
                "conclusion": [
                    "سخن آخر اینکه، {topic} نه تنها یک انتخاب، بلکه یک ضرورت است.",
                ]
            },
            "توییت": {
                "pattern": [
                    "{topic} رو دست کم نگیر. {reason_short} #انگیزشی",
                    "یه راه ساده برای {topic}: {simple_advice} 👌",
                ]
            },
            "تبلیغاتی": {
                "pattern": [
                    "با {product} می‌تونی {benefit} رو تجربه کنی. همین حالا شروع کن. 🚀",
                    "{problem} داری؟ {product} راه‌حلشه. {cta}",
                ]
            },
            "داستان_کوتاه": {
                "opening": ["روزی روزگاری، در دنیایی که {topic} حکمرانی می‌کرد،"],
                "plot": "{character} با چالش {challenge} مواجه بود. {event}",
                "ending": "و سرانجام، {lesson}",
            }
        }

    def _init_tone_lexicon(self):
        self.tone_lexicon = {
            "رسمی": {
                "request": ["خواهشمند است", "استدعا می‌شود"],
                "thanks": ["با سپاس فراوان", "پیشاپیش از مساعدت شما سپاسگزارم"],
                "signature": ["مدیریت ارتباطات", "کارشناس ارشد"],
            },
            "دوستانه": {
                "request": ["لطف می‌کنی", "یه زحمت برات دارم"],
                "thanks": ["مرسی", "دست‌ت درد نکنه"],
                "signature": ["علی", "مریم", "دوست شما"],
            },
            "طنز": {
                "request": ["تمنا می‌کنم به دادمون برسی"],
                "thanks": ["دمت گرم", "آفرین بر شرفت"],
                "signature": ["کاربر خسته", "نویسندهٔ تازه‌کار"],
            },
            "انگیزشی": {
                "request": ["پس منتظر چی هستی؟", "همین الان اقدام کن"],
                "thanks": ["با قدرت ادامه بده!"],
                "signature": ["مربی موفقیت"],
            }
        }

    def _init_topic_expander(self):
        self.topic_map = {
            "کتاب": {
                "subtopics": ["مطالعه روزانه", "انواع کتاب", "نویسندگان بزرگ"],
                "benefits": ["افزایش دانش", "کاهش استرس"],
                "questions": ["آخرین کتابی که خواندی چه بود؟"],
                "facts": ["مطالعه ۳۰ دقیقه در روز، احتمال آلزایمر را کاهش می‌دهد."],
                "examples": ["بیل گیتس سالانه ۵۰ کتاب می‌خواند."]
            },
            "سلامت": {
                "subtopics": ["تغذیه سالم", "ورزش", "خواب کافی"],
                "benefits": ["طول عمر بیشتر", "انرژی بالاتر"],
                "facts": ["۸۰٪ بیماری‌های قلبی با تغییر سبک زندگی قابل پیشگیری است."],
            },
            "تکنولوژی": {
                "subtopics": ["هوش مصنوعی", "بلاکچین", "اینترنت اشیا"],
                "benefits": ["اتوماسیون فرآیندها", "دسترسی سریع به اطلاعات"],
                "examples": ["تسلا با خودروهای خودران صنعت حمل‌ونقل را دگرگون کرد."]
            },
            "موفقیت": {
                "subtopics": ["هدف‌گذاری هوشمند", "عادت‌های افراد موفق"],
                "benefits": ["رضایت شغلی", "اعتماد به نفس"],
                "facts": ["۸۴٪ افراد موفق، روزانه مطالعه می‌کنند."]
            }
        }
        self.default_topic_expansion = {
            "subtopics": ["اهمیت", "روش‌های بهبود", "چالش‌ها"],
            "benefits": ["ارتقای کیفیت زندگی", "صرفه‌جویی در زمان"],
            "questions": ["آیا تا به حال به تأثیر آن فکر کرده‌اید؟"],
            "facts": ["این حوزه روزبه‌روز در حال گسترش است."],
            "examples": ["برای نمونه می‌توان به موفقیت فلان اشاره کرد."]
        }

    def _init_synonyms(self):
        self.synonyms = {
            "خوب": ["عالی", "مناسب", "مطلوب", "درجه یک", "بی‌نظیر"],
            "بزرگ": ["وسیع", "گسترده", "کلان", "عظیم"],
            "مهم": ["حیاتی", "ضروری", "کلیدی", "اساسی"],
            "زیاد": ["فراوان", "بی‌شمار", "متعدد"],
            "کمک": ["یاری", "مساعدت", "همکاری"],
            "مردم": ["افراد", "اشخاص", "عموم", "جامعه"],
            "زندگی": ["حیات", "روزمرگی", "سبک زندگی"],
            "تغییر": ["دگرگونی", "تحول", "بازنگری"]
        }

    def _synonym_replace(self, sentence: str, probability=0.3) -> str:
        words = sentence.split()
        new_words = []
        for w in words:
            clean_w = re.sub(r'[،\.\؟\!\(\)]', '', w)
            if clean_w in self.synonyms and random.random() < probability:
                replacement = random.choice(self.synonyms[clean_w])
                if w != clean_w:
                    suffix = w[len(clean_w):]
                    replacement += suffix
                new_words.append(replacement)
            else:
                new_words.append(w)
        return ' '.join(new_words)

    # --------------- ابزارهای کمکی ---------------
    def _expand_topic(self, topic: str) -> Dict:
        for key, val in self.topic_map.items():
            if key in topic:
                return val
        dyn = {}
        for k, v in self.default_topic_expansion.items():
            dyn[k] = [item.replace("فلان", topic) for item in v]
        return dyn

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'([،\.\!\?\:\-\)\(])', r' \1 ', text)
        return text.split()

    def _train_from_corpus_if_exists(self):
        corpus_path = os.path.join(os.path.dirname(__file__), 'corpus.txt')
        if os.path.exists(corpus_path):
            try:
                with open(corpus_path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                tokens = self._tokenize(raw)
                if tokens:
                    self.total_tokens = len(tokens)
                    self.vocabulary = set(tokens)
                    self.unigram_counts = Counter(tokens)
                    for i in range(len(tokens)-1):
                        self.bigram_counts[tokens[i]][tokens[i+1]] += 1
                    for i in range(len(tokens)-2):
                        key = (tokens[i], tokens[i+1])
                        self.trigram_counts[key][tokens[i+2]] += 1
                    self.is_ngram_ready = True
            except Exception:
                pass

    def _ngram_gen_sentence(self, max_words=20) -> str:
        if not self.is_ngram_ready or not self.vocabulary:
            return ""
        first_word = random.choices(list(self.unigram_counts.keys()),
                                    weights=list(self.unigram_counts.values()))[0]
        generated = [first_word]
        if first_word in self.bigram_counts:
            second_word = random.choices(list(self.bigram_counts[first_word].keys()),
                                         weights=list(self.bigram_counts[first_word].values()))[0]
            generated.append(second_word)
            current_bigram = (first_word, second_word)
        else:
            second_word = random.choice(list(self.vocabulary))
            generated.append(second_word)
            current_bigram = (first_word, second_word)
        for _ in range(max_words - len(generated)):
            candidates = []
            probs = []
            for w in self.vocabulary:
                trigram_entry = self.trigram_counts.get(current_bigram, {})
                total_tri = sum(trigram_entry.values())
                if total_tri > 0 and w in trigram_entry:
                    p = trigram_entry[w]/total_tri
                elif current_bigram[1] in self.bigram_counts:
                    bigram_entry = self.bigram_counts[current_bigram[1]]
                    total_b = sum(bigram_entry.values())
                    p = bigram_entry[w]/total_b if w in bigram_entry and total_b>0 else 0.0
                else:
                    p = self.unigram_counts.get(w,0)/self.total_tokens if self.total_tokens>0 else 0.0
                if p > 0:
                    candidates.append(w)
                    probs.append(p)
            if not candidates:
                break
            total_p = sum(probs)
            probs = [p/total_p for p in probs]
            next_word = random.choices(candidates, weights=probs)[0]
            generated.append(next_word)
            current_bigram = (current_bigram[1], next_word)
        return ' '.join(generated)

    # =============== تحلیل پیشرفتهٔ درخواست کاربر ===============
    def _understand_request(self, user_msg: str) -> Dict[str, Any]:
        raw = user_msg.strip()
        intent = {
            "topic": "موضوع عمومی",
            "tone": "دوستانه",
            "text_type": "پست_اینستاگرام",
            "recipient": "",
            "length": "متوسط",
            "extra_instructions": [],
            "raw": raw,
            "paragraph_count": None,
            "word_count": None,
            "custom_opening": None,
            "custom_closing": None,
            "custom_phrases": [],
            "subject": None,
            "target_audience": None,
            "cta": None,
            "emojis": None
        }

        # ۱. تعداد پاراگراف
        p_match = re.search(r'(\d+|[یکدو سه چهار پنج شش هفت هشت نه ده])\s*(پاراگراف|بند|بخش)', raw)
        if p_match:
            num_map = {"یک":1,"دو":2,"سه":3,"چهار":4,"پنج":5,"شش":6,"هفت":7,"هشت":8,"نه":9,"ده":10}
            txt_num = p_match.group(1)
            intent["paragraph_count"] = int(txt_num) if txt_num.isdigit() else num_map.get(txt_num, None)

        # ۲. تعداد کلمه
        w_match = re.search(r'(حداقل|حدود|بیش از|کمتر از)?\s*(\d+)\s*(کلمه|واژه)', raw)
        if w_match:
            intent["word_count"] = int(w_match.group(2))

        # ۳. شروع سفارشی
        start_match = re.search(r'(?:شروع کن با|با عبارت|ابتدای متن|ابتدا)\s*[«:"](.+?)[»"](?:\s|$)', raw)
        if not start_match:
            start_match = re.search(r'شروع کن با\s+(.+?)(?:\s|$)', raw)
        if start_match:
            intent["custom_opening"] = start_match.group(1).strip()

        # ۴. پایان سفارشی
        end_match = re.search(r'(?:پایان بده با|در آخر بنویس|آخر متن|امضا)\s*[«:"](.+?)[»"](?:\s|$)', raw)
        if not end_match:
            end_match = re.search(r'پایان بده با\s+(.+?)(?:\s|$)', raw)
        if end_match:
            intent["custom_closing"] = end_match.group(1).strip()

        # ۵. عبارات درج‌شونده
        insert_match = re.findall(r'(?:این جمله رو بذار|اینو بگو|عبارت|ذکر کن)[:\s]*[«"](.+?)[»"]', raw)
        intent["custom_phrases"].extend(insert_match)

        # ۶. موضوع ایمیل
        subj_match = re.search(r'(?:با عنوان|موضوع ایمیل|Subject)\s*[:\s]*[«"]?(.+?)[»"]?\s*(?:\.|$)', raw, re.IGNORECASE)
        if subj_match:
            intent["subject"] = subj_match.group(1).strip()

        # ۷. مخاطب
        audience_match = re.search(r'(?:برای|مناسب|مخاطب)\s+(نوجوانان|کودکان|متخصصان|مبتدی‌ها|عموم|دانشجویان|بانوان)', raw)
        if audience_match:
            intent["target_audience"] = audience_match.group(1)

        # ۸. CTA
        cta_match = re.search(r'(CTA|فراخوان|دعوت به)\s*[:\s]*[«"]?(.+?)[»"]?(?:\s|$)', raw)
        if cta_match:
            intent["cta"] = cta_match.group(2).strip()
        elif re.search(r'(همین حالا|کلیک کن|لینک در بیو|ثبت‌نام)', raw):
            intent["cta"] = re.search(r'(همین حالا .+?|کلیک کن .+?|لینک در بیو|ثبت‌نام .+?)', raw).group(1)

        # ۹. ایموجی
        if re.search(r'\b(با ایموجی|ایموجی دار|شکلک)\b', raw):
            intent["emojis"] = True
        elif re.search(r'\b(بدون ایموجی|بی شکلک)\b', raw):
            intent["emojis"] = False

        # ۱۰. نوع متن
        type_keywords = {
            "ایمیل": ["ایمیل", "نامه", "مکاتبه"],
            "پست_اینستاگرام": ["پست", "اینستاگرام", "اینستا", "کپشن", "استوری"],
            "یادداشت_وبلاگ": ["وبلاگ", "بلاگ", "یادداشت", "مقاله", "نوشته", "متن بلند"],
            "توییت": ["توییت", "توییتر", "توئیت"],
            "تبلیغاتی": ["تبلیغ", "آگهی", "پروموت"],
            "داستان_کوتاه": ["داستان", "قصه", "روایت"],
        }
        for tp, kws in type_keywords.items():
            if any(kw in raw for kw in kws):
                intent["text_type"] = tp
                break

        # ۱۱. لحن
        tone_keywords = {
            "رسمی": ["رسمی", "اداری", "محترمانه", "جدی"],
            "دوستانه": ["دوستانه", "خودی", "صمیمی"],
            "طنز": ["طنز", "شوخی", "بامزه", "خنده‌دار"],
            "انگیزشی": ["انگیزشی", "الهام‌بخش", "موتیویشن"],
        }
        for tone, kws in tone_keywords.items():
            if any(kw in raw for kw in kws):
                intent["tone"] = tone
                break

        # ۱۲. طول
        if re.search(r'\b(کوتاه|خلاصه|چند خط)\b', raw):
            intent["length"] = "کوتاه"
        elif re.search(r'\b(بلند|مفصل|جامع|کامل|طولانی)\b', raw):
            intent["length"] = "بلند"

        # ۱۳. موضوع
        topic = None
        for pat in [r'در مورد\s+[\"«]?(.+?)[\"»]?(?:\s|$)',
                    r'دربارهٔ?\s+[\"«]?(.+?)[\"»]?(?:\s|$)',
                    r'موضوع\s+[\"«]?(.+?)[\"»]?(?:\s|$)',
                    r'راجع به\s+[\"«]?(.+?)[\"»]?(?:\s|$)']:
            m = re.search(pat, raw)
            if m:
                topic = m.group(1).strip().rstrip('؟?')
                break
        if not topic:
            clean = raw
            for phrase in ["برام", "بنویس", "بساز", "تولید کن", "یه", "یک", "لطفاً", "خواهشاً", "متن", "بده"]:
                clean = clean.replace(phrase, "")
            clean = re.sub(r'\b(رسمی|دوستانه|طنز|کوتاه|بلند)\b', '', clean)
            clean = clean.strip()
            if len(clean) > 1:
                topic = clean[:50]
        intent["topic"] = topic if topic else "موضوع عمومی"

        # ۱۴. گیرنده
        if intent["text_type"] == "ایمیل":
            recip_match = re.search(r'(?:به|برای)\s+(.+?)\s+(?:ایمیل|نامه|بنویسی)', raw)
            if recip_match:
                intent["recipient"] = recip_match.group(1).strip()
            else:
                intent["recipient"] = "گیرندهٔ محترم" if intent["tone"]=="رسمی" else "دوست من"
        else:
            recip_match = re.search(r'(?:به|برای)\s+(.+?)\s+(?:بگو|بنویس)', raw)
            if recip_match:
                intent["recipient"] = recip_match.group(1).strip()

        # ۱۵. دستورات خاص
        if "سوال" in raw: intent["extra_instructions"].append("ask_question")
        if "ضرب‌المثل" in raw: intent["extra_instructions"].append("include_proverb")
        if "آمار" in raw or "واقعیت" in raw: intent["extra_instructions"].append("include_fact")

        return intent

    # =============== تولید پاراگراف هوشمند ===============
    def _build_sentence(self, topic: str, category="general", tone="دوستانه", expansion=None) -> str:
        patterns = self.sentence_patterns.get(category, self.sentence_patterns["general"])
        base = random.choice(patterns)
        exp = expansion if expansion else self._expand_topic(topic)
        subtopic = random.choice(exp.get("subtopics", [topic]))
        benefit = random.choice(exp.get("benefits", ["بهبود وضعیت"]))
        example = random.choice(exp.get("examples", ["موارد متعدد"]))
        method = random.choice(["تمرین منظم", "مطالعهٔ مستمر", "مشورت با متخصص", "پشتکار"])
        character = random.choice(["شخصیت داستان", "کارآفرین نمونه", "دانشجوی کوشا"])
        sentence = base.format(topic=topic, subtopic=subtopic, benefit=benefit, example=example,
                               method=method, character=character)
        sentence = self._synonym_replace(sentence)
        return sentence

    def _select_connector(self, relation="addition") -> str:
        return random.choice(self.connectors.get(relation, ["و"]))

    def _generate_paragraph(self, topic: str, tone: str, purpose="explain",
                            expansion: Dict = None, num_sentences=None) -> str:
        if expansion is None:
            expansion = self._expand_topic(topic)
        if num_sentences is None:
            num_sentences = random.randint(2, 4)
        purpose_to_categories = {
            "explain": ["general", "cause_effect"],
            "advise": ["advice", "question"],
            "compare": ["comparison", "general"],
            "example": ["example", "story"],
            "conclude": ["conclusion"],
        }
        categories = purpose_to_categories.get(purpose, ["general"])
        sentences = [self._build_sentence(topic, random.choice(categories), tone, expansion) for _ in range(num_sentences)]
        paragraph = sentences[0]
        for s in sentences[1:]:
            if "اما" in s or "هرچند" in s:
                rel = "contrast"
            elif "بنابراین" in s or "در نتیجه" in s:
                rel = "cause"
            elif "برای مثال" in s or "نمونه" in s:
                rel = "example"
            else:
                rel = random.choice(["addition", "emphasis"])
            paragraph += ". " + self._select_connector(rel) + " " + s
        return paragraph

    def _plan_document(self, params: Dict) -> List[Dict]:
        t = params["text_type"]
        length = params["length"]
        custom_p_count = params.get("paragraph_count")

        if custom_p_count:
            if t == "ایمیل":
                plan = [{"purpose": "greeting", "num_sentences": 1}]
                purposes = ["explain", "advise", "example", "conclude"]
                for i in range(custom_p_count):
                    plan.append({"purpose": purposes[i % len(purposes)], "num_sentences": 3})
                return plan
            elif t in ("پست_اینستاگرام", "یادداشت_وبلاگ", "داستان_کوتاه"):
                plan = []
                for i in range(custom_p_count):
                    if i == 0:
                        plan.append({"purpose": "intro", "num_sentences": 2})
                    elif i == custom_p_count-1:
                        plan.append({"purpose": "conclude", "num_sentences": 2})
                    else:
                        plan.append({"purpose": "explain", "num_sentences": 4})
                return plan
            else:
                return [{"purpose": "explain", "num_sentences": 4} for _ in range(custom_p_count)]

        if length == "کوتاه":
            if t == "ایمیل": return [{"purpose": "body", "num_sentences": 2}]
            if t == "پست_اینستاگرام": return [{"purpose": "explain", "num_sentences": 2}]
            return [{"purpose": "explain", "num_sentences": 2}]
        elif length == "متوسط":
            if t == "ایمیل": return [
                {"purpose": "greeting", "num_sentences": 1},
                {"purpose": "explain", "num_sentences": 3},
                {"purpose": "advise", "num_sentences": 2},
                {"purpose": "conclude", "num_sentences": 1},
            ]
            if t == "پست_اینستاگرام": return [
                {"purpose": "explain", "num_sentences": 3},
                {"purpose": "advise", "num_sentences": 2},
            ]
            if t == "یادداشت_وبلاگ": return [
                {"purpose": "intro", "num_sentences": 2},
                {"purpose": "explain", "num_sentences": 4},
                {"purpose": "example", "num_sentences": 3},
                {"purpose": "conclude", "num_sentences": 2},
            ]
            return [{"purpose": "explain", "num_sentences": 4}]
        else:
            if t == "یادداشت_وبلاگ":
                return [
                    {"purpose": "intro", "num_sentences": 3},
                    {"purpose": "explain", "num_sentences": 5},
                    {"purpose": "example", "num_sentences": 4},
                    {"purpose": "compare", "num_sentences": 4},
                    {"purpose": "advise", "num_sentences": 4},
                    {"purpose": "conclude", "num_sentences": 3},
                ]
            return [
                {"purpose": "intro", "num_sentences": 2},
                {"purpose": "explain", "num_sentences": 6},
                {"purpose": "example", "num_sentences": 3},
                {"purpose": "conclude", "num_sentences": 2},
            ]

    # =============== مونتاژ نهایی متن ===============
    def _generate_full_text(self, params: Dict[str, Any]) -> str:
        t = params["text_type"]
        topic = params["topic"]
        tone = params["tone"]
        recipient = params.get("recipient", "")
        lex = self.tone_lexicon.get(tone, self.tone_lexicon["دوستانه"])
        signature = random.choice(lex["signature"]) if "signature" in lex else "نویسنده"
        expansion = self._expand_topic(topic)
        output_parts = []

        if params.get("custom_opening"):
            output_parts.append(params["custom_opening"])
        if t == "ایمیل" and params.get("subject"):
            output_parts.append(f"موضوع: {params['subject']}")

        if t == "ایمیل":
            if not params.get("custom_opening"):
                output_parts.append(random.choice(self.text_structures["ایمیل"]["opening"]).replace("{recipient}", recipient or "دوست من"))
            plan = self._plan_document(params)
            body = []
            for section in plan:
                if section["purpose"] == "greeting":
                    if not any("سلام" in p for p in output_parts):
                        body.append(random.choice(self.text_structures["ایمیل"]["opening"]).replace("{recipient}", recipient))
                else:
                    body.append(self._generate_paragraph(topic, tone, section["purpose"], expansion, section["num_sentences"]))
            for phrase in params.get("custom_phrases", []):
                idx = random.randint(0, len(body))
                body.insert(idx, phrase)
            output_parts.extend(body)
            if params.get("custom_closing"):
                output_parts.append(params["custom_closing"])
            else:
                output_parts.append(random.choice(self.text_structures["ایمیل"]["closing"]).replace("{signature}", signature))

        elif t == "پست_اینستاگرام":
            if not params.get("custom_opening"):
                output_parts.append(random.choice(self.text_structures["پست_اینستاگرام"]["intro"]).replace("{topic}", topic))
            plan = self._plan_document(params)
            for section in plan:
                output_parts.append(self._generate_paragraph(topic, tone, section["purpose"], expansion, section["num_sentences"]))
            if params.get("custom_closing"):
                output_parts.append(params["custom_closing"])
            else:
                output_parts.append(random.choice(self.text_structures["پست_اینستاگرام"]["outro"]))
            output_parts.append(" ".join(random.sample(self.hashtags_pool, random.randint(2,4))))

        elif t == "یادداشت_وبلاگ":
            title = params.get("subject") or self.text_structures["یادداشت_وبلاگ"]["title"].replace("{topic}", topic)
            output_parts.append(title)
            if params.get("custom_opening"):
                output_parts.append(params["custom_opening"])
            else:
                output_parts.append(random.choice(self.text_structures["یادداشت_وبلاگ"]["intro"]).replace("{topic}", topic))
            plan = self._plan_document(params)
            for i, section in enumerate(plan):
                if section["purpose"] == "intro": continue
                content = self._generate_paragraph(topic, tone, section["purpose"], expansion, section["num_sentences"])
                if params["custom_phrases"] and i % 2 == 0:
                    content = random.choice(params["custom_phrases"]) + " " + content
                output_parts.append(content)
            if params.get("custom_closing"):
                output_parts.append(params["custom_closing"])
            else:
                output_parts.append(self._generate_paragraph(topic, tone, "conclude", expansion, 2))

        elif t == "توییت":
            if params.get("custom_opening"):
                tweet = params["custom_opening"]
            else:
                pattern = random.choice(self.text_structures["توییت"]["pattern"])
                tweet = pattern.format(topic=topic, reason_short=random.choice(["واقعاً مؤثره", "زندگیت رو تغییر میده"]),
                                      simple_advice=random.choice(["فقط شروع کن", "روزی ۵ دقیقه وقت بذار"]),
                                      reaction=random.choice(["ذهنم ترکید", "وااای چقدر جالب"]))
            if params.get("custom_closing"):
                tweet += " " + params["custom_closing"]
            output_parts.append(tweet)

        elif t == "تبلیغاتی":
            pattern = random.choice(self.text_structures["تبلیغاتی"]["pattern"])
            ad_text = pattern.format(product=topic, benefit=random.choice(expansion.get("benefits", ["صرفه‌جویی در زمان"])),
                                    problem=random.choice(["از شلوغی خسته شدی", "وقت کم میاری"]),
                                    cta=params.get("cta", "همین الان شروع کن."))
            if params.get("custom_opening"): ad_text = params["custom_opening"] + " " + ad_text
            if params.get("custom_closing"): ad_text += " " + params["custom_closing"]
            output_parts.append(ad_text)

        elif t == "داستان_کوتاه":
            if params.get("custom_opening"):
                output_parts.append(params["custom_opening"])
            else:
                output_parts.append(random.choice(self.text_structures["داستان_کوتاه"]["opening"]).replace("{topic}", topic))
            plot = self.text_structures["داستان_کوتاه"]["plot"].replace("{character}", random.choice(["قهرمان ما","دختری جوان"]))\
                        .replace("{challenge}", topic + " را درک نمی‌کرد")\
                        .replace("{event}", "او تصمیم گرفت هر روز یک قدم کوچک بردارد.")
            output_parts.append(plot)
            if params.get("custom_closing"):
                output_parts.append(params["custom_closing"])
            else:
                output_parts.append(self.text_structures["داستان_کوتاه"]["ending"].replace("{lesson}", random.choice(self.wisdom_quotes)))
        else:
            output_parts.append(self._generate_paragraph(topic, tone, "explain", expansion, 4))

        full_text = "\n\n".join(output_parts)

        # تنظیم تعداد کلمات
        if params.get("word_count"):
            target = params["word_count"]
            while len(full_text.split()) < target:
                full_text += "\n\n" + self._generate_paragraph(topic, tone, "explain", expansion, 3)
            if len(full_text.split()) > target * 1.3:
                paragraphs = full_text.split("\n\n")
                full_text = "\n\n".join(paragraphs[:max(1, len(paragraphs)//2)])

        # ایموجی
        if params.get("emojis") == True:
            emoji_pool = ["😊", "🚀", "💡", "❤️", "🔥", "✨", "📌", "👇", "👌"]
            sentences = re.split(r'(?<=[.؟!])\s+', full_text)
            new_sentences = []
            for s in sentences:
                if random.random() < 0.5: s += " " + random.choice(emoji_pool)
                new_sentences.append(s)
            full_text = " ".join(new_sentences)
        elif params.get("emojis") == False:
            full_text = re.sub(r'[^\w\s،\.\؟\!\(\)]', '', full_text)

        for phrase in params.get("custom_phrases", []):
            if phrase not in full_text:
                full_text = phrase + "\n" + full_text

        return full_text.strip()

    # ======================= PDF =======================
    def export_pdf(self, text: str, output_path: str = None) -> str:
        if not HAS_FPDF:
            return "⚠️ کتابخانه fpdf نصب نیست."
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), f"output_{random.randint(1000,9999)}.pdf")
        font_path = os.path.join(os.path.dirname(__file__), 'Vazir.ttf')
        if not os.path.exists(font_path):
            alt_font = r"/usr/share/fonts/truetype/vazir/Vazir.ttf"
            if not os.path.exists(alt_font):
                return "⚠️ فونت فارسی یافت نشد."
            font_path = alt_font
        pdf = FPDF()
        pdf.add_page()
        try:
            pdf.add_font('Persian', '', font_path, uni=True)
        except Exception:
            return "⚠️ خطا در بارگذاری فونت."
        pdf.set_font('Persian', '', 12)
        for line in text.split('\n'):
            pdf.multi_cell(0, 10, line)
        pdf.output(output_path)
        return output_path

    # ======================= مدیریت نشست =======================
    def _parse_followup(self, msg: str) -> Optional[Dict]:
        m = msg.strip()
        if re.search(r'\b(PDF|خروجی|پی‌دی‌اف)\b', m):
            return {"action": "pdf"}
        for persian_type, kw_list in [("ایمیل",["ایمیل","نامه"]),
                                      ("پست_اینستاگرام",["اینستاگرام","پست","کپشن"]),
                                      ("یادداشت_وبلاگ",["وبلاگ","مقاله","یادداشت"]),
                                      ("توییت",["توییت","توییتر"]),
                                      ("تبلیغاتی",["تبلیغ","آگهی"]),
                                      ("داستان_کوتاه",["داستان","قصه"])]:
            if any(kw in m for kw in kw_list):
                if "تبدیل" in m or "کن" in m or re.search(r'\bبکن\b', m):
                    return {"action": "change_type", "text_type": persian_type}
                if any(kw == word for word in m.split() for kw in kw_list):
                    return {"action": "change_type", "text_type": persian_type}
        for tone, kw_list in [("رسمی",["رسمی","اداری"]),("دوستانه",["دوستانه","صمیمی"]),
                              ("طنز",["طنز","شوخی"]),("انگیزشی",["انگیزشی"])]:
            if any(kw in m for kw in kw_list):
                return {"action": "change_tone", "tone": tone}
        if re.search(r'\b(متن جدید|دوباره|از نو|بساز دوباره)\b', m):
            return {"action": "new"}
        if re.search(r'\b(خروج|تمام|بسه)\b', m):
            return {"action": "exit"}
        return None

    def process(self, message: str, session_id: str = "default") -> str:
        if session_id not in self.sessions:
            self.sessions[session_id] = {"state": "idle"}
        sess = self.sessions[session_id]

        if sess.get("state") == "text_generated":
            cmd = self._parse_followup(message)
            if cmd:
                act = cmd["action"]
                if act == "pdf":
                    path = self.export_pdf(sess["last_text"])
                    return f"✅ فایل PDF ذخیره شد:\n{path}\n\nهنوز می‌توانید درخواست دیگری بدهید."
                elif act == "change_type":
                    sess["text_type"] = cmd["text_type"]
                    new_text = self._generate_full_text(sess)
                    sess["last_text"] = new_text
                    return f"🔁 متن با نوع جدید ({cmd['text_type']}):\n\n{new_text}\n\n――――――――――――――\nگزینه‌ها: PDF | تبدیل | لحن | جدید | خروج"
                elif act == "change_tone":
                    sess["tone"] = cmd["tone"]
                    new_text = self._generate_full_text(sess)
                    sess["last_text"] = new_text
                    return f"🔁 متن با لحن {cmd['tone']}:\n\n{new_text}\n\n――――――――――――――\nگزینه‌ها: PDF | تبدیل | لحن | جدید | خروج"
                elif act == "new":
                    self.sessions[session_id] = {"state": "idle"}
                    return "✅ شروع دوباره. لطفاً درخواست جدیدتان را بگویید."
                elif act == "exit":
                    self.sessions[session_id] = {"state": "idle"}
                    return "👋 تمام شد. هر زمان خواستید برگردید."
            else:
                self.sessions[session_id] = {"state": "idle"}

        params = self._understand_request(message)
        for k, v in params.items():
            sess[k] = v
        sess["state"] = "text_generated"
        generated_text = self._generate_full_text(sess)
        if not generated_text and self.is_ngram_ready:
            generated_text = self._ngram_gen_sentence()
        sess["last_text"] = generated_text
        post_guide = (
            "\n\n――――――――――――――――――――\n"
            "برای ادامه می‌توانید بگویید:\n"
            "🔸 خروجی PDF\n"
            "🔸 تبدیل به ایمیل / پست / وبلاگ / توییت / تبلیغ / داستان\n"
            "🔸 تغییر لحن (رسمی، دوستانه، طنز، انگیزشی)\n"
            "🔸 متن جدید\n"
            "🔸 خروج"
        )
        return generated_text + post_guide


# -------------------------- اتصال به ربات --------------------------
_generator = SmartPersianGenerator()

def generate_response(user_message: str, conversation_id=None) -> str:
    """
    تابع مورد نیاز ربات.
    از conversation_id به عنوان session_id استفاده می‌کند.
    """
    session = str(conversation_id) if conversation_id is not None else "default"
    return _generator.process(user_message, session)