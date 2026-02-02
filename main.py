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

# كلمات الطرد (السب والكفر)
BAN_WORDS = ["كسمك", "كسمه", "كسختك", "عرضك", "شرفك", "دين امك", "ينعل دين", "كفر"]

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
sub_counts = {}
user_warnings = {}
admin_warnings = {}
mentions_tracker = {}
original_msg_store = {}

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
                f"🚨 **تنبيه: تم تعديل رسالة في جروب المواجهة!**\n\n"
                f"📜 **الرسالة قبل التعديل:**\n`{old_text}`\n\n"
                f"🔄 **الرسالة بعد التعديل:**\n`{new_text}`\n\n"
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
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # حفظ الرسالة الأصلية فوراً
    original_msg_store[mid] = msg

    # --- [هنا التعديل: الرد على القوانين] ---
    for obj_key, obj_val in OBJECTION_RESPONSES.items():
        if obj_key in msg_cleaned:
            await update.message.reply_text(obj_val)

    # تحديد رتبة المستخدم (موسى والمالك كلاهما حكم بكامل الصلاحيات)
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_owner = (chat_member.status in ['creator', 'administrator']) # تعديل بسيط ليشمل الأدمن المالك
        is_referee = (user.username == "mwsa_20") or (chat_member.status == 'creator')
    except:
        is_owner = False
        is_referee = (user.username == "mwsa_20")

    # --- ميزة إلغاء الإنذار (لموسى والحكم فقط) ---
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        # إذا كان رداً على رسالة
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        # إذا كان منشناً بالاسم
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions:
                target_t = mentions[0]
        
        if target_t:
            if cid in user_warnings and target_t in user_warnings[cid]:
                user_warnings[cid][target_t] = 0
            if cid in admin_warnings and target_t in admin_warnings[cid]:
                admin_warnings[cid][target_t] = 0
            await update.message.reply_text(f"✅ تم صفر (إلغاء) كافة إنذارات {target_t} بواسطة الإدارة.")
            return

    # --- نظام الطرد الآلي (للكفر والسب) ---
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username != "mwsa_20":
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} فوراً لانتهاك قوانين الاتحاد (سب/كفر).")
                except:
                    pass
            return

    # --- ميزة الروليت ---
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 **قرعة الروليت:**\n\n🏆 الفائز هو: {winner}")
            return

    # --- نظام الإنذارات (م) وللاعبين (صلاحية موسى والمالك) ---
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        
        # إنذار مسؤول (م) - متاح لموسى والمالك
        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ **إنذار مسؤول (م)**\n👤 المسؤول: {t_tag}\n🔢 العدد: ({count}/3)")
            if count >= 3:
                await update.message.reply_text(f"🚫 تم سحب صلاحيات المسؤول {t_tag} بواسطة الإدارة.")
            return

        # إنذار لاعب عادي - متاح لموسى والمالك
        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            await update.message.reply_text(f"⚠️ **إنذار لاعب**\n👤 اللاعب: {t_tag}\n🔢 العدد: ({count}/3)")
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
            "matches": []
        }
        await update.message.reply_text(f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- تسجيل القائمة (حصر القائد ومنع تسجيل الخصم) ---
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            
            if target_k:
                other_k = "c2" if target_k == "c1" else "c1"
                # إذا كان المستخدم مسجل كقائد للكلان الخصم
                if w[other_k]["leader"] == u_tag:
                    await update.message.reply_text("❌ أنت قائد الكلان الخصم، لا يمكنك إرسال قائمة منافسك!")
                    return
                
                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']} بواسطة القائد {u_tag}")

                # إذا اكتملت القائمتين يتم إنشاء جدول المواجهات
                if w["c1"]["p"] and w["c2"]["p"]:
                    p1 = list(w["c1"]["p"])
                    p2 = list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    
                    rows = []
                    for i, m in enumerate(w["matches"]):
                        rows.append(f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |")
                    
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
            return

        # --- تحديد المساعد (للقائد وموسى والمالك) ---
        asst_match = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
        if asst_match:
            target_asst = asst_match.group(1)
            clan_name = asst_match.group(2).upper()
            target_key = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            
            if target_key and (w[target_key]["leader"] == u_tag or is_referee):
                if cid not in clans_mgmt: clans_mgmt[cid] = {}
                clans_mgmt[cid][clan_name] = {"asst": target_asst}
                await update.message.reply_text(f"✅ تم تعيين المساعد {target_asst} لكلان {clan_name}.")
            elif target_key:
                await update.message.reply_text("❌ فقط قائد الكلان أو الحكم يمكنه تحديد المساعد.")
            return

        # --- نظام إضافة النقاط (تسجيل عادي وفري) ---
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            
            # تحديد الكلان المستهدف من نص الرسالة
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if not win_k: return

            # 1. حالة التسجيل العادي (مباراة بين شخصين)
            if len(players) >= 2 and len(scores) >= 2:
                # التحقق من الصلاحية: (مالك، موسى، قائد الكلان، أو مساعد الكلان)
                asst_tag = clans_mgmt.get(cid, {}).get(w[win_k]["n"].upper(), {}).get("asst")
                if not (is_referee or u_tag == w[win_k]["leader"] or u_tag == asst_tag):
                    await update.message.reply_text("❌ عذراً، تسجيل نتائج المباريات مسموح فقط للحكام أو قادة ومساعدين الكلان الفائز.")
                    return

                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                
                # تحديث سكور الجدول
                for m in w["matches"]:
                    if (u1 in [m["p1"], m["p2"]]) and (u2 in [m["p1"], m["p2"]]):
                        if u1 == m["p1"]:
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                
                await update.message.reply_text(f"✅ تم تسجيل نقطة مباراة لـ {w[win_k]['n']}.")

            # 2. حالة النقطة الفري (قرار إداري - لموسى والمالك فقط)
            else:
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري (+1 اسم الكلان) هي صلاحية حصرية لموسى أو مالك الجروب فقط.")
                    return
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                await update.message.reply_text(f"⚖️ قرار إداري: إضافة نقطة فري لكلان {w[win_k]['n']} بواسطة {u_tag}.")

            # تحديث عنوان الجروب والرسالة المثبتة
            try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except: pass

            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass

            # فحص نهاية الحرب (4 نقاط)
            if w[win_k]["s"] >= 4:
                w["active"] = False
                history = w[win_k]["stats"]
                # اختيار الحاسم: آخر لاعب حقيقي سجل نقطة (تجاهل الفري)
                real_players = [h for h in history if not h["is_free"]]
                hasm = real_players[-1]["name"] if real_players else "فوز إداري"
                # النجم: أقل واحد استقبل أهداف في مبارياته
                star = min(real_players, key=lambda x: x["rec"])["name"] if real_players else "غير محدد"
                
                await update.message.reply_text(f"🎊 انتهت الحرب بفوز كلان: {w[win_k]['n']} 🎊\n\n🎯 الحاسم: {hasm}\n⭐ النجم: {star}")

# --- تشغيل البوت ---
if __name__ == "__main__":
    # تشغيل Flask في خيط منفصل
    threading.Thread(target=run_flask).start()
    
    # بناء تطبيق التليجرام
    app = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الرسائل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    
    print("✅ البوت يعمل الآن بكامل طاقته وميزاته...")
    app.run_polling()
