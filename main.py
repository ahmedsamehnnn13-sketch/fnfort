import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask 

# --- إعدادات Flask لضمان استمرارية البوت ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live (Optimized & Archive Enabled)!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"       # الملف الحي
ARCHIVE_FILE = "wars_archive.json" # ملف الأرشيف

# --- القادة المستثنون من القيود ---
SUPER_ADMINS = ["mwsa_20", "levil_8"]

# --- قاموس القوانين التفصيلية ---
DETAILED_LAWS = {
    "قوائم": """⚖️ **قوانين القوائم والنجم والحاسم:**
1️⃣ **القواعد الأساسية:**
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم (الأهداف، التأثير، السلوك).
- يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
- المنشن للحكم إلزامي عند إرسال القائمة، بدونه تعتبر لاغية (مدة الاعتراض 10 ساعات).
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ **قوانين السكربت:**
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ **توقيت المواجهات والتمديد:**
⏰ **الوقت الرسمي:** من 9 صباحاً حتى 1 صباحاً.
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ **قوانين التواجد والغياب:**
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ **قوانين التصوير (محدث):**
1- وقت التصوير في البداية فقط.
2- **الآيفون:** فيديو (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ **قوانين الانسحاب والخروج:**
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ **قوانين السب والإساءة:**
🚫 سب الأهل/الكفر = طرد وحظر.
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ **قوانين الـ VAR:**
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ **قوانين الانتقالات:**
📺 مسموحة فقط يومي (الخميس والجمعة).
🔗 للمزيد: https://t.me/arab_union3""",
    
    "عقود": """⚖️ **قوانين العقود:**
🤔 أقصى حد للمسؤولين في العقود: 8 قادة.
🔗 للمزيد: https://t.me/arab_union3"""
}

# كلمات الطرد (السب والكفر) - القائمة الصارمة المطلوبة
BAN_WORDS = ["كسمك", "كسختك", "خالتك", "عمتك", "امك", "اختك", "دين", "رب", "كفر", "الله"] 

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}

# --- دوال الحفظ والأرشفة (Technical Optimization) ---
def save_data():
    """حفظ البيانات الحية فقط"""
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Save Error: {e}")

