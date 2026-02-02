import random, re, logging, os, asyncio, json, threading
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask 

# --- إعدادات Flask ---
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الأصلية ---
TOKEN = "8291199369:AAEsxpKw1mxb9pybB4e5XIm-NG0OPjHA1Lw"
CONSTITUTION_LINK = "https://t.me/arab_union3/91?single"

CONSTITUTION_TEXT = f"""
━━━━━━━━━━━━━━━━━━━━
🎮 كليشة قوانين الاتحاد الرسمي (شاملة)
━━━━━━━━━━━━━━━━━━━━
1️⃣ القوائم: أي فوز قوائم يمنع كتابة النجم والحاسم.
2️⃣ السكربت: بطاقة ≤ 92 تعتبر سكربت.
7️⃣ السب: سب الأهل أو الكفر = طرد فوري.
15️⃣ القادة: المساعد له تبديل واحد فقط، وتغيير المساعد متاح مرة واحدة.
━━━━━━━━━━━━━━━━━━━━
✅ للمزيد راجع الرابط: {CONSTITUTION_LINK}"""

OBJECTION_RESPONSES = {
    "بدون منشن": "⚖️ حكم الاتحاد: المادة 4 - المنشن إلزامي للقوائم والحاسم والتبديل.",
    "مخالفة الوقت": "⚖️ حكم الاتحاد: المادة 10 - يمنع إجبار الخصم على الاتفاق في وقت غير رسمي.",
    "كاذب": "⚖️ حكم الاتحاد: الاعتراض الكاذب يعرض الكلان لخصم نقاط أو حظر أسبوع.",
    "سب": "⚖️ حكم الاتحاد: المادة 7 - سب الأهل أو الاستهزاء يؤدي لتبديل إلزامي أو طرد.",
    "تصوير": "⚖️ حكم الاتحاد: المادة 5 - تصوير السيريال للآيفون إلزامي، النقص = مخالفة.",
    "انتقالات": "⚖️ حكم الاتحاد: المادة 11 - الانتقالات مسموحة (الخميس والجمعة) فقط.",
    "فار": "⚖️ حكم الاتحاد: المادة 14 - VAR مرتين لنفس الكلان = حظر أسبوع.",
    "خروج": "⚖️ حكم الاتحاد: المادة 12 - خروج الخاسر قبل الدقيقة 80 والفرق هدف يتطلب اتفاقاً جديداً.",
    "تبديل": "⚖️ حكم الاتحاد: المادة 15 - تجاوز التبديلات المسموحة للقائد أو المساعد."
}

LAW_AI_DATABASE = {
    "السكربت": {"keys": ["سكربت", "92", "ميسي"], "ans": "🛡️ المادة 2: بطاقة ≤ 92 تعتبر سكربت."},
    "الخروج": {"keys": ["خرج", "80"], "ans": "🏃 المادة 12: دقيقة < 80 اتفاق جديد، دقيقة > 80 النتيجة ثابتة."},
    "الفار": {"keys": ["فار", "var"], "ans": "🖥️ المادة 14: الفار مرة واحدة للقائد، مرتين = حظر أسبوع."}
}

BAN_WORDS = ["كسمك", "كسمه", "كسختك", "عرضك", "شرفك", "دين امك", "ينعل دين", "كفر"]

wars, clans_mgmt, sub_counts = {}, {}, {}
user_warnings, admin_warnings, mentions_tracker = {}, {}, {}

def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join(dic.get(char, char) for char in n_str)

def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = re.sub(r'^(ال)', '', text)
    return text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')

