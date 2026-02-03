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
    port = int(os.environ.get("PORT", 7860))
    web_app.run(host='0.0.0.0', port=port)

# --- الإعدادات الثابتة ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3/91?single"
AU_LINK = "https://t.me/arab_union3"

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
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {}

def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join(dic.get(char, char) for char in str(num))

def clean_text(text):
    if not text: return ""
    text = text.lower().replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return re.sub(r'^(ال)', '', text).strip()

async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text: return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old, new = original_msg_store[mid], update.edited_message.text
        if old != new:
            await update.edited_message.reply_text(f"🚨 **تعديل كشفناه!**\n📜 قبل: `{old}`\n🔄 بعد: `{new}`")

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    cid, msg, mid = update.effective_chat.id, update.message.text, update.message.message_id
    msg_up, msg_cleaned, user = msg.upper().strip(), clean_text(msg), update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    if len(original_msg_store) > 500: original_msg_store.clear()
    original_msg_store[mid] = msg

    for k, v in OBJECTION_RESPONSES.items():
        if k in msg_cleaned: await update.message.reply_text(v)

    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_referee = (user.username == "mwsa_20") or (chat_member.status in ['creator', 'administrator'])
    except: is_referee = (user.username == "mwsa_20")

    if any(word in msg.lower() for word in BAN_WORDS) and user.username != "mwsa_20":
        try: await context.bot.ban_chat_member(cid, user.id); await update.message.reply_text(f"🚫 طرد {u_tag}")
        except: pass
        return

    # --- تشغيل الحرب ---
    if "CLAN" in msg_up and "VS" in msg_up and "+1" not in msg_up:
        parts = msg_up.split(" VS ")
        c1 = parts[0].replace("CLAN", "").strip()
        c2 = parts[1].replace("CLAN", "").strip()
        wars[cid] = {
            "c1": {"n": c1, "s": 0, "p": [], "stats": [], "leader": None, "leader_swaps": 0, "asst": None, "asst_swaps": 0},
            "c2": {"n": c2, "s": 0, "p": [], "stats": [], "leader": None, "leader_swaps": 0, "asst": None, "asst_swaps": 0},
            "active": True, "mid": None, "matches": []
        }
        await update.message.reply_text(f"⚔️ بدأت الحرب: {c1} ضد {c2}")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1} 0 - 0 {c2} ⚔️")
        except Exception as e: print(f"Title Error: {e}")
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- إضافة النقاط (تم الإصلاح هنا) ---
        if "+1" in msg.replace(" ", ""):
            # التحقق من الكلان المذكور في الرسالة
            target_win = None
            if w["c1"]["n"].upper() in msg_up: target_win = "c1"
            elif w["c2"]["n"].upper() in msg_up: target_win = "c2"
            
            if target_win:
                players = re.findall(r'@\w+', msg)
                scores = re.findall(r'(\d+)', msg)

                # نقطة عادية
                if len(players) >= 2 and len(scores) >= 2:
                    if not (is_referee or u_tag == w[target_win]["leader"] or u_tag == w[target_win]["asst"]):
                        await update.message.reply_text("❌ صلاحية القائد/المساعد/الحكم فقط.")
                        return
                    sc1, sc2 = int(scores[0]), int(scores[1])
                    w[target_win]["s"] += 1
                    w[target_win]["stats"].append({"name": players[0] if sc1 > sc2 else players[1], "rec": min(sc1, sc2), "is_free": False})
                    
                    # تحديث الجدول
                    for m in w["matches"]:
                        if players[0] in [m["p1"], m["p2"]] and players[1] in [m["p1"], m["p2"]]:
                            if players[0] == m["p1"]: m["s1"], m["s2"] = sc1, sc2
                            else: m["s1"], m["s2"] = sc2, sc1
                    await update.message.reply_text(f"✅ سجل {w[target_win]['n']} نقطة.")
                
                # نقطة فري
                elif is_referee:
                    w[target_win]["s"] += 1
                    w[target_win]["stats"].append({"name": "Free", "rec": 0, "is_free": True})
                    await update.message.reply_text(f"⚖️ نقطة فري لـ {w[target_win]['n']}.")

                # --- تحديث اسم المجموعة والسكور ---
                try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except: pass

                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(table, cid, w["mid"], disable_web_page_preview=True)
                    except: pass

                if w[target_win]["s"] >= 4:
                    w["active"] = False
                    real = [h for h in w[target_win]["stats"] if not h["is_free"]]
                    if real:
                        hasm, star = real[-1]["name"], min(real, key=lambda x: x["rec"])["name"]
                        await update.message.reply_text(f"🎊 انتهت!\n🏆 الفائز: {w[target_win]['n']}\n🎯 الحاسم: {hasm}\n⭐ النجم: {star}")

        # ميزات القيادة والمساعد والقوائم (نفس الكود السابق بدون تغيير)
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
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
        
        # ميزات المساعد ومسؤول بدالي
        if "مساعدي" in msg or "مسؤول بدالي" in msg:
            target_user = re.search(r'@\w+', msg)
            clan_match = re.search(r'كلان\s+(\w+)', msg_up)
            if target_user and clan_match:
                c_n = clan_match.group(1)
                tk = "c1" if w["c1"]["n"].upper() == c_n else ("c2" if w["c2"]["n"].upper() == c_n else None)
                if tk and w[tk]["leader"] == u_tag:
                    if "مساعدي" in msg: w[tk]["asst"] = target_user.group(0); await update.message.reply_text(f"✅ مساعد {c_n}: {w[tk]['asst']}")
                    else: w[tk]["leader"] = target_user.group(0); await update.message.reply_text(f"🔄 مسؤول {c_n}: {w[tk]['leader']}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.run_polling(drop_pending_updates=True)
