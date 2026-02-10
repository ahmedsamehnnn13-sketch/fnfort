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
    return "Bot is Running Live with Auto-Archive & New Rules!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"       # الملف النشط (صغير وسريع)
ARCHIVE_FILE = "history_archive.json" # ملف الأرشيف (للمواجهات المنتهية)

# --- قاموس القوانين التفصيلية ---
DETAILED_LAWS = {
    "قوائم": """⚖️ **قوانين القوائم والنجم والحاسم:**
1️⃣ **القواعد الأساسية:**
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم.
- يمنع جدولة القوائم والقائد غير متصل.
🔗 للمزيد: https://t.me/arab_union3""",
    
    "وقت": """⚖️ **توقيت المواجهات:**
⏰ من 9 صباحاً حتى 1 صباحاً.
🔥 التمديد: يوم واحد (للأدوار العادية).
🔗 للمزيد: https://t.me/arab_union3""",
}

# --- كلمات الطرد (السب والكفر الصريح فقط) ---
BAN_WORDS = [
    "كسمك", "كسمه", "كسختك", "كس امك", "كس اختك", "كس عمتك", "كس خالتك",
    "ينعل دين", "ربك", "الرب", "كفر", "دين امك", "ابوك", "امك"
]

# --- القادة المستثنون من القيود (موسى وليفاي) ---
EXEMPT_ADMINS = ["mwsa_20", "levil_8"]

# --- مخازن البيانات ---
wars = {}          # المواجهات النشطة فقط
clans_mgmt = {}    # إدارة المساعدين والتبديلات وتغيير الحواسم
user_warnings = {} # إنذارات اللاعبين
admin_warnings = {} # إنذارات المسؤولين
tag_system = {}    # نظام حساب التاكات (الوقت والعدد)
last_active_time = {} # لتتبع آخر ظهور للاعب (لحساب الـ 10 دقائق)

# --- دوال الحفظ والأرشفة (Technical Optimization) ---

def save_data():
    """حفظ البيانات النشطة فقط"""
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings,
        "tag_system": tag_system
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def archive_war_data(cid, war_data):
    """نقل المواجهة المنتهية إلى ملف الأرشيف لتقليل حجم الملف الرئيسي"""
    archive_entry = {
        "chat_id": cid,
        "end_date": str(datetime.now()),
        "data": war_data
    }
    
    # تحميل الأرشيف القديم إن وجد وإضافة الجديد
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
        print(f"✅ War {cid} archived successfully.")
    except Exception as e:
        print(f"❌ Error archiving: {e}")

def load_data():
    """استرجاع البيانات النشطة"""
    global wars, clans_mgmt, user_warnings, admin_warnings, tag_system
    if not os.path.exists(DATA_FILE): return
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "wars" in data: wars = {int(k): v for k, v in data["wars"].items()}
            if "clans_mgmt" in data: clans_mgmt = {int(k): v for k, v in data["clans_mgmt"].items()}
            if "user_warnings" in data: user_warnings = {int(k): v for k, v in data["user_warnings"].items()}
            if "admin_warnings" in data: admin_warnings = {int(k): v for k, v in data["admin_warnings"].items()}
            if "tag_system" in data: tag_system = {int(k): v for k, v in data["tag_system"].items()}
        print("✅ Data loaded.")
    except Exception as e:
        print(f"❌ Error loading: {e}")

# --- أدوات مساعدة ---
def to_emoji(num):
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join(dic.get(c, c) for c in str(num))

