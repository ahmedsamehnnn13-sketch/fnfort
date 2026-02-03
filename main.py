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
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3/91?single"
AU_LINK = "https://t.me/arab_union3"

# كليشة القوانين
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

# ردود الاعتراضات التلقائية
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

BAN_WORDS = ["كسمك", "كسمه", "كسختك", "عرضك", "شرفك", "دين امك", "ينعل دين", "كفر"]

wars = {}
clans_mgmt = {} # لتخزين المساعدين وعدد مرات التبديل
user_warnings = {}
admin_warnings = {}
original_msg_store = {}

def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    result = ""
    for char in n_str:
        result += dic.get(char, char)
    return result

def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = re.sub(r'^(ال)', '', text)
    return text

async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text: return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(f"🚨 **تنبيه: تم تعديل رسالة!**\n📜 قبل: `{old_text}`\n🔄 بعد: `{new_text}`")

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.message_id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    original_msg_store[mid] = msg

    for obj_key, obj_val in OBJECTION_RESPONSES.items():
        if obj_key in msg_cleaned:
            await update.message.reply_text(obj_val)

    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_referee = (user.username == "mwsa_20") or (chat_member.status == 'creator')
    except: is_referee = (user.username == "mwsa_20")

    # --- ميزة إلغاء إنذار واحد فقط ---
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions: target_t = mentions[0]
        
        if target_t:
            done = False
            if cid in user_warnings and user_warnings[cid].get(target_t, 0) > 0:
                user_warnings[cid][target_t] -= 1
                done = True
            if cid in admin_warnings and admin_warnings[cid].get(target_t, 0) > 0:
                admin_warnings[cid][target_t] -= 1
                done = True
            
            if done: await update.message.reply_text(f"✅ تم إلغاء إنذار واحد لـ {target_t}.")
            else: await update.message.reply_text(f"ℹ️ {target_t} ليس لديه إنذارات حالياً.")
            return

    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username != "mwsa_20":
                try: await context.bot.ban_chat_member(cid, user.id)
                except: pass
            return

    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 الفائز هو: {winner}")
            return

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ إنذار مسؤول {t_tag} ({count}/3)")
            return
        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ إنذار لاعب {t_tag} ({count}/3)")
            if count >= 3:
                try: await context.bot.ban_chat_member(cid, target_user.id)
                except: pass
            return

    if "CLAN" in msg_up and "VS" in msg_up and "+ 1" not in msg_up:
        parts = msg_up.split(" VS ")
        c1_name = parts[0].replace("CLAN ", "").strip()
        c2_name = parts[1].replace("CLAN ", "").strip()
        wars[cid] = {
            "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None, "leader_swaps": 0, "asst": None, "asst_swaps": 0}, 
            "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None, "leader_swaps": 0, "asst": None, "asst_swaps": 0}, 
            "active": True, "mid": None, "matches": []
        }
        await update.message.reply_text(f"⚔️ بدأت الحرب: {c1_name} VS {c2_name}")
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- [ميزة مسؤول بدالي] ---
        if "مسؤول بدالي" in msg:
            target_leader = re.search(r'@\w+', msg)
            clan_match = re.search(r'كلان\s+(\w+)', msg_up)
            if target_leader and clan_match:
                new_l = target_leader.group(0)
                c_name = clan_match.group(1)
                target_k = "c1" if w["c1"]["n"].upper() == c_name else ("c2" if w["c2"]["n"].upper() == c_name else None)
                
                if target_k:
                    if w[target_k]["leader"] == u_tag:
                        if w[target_k]["leader_swaps"] < 1:
                            w[target_k]["leader"] = new_l
                            w[target_k]["leader_swaps"] += 1
                            await update.message.reply_text(f"🔄 تم نقل قيادة كلان {c_name} من {u_tag} إلى {new_l}.\n⚠️ لا يمكن تبديل المسؤول مرة أخرى لهذا الكلان.")
                        else:
                            await update.message.reply_text("❌ عذراً، تم استخدام الحد الأقصى لتبديل المسؤول (مرة واحدة فقط).")
                    else:
                        await update.message.reply_text("❌ فقط القائد الحالي للكلان يمكنه تعيين مسؤول بديل.")
            return

        # --- [ميزة تحديد المساعد] ---
        if "مساعدي" in msg:
            target_asst = re.search(r'@\w+', msg)
            clan_match = re.search(r'كلان\s+(\w+)', msg_up)
            if target_asst and clan_match:
                new_a = target_asst.group(0)
                c_name = clan_match.group(1)
                target_k = "c1" if w["c1"]["n"].upper() == c_name else ("c2" if w["c2"]["n"].upper() == c_name else None)
                
                if target_k:
                    # القائد أو المساعد الحالي فقط من يحق لهم التبديل
                    if u_tag == w[target_k]["leader"] or u_tag == w[target_k]["asst"]:
                        if w[target_k]["asst_swaps"] < 1:
                            w[target_k]["asst"] = new_a
                            w[target_k]["asst_swaps"] += 1
                            await update.message.reply_text(f"✅ تم تعيين {new_a} مساعداً لكلان {c_name}.\n⚠️ متبقي تبديل واحد للمساعد.")
                        else:
                            await update.message.reply_text("❌ عذراً، تم استهلاك الحد الأقصى لتبديل المساعدين.")
                    else:
                        await update.message.reply_text("❌ فقط القائد أو المساعد يمكنهم إدارة رتبة المساعد.")
            return

        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if target_k:
                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                if w["c1"]["p"] and w["c2"]["p"]:
                    p1, p2 = list(w["c1"]["p"]), list(w["c2"]["p"])
                    random.shuffle(p1); random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    rows = [f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
            return

        # --- نظام إضافة النقاط وتعديل القرعة الذكي ---
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if not win_k: return

            if len(players) >= 2 and len(scores) >= 2:
                # التحقق من الصلاحيات (حكم، قائد، أو مساعد)
                if not (is_referee or u_tag == w[win_k]["leader"] or u_tag == w[win_k]["asst"]):
                    await update.message.reply_text("❌ غير مسموح لك بتسجيل النتيجة. يجب أن تكون الحكم أو القائد أو المساعد.")
                    return

                u1, u2 = players[0].lower(), players[1].lower()
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                match_found = False
                for m in w["matches"]:
                    m_p1, m_p2 = m["p1"].lower(), m["p2"].lower()
                    if (u1 == m_p1 and u2 == m_p2) or (u1 == m_p2 and u2 == m_p1):
                        if u1 == m_p1: m["s1"], m["s2"] = sc1, sc2
                        else: m["s1"], m["s2"] = sc2, sc1
                        match_found = True
                        break
                
                if not match_found:
                    idx1 = next((i for i, m in enumerate(w["matches"]) if u1 in [m["p1"].lower(), m["p2"].lower()]), None)
                    idx2 = next((i for i, m in enumerate(w["matches"]) if u2 in [m["p1"].lower(), m["p2"].lower()]), None)
                    
                    if idx1 is not None and idx2 is not None:
                        m1, m2 = w["matches"][idx1], w["matches"][idx2]
                        old_opp1 = m1["p2"] if m1["p1"].lower() == u1 else m1["p1"]
                        old_opp2 = m2["p2"] if m2["p1"].lower() == u2 else m2["p1"]
                        w["matches"][idx1] = {"p1": u1 if m1["p1"].lower()==u1 else m1["p2"], "p2": u2 if m2["p1"].lower()==u2 else m2["p2"], "s1": sc1, "s2": sc2}
                        w["matches"][idx2] = {"p1": old_opp1, "p2": old_opp2, "s1": 0, "s2": 0}
                    else:
                        w["matches"].append({"p1": u1, "p2": u2, "s1": sc1, "s2": sc2})

                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                await update.message.reply_text(f"✅ تم تسجيل النتيجة وتعديل القرعة لـ {w[win_k]['n']}.")

            else: 
                if not is_referee: return
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                await update.message.reply_text(f"⚖️ نقطة فري لـ {w[win_k]['n']}.")

            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass

            if w[win_k]["s"] >= 4:
                w["active"] = False
                real = [h for h in w[win_k]["stats"] if not h["is_free"]]
                if real:
                    hasm = real[-1]["name"]
                    star = min(real, key=lambda x: x["rec"])["name"]
                    await update.message.reply_text(f"🎊 فاز {w[win_k]['n']}\n🎯 الحاسم: {hasm}\n⭐ النجم: {star}")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.run_polling()
