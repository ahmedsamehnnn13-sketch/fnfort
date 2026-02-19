import random
import re
import json
import os
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, JobQueue
from flask import Flask

# -------------------- إعدادات Flask --------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Referee Bot is Running!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# -------------------- الثوابت --------------------
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"  # توكن بوت الحكم
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "referee_data.json"
SUPER_ADMINS = ["mwsa_20", "levil_8"]  # السوبر أدمن

# -------------------- قاموس القوانين (موسع) --------------------
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم والنجم والحاسم:
1️⃣ أي فوز قوائم يمنع كتابة النجم والحاسم.
2️⃣ إذا كان الحاسم For Free لا يحتسب، ويعتبر الشخص قبله هو الحاسم.
3️⃣ الشخص الفائز بالمباراة وهو غير حاسم: الكلان يُحظر من النشر أسبوع.
4️⃣ المنشن للحكم إلزامي عند إرسال القائمة (مدة الاعتراض 10 ساعات).""",
    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط.""",
    "وقت": """⚖️ توقيت المواجهات:
⏰ الوقت الرسمي: 9 صباحاً – 1 صباحاً.
🔥 التمديد: يوم للأدوار العادية، يومين لنصف/نهائي.
🔹 شروط التمديد: حاسمة، اتفاق الطرفين، تواجد...""",
    "تواجد": """⚖️ التواجد والغياب:
🤔 غياب 20 ساعة بدون اتفاق = تبديل.
🤔 الرد خلال 10 دقائق بدون موعد = تهرب (تبديل).
🤔 التاك يحسب إذا لم يرد الخصم خلال 10 دقائق.""",
    "تصوير": """⚖️ التصوير:
1- وقت التصوير في البداية فقط.
2- الآيفون: فيديو (روم المحادثة + الرقم التسلسلي من "حول").
3- يمنع التصوير في النهاية لتجنب الغش.""",
    "انسحاب": """⚖️ الانسحاب:
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🤔 خروج متعمد = هدف مباشر.
🤔 الخروج بدون فسخ عقد = حظر بالمدة المتبقية (أقصى أسبوعين).""",
    "سب": """⚖️ السب والإساءة:
🚫 سب الأهل/الكفر = طرد + حظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص أثناء المواجهة = تبديل + حظر.
🚫 استفزاز الخصم = عقوبة تقديرية.""",
    "فار": """⚖️ الـ VAR:
✅ مرة واحدة لكل مواجهة (نصف نهائي، ربع نهائي، دور 16).
✅ الاعتماد الأساسي على الحكم.""",
    "انتقالات": """⚖️ الانتقالات:
📺 مسموحة فقط الخميس والجمعة.
🤔 أي انتقال في يوم آخر = غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر يمكنه الانتقال أي وقت.""",
    "عقود": """⚖️ العقود:
🤔 أقصى حد 8 قادة (القائد التاسع وهمي ويطرد).
🤔 فسخ العقد حصراً من القادة المسجلين.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).""",
    "نشر": """⚖️ النشر:
📢 أي فوز قوائم يمنع نشر النجم والحاسم.
📢 النشر الوهمي = حظر الكلان من قنوات النشر أسبوع.""",
    "حظر": """⚖️ الحظر والتنازل:
⛔️ المدة الأساسية أسبوعين.
🤝 التنازل يخفض المدة للنصف.
🚫 لا يشمل التنازل: الكفر، الوهمي، سب اللجنة، VPN، إضافة لاعب محظور.""",
    "اتفاق": """⚖️ الاتفاق والاعتراض:
✅ الاتفاق يسقط أغلب القوانين باستثناء: الحظر، دليل الخروج، آخر ساعتين، العقود...
⚠️ الاعتراض على قرار الحكم يسقط بعد 12 ساعة من انتهاء المواجهة.""",
    "تاكات": """⚖️ نظام التاكات:
🕐 التاك يحسب بعد 10 دقائق من عدم الرد.
🔄 تاك واحد لكل لاعب في نصف ساعة.
📊 بعد 3 أيام، يرسل البوت تقرير التاكات وأزرار للفائز (نقطة فري).""",
    "تبديلات": """⚖️ التبديلات:
🔄 كل كلان 3 تبديلات فقط.
📝 الأمر: "تبديل CLAN @old @new"
⚠️ التبديل الرابع لا يحتسب.""",
    "حاسم": """⚖️ الحاسم:
🔥 عند التعادل 3-3، يرسل القائد: "حاسم CLAN @player".
⚔️ يتم إيقاف التاكات وتحديد مباراة حاسمة."""
}