def archive_war_data(chat_id, war_data):
    """نقل بيانات الحرب المنتهية إلى الأرشيف وحذفها من الملف الرئيسي"""
    archive_data = {}
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        except: pass
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    archive_data[f"{chat_id}_{timestamp}"] = war_data
    
    try:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=4)
        print(f"✅ المواجهة تمت أرشفتها بنجاح للشات {chat_id}")
    except Exception as e:
        print(f"❌ خطأ في الأرشفة: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings
    if not os.path.exists(DATA_FILE): return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "wars" in data: wars = {int(k): v for k, v in data["wars"].items()}
            if "clans_mgmt" in data: clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
            if "user_warnings" in data: user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
            if "admin_warnings" in data: admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
        print("✅ Data loaded.")
    except Exception as e:
        print(f"❌ Load Error: {e}")

# دالة تحويل الأرقام لإيموجي
def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join([dic.get(c, c) for c in str(num)])

# دالة تنظيف النصوص
def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return re.sub(r'^(ال)', '', text)

# --- المعالج الرئيسي ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    cid = update.effective_chat.id
    msg = update.message.text
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"
    
    # تحديد الرتب
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_admin_or_creator = chat_member.status in ['creator', 'administrator']
    except: is_admin_or_creator = False

    is_super = user.username in SUPER_ADMINS
    is_referee = is_super or is_admin_or_creator

    # 1️⃣ --- نظام الطرد الآلي (السب والكفر) ---
    for word in BAN_WORDS:
        if word in msg.lower(): 
            if not is_super:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} لانتهاك القوانين (سب الأهل/الكفر).")
                except: pass
            return

    # 2️⃣ --- أوامر الحكم والإدارة ---
    # الرد على القوانين
    if f"@{context.bot.username}" in msg or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
        for k, v in DETAILED_LAWS.items():
            if k in msg_cleaned:
                await update.message.reply_text(v, disable_web_page_preview=True)
                return

    # طرد لاعب
    if msg.startswith("طرد لاعب") and is_referee:
        target_id = None
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
        
        if target_id:
            try:
                await context.bot.ban_chat_member(cid, target_id)
                await update.message.reply_text("✅ تم الطرد بنجاح.")
            except:
                await update.message.reply_text("❌ لم أتمكن من الطرد.")
        else:
             await update.message.reply_text("⚠️ قم بالرد على رسالة اللاعب بـ 'طرد لاعب'.")
        return

    # 3️⃣ --- بداية المواجهة (تنسيق صارم فقط) ---
    # يقبل فقط: CLAN X VS CLAN Y (في رسالة منفصلة)
    if re.fullmatch(r'CLAN\s+.+\s+VS\s+CLAN\s+.+', msg_up):
        parts = msg_up.split(" VS ")
        c1_name = parts[0].replace("CLAN ", "").strip()
        c2_name = parts[1].replace("CLAN ", "").strip()
        
        wars[cid] = {
            "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None, "subs_used": 0, "hasim_changes": 0, "asst_changes": 0},
            "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None, "subs_used": 0, "hasim_changes": 0, "asst_changes": 0},
            "active": True,
            "mid": None,
            "matches": [],
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": {} # {user_tag: {last: datetime, count: 0, pending: bool, pending_start: datetime}}
        }
        save_data()
        await update.message.reply_text(f"⚔️ بدأت **المواجهة** الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        return

    # عمليات داخل المواجهة النشطة
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]
        
        # --- نظام التاكات (Tag System) ---
        sender_clean = f"@{user.username}" if user.username else None
        if sender_clean:
            now = datetime.now()
            
            # 1. فحص إذا كان هذا الرد ينهي تاك معلق
            if update.message.reply_to_message:
                replied_user = update.message.reply_to_message.from_user.username
                if replied_user:
                    replied_tag = f"@{replied_user}"
                    if replied_tag in w["tags"]:
                        tag_data = w["tags"][replied_tag]
                        # إذا كان عليه تاك معلق ومن رد هو الخصم المطلوب أو أي شخص (للتسهيل سنعتبر الرد يلغي التاك)
                        if tag_data.get("pending", False):
                            tag_data["pending"] = False
                            w["tags"][replied_tag] = tag_data
                            save_data()

            # 2. احتساب تاك جديد
            tag_match = re.findall(r'(@\w+)', msg)
            if tag_match:
                target = tag_match[0]
                
                # تهيئة السجل
                if sender_clean not in w["tags"]:
                    w["tags"][sender_clean] = {"count": 0, "last_valid": None, "pending": False, "pending_time": None}
                
                user_tag_data = w["tags"][sender_clean]
                
                # فحص الـ 30 دقيقة
                can_tag = True
                if user_tag_data["last_valid"]:
                    last_dt = datetime.strptime(user_tag_data["last_valid"], "%Y-%m-%d %H:%M:%S")
                    if now - last_dt < timedelta(minutes=30):
                        can_tag = False
                
                if can_tag:
                    user_tag_data["last_valid"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    user_tag_data["pending"] = True
                    user_tag_data["pending_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    w["tags"][sender_clean] = user_tag_data
                    save_data()

        # --- تسجيل القائمة ---
        if "قائم" in msg and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"] in msg_up: target_k = "c1"
            elif w["c2"]["n"] in msg_up: target_k = "c2"
            
            if target_k:
                # فقط القائد أو الحكم
                if not is_referee and w[target_k]["leader"] != u_tag and w[target_k]["leader"] is not None:
                     return
                
                if w[target_k]["leader"] is None: w[target_k]["leader"] = u_tag

                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']}")

                # نزول الجدول
                if w["c1"]["p"] and w["c2"]["p"] and not w["matches"]:
                    p1, p2 = list(w["c1"]["p"]), list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    w["matches"] = [{"p1": x, "p2": y, "s1": 0, "s2": 0} for x, y in zip(p1, p2)]
                    save_data()
                    
                    rows = []
                    for i, m in enumerate(w["matches"]):
                        rows.append(f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |")
                    
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    try: await context.bot.pin_chat_message(cid, sent.message_id)
                    except: pass
                    w["mid"] = sent.message_id
                    save_data()
            return

        # --- التبديلات (Substitutions) ---
        if msg.startswith("تبديل"):
            mentions = re.findall(r'(@\w+)', msg)
            clan_in_msg = next((name for name in [w["c1"]["n"], w["c2"]["n"]] if name in msg_up), None)
            
            if clan_in_msg and len(mentions) >= 2:
                tk = "c1" if w["c1"]["n"] == clan_in_msg else "c2"
                
                # التحقق من الصلاحية
                if not is_referee and w[tk]["leader"] != u_tag: return

                # التحقق من الحد (3)
                if w[tk]["subs_used"] >= 3:
                    await update.message.reply_text(f"❌ تم رفض التبديل الرابع لكلان {clan_in_msg} (الحد الأقصى 3).")
                    return
                
                p_out, p_in = mentions[0], mentions[1] # افتراض الترتيب
                
                replaced = False
                for m in w["matches"]:
                    # محاولة استبدال اللاعب في الجدول
                    if m["p1"] == p_out:
                        m["p1"] = p_in
                        replaced = True
                    elif m["p2"] == p_out:
                        m["p2"] = p_in
                        replaced = True
                    elif m["p1"] == p_in: # العكس
                        m["p1"] = p_out # تصحيح إذا عكسهم المستخدم
                        # هنا نحتاج منطق أدق لكن سنفترض أن الأول هو الموجود في القائمة
                        pass
                
                # إذا لم يجد p_out نجرب العكس
                if not replaced:
                    for m in w["matches"]:
                         if m["p1"] == p_in:
                             m["p1"] = p_out
                             p_temp = p_in
                             p_in = p_out
                             p_out = p_temp
                             replaced = True
                         elif m["p2"] == p_in:
                             m["p2"] = p_out
                             p_temp = p_in
                             p_in = p_out
                             p_out = p_temp
                             replaced = True

                if replaced:
                    w[tk]["subs_used"] += 1
                    save_data()
                    
                    # الكليشة المطلوبة
                    sub_msg = (
                        f": #الاتـحاد_العـربي\n\n"
                        f":  Players' entry and exit substitution section : \n"
                        f"◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                        f"• تـبـديــل ✯\n\n"
                        f"• دخــول | {p_in} | ↑\n"
                        f"• خــروج | {p_out} | ↓\n"
                        f"◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                        f"{{ {u_tag} }} "
                    )
                    await update.message.reply_text(sub_msg)
                else:
                    await update.message.reply_text("❌ لم يتم العثور على اللاعب في الجدول.")
            return

        # --- تحديد الحاسم (Decider) ---
        if msg.startswith("حاسم") or "الحاسم" in msg:
            mentions = re.findall(r'(@\w+)', msg)
            if mentions:
                new_hasim = mentions[0]
                tk = None
                if w["c1"]["leader"] == u_tag: tk = "c1"
                elif w["c2"]["leader"] == u_tag: tk = "c2"
                elif is_referee: 
                    # الحكم يختار الكلان الأول افتراضياً إذا لم يحدد، أو يحتاج منطق إضافي
                    pass 
                
                if tk:
                    # القيود: 2 لغير موسى وليفاي
                    limit = 2
                    user_clean = user.username if user.username else ""
                    if user_clean in SUPER_ADMINS: limit = 99
                    
                    if w[tk]["hasim_changes"] >= limit:
                        await update.message.reply_text(f"❌ تم تجاوز حد تغيير الحاسم ({limit}).")
                        return
                    
                    w[tk]["hasim_changes"] += 1
                    save_data()
                    
                    # الكليشة المطلوبة
                    hasim_msg = (
                        f"● الـحـاسـم ℘\n"
                        f"⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n\n"
                        f"↬   ⁽  {new_hasim}  ₎\n\n"
                        f"⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n"
                        f"< {u_tag} >"
                    )
                    await update.message.reply_text(hasim_msg)
            return

        # --- إضافة النقاط (+1) ---
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"] in msg_up else ("c2" if w["c2"]["n"] in msg_up else None)
            
            if win_k and len(players) >= 2 and len(scores) >= 2:
                if not (is_referee or u_tag == w[win_k]["leader"]):
                    return

                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                winner = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": winner, "goals": max(sc1, sc2), "rec": min(sc1, sc2)})
                
                # تحديث الجدول
                for m in w["matches"]:
                    if m["p1"].lower() == u1.lower() or m["p1"].lower() == u2.lower():
                        if m["p1"].lower() == u1.lower():
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                
                save_data()
                await update.message.reply_text(f"✅ هدف لـ {w[win_k]['n']}")
                
                try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except: pass
                
                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    new_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(new_table, cid, w["mid"], disable_web_page_preview=True)
                    except: pass
                
                # --- نهاية المواجهة (4 أهداف) ---
                if w[win_k]["s"] >= 4:
                    w["active"] = False
                    
                    real_stats = w[win_k]["stats"]
                    last_scorer = real_stats[-1]["name"] if real_stats else "N/A"
                    # النجم: الأكثر تهديفاً (الأهداف - الاستقبال)
                    star = max(real_stats, key=lambda x: (x["goals"] - x["rec"]))["name"] if real_stats else "N/A"
                    
                    # حساب التاكات النهائية
                    tags_msg = "\n📊 **تقرير التاكات:**\n"
                    now = datetime.now()
                    for user_t, data in w["tags"].items():
                        count = data["count"]
                        # إذا كان هناك تاك معلق ومر عليه أكثر من 10 دقائق، نحسبه
                        if data.get("pending"):
                            p_time = datetime.strptime(data["pending_time"], "%Y-%m-%d %H:%M:%S")
                            if now - p_time > timedelta(minutes=10):
                                count += 1
                        
                        if count > 0:
                            tags_msg += f"- {user_t}: {count} تاك\n"

                    final_msg = (
                        f"🎊 انتهت المواجهة بفوز: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {last_scorer}\n"
                        f"⭐ النجم: {star}\n"
                        f"{tags_msg}"
                    )
                    await update.message.reply_text(final_msg)
                    
                    # --- الأرشفة (Auto-Archive) ---
                    archive_war_data(cid, w) # نقل للأرشيف
                    del wars[cid] # حذف من الذاكرة الحية لتسريع البوت
                    save_data() # حفظ الملف نظيفاً

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    load_data()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    
    print("✅ البوت يعمل بالنظام المطور (الأرشفة + التنسيق الصارم + الكليشات الجديدة)...")
    app.run_polling()
