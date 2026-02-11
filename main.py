import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask 

# --- إعدادات Flask لضمان استمرارية البوت ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running Live & Optimized (Auto-Archive Enabled)!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"

# ملفات البيانات
DATA_FILE = "bot_data.json"       # للمواجهات الحالية فقط
ARCHIVE_FILE = "wars_archive.json" # للأرشيف (تخزين طويل الأمد)

# السوبر أدمن (استثناء من الحدود)
SUPER_ADMINS_IDS = ["mwsa_20", "levil_8"] 

# --- قاموس القوانين (محدث) ---
DETAILED_LAWS = {
    "قوائم": """⚖️ **قوانين القوائم والنجم والحاسم:**
1️⃣ **القواعد الأساسية:**
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم.
- يمنع جدولة القوائم.
- المنشن للحكم إلزامي عند إرسال القائمة.

2️⃣ **التوقيت:**
- نصف النهائي/النهائي: 18 ساعة.
- باقي الأدوار: 14 ساعة.
🔗 للمزيد: https://t.me/arab_union3""",
    
    "تاكات": """⚖️ **نظام التاكات:**
- يحتسب التاك رسمياً إذا لم يرد الخصم خلال 10 دقائق.
- يحق لك تاك واحد كل 30 دقيقة.
- يبدأ احتساب التاكات بعد نزول الجدول (القرعة).
- يتم جمع التاكات تلقائياً عند طلبها أو نهاية المواجهة.""",
}

# --- كلمات الطرد (تحديث شامل: إزالة "شرفك" وإضافة الشتائم الصريحة) ---
BAN_WORDS = [
    "كسمك", "كسختك", "كسم", "كس اختك", 
    "خالتك", "عمتك", "امك", "أختك", "اختك",
    "ينعل دين", "ربك", "الله", "رسول", 
    "كس امك", "يا ابن القحبة", "يا ابن المتناكة", "زبي", "شرموطة"
]

# --- هياكل البيانات ---
wars = {}          
clans_mgmt = {}    
user_warnings = {} 
admin_warnings = {} 

# --- دوال الحفظ والأرشفة (Optimized) ---
def save_data():
    """حفظ البيانات النشطة فقط"""
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=str)
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def archive_war_data(chat_id, war_data):
    """نقل المواجهة المنتهية للأرشيف وحذفها من الملف الرئيسي"""
    archive_entry = {
        "chat_id": chat_id,
        "archived_at": str(datetime.now()),
        "final_score": f"{war_data['c1']['n']} {war_data['c1']['s']} - {war_data['c2']['s']} {war_data['c2']['n']}",
        "data": war_data
    }
    
    current_archive = []
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                current_archive = json.load(f)
        except: pass
    
    current_archive.append(archive_entry)
    
    try:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_archive, f, ensure_ascii=False, indent=4)
        print(f"✅ War archived for Chat ID: {chat_id}")
    except Exception as e:
        print(f"❌ Error archiving: {e}")

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
    except Exception as e: print(f"❌ Error loading data: {e}")

# --- أدوات مساعدة ---
def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join([dic.get(char, char) for char in str(num)])

def clean_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return text

# 🔥 دالة التحقق من UI (بأي زخرفة في العالم) 🔥
def has_ui_decoration(text):
    if not text: return False
    # Regex يبحث عن حرف U بأشكاله المختلفة يليه حرف I بأشكاله المختلفة
    # uUᴜ𝒰𝐔𝑼𝗨𝚊𝔘𝖴 : أشكال U
    # iIɪ𝒤𝐈𝑰𝗜𝚰ℑ𝖨 : أشكال I
    # [\s\.\-_~]* : مسافات أو رموز بين الحرفين مسموحة (مثل U.I)
    pattern = r'[uUúùûüūůűŭųᴜ𝒰𝐔𝑼𝗨𝚊𝔘𝖴][\s\.\-_~]*[iIíìîïīįıɪ𝒤𝐈𝑰𝗜𝚰ℑ𝖨]'
    return re.search(pattern, text, re.IGNORECASE) is not None

