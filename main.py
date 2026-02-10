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
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"  # اسم ملف حفظ البيانات

# --- قاموس القوانين التفصيلية ---
DETAILED_LAWS = {
    "قوائم": """⚖️ **قوانين القوائم والنجم والحاسم:**
1️⃣ **القواعد الأساسية:**
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم (الأهداف، التأثير، السلوك).
- يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
- المنشن للحكم إلزامي عند إرسال القائمة، بدونه تعتبر لاغية (مدة الاعتراض 10 ساعات).

2️⃣ **التوقيت:**
- نصف النهائي/النهائي: 18 ساعة (+15د سماح).
- باقي الأدوار: 14 ساعة (+15د سماح).
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ **قوانين السكربت:**
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط (الخروج فوراً مع دليل).
⬆️ في المنتصف: تغيير التشكيلة أو المدرب لا يعتبر سكربت.
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ **توقيت المواجهات والتمديد:**
⏰ **الوقت الرسمي:** من 9 صباحاً حتى 1 صباحاً.
🚫 لا يجبر الخصم على اللعب في وقت غير رسمي (2-8 صباحاً).

🔥 **التمديد:**
- يوم واحد (للأدوار العادية)، يومين (نصف/نهائي).
- يمدد تلقائياً إذا: (حاسمة، اتفاق طرفين، شروط التمديد المنطبقة).
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ **قوانين التواجد والغياب:**
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 غياب الطرفين = يتم تبديل الطرف الأقل محاولة للاتفاق.
🤔 وضع تفاعل (Reaction) على الموعد يعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد يعتبر تهرباً (يستوجب التبديل).
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ **قوانين التصوير (محدث):**
1- وقت التصوير في البداية فقط.
2- **الآيفون:** فيديو (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
3- يمنع التصوير نهاية المباراة لتجنب الغش.
4- إرسال التصوير متاح في أي وقت (بداية أو نهاية).
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ **قوانين الانسحاب والخروج:**
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🤔 خروج متعمد (اعتراف) = هدف مباشر.
🤔 سوء نت: فيديو 30 ثانية يوضح اللاق والإشعارات.
🤔 الخروج بدون فسخ عقد = حظر بمدة العقد المتبقية.
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ **قوانين السب والإساءة:**
🚫 سب الأهل/الكفر = طرد وحظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص (أثناء المواجهة) = تبديل + حظر (يتطلب دليل فيديو لليوزر).
🚫 استفزاز الخصم أو الحكم = عقوبة تقديرية (تبديل/حظر).
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ **قوانين الـ VAR:**
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
✅ الاعتماد الأساسي على حكم المباراة.
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ **قوانين الانتقالات:**
📺 مسموحة فقط يومي (الخميس والجمعة).
🤔 أي انتقال في يوم آخر يعتبر غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر (بدون عقد) يمكنه الانتقال في أي وقت.
🔗 للمزيد: https://t.me/arab_union3""",
    
    "عقود": """⚖️ **قوانين العقود:**
🤔 أقصى حد للمسؤولين في العقود: 8 قادة.
🤔 القائد الـ 9 يعتبر وهمي ويطرد.
🤔 فسخ العقد حصراً من القادة المسجلين.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).
🔗 للمزيد: https://t.me/arab_union3"""
}