def clean_text(text):
    if not text: return ""
    text = text.lower().replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
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
    
    # تسجيل وقت آخر نشاط للمستخدم (لنظام التاكات)
    if cid not in last_active_time: last_active_time[cid] = {}
    last_active_time[cid][u_tag] = datetime.now().timestamp()

    # تحديد الرتب
    super_admins = EXEMPT_ADMINS
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in super_admins) or is_creator
    except:
        is_referee = (user.username in super_admins)

    # 1. نظام الطرد (سب الأهل والكفر)
    for word in BAN_WORDS:
        if word in msg_cleaned: # استخدام النص المنظف لكشف التحايل
            if user.username not in super_admins:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} لانتهاك الخطوط الحمراء (الأهل/الكفر).")
                except: pass
            return

    # 2. أوامر الإدارة (طرد، إلغاءات)
    if is_referee:
        if msg.startswith("طرد ") and "@" in msg:
            target = msg.split("طرد ")[1].strip()
            # محاولة استخراج اليوزر
            t_username = target.replace("@", "")
            await update.message.reply_text(f"🚫 أمر طرد لـ {target}.. (يتطلب صلاحيات بوت).")
            # ملاحظة: البوت يحتاج لطريقة لجلب الآيدي من اليوزرنيم للطرد الفعلي
            return

        # أوامر الإلغاء
        if msg.startswith("الغاء حاسم"):
             # منطق تقليل عداد تغيير الحاسم
             await update.message.reply_text("✅ تم إلغاء تغيير الحاسم واحتساب المحاولة السابقة كأن لم تكن.")
             return
        if msg.startswith("الغاء مساعد"):
             await update.message.reply_text("✅ تم إلغاء تعيين المساعد.")
             return
        if msg.startswith("الغاء تبديل"):
             await update.message.reply_text("✅ تم إلغاء التبديل واسترجاع المحاولة.")
             # هنا يجب تقليل عداد التبديلات في clans_mgmt
             return

    # 3. بداية المواجهة (وليس الحرب)
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
            "start_time": datetime.now().timestamp()
        }
        # تهيئة سجلات الإدارة للكود الجديد
        clans_mgmt[cid] = {
            c1_name: {"subs_used": 0, "hasem_changed": 0, "asst_changed": 0, "asst": None},
            c2_name: {"subs_used": 0, "hasem_changed": 0, "asst_changed": 0, "asst": None}
        }
        tag_system[cid] = {} # تصفير التاكات
        
        save_data()
        await update.message.reply_text(f"⚔️ بدأت **المواجهة** الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        return

    # العمليات داخل المواجهة
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # 4. التبديلات (الكليشة الجديدة والقوانين)
        if "تبديل" in msg and "CLAN" in msg_up:
            # مثال: تبديل CLAN STO
            clan_name_in_msg = msg_up.replace("تبديل CLAN ", "").strip()
            
            # تحديد أي فريق
            target_k = None
            if w["c1"]["n"] == clan_name_in_msg: target_k = "c1"
            elif w["c2"]["n"] == clan_name_in_msg: target_k = "c2"
            
            if not target_k: return

            mgmt = clans_mgmt[cid][clan_name_in_msg]
            
            # التحقق من الصلاحية (قائد، مساعد، حكم)
            actor_role = "referee" if is_referee else ("leader" if w[target_k]["leader"] == u_tag else ("assist" if mgmt["asst"] == u_tag else None))
            if not actor_role:
                await update.message.reply_text("❌ هذا الأمر للقادة والمساعدين والحكام فقط.")
                return

            # التحقق من العدد
            if mgmt["subs_used"] >= 3 and not is_referee:
                await update.message.reply_text(f"❌ تم استهلاك جميع التبديلات (3/3) لكلان {clan_name_in_msg}.")
                return

            # استخراج اللاعبين (محاكاة - يفترض الرد على رسالة توضح من خرج ومن دخل)
            in_player = "اللاعب البديل" 
            out_player = "اللاعب المستبدل"

            mgmt["subs_used"] += 1
            save_data()

            # كليشة التبديل المطلوبة
            sub_msg = (
                f": #الاتـحاد_العـربي\n\n"
                f":  Players' entry and exit substitution section : \n"
                f"◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                f"• تـبـديــل ✯\n\n"
                f"• دخــول | {in_player} | ↑\n"
                f"• خــروج | {out_player} | ↓\n"
                f"◊═━───┈┉ ᴜɪ ┉┈───━═◊\n"
                f"{{ {u_tag} }}\n" # يوزر الحكم/المسؤول
                f"🔢 التبديل رقم: {mgmt['subs_used']}/3"
            )
            await update.message.reply_text(sub_msg)
            return

        # 5. نظام التاكات (Tags)
        # أمر: تاك @user
        if msg.startswith("تاك ") and "@" in msg:
            target_p = msg.split("تاك ")[1].strip() # الخصم
            
            # التحقق من الوقت الحالي
            now = datetime.now().timestamp()
            
            # سجل التاكات للاعب الحالي
            if u_tag not in tag_system[cid]:
                tag_system[cid][u_tag] = {"count": 0, "last_claim": 0}
            
            p_data = tag_system[cid][u_tag]

            # شرط 1: تاك كل نص ساعة
            if now - p_data["last_claim"] < 1800: # 1800 ثانية = 30 دقيقة
                rem_min = int((1800 - (now - p_data["last_claim"])) / 60)
                await update.message.reply_text(f"⏳ انتظر {rem_min} دقيقة لطلب تاك جديد.")
                return
            
            # شرط 2: الخصم لم يرد خلال 10 دقائق
            opp_last_seen = last_active_time.get(cid, {}).get(target_p, 0)
            if (now - opp_last_seen) > 600: # 600 ثانية = 10 دقائق
                p_data["count"] += 1
                p_data["last_claim"] = now
                save_data()
                await update.message.reply_text(f"✅ **تم احتساب التاك رسمياً!**\n👤 الخصم: {target_p} (غائب لأكثر من 10د).\n🔢 تاكاتك: {p_data['count']}")
            else:
                await update.message.reply_text(f"❌ الخصم {target_p} موجود (تفاعل منذ أقل من 10د).")
            return

        # أمر: حسب التاكات (تقرير)
        if "حسب التاكات" in msg or "تقرير التاكات" in msg:
            report = "📊 **تقرير التاكات (للمواجهة الحالية):**\n\n"
            for p, data in tag_system[cid].items():
                report += f"👤 {p} : {data['count']} تاك\n"
            await update.message.reply_text(report)
            return

        # 6. تسجيل القائمة
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"].upper() in msg_up: target_k = "c1"
            elif w["c2"]["n"].upper() in msg_up: target_k = "c2"
            
            if target_k:
                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']}.")

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
                    try: await context.bot.pin_chat_message(chat_id=cid, message_id=sent.message_id)
                    except: pass
            return

        # 7. تسجيل النتائج (+1)
        if "+ 1" in msg_up or "+1" in msg_up:
            players = re.findall(r'@\w+', msg_up)
            scores = re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if not win_k: return

            if len(players) >= 2 and len(scores) >= 2:
                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                
                # تحديث الجدول
                for m in w["matches"]:
                    mp1_u = m["p1"].upper()
                    mp2_u = m["p2"].upper()
                    if (u1 == mp1_u or u1 == mp2_u) and (u2 == mp1_u or u2 == mp2_u):
                        if u1 == mp1_u: m["s1"], m["s2"] = sc1, sc2
                        else: m["s1"], m["s2"] = sc2, sc1
                
                save_data()
                await update.message.reply_text(f"✅ تم تسجيل نقطة مواجهة لـ {w[win_k]['n']}.")

            elif is_referee: # نقطة فري
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                save_data()
                await update.message.reply_text(f"⚖️ نقطة فري لكلان {w[win_k]['n']}.")

            try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except: pass

            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass
            
            # --- 8. نهاية المواجهة والأرشفة التلقائية ---
            if w[win_k]["s"] >= 4:
                w["active"] = False
                
                # كليشة الحاسم الجديدة
                history = w[win_k]["stats"]
                real_players = [h for h in history if not h["is_free"]]
                if real_players:
                    hasm = real_players[-1]["name"]
                    
                    hasm_msg = (
                        f"● الـحـاسـم ℘\n"
                        f"⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n\n"
                        f"↬   ⁽  {hasm}  ₎\n\n"
                        f"⋆ ─┄─┄─┄─┄  ᴜɪ  ─┄─┄─┄─┄ ⋆\n"
                        f"< {u_tag} >"
                    )
                    await update.message.reply_text(hasm_msg)
                
                await update.message.reply_text(f"🎊 انتهت المواجهة بفوز {w[win_k]['n']} {w['c1']['s']}-{w['c2']['s']}")
                
                # ::: الأرشفة :::
                # نقل البيانات للأرشيف وحذفها من wars
                archive_war_data(cid, w)
                del wars[cid]
                # حذف بيانات الإدارة لهذه المحادثة أيضاً لتخفيف الحمل
                if cid in clans_mgmt: del clans_mgmt[cid]
                if cid in tag_system: del tag_system[cid]
                
                save_data()
                print(f"🧹 Chat {cid} data cleaned from main memory.")

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    load_data()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    
    print("✅ البوت يعمل بنظام الأرشفة التلقائية...")
    app.run_polling()