def is_valid_tag_time():
    now = datetime.now().time()
    if time(1, 0) <= now <= time(9, 0): return False
    return True

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    cid, msg = update.effective_chat.id, update.message.text
    msg_cleaned = clean_text(msg)
    msg_up = msg.upper().strip() 
    user = update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # --- [ صلاحيات موسى المطلقة - مساعد حكم عام ] ---
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        # اليوزر @mwsa_20 يعتبر Owner في أي جروب تلقائياً
        is_owner = (chat_member.status in ['creator', 'administrator']) or (user.username == "mwsa_20")
    except: 
        is_owner = (user.username == "mwsa_20")

    if user.username == "mwsa_20" and msg == "فحص":
        await update.message.reply_text("✅ نظام المساعد مفعل: موسى (@mwsa_20) لديه كامل صلاحيات الحكم الآن.")
        return

    is_assistant = any(c.get("asst") == u_tag for c in clans_mgmt.get(cid, {}).values())

    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 نتيجة الروليت هي:\n\n🏆 الفائز: {winner}")
            return

    if cid in mentions_tracker:
        tracker = mentions_tracker[cid]
        if u_tag in tracker:
            opponent = tracker[u_tag]["opp"]
            if opponent in msg:
                if not is_valid_tag_time():
                    await update.message.reply_text(f"❌ التاك غير محسوب (الوقت الحالي من 1 بليل لـ 9 صباحاً ممنوع).")
                else:
                    tracker[u_tag]["time"] = datetime.now()
                    tracker[u_tag]["active"] = True
                    await update.message.reply_text(f"✅ تم تسجيل تاك {u_tag} ضد {opponent}.\n⏰ المهلة 10 دقائق للرد.")

        for sender, data in tracker.items():
            if data["opp"] == u_tag and data["active"] and data["time"]:
                diff = (datetime.now() - data["time"]).total_seconds() / 60
                if diff <= 10:
                    data["active"] = False
                    await update.message.reply_text(f"✅ رد سريع من {u_tag} (خلال {int(diff)} دقيقة). تم إلغاء المنشن.")

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        # موسى يقدر يعطي إنذار أو إنذار م في أي وقت
        if msg.strip() == "انذار م" and is_owner:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ **إنذار مسؤول (م)**\n👤 المسؤول: {t_tag}\n🔢 عدد الإنذارات: ({count}/3)")
            if count >= 3:
                for clan in clans_mgmt.get(cid, {}):
                    if clans_mgmt[cid][clan].get("asst") == t_tag:
                        clans_mgmt[cid][clan]["asst"] = None
                await update.message.reply_text(f"🚫 تم تنزيل المسؤول {t_tag} من منصبه.")
            return
        elif msg.strip() == "انذار" and is_owner:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ **إنذار لاعب**\n👤 اللاعب: {t_tag}\n🔢 عدد الإنذارات: ({count}/3)")
            if count >= 3:
                try: await context.bot.ban_chat_member(cid, target_user.id)
                except: pass
            return

    if "𝐀𝐑𝐀𝐁 𝐔𝐍𝐈𝐎𝐍" in msg:
        if is_owner or is_assistant:
            for key, reply in OBJECTION_RESPONSES.items():
                if key in msg:
                    await update.message.reply_text(f"{reply}\n🔗 [الدستور]({CONSTITUTION_LINK})")
                    return
        return

    asst_match = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
    if asst_match:
        target_asst, clan_name = asst_match.group(1), asst_match.group(2).upper()
        if cid not in clans_mgmt: clans_mgmt[cid] = {}
        if clan_name not in clans_mgmt[cid]:
            clans_mgmt[cid][clan_name] = {"asst": target_asst, "changes": 0}
            await update.message.reply_text(f"✅ تم تعيين {target_asst} مساعداً لـ كلان {clan_name}.")
        return

    if "تبديل" in msg_cleaned and is_assistant:
        if sub_counts.get(user.id, 0) < 1:
            sub_counts[user.id] = 1
            await update.message.reply_text(f"🔄 تم قبول التبديل للمساعد {u_tag}.")
        else:
            await update.message.reply_text("❌ المادة 15: تبديل واحد فقط.")
        return

    for cat, data in LAW_AI_DATABASE.items():
        if any(key in msg_cleaned for key in data["keys"]):
            await update.message.reply_text(data["ans"]); return

    if any(word in msg.lower() for word in BAN_WORDS):
        # موسى لا يتم طرده أبداً حتى لو غلط في الكلام
        if user.username != "mwsa_20":
            try: await context.bot.ban_chat_member(cid, user.id); await update.message.reply_text(f"🚫 طرد آلي.")
            except: pass
        return

    if "CLAN" in msg_up and "VS" in msg_up and "+ 1" not in msg_up:
        parts = msg_up.split(" VS ")
        c1 = parts[0].replace("CLAN ", "").strip()
        c2 = parts[1].replace("CLAN ", "").strip()
        wars[cid] = {"c1": {"n": c1, "s": 0, "p": [], "stats": []}, "c2": {"n": c2, "s": 0, "p": [], "stats": []}, "m": [], "mid": None, "active": True}
        await update.message.reply_text(f"⚔️ بدأت المواجهة: {c1} VS {c2}")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1} 0 - 0 {c2} ⚔️")
        except: pass
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target = "c1" if w["c1"]["n"].upper() in msg_up or not w["c1"]["p"] else "c2"
            w[target]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.strip() and p.startswith('@')]
            await update.message.reply_text(f"✅ سجلت قائمة {w[target]['n']}")
            if w["c1"]["p"] and w["c2"]["p"]:
                p1, p2 = list(w["c1"]["p"]), list(w["c2"]["p"])
                random.shuffle(p1); random.shuffle(p2)
                mentions_tracker[cid] = {u: {"opp": "", "time": None, "active": False} for u in p1+p2}
                for u1, u2 in zip(p1, p2): mentions_tracker[cid][u1]["opp"], mentions_tracker[cid][u2]["opp"] = u2, u1
                w["m"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                rows = [f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |" for i, m in enumerate(w["m"])]
                res = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n{CONSTITUTION_LINK}"
                sent = await update.message.reply_text(res, disable_web_page_preview=True)
                w["mid"] = sent.message_id
            return

        if "+ 1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_part = msg_up.split("+ 1")[-1].strip().upper()
            if len(players) >= 2 and len(scores) >= 2:
                u1_m, u2_m = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                winner_key = "c1" if w["c1"]["n"].upper() in win_part else ("c2" if w["c2"]["n"].upper() in win_part else None)
                if winner_key:
                    w[winner_key]["s"] += 1
                    p_win = u1_m if (sc1 > sc2) else u2_m
                    w[winner_key]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2)})
                    try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                    except: pass
                    for m in w["m"]:
                        if (u1_m == m["p1"] and u2_m == m["p2"]) or (u1_m == m["p2"] and u2_m == m["p1"]):
                            if u1_m == m["p1"]: m["s1"], m["s2"] = sc1, sc2
                            else: m["s1"], m["s2"] = sc2, sc1
                    if w["mid"]:
                        rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["m"])]
                        new_txt = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n{CONSTITUTION_LINK}"
                        try: await context.bot.edit_message_text(new_txt, cid, w["mid"], disable_web_page_preview=True)
                        except: pass
                    await update.message.reply_text(f"✅ سجلت نقطة لـ {w[winner_key]['n']}. النتيجة: {w['c1']['s']} - {w['c2']['s']}")
                    if w[winner_key]["s"] >= 4:
                        w["active"] = False
                        history = w[winner_key]["stats"]
                        await update.message.reply_text(f"🎊 فاز كلان {w[winner_key]['n']} 🎊\n🎯 الحاسم: {history[-1]['name']}")

# --- التشغيل النهائي ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    print("✅ Bot is polling...")
    app.run_polling()