# كلمات الطرد (السب والكفر)
BAN_WORDS = ["كسمك", "كسمه", "كسختك", "عرضك", "شرفك", "دين امك", "ينعل دين", "كفر"]

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
                except: pass
            return

    # --- ميزة الروليت ---
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 **قرعة الروليت:**\n\n🏆 الفائز هو: {winner}")
            return

    # --- نظام الإنذارات (م) وللاعبين ---
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        
        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            save_data() # حفظ
            await update.message.reply_text(f"⚠️ **إنذار مسؤول (م)**\n👤 المسؤول: {t_tag}\n🔢 العدد: ({count}/3)")
            if count >= 3:
                await update.message.reply_text(f"🚫 تم سحب صلاحيات المسؤول {t_tag} بواسطة الإدارة.")
            return

        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            save_data() # حفظ
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
        save_data() # حفظ بداية الحرب
        await update.message.reply_text(f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        return

    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # --- [جديد] ميزة تعيين قائد بديل يدوياً ---
        sub_leader_match = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader_match and is_referee:
            new_leader = sub_leader_match.group(1)
            target_clan_name = sub_leader_match.group(2).strip().upper()
            
            # البحث عن الكلان المقصود
            target_k = None
            if w["c1"]["n"].upper() == target_clan_name: target_k = "c1"
            elif w["c2"]["n"].upper() == target_clan_name: target_k = "c2"
            
            if target_k:
                w[target_k]["leader"] = new_leader
                save_data() # حفظ القائد الجديد
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
                save_data() # حفظ القائمة
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']} (بواسطة {u_tag}).")

                if w["c1"]["p"] and w["c2"]["p"]:
                    p1 = list(w["c1"]["p"])
                    p2 = list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    save_data() # حفظ الجدول
                    
                    rows = []
                    for i, m in enumerate(w["matches"]):
                        rows.append(f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |")
                    
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    save_data() # حفظ آيدي رسالة الجدول
                    
                    # --- [إضافة] تثبيت الرسالة تلقائياً ---
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
                save_data() # حفظ المساعد
                await update.message.reply_text(f"✅ تم تعيين المساعد {target_asst} لكلان {clan_name}.")
            elif target_key:
                await update.message.reply_text("❌ فقط قائد الكلان أو الحكم يمكنه تحديد المساعد.")
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

                u1, u2 = players[0], players[1] # أسماء اللاعبين (UPPERCASE بسبب regex)
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                
                # --- تحديث نتيجة المباراة في الجدول (إصلاح عدم التحديث) ---
                for m in w["matches"]:
                    # نحول أسماء اللاعبين في الجدول لحروف كبيرة للمقارنة فقط
                    mp1_u = m["p1"].upper()
                    mp2_u = m["p2"].upper()
                    
                    if (u1 == mp1_u or u1 == mp2_u) and (u2 == mp1_u or u2 == mp2_u):
                        # تحديث النتائج بناءً على مكان اللاعب في الجدول
                        if u1 == mp1_u:
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                
                save_data() # حفظ النتيجة وتحديث المباريات
                await update.message.reply_text(f"✅ تم تسجيل نقطة مباراة لـ {w[win_k]['n']}.")

            else:
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري حصرية للإدارة.")
                    return
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                save_data() # حفظ النقطة الفري
                await update.message.reply_text(f"⚖️ قرار إداري: إضافة نقطة فري لكلان {w[win_k]['n']} بواسطة {u_tag}.")

            try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except: pass

            # تحديث الجدول المعروض في التليجرام
            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass
            
            # --- إنهاء الحرب وإرسال النتائج النهائية ---
            if w[win_k]["s"] >= 4:
                w["active"] = False
                save_data() # حفظ نهاية الحرب
                history = w[win_k]["stats"]
                real_players = [h for h in history if not h["is_free"]]
                
                if real_players:
                    hasm = real_players[-1]["name"]
                    star_player_data = min(real_players, key=lambda x: x["rec"])
                    star = star_player_data["name"]
                    star_rec = star_player_data["rec"]
                    result_msg = (
                        f"🎊 انتهت الحرب بفوز كلان: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {hasm} (آخر من سجل)\n"
                        f"⭐ النجم: {star} (استقبل {star_rec} أهداف فقط)"
                    )
                else:
                    result_msg = f"🎊 انتهت الحرب بفوز إداري لكلان: {w[win_k]['n']} 🎊"
                
                # إرسال رسالة النتيجة أولاً
                await update.message.reply_text(result_msg)

                # --- [تم التعديل] إرسال تفاصيل النتائج الواقعية (ليست 0/0) ---
                match_results_str = ""
                for i, m in enumerate(w["matches"]):
                    # الآن سيتم سحب النتائج المسجلة s1 و s2 بدلاً من الأصفار
                    line = f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |"
                    match_results_str += line + "\n"
                    match_results_str += "─── ─── ─── ─── ───\n"
                
                # إرسال الرسالة النهائية
                await update.message.reply_text(f"📊 **تفاصيل النتائج:**\n\n{match_results_str}")

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    # تحميل البيانات المحفوظة عند التشغيل
    load_data()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    
    print("✅ البوت يعمل الآن (مع خاصية حفظ البيانات وتحديث النتائج واقعياً)...")
    app.run_polling()
