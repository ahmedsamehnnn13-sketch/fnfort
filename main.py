Import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, JobQueue
from flask import Flask

# --- إعدادات Flask لضمان استمرارية البوت ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live with AI Referee!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"
REFEREES_GROUP_ID = -1001234567890  # ضع هنا معرف مجموعة الحكام الحقيقي
SUPER_ADMINS = ["mwsa_20", "levil_8"]  # حسابات السوبر أدمن

# --- قاموس القوانين التفصيلية (موسع بكل القوانين الجديدة) ---
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم والنجم والحاسم:
1️⃣ القواعد الأساسية:
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم (الأهداف، التأثير، السلوك).
- يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
- المنشن للحكم إلزامي عند إرسال القائمة، بدونه تعتبر لاغية (مدة الاعتراض 10 ساعات).
2️⃣ إذا كان الحاسم For Free لا يحتسب، ويعتبر الشخص قبله هو الحاسم.
3️⃣ الشخص الفائز بالمباراة وهو غير حاسم: الكلان يُحظر من النشر لمدة أسبوع.
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط (الخروج فوراً مع دليل).
⬆️ في المنتصف: تغيير التشكيلة أو المدرب لا يعتبر سكربت.
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ توقيت المواجهات والتمديد:
⏰ الوقت الرسمي: من 9 صباحاً حتى 1 صباحاً.
🚫 لا يجبر الخصم على اللعب في وقت غير رسمي (2-8 صباحاً).
🔥 التمديد:
- يوم واحد (للأدوار العادية)، يومين (نصف/نهائي).
- يمدد تلقائياً إذا: (حاسمة، اتفاق طرفين، شروط التمديد المنطبقة).
- شروط التمديد: تواجد الطرف الراغب بالتمديد، خلو الكلان من الطرد/الإنذارات، اتفاق على القوائم.
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ قوانين التواجد والغياب:
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 غياب الطرفين = يتم تبديل الطرف الأقل محاولة للاتفاق.
🤔 وضع تفاعل (Reaction) على الموعد يعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد يعتبر تهرباً (يستوجب التبديل).
🤔 التاك: إذا لم يرد الخصم خلال 10 دقائق يحتسب تاك رسمي.
🤔 مسموح تاك واحد لكل لاعب لخصمه في نصف ساعة.
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ قوانين التصوير (محدث):
1- وقت التصوير في البداية فقط.
2- الآيفون: فيديو (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
3- يمنع التصوير نهاية المباراة لتجنب الغش.
4- إرسال التصوير متاح في أي وقت (بداية أو نهاية).
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ قوانين الانسحاب والخروج:
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🤔 خروج متعمد (اعتراف) = هدف مباشر.
🤔 سوء نت: فيديو 30 ثانية يوضح اللاق والإشعارات.
🤔 الخروج بدون فسخ عقد = حظر بمدة العقد المتبقية (أقصى أسبوعين).
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ قوانين السب والإساءة:
🚫 سب الأهل/الكفر = طرد وحظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص (أثناء المواجهة) = تبديل + حظر (يتطلب دليل فيديو لليوزر).
🚫 استفزاز الخصم أو الحكم = عقوبة تقديرية (تبديل/حظر).
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ قوانين الـ VAR:
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
✅ الاعتماد الأساسي على حكم المباراة.
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ قوانين الانتقالات:
📺 مسموحة فقط يومي (الخميس والجمعة).
🤔 أي انتقال في يوم آخر يعتبر غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر (بدون عقد) يمكنه الانتقال في أي وقت.
🔗 للمزيد: https://t.me/arab_union3""",

    "عقود": """⚖️ قوانين العقود:
🤔 أقصى حد للمسؤولين في العقود: 8 قادة.
🤔 القائد الـ 9 يعتبر وهمي ويطرد.
🤔 فسخ العقد حصراً من القادة المسجلين.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).
🔗 للمزيد: https://t.me/arab_union3""",

    "نشر": """⚖️ قوانين النشر:
📢 أي فوز قوائم يمنع نشر النجم والحاسم.
📢 النشر الوهمي: حظر الكلان من قنوات النشر لمدة أسبوع.
📢 إذا تكرر: خصم نقاط من التصنيف.
📢 يمكن نشر انتصارات قديمة في قناة النشر بعد انتهاء الحظر، ولكن ليس في قناة البطولات.
🔗 للمزيد: https://t.me/arab_union3""",

    "حظر": """⚖️ قوانين الحظر والتنازل:
⛔️ مدة الحظر الأساسية: أسبوعين.
🤝 التنازل من الطرف المشتكي يخفض المدة للنصف.
🚫 لا يشمل التنازل: الكفر، الوهمي، سب اللجنة، استخدام VPN، إضافة لاعب محظور.
🔗 للمزيد: https://t.me/arab_union3""",

    "اتفاق": """⚖️ قوانين الاتفاق والاعتراض:
✅ الاتفاق يسقط أغلب القوانين باستثناء: الحظر، دليل الخروج، التبديل الإضافي، آخر ساعتين، العقود، قانون 24 ساعة، عدم الاتفاق على موعد، تضييع الوقت والسكربت، التصوير، الحسابات الاحتيالية.
⚠️ الاعتراض على قرار الحكم يسقط بعد 12 ساعة من انتهاء المواجهة.
🔗 للمزيد: https://t.me/arab_union3""",

    "تاكات": """⚖️ نظام التاكات:
🕐 التاك يحسب إذا لم يرد الخصم خلال 10 دقائق.
🔄 تاك واحد لكل لاعب في نصف ساعة.
📊 بعد 3 أيام، يرسل البوت تقرير التاكات ويسأل القادة عن الفائز (نقطة فري).
🔗 للمزيد: https://t.me/arab_union3""",

    "تبديلات": """⚖️ نظام التبديلات:
🔄 كل كلان له 3 تبديلات فقط.
📝 الأمر: "تبديل CLAN NAME @old @new" أو بالرد على اللاعب القديم وذكر الجديد.
⚠️ التبديل الرابع لا يحتسب ويحذر الكلان.
🔗 للمزيد: https://t.me/arab_union3""",

    "حاسم": """⚖️ نظام الحاسم:
🔥 عندما تصبح النتيجة 3-3، يدخل الكلانان في وضع الحاسم.
📢 يرسل القائد: "حاسم CLAN NAME @player".
⚔️ يتم إيقاف التاكات وتحديد مباراة حاسمة بين اللاعبين.
🔗 للمزيد: https://t.me/arab_union3"""
}