# --- المعالج الرئيسي ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    cid = update.effective_chat.id
    msg = update.message.text
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # تحديد الرتب
    is_super = user.username in SUPER_ADMINS_IDS
    try:
        cm = await context.bot.get_chat_member(cid, user.id)
        is_creator = (cm.status == 'creator')
        is_referee = is_super or is_creator
        is_admin = cm.status in ['creator', 'administrator']
    except:
        is_referee = is_super
        is_admin = False

    # 1️⃣ **التحقق من التوحيد (UI)**
    # استثناء الحكام والبوتات
    if not is_admin:
        full_name = (user.first_name + " " + (user.last_name or ""))
        if not has_ui_decoration(full_name):
            try:
                await update.message.delete()
                alert = await update.message.reply_text(
                    f"🚫 {u_tag}\n⚠️ **يجب وضع شعار التوحيد (UI) بجانب اسمك للمشاركة.**"
                )
                await asyncio.sleep(5)
                try: await alert.delete()
                except: pass
            except: pass
            return

    # 2️⃣ **نظام الطرد (الشتائم)**
    for word in BAN_WORDS:
        if word in msg.lower():
            if not is_super:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} (مخالفة الأخلاق/الدين).")
                except: pass
            return

    # 3️⃣ **بدء المواجهة (رسالة منفصلة حصراً)**
    # Regex strict for "CLAN x VS CLAN y" only
    if re.fullmatch(r'CLAN\s+.+\s+VS\s+CLAN\s+.+', msg_up, re.IGNORECASE):
        parts = msg_up.split(" VS ")
        c1_name = parts[0].replace("CLAN ", "").strip()
        c2_name = parts[1].replace("CLAN ", "").strip()
        
        wars[cid] = {
            "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None, "subs": 0},
            "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None, "subs": 0},
            "active": True,
            "mid": None,
            "matches": [], # قائمة المباريات
            "match_map": {}, # خريطة: من يلعب ضد من {player_id: opponent_id}
            "tags_data": {}, # {user_id: {'count': 0, 'last_tag': time, 'pending': time}}
            "start_time": datetime.now(),
            "changes": {"hasm": {}, "admin": {}, "asst": {}} # تتبع تغييرات الأشخاص
        }
        save_data()
        await update.message.reply_text(f"⚔️ بدأت المواجهة الرسمية:\n🔥 {c1_name} 0 - 0 {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        return

    # --- عمليات داخل المواجهة ---
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]
        
        # 4️⃣ **نظام التبديل (محدود بـ 3 وكليشة خاصة)**
        if msg_cleaned.startswith("تبديل ") and "clan" in msg_cleaned:
            target_clan = msg_up.replace("تبديل ", "").replace("CLAN ", "").strip()
            
            # تحديد الكلان
            tk = None
            if w["c1"]["n"] == target_clan: tk = "c1"
            elif w["c2"]["n"] == target_clan: tk = "c2"
            
            if tk:
                # تحقق الصلاحية
                if not (is_referee or w[tk]["leader"] == u_tag):
                    await update.message.reply_text("❌ للقادة والحكام فقط.")
                    return
                
                # تحقق العدد (3)
                if w[tk]["subs"] >= 3:
                    await update.message.reply_text(f"❌ استنفذ كلان {target_clan} تبديلاته (3/3).")
                    return
                
                w[tk]["subs"] += 1
                save_data()
                
                # الكليشة المطلوبة
                sub_txt = (
                    ": #الاتـحاد_العـربي\n\n"
                    ":  Players' entry and exit substitution section : \n"
                    "◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                    "• تـبـديــل ✯\n\n"
                    "• دخــول | @ | ↑\n"
                    "• خــروج | @ | ↓\n"
                    "◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                    f"{{ {u_tag} }}\n"
                    f"🔢 التبديل: {w[tk]['subs']}/3"
                )
                await update.message.reply_text(sub_txt)
            return

        # 5️⃣ **نظام الحاسم والمسؤول (الحدود)**
        # مثال: تغيير حاسم
        if "تغيير حاسم" in msg_cleaned:
            # تحقق من قام بالتغيير سابقاً (Logic implementation depending on user tracking)
            # هنا سنضع الكليشة المطلوبة عند كتابة "حاسم"
            pass

        if msg_cleaned == "حاسم":
            hasm_txt = (
                "● الـحـاسـم ℘\n"
                "⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n\n"
                "↬   ⁽  @user  ₎\n\n"
                "⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n"
                f"< {u_tag} >"
            )
            await update.message.reply_text(hasm_txt)
            return

        # 6️⃣ **القوائم والجدول (بداية التاكات)**
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"] in msg_up: target_k = "c1"
            elif w["c2"]["n"] in msg_up: target_k = "c2"
            
            if target_k:
                w[target_k]["leader"] = u_tag
                raw_players = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                w[target_k]["p"] = raw_players
                save_data()
                await update.message.reply_text(f"✅ تم تسجيل قائمة {w[target_k]['n']}.")

                # إذا اكتمل الكلانين -> قرعة
                if w["c1"]["p"] and w["c2"]["p"]:
                    p1 = list(w["c1"]["p"])
                    p2 = list(w["c2"]["p"])
                    random.shuffle(p1)
                    random.shuffle(p2)
                    
                    # إنشاء الجدول وتخزين خصوم
                    w["matches"] = []
                    w["match_map"] = {} # لتحديد الخصم بسرعة
                    
                    rows = []
                    for i, (u1, u2) in enumerate(zip(p1, p2)):
                        w["matches"].append({"p1": u1, "p2": u2, "s1": 0, "s2": 0})
                        # تخزين الخصم (الاسم فقط للتسهيل)
                        w["match_map"][u1.upper()] = u2.upper()
                        w["match_map"][u2.upper()] = u1.upper()
                        rows.append(f"{i+1} | {u1} {to_emoji(0)}|🆚|{to_emoji(0)} {u2} |")
                    
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ بدأت التاكات الآن\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    try: await context.bot.pin_chat_message(cid, sent.message_id)
                    except: pass
                    save_data()
            return

        # 7️⃣ **نظام التاكات (ذكي)**
        # يعمل فقط اذا نزلت القرعة (match_map ممتلئة)
        if w.get("match_map"):
            sender_name = f"@{user.username}".upper() if user.username else ""
            
            # أ) الرد على التاك (إلغاء المؤقت)
            if sender_name in w["match_map"]: # المرسل لاعب في الحرب
                opponent = w["match_map"][sender_name]
                # هل الخصم كان عامل لي تاك معلق؟
                if opponent in w["tags_data"]:
                    t_data = w["tags_data"][opponent]
                    if t_data.get("pending_target") == sender_name:
                        # الرد تم، إلغاء المعلق
                        del w["tags_data"][opponent]["pending_target"]
                        del w["tags_data"][opponent]["pending_time"]
                        # لا نرسل رسالة إزعاج، فقط نلغي بصمت

            # ب) إنشاء تاك جديد
            if update.message.reply_to_message: # يجب أن يكون رد
                target_u = update.message.reply_to_message.from_user
                target_name = f"@{target_u.username}".upper() if target_u.username else ""
                
                # هل هو خصمي؟
                if sender_name in w["match_map"] and w["match_map"][sender_name] == target_name:
                    now = datetime.now()
                    
                    # تهيئة البيانات
                    if sender_name not in w["tags_data"]: 
                        w["tags_data"][sender_name] = {"count": 0, "last_tag": None}
                    
                    user_tag_data = w["tags_data"][sender_name]

                    # 1. فحص التاكات المعلقة السابقة وتحويلها لرسمية اذا انتهى وقتها
                    if "pending_time" in user_tag_data:
                        start_t = datetime.fromisoformat(str(user_tag_data["pending_time"]))
                        if (now - start_t) > timedelta(minutes=10):
                            user_tag_data["count"] += 1
                            del user_tag_data["pending_target"]
                            del user_tag_data["pending_time"]
                            # تم احتساب السابق
                    
                    # 2. فحص الكولدوان (30 دقيقة)
                    can_tag = True
                    if user_tag_data["last_tag"]:
                        last_t = datetime.fromisoformat(str(user_tag_data["last_tag"]))
                        if (now - last_t) < timedelta(minutes=30):
                            can_tag = False
                            rem = 30 - int((now - last_t).seconds / 60)
                            await update.message.reply_text(f"⏳ انتظر {rem} دقيقة لعمل تاك جديد.")
                    
                    # 3. إنشاء التاك
                    if can_tag:
                        user_tag_data["pending_target"] = target_name
                        user_tag_data["pending_time"] = str(now)
                        user_tag_data["last_tag"] = str(now)
                        save_data()
                        await update.message.reply_text(f"⏱️ بدء احتساب التاك على {target_name}.\nإذا لم يرد خلال 10 دقائق سيتم احتسابه.")

        # تقرير التاكات
        if "تاكات" in msg_cleaned:
            report = "📊 **تقرير التاكات:**\n"
            for p, d in w.get("tags_data", {}).items():
                # تحديث المعلق قبل العرض
                count = d["count"]
                if "pending_time" in d:
                    start_t = datetime.fromisoformat(str(d["pending_time"]))
                    if (datetime.now() - start_t) > timedelta(minutes=10):
                        count += 1
                if count > 0:
                    report += f"👤 {p}: {count}\n"
            await update.message.reply_text(report or "لا توجد تاكات محسوبة حتى الآن.")

        # 8️⃣ **تسجيل النتائج والأرشفة**
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"] in msg_up else ("c2" if w["c2"]["n"] in msg_up else None)
            
            if win_k and len(players) >= 2:
                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": u1, "goals": max(sc1,sc2), "rec": min(sc1,sc2)})
                
                # تحديث الجدول
                for m in w["matches"]:
                    if u1.upper() in [m["p1"].upper(), m["p2"].upper()]:
                        if u1.upper() == m["p1"].upper(): m["s1"], m["s2"] = sc1, sc2
                        else: m["s1"], m["s2"] = sc2, sc1

                save_data()
                await update.message.reply_text(f"✅ هدف لـ {w[win_k]['n']}.")

                # تحديث الرسالة
                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    new_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(new_table, cid, w["mid"], disable_web_page_preview=True)
                    except: pass

                # 🔥 إنهاء وأرشفة (4-0 أو 4-3) 🔥
                if w["c1"]["s"] >= 4 or w["c2"]["s"] >= 4:
                    winner = w["c1"]["n"] if w["c1"]["s"] >= 4 else w["c2"]["n"]
                    await update.message.reply_text(f"🏁 انتهت المواجهة بفوز {winner}!\n📤 جاري نقل البيانات للأرشيف...")
                    
                    archive_war_data(cid, w)
                    del wars[cid]
                    save_data()

# --- التشغيل ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    load_data()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    print("✅ Bot Started with Auto-Archive, Smart UI Regex, and Tag System.")
    app.run_polling()