# كلمات الطرد
BAN_WORDS = ["كسمك", "كسمه", "كسختك", "كسم", "كس", "شرموطة", "منيوك", "ابن المتناكة", "ابن الشرموطة", "كفر", "الحمد لله", "بسم الله", "اللهم", "كسم الدين"]

# -------------------- هياكل البيانات --------------------
wars = {}               # المفتاح: chat_id
clans_mgmt = {}         # تخزين المساعدين
user_warnings = {}       # إنذارات اللاعبين
admin_warnings = {}      # إنذارات المسؤولين
original_msg_store = {}  # للكشف عن التعديلات

# -------------------- دوال الحفظ والتحميل --------------------
def save_data():
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=str)
        print("✅ Referee data saved.")
    except Exception as e:
        print(f"❌ Save error: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # تحويل المفاتيح إلى int وتحويل السلاسل الزمنية
            if "wars" in data:
                wars = {}
                for k, v in data["wars"].items():
                    cid = int(k)
                    # تحويل التواريخ المخزنة كنصوص
                    if "start_time" in v:
                        v["start_time"] = datetime.fromisoformat(v["start_time"])
                    if "taсks" in v:  # قد يكون الاسم به مشكلة ترميز، سنستخدم "tacks" بدلاً من ذلك
                        pass  # سيتم إعادة بنائها لاحقاً
                    wars[cid] = v
            if "clans_mgmt" in data:
                clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
            if "user_warnings" in data:
                user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
            if "admin_warnings" in data:
                admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
        print("✅ Referee data loaded.")
    except Exception as e:
        print(f"❌ Load error: {e}")

# -------------------- دوال مساعدة --------------------
def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return ''.join(dic.get(ch, ch) for ch in n_str)

def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return re.sub(r'^(ال)', '', text)

def is_official_time(dt=None):
    if dt is None:
        dt = datetime.now()
    return dt.hour >= 9 or dt.hour < 1  # 9-23 و 0-1

# -------------------- وظائف الخلفية --------------------
async def check_absence_job(context: ContextTypes.DEFAULT_TYPE):
    """مراقبة غياب اللاعبين كل ساعة"""
    now = datetime.now()
    for cid, war in list(wars.items()):
        if not war.get("active"):
            continue
        for clan_key in ["c1", "c2"]:
            clan = war[clan_key]
            for player in clan.get("p", []):
                last = war.get("last_activity", {}).get(player)
                if last and (now - last) > timedelta(hours=20):
                    await context.bot.send_message(
                        cid,
                        f"⚠️ تحذير: {player} غائب 20 ساعة بدون اتفاق. سيتم التبديل إن لم يتواصل."
                    )
                    # يمكن تنفيذ التبديل التلقائي هنا

async def send_tac_report(context: ContextTypes.DEFAULT_TYPE):
    """تقرير التاكات بعد 3 أيام"""
    cid = context.job.data["cid"]
    if cid not in wars or not wars[cid].get("active"):
        return
    war = wars[cid]
    if war.get("tac_report_sent"):
        return
    war["tac_report_sent"] = True
    save_data()

    # تجميع التاكات
    report = "📊 **تقرير التاكات بعد 3 أيام**\n\n"
    keyboard = []
    for clan_key in ["c1", "c2"]:
        clan = war[clan_key]
        report += f"🔹 {clan['n']}:\n"
        for player in clan.get("p", []):
            taсks = war.get("taсks", {}).get(clan_key, {}).get(player, [])
            report += f"  {player}: {len(taсks)} تاك\n"
            if taсks:
                keyboard.append([InlineKeyboardButton(f"✅ فاز {player}", callback_data=f"tacwin_{cid}_{clan_key}_{player}")])
    report += "\nاضغط على اللاعب الفائز (مرة واحدة للكلان)."
    await context.bot.send_message(cid, report, reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------- معالج التعديلات --------------------
async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text:
        return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old = original_msg_store[mid]
        new = update.edited_message.text
        if old != new:
            await update.edited_message.reply_text(
                f"🚨 تنبيه: تم تعديل رسالة!\n📜 قبل: {old}\n🔄 بعد: {new}\n⚠️ التلاعب ممنوع."
            )

# -------------------- معالج النصوص الرئيسي --------------------
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

    # حفظ الرسالة الأصلية
    original_msg_store[mid] = msg

    # تحديد الرتبة
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in SUPER_ADMINS) or is_creator
    except:
        is_referee = (user.username in SUPER_ADMINS)

    # ----- الذكاء الاصطناعي للقوانين -----
    is_bot_mentioned = (f"@{bot_username}" in msg) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)
    if is_bot_mentioned:
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return
        # إذا لم يجد، نبحث بكلمات مفتاحية
        key_map = {
            "قائم": "قوائم", "سكربت": "سكربت", "وقت": "وقت", "تمديد": "وقت",
            "تواجد": "تواجد", "حضور": "تواجد", "تصوير": "تصوير", "انسحاب": "انسحاب",
            "خروج": "انسحاب", "سب": "سب", "فار": "فار", "انتقالات": "انتقالات",
            "عقد": "عقود", "نشر": "نشر", "حظر": "حظر", "تنازل": "حظر",
            "اتفاق": "اتفاق", "اعتراض": "اتفاق", "تاك": "تاكات", "تبديل": "تبديلات", "حاسم": "حاسم"
        }
        for word, section in key_map.items():
            if word in msg_cleaned:
                await update.message.reply_text(DETAILED_LAWS[section], disable_web_page_preview=True)
                return

    # ----- إلغاء الإنذار (للمشرفين) -----
    if "الغاء انذار" in msg_cleaned and is_referee:
        target = None
        if update.message.reply_to_message:
            tu = update.message.reply_to_message.from_user
            target = f"@{tu.username}" if tu.username else f"ID:{tu.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions: target = mentions[0]
        if target:
            if cid in user_warnings and target in user_warnings[cid]:
                user_warnings[cid][target] = 0
            if cid in admin_warnings and target in admin_warnings[cid]:
                admin_warnings[cid][target] = 0
            save_data()
            await update.message.reply_text(f"✅ تم صفر إنذارات {target}.")
            return

    # ----- الطرد التلقائي للكلمات الممنوعة -----
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in SUPER_ADMINS:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} لاستخدام كلمات ممنوعة.")
                except:
                    pass
            return

    # ----- الروليت -----
    if "روليت" in msg:
        mentions = re.findall(r'@\w+', msg)
        if len(mentions) >= 2:
            winner = random.choice(mentions)
            await update.message.reply_text(f"🎲 الفائز بالروليت: {winner}")
            return

    # ----- الإنذارات -----
    if update.message.reply_to_message:
        tu = update.message.reply_to_message.from_user
        t_tag = f"@{tu.username}" if tu.username else f"ID:{tu.id}"
        if msg.strip() == "انذار م" and is_referee:
            admin_warnings.setdefault(cid, {})
            admin_warnings[cid][t_tag] = admin_warnings[cid].get(t_tag, 0) + 1
            save_data()
            await update.message.reply_text(f"⚠️ إنذار مسؤول {t_tag} ({admin_warnings[cid][t_tag]}/3)")
            if admin_warnings[cid][t_tag] >= 3:
                await update.message.reply_text(f"🚫 سحب صلاحية {t_tag}.")
            return
        if msg.strip() == "انذار" and is_referee:
            user_warnings.setdefault(cid, {})
            user_warnings[cid][t_tag] = user_warnings[cid].get(t_tag, 0) + 1
            save_data()
            await update.message.reply_text(f"⚠️ إنذار لاعب {t_tag} ({user_warnings[cid][t_tag]}/3)")
            if user_warnings[cid][t_tag] >= 3:
                try:
                    await context.bot.ban_chat_member(cid, tu.id)
                except:
                    pass
            return

    # ----- بدء المواجهة يدوياً (إذا لم تكن حرب نشطة) -----
    if "CLAN" in msg_up and "VS" in msg_up and "+ 1" not in msg_up and cid not in wars:
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
        await update.message.reply_text(f"⚔️ بدأت الحرب: {c1_name} vs {c2_name}")
        try:
            await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except:
            pass
        # جدولة تقرير التاكات بعد 3 أيام
        context.job_queue.run_once(send_tac_report, timedelta(days=3), data={"cid": cid})
        return

    # ----- إذا كانت الحرب نشطة -----
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # تحديث آخر نشاط للاعب
        for clan in ["c1", "c2"]:
            if u_tag in w[clan].get("p", []):
                w.setdefault("last_activity", {})[u_tag] = datetime.now()
                save_data()
                break

        # ----- التاكات -----
        if "تاك" in msg_cleaned and (update.message.reply_to_message or len(re.findall(r'@\w+', msg)) >= 2):
            from_player = u_tag
            to_player = None
            if update.message.reply_to_message:
                tu = update.message.reply_to_message.from_user
                to_player = f"@{tu.username}" if tu.username else f"ID:{tu.id}"
            else:
                mentions = re.findall(r'@\w+', msg)
                if len(mentions) >= 2:
                    to_player = mentions[1] if mentions[0] == u_tag else mentions[0]
            if to_player and from_player != to_player:
                # تحديد الانتماء
                clan_from = None
                clan_to = None
                for k in ["c1", "c2"]:
                    if from_player in w[k]["p"]: clan_from = k
                    if to_player in w[k]["p"]: clan_to = k
                if clan_from and clan_to and clan_from != clan_to:
                    # التحقق من 30 دقيقة
                    pair_key = f"{clan_from}_{from_player}_{clan_to}_{to_player}"
                    last = w["last_tack_time"].get(pair_key)
                    now = datetime.now()
                    if last and (now - last) < timedelta(minutes=30):
                        await update.message.reply_text("⏳ انتظر 30 دقيقة بين التاكات.")
                        return
                    # تسجيل التاك
                    w.setdefault("taсks", {}).setdefault(clan_to, {}).setdefault(to_player, []).append({"from": from_player, "time": now})
                    w.setdefault("last_tack_time", {})[pair_key] = now
                    save_data()
                    await update.message.reply_text(f"✅ تاك من {from_player} إلى {to_player}.")
                else:
                    await update.message.reply_text("❌ التاك يكون بين خصمين فقط.")
            return

        # ----- تعيين قائد بديل -----
        sub_leader = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader and is_referee:
            new_leader = sub_leader.group(1)
            clan_name = sub_leader.group(2).strip().upper()
            target = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            if target:
                w[target]["leader"] = new_leader
                save_data()
                await update.message.reply_text(f"✅ تم تعيين {new_leader} قائداً لكلان {w[target]['n']}.")
            else:
                await update.message.reply_text("❌ الكلان غير موجود.")
            return

        # ----- تسجيل القائمة -----
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"].upper() in msg_up: target_k = "c1"
            elif w["c2"]["n"].upper() in msg_up: target_k = "c2"
            if target_k:
                # التحقق من الصلاحية
                other_k = "c2" if target_k == "c1" else "c1"
                if not is_referee and w[other_k]["leader"] == u_tag:
                    await update.message.reply_text("❌ لا يمكنك إرسال قائمة الخصم.")
                    return
                w[target_k]["leader"] = u_tag
                # استخراج اللاعبين من الرسالة المُردود عليها
                players = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                w[target_k]["p"] = players
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد قائمة {w[target_k]['n']}.")

                # إذا اكتملت القائمتان، ننشئ الجدول
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
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    save_data()
                    try:
                        await context.bot.pin_chat_message(cid, sent.message_id)
                    except:
                        pass
            return

        # ----- تحديد المساعد -----
        asst = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
        if asst:
            target_asst = asst.group(1)
            clan_name = asst.group(2).upper()
            target = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            if target and (w[target]["leader"] == u_tag or is_referee):
                clans_mgmt.setdefault(cid, {})[clan_name] = {"asst": target_asst}
                save_data()
                await update.message.reply_text(f"✅ مساعد {target_asst} لكلان {clan_name}.")
            else:
                await update.message.reply_text("❌ غير مصرح.")
            return

        # ----- التبديلات -----
        sub = re.search(r'تبديل\s+(\w+)\s+(@\w+)\s+(@\w+)', msg)
        if sub:
            clan_name = sub.group(1).upper()
            old = sub.group(2)
            new = sub.group(3)
            target = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            if not target:
                await update.message.reply_text("❌ اسم الكلان غير صحيح.")
                return
            # التحقق من الصلاحية
            asst_tag = clans_mgmt.get(cid, {}).get(w[target]["n"].upper(), {}).get("asst")
            if not (is_referee or u_tag == w[target]["leader"] or u_tag == asst_tag):
                await update.message.reply_text("❌ غير مصرح بالتبديل.")
                return
            if w["replacements"][target] >= 3:
                await update.message.reply_text("❌ استنفدت التبديلات.")
                return
            # البحث عن المباراة
            found = False
            for match in w["matches"]:
                if match["p1"] == old or match["p2"] == old:
                    if match["p1"] == old:
                        match["p1"] = new
                    else:
                        match["p2"] = new
                    found = True
                    break
            if not found:
                await update.message.reply_text("❌ اللاعب القديم غير موجود.")
                return
            w["replacements"][target] += 1
            w["replacement_log"][target].append({"old": old, "new": new, "time": datetime.now()})
            save_data()
            await update.message.reply_text(f"✅ تم التبديل. تبقت {3 - w['replacements'][target]} تبديلات.")
            # تحديث الجدول
            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                try:
                    await context.bot.edit_message_text(updated, cid, w["mid"], disable_web_page_preview=True)
                except:
                    pass
            return

        # ----- الحاسم -----
        decisive = re.search(r'حاسم\s+(\w+)\s+(@\w+)', msg)
        if decisive and w["c1"]["s"] == 3 and w["c2"]["s"] == 3 and not w["decisive_mode"]:
            clan_name = decisive.group(1).upper()
            player = decisive.group(2)
            target = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            if not target:
                await update.message.reply_text("❌ اسم الكلان خطأ.")
                return
            # التحقق من الصلاحية
            asst_tag = clans_mgmt.get(cid, {}).get(w[target]["n"].upper(), {}).get("asst")
            if not (is_referee or u_tag == w[target]["leader"] or u_tag == asst_tag):
                await update.message.reply_text("❌ غير مصرح.")
                return
            if player not in w[target]["p"]:
                await update.message.reply_text("❌ اللاعب ليس في القائمة.")
                return
            w["decisive_players"][target] = player
            save_data()
            await update.message.reply_text(f"✅ تم تحديد {player} كلاعب حاسم لـ {w[target]['n']}.")
            if w["decisive_players"]["c1"] and w["decisive_players"]["c2"]:
                w["decisive_mode"] = True
                await update.message.reply_text(f"🔥 وضع الحاسم! {w['decisive_players']['c1']} vs {w['decisive_players']['c2']}")
            return

        # ----- إضافة النقاط -----
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if not win_k:
                return
            if len(players) >= 2 and len(scores) >= 2:
                asst_tag = clans_mgmt.get(cid, {}).get(w[win_k]["n"].upper(), {}).get("asst")
                if not (is_referee or u_tag == w[win_k]["leader"] or u_tag == asst_tag):
                    await update.message.reply_text("❌ غير مصرح بالتسجيل.")
                    return
                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                # تحديث الجدول
                for m in w["matches"]:
                    if (u1 == m["p1"].upper() or u1 == m["p2"].upper()) and (u2 == m["p1"].upper() or u2 == m["p2"].upper()):
                        if u1 == m["p1"].upper():
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                        # طرد اللاعبين بعد المباراة (اختياري - نطردهم ثم نعيد السماح بعد قليل؟ الأفضل طرد مؤقت)
                        # سيتم تنفيذه لاحقاً في وظيفة منفصلة
                        break
                save_data()
                await update.message.reply_text(f"✅ نقطة لـ {w[win_k]['n']}.")
                # تحديث عنوان المجموعة
                try:
                    await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except:
                    pass
                # تحديث الجدول
                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    updated = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                    try:
                        await context.bot.edit_message_text(updated, cid, w["mid"], disable_web_page_preview=True)
                    except:
                        pass
                # التحقق من الفوز
                if w[win_k]["s"] >= 4:
                    w["active"] = False
                    save_data()
                    # حساب النجم والحاسم
                    real = [h for h in w[win_k]["stats"] if not h.get("is_free")]
                    if real:
                        hasm = real[-1]["name"]
                        star_data = max(real, key=lambda x: x["goals"] - x["rec"])
                        star = star_data["name"]
                        star_goals, star_rec = star_data["goals"], star_data["rec"]
                        result = f"🎊 فاز {w[win_k]['n']}!\n🎯 الحاسم: {hasm}\n⭐ النجم: {star} ({star_goals}-{star_rec})"
                    else:
                        result = f"🎊 فوز إداري لـ {w[win_k]['n']}."
                    await update.message.reply_text(result)
                    # إرسال تفاصيل النتائج
                    details = "📊 النتائج:\n"
                    for i, m in enumerate(w["matches"]):
                        details += f"{i+1}. {m['p1']} {to_emoji(m['s1'])} - {to_emoji(m['s2'])} {m['p2']}\n"
                    await update.message.reply_text(details)
            else:
                # نقطة فري (للإدارة فقط)
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري للإدارة فقط.")
                    return
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                save_data()
                await update.message.reply_text(f"⚖️ نقطة فري لـ {w[win_k]['n']}.")
                try:
                    await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except:
                    pass

    # ----- استقبال أمر بدء المواجهة من بوت النشر -----
    if "بدء مواجهة:" in msg:
        # الصيغة: بدء مواجهة: الرابط: xxx النوع: xxx الكلانات: CLAN A VS CLAN B
        link_match = re.search(r'الرابط:\s*(.+)', msg)
        type_match = re.search(r'النوع:\s*(.+)', msg)
        clans_match = re.search(r'الكلانات:\s*(.+)', msg)
        if link_match and clans_match:
            source_url = link_match.group(1).strip()
            war_type = type_match.group(1).strip() if type_match else ""
            clans_text = clans_match.group(1).strip().upper()
            parts = clans_text.split(" VS ")
            if len(parts) != 2:
                await update.message.reply_text("❌ صيغة الكلانات غير صحيحة.")
                return
            c1_n = parts[0].replace("CLAN ", "").strip()
            c2_n = parts[1].replace("CLAN ", "").strip()

            # بدء الحرب
            wars[cid] = {
                "c1": {"n": c1_n, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_n, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True,
                "mid": None,
                "matches": [],
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
                "last_activity": {},
                "source_link": source_url,
                "war_type": war_type
            }
            save_data()
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {c1_n} 0 - 0 {c2_n} {war_type}")
                await context.bot.set_chat_description(cid, f"مواجهة: {source_url}")
            except Exception as e:
                print(f"Error setting title: {e}")
            await update.message.reply_text("🚀 تم بدء المواجهة بناءً على أمر بوت النشر.")
            context.job_queue.run_once(send_tac_report, timedelta(days=3), data={"cid": cid})
            return

    # ----- الاعتراض على البوت -----
    if "اعتراض" in msg_cleaned or "عندي اعتراض" in msg_cleaned:
        context.user_data["awaiting_objection"] = {"cid": cid, "user": u_tag}
        await update.message.reply_text("✍️ اكتب اعتراضك بالتفصيل وسيتم تحويله للحكام.")
        return

# -------------------- معالج الاعتراضات --------------------
async def handle_objection_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_objection"):
        data = context.user_data["awaiting_objection"]
        cid = data["cid"]
        user = data["user"]
        obj_text = update.message.text
        # إرسال إلى مجموعة الحكام (يجب تعيين معرف المجموعة)
        REF_GROUP = -1001234567890  # غيّره لمعرف مجموعة الحكام
        try:
            await context.bot.send_message(
                REF_GROUP,
                f"⚠️ اعتراض من {user} في {cid}:\n{obj_text}"
            )
            await update.message.reply_text("✅ تم إرسال اعتراضك.")
        except:
            await update.message.reply_text("❌ فشل الإرسال للحكام.")
        del context.user_data["awaiting_objection"]
    else:
        pass

# -------------------- معالج الأزرار --------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("tacwin_"):
        parts = data.split("_")
        cid = int(parts[1])
        clan_key = parts[2]
        player = parts[3]
        if cid in wars and wars[cid]["active"]:
            war = wars[cid]
            war[clan_key]["s"] += 1
            war[clan_key]["stats"].append({"name": f"TacWin_{player}", "goals": 0, "rec": 0, "is_free": True})
            save_data()
            await query.edit_message_text(f"✅ تم إضافة نقطة فري لـ {war[clan_key]['n']} بفوز {player} في التاكات.")
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {war['c1']['n']} {war['c1']['s']} - {war['c2']['s']} {war['c2']['n']} ⚔️")
            except:
                pass

# -------------------- التشغيل --------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    load_data()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_objection_text), group=1)

    if app.job_queue:
        app.job_queue.run_repeating(check_absence_job, interval=3600, first=10)
        print("✅ JobQueue active.")
    else:
        print("⚠️ JobQueue not available.")

    print("✅ Referee Bot is running...")
    app.run_polling()