# كلمات الطرد (السب والكفر)
BAN_WORDS = ["كسمك", "كسمه", "كسختك", "كسم", "كس", "شرموطة", "منيوك", "ابن المتناكة", "ابن الشرموطة", "كفر", "الحمد لله", "بسم الله", "اللهم", "كسم الدين"]  # إضافة كلمات الكفر والسب

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {}  # لا يتم حفظ هذا في الملف لتقليل الحجم

# --- دوال الحفظ والاسترجاع (Persistence) ---
def save_data():
    """حفظ البيانات في ملف JSON لضمان عدم ضياعها عند الريستارت"""
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=str)
        print("✅ Data saved successfully.")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def load_data():
    """استرجاع البيانات عند تشغيل البوت"""
    global wars, clans_mgmt, user_warnings, admin_warnings
    if not os.path.exists(DATA_FILE):
        return
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # استرجاع البيانات مع تحويل المفاتيح إلى أرقام وتاريخ
            if "wars" in data:
                wars = {}
                for k, v in data["wars"].items():
                    cid = int(k)
                    # تحويل الأوقات المخزنة كـ string إلى datetime
                    if "start_time" in v:
                        v["start_time"] = datetime.fromisoformat(v["start_time"])
                    if "taсks" in v:
                        for clan, players in v["taсks"].items():
                            for player, taсks in players.items():
                                for t in taсks:
                                    t["time"] = datetime.fromisoformat(t["time"])
                    if "last_tack_time" in v:
                        for key, t in v["last_tack_time"].items():
                            v["last_tack_time"][key] = datetime.fromisoformat(t)
                    if "last_activity" in v:
                        for player, t in v["last_activity"].items():
                            v["last_activity"][player] = datetime.fromisoformat(t)
                    wars[cid] = v
            if "clans_mgmt" in data:
                clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
            if "user_warnings" in data:
                user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
            if "admin_warnings" in data:
                admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
                
        print("✅ Data loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")

# دالة تحويل الأرقام لإيموجي
def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    result = ""
    for char in n_str:
        result += dic.get(char, char)
    return result

# دالة تنظيف النصوص
def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = re.sub(r'^(ال)', '', text)
    return text

# دالة للتحقق من الوقت الرسمي
def is_official_time(dt=None):
    if dt is None:
        dt = datetime.now()
    hour = dt.hour
    # الوقت الرسمي من 9 صباحاً إلى 1 صباحاً (أي 1:00 يعتبر داخل، 1:59 يعتبر خارج؟ نعتبر حتى 1:00)
    return hour >= 9 or hour < 1  # 9-23 و 0-1

# دالة لبدء مهمة مراقبة الغياب
async def check_absence_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة دورية لفحص غياب اللاعبين (كل ساعة)"""
    now = datetime.now()
    for cid, war in list(wars.items()):
        if not war.get("active"):
            continue
        for clan_key in ["c1", "c2"]:
            clan = war[clan_key]
            for player in clan.get("p", []):
                last_active = war.get("last_activity", {}).get(player)
                if last_active and (now - last_active) > timedelta(hours=20):
                    # غياب 20 ساعة بدون نشاط
                    await context.bot.send_message(
                        cid,
                        f"⚠️ تحذير: اللاعب {player} غائب لمدة 20 ساعة. إذا لم يتم الاتفاق على موعد قريب، سيتم تبديله."
                    )
                    # يمكن تنفيذ التبديل التلقائي هنا بعد تكرار التحذير

# دالة لإرسال تقرير التاكات بعد 3 أيام
async def send_tac_report(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تقرير التاكات إلى مجموعة المواجهة"""
    cid = context.job.data["cid"]
    if cid not in wars or not wars[cid].get("active"):
        return
    war = wars[cid]
    if war.get("tac_report_sent"):
        return
    war["tac_report_sent"] = True
    save_data()

    # تجميع التاكات لكل كلان
    report = "📊 **تقرير التاكات بعد 3 أيام**\n\n"
    keyboard = []
    for clan_key in ["c1", "c2"]:
        clan = war[clan_key]
        report += f"🔹 {clan['n']}:\n"
        for player in clan.get("p", []):
            taсks = war.get("taсks", {}).get(clan_key, {}).get(player, [])
            report += f"  {player}: {len(taсks)} تاك\n"
            if taсks:
                # إضافة زر للاعب للتصويت بالفوز
                keyboard.append([InlineKeyboardButton(f"✅ فاز {player}", callback_data=f"tacwin_{cid}_{clan_key}_{player}")])
    report += "\nاضغط على زر اللاعب الذي تعتقد أنه فاز بالتاك (لكل لاعب مرة واحدة).\nسيتم إضافة نقطة فري لكلان الفائز."
    await context.bot.send_message(cid, report, reply_markup=InlineKeyboardMarkup(keyboard))

# --- ميزة مراقبة التعديلات وفضحها ---
async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text:
        return
    
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(
                f"🚨 تنبيه: تم تعديل رسالة في جروب المواجهة!\n\n"
                f"📜 الرسالة قبل التعديل:\n{old_text}\n\n"
                f"🔄 الرسالة بعد التعديل:\n{new_text}\n\n"
                f"⚠️ التلاعب بالرسائل والقوائم ممنوع."
            )

# --- معالج الاستفسارات الذكية عن القوانين ---
async def handle_ai_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """محاولة فهم سؤال المستخدم والرد بأحد القوانين المناسبة"""
    text = update.message.text
    cleaned = clean_text(text)
    
    # البحث عن كلمات مفتاحية في النص
    for keyword, law_text in DETAILED_LAWS.items():
        if keyword in cleaned:
            await update.message.reply_text(law_text, disable_web_page_preview=True)
            return True
    
    # إذا لم يجد تطابقاً تاماً، نبحث عن كلمات قريبة
    keywords = {
        "قائم": "قوائم",
        "سكربت": "سكربت",
        "وقت": "وقت",
        "تمديد": "وقت",
        "تواجد": "تواجد",
        "حضور": "تواجد",
        "تصوير": "تصوير",
        "انسحاب": "انسحاب",
        "خروج": "انسحاب",
        "سب": "سب",
        "شتم": "سب",
        "فار": "فار",
        "انتقالات": "انتقالات",
        "عقد": "عقود",
        "نشر": "نشر",
        "حظر": "حظر",
        "تنازل": "حظر",
        "اتفاق": "اتفاق",
        "اعتراض": "اتفاق",
        "تاك": "تاكات",
        "تبديل": "تبديلات",
        "حاسم": "حاسم"
    }
    for word, section in keywords.items():
        if word in cleaned:
            await update.message.reply_text(DETAILED_LAWS[section], disable_web_page_preview=True)
            return True
    
    return False

# --- المعالج الرئيسي للمواجهة ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.message_id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # حفظ الرسالة الأصلية فوراً
    original_msg_store[mid] = msg

    # تحديد رتبة المستخدم
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in SUPER_ADMINS) or is_creator
    except:
        is_creator = False
        is_referee = (user.username in SUPER_ADMINS)

    # تحديث آخر نشاط للاعب إذا كان في حرب
    if cid in wars:
        war = wars[cid]
        for clan in ["c1", "c2"]:
            if u_tag in war[clan].get("p", []):
                if "last_activity" not in war:
                    war["last_activity"] = {}
                war["last_activity"][u_tag] = datetime.now()
                save_data()
                break

    # --- الرد على الاعتراضات والقوانين (بشرط المنشن) ---
    is_bot_mentioned = (f"@{bot_username}" in msg) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

    if is_bot_mentioned:
        handled = await handle_ai_query(update, context)
        if handled:
            return

    # --- ميزة إلغاء الإنذار (للسوبر أدمن فقط) ---
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions: target_t = mentions[0]
        
        if target_t:
            if cid in user_warnings and target_t in user_warnings[cid]:
                user_warnings[cid][target_t] = 0
            if cid in admin_warnings and target_t in admin_warnings[cid]:
                admin_warnings[cid][target_t] = 0
            save_data()
            await update.message.reply_text(f"✅ تم صفر (إلغاء) كافة إنذارات {target_t} بواسطة الإدارة.")
            return

    # --- نظام الطرد الآلي (للكفر والسب) ---
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in SUPER_ADMINS:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} فوراً لانتهاك قوانين الاتحاد (سب/كفر).")
                except Exception as e:
                    print(f"Ban error: {e}")
            return

    # --- ميزة الروليت ---
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 قرعة الروليت:\n\n🏆 الفائز هو: {winner}")
            return

    # --- نظام الإنذارات (م) وللاعبين ---
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        
        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(f"⚠️ إنذار مسؤول (م)\n👤 المسؤول: {t_tag}\n🔢 العدد: ({count}/3)")
            if count >= 3:
                await update.message.reply_text(f"🚫 تم سحب صلاحيات المسؤول {t_tag} بواسطة الإدارة.")
            return

        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(f"⚠️ إنذار لاعب\n👤 اللاعب: {t_tag}\n🔢 العدد: ({count}/3)")
            if count >= 3:
                try: await context.bot.ban_chat_member(cid, target_user.id)
                except: pass
            return

    # --- بدء المواجهة (الكلانات) ---
    if "CLAN" in msg_up and "VS" in msg_up and "+ 1" not in msg_up:
        parts = msg_up.split(" VS ")
        c1_name = parts[0].replace("CLAN ", "").strip()
        c2_name = parts[1].replace("CLAN ", "").strip()
        
        wars[cid] = {
            "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None},
            "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None},
            "active": True,
            "mid": None,
            "matches": [],
            "start_time": datetime.now(),
            "duration_hours": 48,  # يمكن تغييره حسب الدور
            "extended": False,
            "extension_reason": None,
            "taсks": {"c1": {}, "c2": {}},
            "last_tack_time": {},
            "replacements": {"c1": 0, "c2": 0},
            "replacement_log": {"c1": [], "c2": []},
            "decisive_mode": False,
            "decisive_players": {"c1": None, "c2": None},
            "tac_report_sent": False,
            "last_activity": {}
        }
        save_data()
        await update.message.reply_text(f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try:
            await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        
        # جدولة تقرير التاكات بعد 3 أيام
        context.job_queue.run_once(send_tac_report, timedelta(days=3), data={"cid": cid})
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- تسجيل التاكات ---
        if "تاك" in msg_cleaned and (update.message.reply_to_message or len(re.findall(r'@\w+', msg)) >= 2):
            # تحديد المرسل والهدف
            from_player = u_tag
            to_player = None
            if update.message.reply_to_message:
                to_user = update.message.reply_to_message.from_user
                to_player = f"@{to_user.username}" if to_user.username else f"ID:{to_user.id}"
            else:
                mentions = re.findall(r'@\w+', msg)
                if len(mentions) >= 2:
                    # إذا كان هناك منشنان، الأول هو المرسل (عادة ما يكون نفسه) والثاني هو الهدف
                    if mentions[0] == u_tag or u_tag not in mentions:
                        to_player = mentions[1] if len(mentions) > 1 else None
                    else:
                        to_player = mentions[0]
            
            if to_player and from_player != to_player:
                # التحقق من أن اللاعبين في الحرب ومن خصمين
                clan_from = None
                clan_to = None
                for clan_key in ["c1", "c2"]:
                    if from_player in w[clan_key].get("p", []):
                        clan_from = clan_key
                    if to_player in w[clan_key].get("p", []):
                        clan_to = clan_key
                if clan_from and clan_to and clan_from != clan_to:
                    # التحقق من مرور 30 دقيقة على آخر تاك بينهما
                    pair_key = f"{clan_from}_{from_player}_{clan_to}_{to_player}"
                    last = w.get("last_tack_time", {}).get(pair_key)
                    now = datetime.now()
                    if last and (now - last) < timedelta(minutes=30):
                        await update.message.reply_text("⏳ يجب الانتظار 30 دقيقة بين كل تاك ونفس الخصم.")
                        return
                    
                    # تسجيل التاك
                    if to_player not in w["taсks"][clan_to]:
                        w["taсks"][clan_to][to_player] = []
                    w["taсks"][clan_to][to_player].append({"from": from_player, "time": now})
                    if "last_tack_time" not in w:
                        w["last_tack_time"] = {}
                    w["last_tack_time"][pair_key] = now
                    save_data()
                    await update.message.reply_text(f"✅ تم تسجيل تاك من {from_player} إلى {to_player}.")
                else:
                    await update.message.reply_text("❌ التاك يكون بين لاعبين من كلانين متخاصمين فقط.")
            return

        # --- [جديد] ميزة تعيين قائد بديل يدوياً ---
        sub_leader_match = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader_match and is_referee:
            new_leader = sub_leader_match.group(1)
            target_clan_name = sub_leader_match.group(2).strip().upper()
            
            target_k = None
            if w["c1"]["n"].upper() == target_clan_name: target_k = "c1"
            elif w["c2"]["n"].upper() == target_clan_name: target_k = "c2"
            
            if target_k:
                w[target_k]["leader"] = new_leader
                save_data()
                await update.message.reply_text(f"✅ تم تعيين {new_leader} قائداً رسمياً لكلان {w[target_k]['n']} بدلاً من القائد السابق.")
            else:
                await update.message.reply_text(f"❌ لم يتم العثور على كلان بهذا الاسم في الحرب الحالية.")
            return

        # --- تسجيل القائمة ---
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"].upper() in msg_up: target_k = "c1"
            elif w["c2"]["n"].upper() in msg_up: target_k = "c2"
            
            if target_k:
                if is_referee:
                    pass 
                else:
                    other_k = "c2" if target_k == "c1" else "c1"
                    if w[other_k]["leader"] == u_tag:
                        await update.message.reply_text("❌ أنت قائد الكلان الخصم، لا يمكنك إرسال قائمة منافسك!")
                        return

                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']} (بواسطة {u_tag}).")

                if w["c1"]["p"] and w["c2"]["p"]:
                    p1 = list(w["c1"]["p"])
                    p2 = list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    save_data()
                    
                    rows = []
                    for i, m in enumerate(w["matches"]):
                        rows.append(f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |")
                    
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    save_data()
                    
                    try:
                        await context.bot.pin_chat_message(chat_id=cid, message_id=sent.message_id)
                    except Exception as e:
                        print(f"Error pinning message: {e}")
            return

        # --- تحديد المساعد ---
        asst_match = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
        if asst_match:
            target_asst = asst_match.group(1)
            clan_name = asst_match.group(2).upper()
            target_key = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            
            if target_key and (w[target_key]["leader"] == u_tag or is_referee):
                if cid not in clans_mgmt: clans_mgmt[cid] = {}
                clans_mgmt[cid][clan_name] = {"asst": target_asst}
                save_data()
                await update.message.reply_text(f"✅ تم تعيين المساعد {target_asst} لكلان {clan_name}.")
            elif target_key:
                await update.message.reply_text("❌ فقط قائد الكلان أو الحكم يمكنه تحديد المساعد.")
            return

        # --- نظام التبديلات ---
        sub_match = re.search(r'تبديل\s+(\w+)\s+(@\w+)\s+(@\w+)', msg)
        if sub_match:
            clan_name = sub_match.group(1).upper()
            old_player = sub_match.group(2)
            new_player = sub_match.group(3)
            target_key = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            
            if target_key:
                asst_tag = clans_mgmt.get(cid, {}).get(w[target_key]["n"].upper(), {}).get("asst")
                if not (is_referee or u_tag == w[target_key]["leader"] or u_tag == asst_tag):
                    await update.message.reply_text("❌ عذراً، التبديل مسموح للحكام أو القادة/المساعدين فقط.")
                    return
                
                if w["replacements"][target_key] >= 3:
                    await update.message.reply_text("❌ لقد استنفدت الكلان عدد التبديلات المسموح بها (3).")
                    return
                
                # البحث عن المباراة التي فيها old_player
                found = False
                for match in w["matches"]:
                    if match["p1"] == old_player or match["p2"] == old_player:
                        # تبديل اللاعب
                        if match["p1"] == old_player:
                            match["p1"] = new_player
                        else:
                            match["p2"] = new_player
                        found = True
                        break
                if found:
                    w["replacements"][target_key] += 1
                    w["replacement_log"][target_key].append({"old": old_player, "new": new_player, "time": datetime.now()})
                    save_data()
                    await update.message.reply_text(f"✅ تم تبديل {old_player} بـ {new_player} في كلان {w[target_key]['n']}. التبديلات المتبقية: {3 - w['replacements'][target_key]}")
                    
                    # تحديث الجدول
                    if w["mid"]:
                        rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                        updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                        try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                        except: pass
                else:
                    await update.message.reply_text(f"❌ لم يتم العثور على اللاعب {old_player} في المباريات.")
            else:
                await update.message.reply_text("❌ اسم الكلان غير صحيح.")
            return

        # --- نظام الحاسم ---
        decisive_match = re.search(r'حاسم\s+(\w+)\s+(@\w+)', msg)
        if decisive_match:
            if w["c1"]["s"] == 3 and w["c2"]["s"] == 3 and not w["decisive_mode"]:
                clan_name = decisive_match.group(1).upper()
                player = decisive_match.group(2)
                target_key = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
                
                if target_key:
                    asst_tag = clans_mgmt.get(cid, {}).get(w[target_key]["n"].upper(), {}).get("asst")
                    if not (is_referee or u_tag == w[target_key]["leader"] or u_tag == asst_tag):
                        await update.message.reply_text("❌ فقط القائد أو المساعد يمكنه تحديد الحاسم.")
                        return
                    
                    if player not in w[target_key]["p"]:
                        await update.message.reply_text("❌ هذا اللاعب ليس في قائمة الكلان.")
                        return
                    
                    w["decisive_players"][target_key] = player
                    save_data()
                    await update.message.reply_text(f"✅ تم تحديد {player} كلاعب حاسم لكلان {w[target_key]['n']}.")
                    
                    if w["decisive_players"]["c1"] and w["decisive_players"]["c2"]:
                        w["decisive_mode"] = True
                        # إيقاف التاكات القديمة وبدء حاسم
                        await update.message.reply_text(f"🔥 وضع الحاسم مفعل! المباراة النهائية بين {w['decisive_players']['c1']} و {w['decisive_players']['c2']}.")
                        # يمكن تحديث الجدول لعرض المباراة الحاسمة فقط
            else:
                await update.message.reply_text("❌ لا يمكن الدخول في وضع الحاسم إلا عند التعادل 3-3.")
            return

        # --- نظام إضافة النقاط وتحديث المباريات ---
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if not win_k: return

            if len(players) >= 2 and len(scores) >= 2:
                asst_tag = clans_mgmt.get(cid, {}).get(w[win_k]["n"].upper(), {}).get("asst")
                if not (is_referee or u_tag == w[win_k]["leader"] or u_tag == asst_tag):
                    await update.message.reply_text("❌ عذراً، التسجيل مسموح للحكام أو القادة/المساعدين فقط.")
                    return

                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                
                # تحديث نتيجة المباراة في الجدول
                for m in w["matches"]:
                    mp1_u = m["p1"].upper()
                    mp2_u = m["p2"].upper()
                    if (u1 == mp1_u or u1 == mp2_u) and (u2 == mp1_u or u2 == mp2_u):
                        if u1 == mp1_u:
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                        # طرد اللاعبين بعد المباراة
                        try:
                            # طرد (ban + unban) لإزالة العضو وإعادة السماح بدخوله لاحقاً
                            for player in [u1, u2]:
                                # استخراج user_id من الـ tag (هذا يتطلب تخزين معرفات اللاعبين أو البحث)
                                # سنستخدم طريقة بديلة: نطرد باستخدام @username (إذا كان البوت لديه صلاحية)
                                # لا يمكن طرد باستخدام username، نحتاج user_id.
                                # لذا سنقوم بتخزين user_id عند إرسال القوائم، أو استخدام get_chat_member
                                pass
                        except Exception as e:
                            print(f"Kick error: {e}")
                        break
                
                save_data()
                await update.message.reply_text(f"✅ تم تسجيل نقطة مباراة لـ {w[win_k]['n']}.")

            else:
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري حصرية للإدارة.")
                    return
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                save_data()
                await update.message.reply_text(f"⚖️ قرار إداري: إضافة نقطة فري لكلان {w[win_k]['n']} بواسطة {u_tag}.")

            try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except: pass

            # تحديث الجدول المعروض
            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass
            
            # إنهاء الحرب وإرسال النتائج النهائية
            if w[win_k]["s"] >= 4:
                w["active"] = False
                save_data()
                history = w[win_k]["stats"]
                real_players = [h for h in history if not h["is_free"]]
                
                if real_players:
                    hasm = real_players[-1]["name"]
                    star_player_data = max(real_players, key=lambda x: (x["goals"] - x["rec"]))
                    star = star_player_data["name"]
                    star_goals = star_player_data["goals"]
                    star_rec = star_player_data["rec"]

                    result_msg = (
                        f"🎊 انتهت الحرب بفوز كلان: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {hasm} (آخر من سجل)\n"
                        f"⭐ النجم: {star} (سجل {star_goals} واستقبل {star_rec})"
                    )
                else:
                    result_msg = f"🎊 انتهت الحرب بفوز إداري لكلان: {w[win_k]['n']} 🎊"
                
                await update.message.reply_text(result_msg)

                # إرسال تفاصيل النتائج النهائية
                match_results_str = ""
                for i, m in enumerate(w["matches"]):
                    line = f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |"
                    match_results_str += line + "\n"
                    match_results_str += "─── ─── ─── ─── ───\n"
                
                await update.message.reply_text(f"📊 تفاصيل النتائج:\n\n{match_results_str}")

    # --- استقبال أوامر بوت النشر ---
    if "بدء مواجهة:" in msg:
        link_match = re.search(r'الرابط: (.+)', msg)
        type_match = re.search(r'النوع: (.+)', msg)
        clans_match = re.search(r'الكلانات: (.+)', msg)
        
        if link_match and clans_match:
            source_url = link_match.group(1)
            war_type = type_match.group(1) if type_match else ""
            clans_text = clans_match.group(1)
            
            parts = clans_text.upper().split(" VS ")
            c1_n = parts[0].replace("CLAN ", "").strip()
            c2_n = parts[1].replace("CLAN ", "").strip()

            wars[cid] = {
                "c1": {"n": c1_n, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_n, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [], "source_link": source_url,
                "start_time": datetime.now(),
                "duration_hours": 48,
                "extended": False,
                "taсks": {"c1": {}, "c2": {}},
                "last_tack_time": {},
                "replacements": {"c1": 0, "c2": 0},
                "replacement_log": {"c1": [], "c2": []},
                "decisive_mode": False,
                "decisive_players": {"c1": None, "c2": None},
                "tac_report_sent": False,
                "last_activity": {}
            }
            save_data()

            try:
                await context.bot.set_chat_title(cid, f"⚔️ {c1_n} 0 - 0 {c2_n} {war_type}")
                await context.bot.set_chat_description(cid, f"مواجهة رسمية بين {c1_n} و {c2_n}\nالمنظم: موجود\nرابط المنشور: {source_url}")
            except Exception as e:
                print(f"Error updating chat: {e}")

            await update.message.reply_text(f"🚀 تم استلام البيانات من بوت النشر.\nتم تحديث اسم الجروب والوصف وبدء الحرب!")
            context.job_queue.run_once(send_tac_report, timedelta(days=3), data={"cid": cid})
            return

    # --- نظام الاعتراض على قرارات البوت ---
    if "اعتراض" in msg_cleaned or "عندي اعتراض" in msg_cleaned:
        if cid not in wars or not wars[cid]["active"]:
            return
        # طلب كتابة الاعتراض
        await update.message.reply_text("✍️ اكتب اعتراضك بالتفصيل وسيتم تحويله إلى مجموعة الحكام للنظر فيه.")
        # في الواقع، نحتاج لتخزين حالة انتظار للاعتراض، ثم أخذ النص التالي وإرساله للحكام
        # سنقوم بذلك عبر Context.user_data
        context.user_data["awaiting_objection"] = {"cid": cid, "user": u_tag}
        return

# --- معالج النصوص للاعتراضات (بعد طلب الاعتراض) ---
async def handle_objection_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_objection"):
        data = context.user_data["awaiting_objection"]
        cid = data["cid"]
        user = data["user"]
        objection_text = update.message.text
        # إرسال إلى مجموعة الحكام
        await context.bot.send_message(
            REFEREES_GROUP_ID,
            f"⚠️ اعتراض جديد من {user} في مجموعة {cid}:\n\n{objection_text}\n\nللرد، استخدم /reply {cid} متبوعاً بالقرار."
        )
        await update.message.reply_text("✅ تم إرسال اعتراضك إلى الحكام. سيتم الرد قريباً.")
        del context.user_data["awaiting_objection"]
    else:
        # إذا لم يكن في حالة انتظار، نتجاهل
        pass

# --- معالج أزرار تقرير التاكات ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("tacwin_"):
        parts = data.split("_")
        cid = int(parts[1])
        clan_key = parts[2]
        player = parts[3]
        if cid in wars:
            war = wars[cid]
            # إضافة نقطة فري للكلان
            war[clan_key]["s"] += 1
            war[clan_key]["stats"].append({"name": f"TacWin_{player}", "goals": 0, "rec": 0, "is_free": True})
            save_data()
            await query.edit_message_text(f"✅ تم إضافة نقطة فري لكلان {war[clan_key]['n']} بفوز {player} في التاكات.")
            # تحديث عنوان المجموعة
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {war['c1']['n']} {war['c1']['s']} - {war['c2']['s']} {war['c2']['n']} ⚔️")
            except: pass

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    # تحميل البيانات المحفوظة عند التشغيل
    load_data()
    
    # إضافة المعالجات
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # معالج الاعتراضات (يجب أن يكون بعد المعالج الرئيسي لأنه يلتقط أي نص)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_objection_text), group=1)
    
    # جدولة وظيفة فحص الغياب كل ساعة
    job_queue = app.job_queue
    job_queue.run_repeating(check_absence_job, interval=3600, first=10)
    
    print("✅ البوت يعمل الآن (مع خاصية حفظ البيانات، الذكاء الاصطناعي، التاكات، التبديلات، الحاسم، الاعتراضات، وتحديث النتائج)...")
    app.run_polling()
الكود دا حلو؟ فيه كل دا
البوت الحكم واليه عمله

عندما يرسله بوت النشر بدا مواجهه يغير اسم الجروب للمواجهه الحاليه وتبدا المواجهه والقوانين كما في هذا الكود بالضبط
import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask 


# --- إعدادات Flask لضمان استمرارية البوت ---
web_app = Flask(name)

@web_app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"  # اسم ملف حفظ البيانات

# --- قاموس القوانين التفصيلية ---
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم والنجم والحاسم:
1️⃣ القواعد الأساسية:
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم (الأهداف، التأثير، السلوك).
- يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
- المنشن للحكم إلزامي عند إرسال القائمة، بدونه تعتبر لاغية (مدة الاعتراض 10 ساعات).

2️⃣ التوقيت:
- نصف النهائي/النهائي: 18 ساعة (+15د سماح).
- باقي الأدوار: 14 ساعة (+15د سماح).
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط (الخروج فوراً مع دليل).
⬆️ في المنتصف: تغيير التشكيلة أو المدرب لا يعتبر سكربت.
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ توقيت المواجهات والتمديد:
⏰ الوقت الرسمي: من 9 صباحاً حتى 1 صباحاً.
🚫 لا يجبر الخصم على اللعب في وقت غير رسمي (2-8 صباحاً).

🔥 التمديد:
- يوم واحد (للأدوار العادية)، يومين (نصف/نهائي).
- يمدد تلقائياً إذا: (حاسمة، اتفاق طرفين، شروط التمديد المنطبقة).
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ قوانين التواجد والغياب:
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 غياب الطرفين = يتم تبديل الطرف الأقل محاولة للاتفاق.
🤔 وضع تفاعل (Reaction) على الموعد يعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد يعتبر تهرباً (يستوجب التبديل).
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ قوانين التصوير (محدث):
1- وقت التصوير في البداية فقط.
2- الآيفون: فيديو (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
3- يمنع التصوير نهاية المباراة لتجنب الغش.
4- إرسال التصوير متاح في أي وقت (بداية أو نهاية).
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ قوانين الانسحاب والخروج:
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🤔 خروج متعمد (اعتراف) = هدف مباشر.
🤔 سوء نت: فيديو 30 ثانية يوضح اللاق والإشعارات.
🤔 الخروج بدون فسخ عقد = حظر بمدة العقد المتبقية.
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ قوانين السب والإساءة:
🚫 سب الأهل/الكفر = طرد وحظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص (أثناء المواجهة) = تبديل + حظر (يتطلب دليل فيديو لليوزر).
🚫 استفزاز الخصم أو الحكم = عقوبة تقديرية (تبديل/حظر).
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ قوانين الـ VAR:
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
✅ الاعتماد الأساسي على حكم المباراة.
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ قوانين الانتقالات:
📺 مسموحة فقط يومي (الخميس والجمعة).
🤔 أي انتقال في يوم آخر يعتبر غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر (بدون عقد) يمكنه الانتقال في أي وقت.
🔗 للمزيد: https://t.me/arab_union3""",
    
    "عقود": """⚖️ قوانين العقود:
🤔 أقصى حد للمسؤولين في العقود: 8 قادة.
🤔 القائد الـ 9 يعتبر وهمي ويطرد.
🤔 فسخ العقد حصراً من القادة المسجلين.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).
🔗 للمزيد: https://t.me/arab_union3"""
}

# كلمات الطرد (السب والكفر)
BAN_WORDS = ["كسمك", "كسمه", "كسختك",]

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {} # لا يتم حفظ هذا في الملف لتقليل الحجم

# --- دوال الحفظ والاسترجاع (Persistence) ---
def save_data():
    """حفظ البيانات في ملف JSON لضمان عدم ضياعها عند الريستارت"""
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅ Data saved successfully.")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def load_data():
    """استرجاع البيانات عند تشغيل البوت"""
    global wars, clans_mgmt, user_warnings, admin_warnings
    if not os.path.exists(DATA_FILE):
        return
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # استرجاع البيانات مع تحويل مفاتيح القواميس إلى أرقام (Integers) لأن JSON يحفظها كنصوص
            if "wars" in data:
                wars = {int(k): v for k, v in data["wars"].items()}
            if "clans_mgmt" in data:
                clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
            if "user_warnings" in data:
                user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
            if "admin_warnings" in data:
                admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
                
        print("✅ Data loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")

# دالة تحويل الأرقام لإيموجي
def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    result = ""
    for char in n_str:
        result += dic.get(char, char)
    return result

# دالة تنظيف النصوص
def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = re.sub(r'^(ال)', '', text)
    return text

# --- ميزة مراقبة التعديلات وفضحها ---
async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text:
        return
    
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(
                f"🚨 تنبيه: تم تعديل رسالة في جروب المواجهة!\n\n"
                f"📜 الرسالة قبل التعديل:\n{old_text}\n\n"
                f"🔄 الرسالة بعد التعديل:\n{new_text}\n\n"
                f"⚠️ التلاعب بالرسائل والقوائم ممنوع."
            )

# --- المعالج الرئيسي للمواجهة ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.message_id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # حفظ الرسالة الأصلية فوراً
    original_msg_store[mid] = msg

    # تحديد رتبة المستخدم
    super_admins = ["mwsa_20", "levil_8"]
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in super_admins) or is_creator
    except:
        is_creator = False
        is_referee = (user.username in super_admins)

    # --- الرد على الاعتراضات والقوانين (بشرط المنشن) ---
    is_bot_mentioned = (f"@{bot_username}" in msg) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)

if is_bot_mentioned:
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return

    # --- ميزة إلغاء الإنذار (للسوبر أدمن فقط) ---
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions: target_t = mentions[0]
        
        if target_t:
            if cid in user_warnings and target_t in user_warnings[cid]:
                user_warnings[cid][target_t] = 0
            if cid in admin_warnings and target_t in admin_warnings[cid]:
                admin_warnings[cid][target_t] = 0
            save_data() # حفظ التغيير
            await update.message.reply_text(f"✅ تم صفر (إلغاء) كافة إنذارات {target_t} بواسطة الإدارة.")
            return

    # --- نظام الطرد الآلي (للكفر والسب) ---
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in super_admins:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} فوراً لانتهاك قوانين الاتحاد (سب/كفر).")
                excep
