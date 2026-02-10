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
    return "Bot is Running Live (Optimized Version)!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"       # الملف الحي (السريع)
ARCHIVE_FILE = "wars_archive.json" # ملف الأرشيف (الضخم)

# --- القادة المستثنون من القيود (موسى وليفاي) ---
SUPER_ADMINS = ["mwsa_20", "levil_8"]

# --- قاموس القوانين التفصيلية (تم اختصاره للتركيز على الكود التقني) ---
DETAILED_LAWS = {
    "قوائم": "⚖️ **قوانين القوائم:**\n- نصف النهائي/النهائي: 18 ساعة.\n- باقي الأدوار: 14 ساعة.\n🔗 للمزيد: " + AU_LINK,
    "سكربت": "⚖️ **قوانين السكربت:**\n- طاقات 92 أو أقل = سكربت.\n🔗 للمزيد: " + AU_LINK,
    "وقت": "⚖️ **توقيت المواجهات:**\n- الرسمي: 9 م - 1 ص.\n🔗 للمزيد: " + AU_LINK,
    "تواجد": "⚖️ **الغياب:**\n- غياب 20 ساعة = تبديل.\n🔗 للمزيد: " + AU_LINK,
    "تصوير": "⚖️ **التصوير:**\n- بداية المباراة فقط (فيديو + سيريال).\n🔗 للمزيد: " + AU_LINK,
    "انسحاب": "⚖️ **الانسحاب:**\n- خروج بدون دليل = هدف.\n🔗 للمزيد: " + AU_LINK,
    "سب": "⚖️ **السب:**\n- سب الأهل/الكفر = طرد وحظر.\n🔗 للمزيد: " + AU_LINK,
    "فار": "⚖️ **VAR:**\n- مرة واحدة في الأدوار الإقصائية.\n🔗 للمزيد: " + AU_LINK,
    "انتقالات": "⚖️ **الانتقالات:**\n- الخميس والجمعة فقط.\n🔗 للمزيد: " + AU_LINK,
    "عقود": "⚖️ **العقود:**\n- حد أقصى 8 قادة.\n🔗 للمزيد: " + AU_LINK
}

# كلمات الطرد (السب والكفر) - قائمة صارمة جداً
BAN_WORDS = ["كسمك", "كسختك", "خالتك", "عمتك", "امك", "اختك", "دين", "رب", "كفر", "الله"] 
# تم إزالة "شرفك" و"عرضك" وإبقاء سب الأهل المباشر والكفر

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
# original_msg_store لا يحفظ في الملف لتوفير المساحة

# --- دوال الحفظ والأرشفة (Technical Optimization) ---
def save_data():
    """حفظ البيانات الحية فقط (بدون الأرشيف) لسرعة الأداء"""
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
    """نقل بيانات الحرب المنتهية إلى ملف الأرشيف لتقليل حجم الملف الرئيسي"""
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
        print(f"✅ War archived for chat {chat_id}")
    except Exception as e:
        print(f"❌ Archive Error: {e}")

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

# --- المعالج الرئيسي للمواجهة ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    cid = update.effective_chat.id
    msg = update.message.text
    msg_up = msg.upper().strip() # لا نستخدم clean_text هنا للحفاظ على التنسيق
    user = update.effective_user
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"
    
    # 1️⃣ --- نظام التوحيد (UI Check) ---
    # يجب أن يكون الاسم يحتوي على UI لكي يرسل، وإلا يحذف ويحذر
    # نستثني الحكم والإدارة والبوت
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_admin_or_creator = chat_member.status in ['creator', 'administrator']
    except: is_admin_or_creator = False

    is_super = user.username in SUPER_ADMINS
    
    if not is_super and not is_admin_or_creator:
        full_name = user.full_name
        if "UI" not in full_name and "ui" not in full_name and "Ui" not in full_name:
            try:
                await update.message.delete()
                warning_msg = await update.message.reply_text(f"⚠️ {u_tag} **يجب وضع شعار التوحيد (UI) بجانب اسمك لإرسال الرسائل!**")
                # حذف التحذير بعد 5 ثواني لعدم تعبئة الشات
                await asyncio.sleep(5)
                await context.bot.delete_message(chat_id=cid, message_id=warning_msg.message_id)
            except: pass
            return # توقف هنا، لا تكمل المعالجة

    # 2️⃣ --- نظام الطرد الآلي (السب والكفر) ---
    for word in BAN_WORDS:
        if word in msg.lower(): # فحص دقيق
            if not is_super:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} لانتهاك القوانين (سب الأهل/الكفر).")
                except: pass
            return

    # 3️⃣ --- أوامر الحكم والإدارة ---
    is_referee = is_super or is_admin_or_creator
    
    # الرد على القوانين
    if f"@{context.bot.username}" in msg or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
        cleaned = clean_text(msg)
        for k, v in DETAILED_LAWS.items():
            if k in cleaned:
                await update.message.reply_text(v, disable_web_page_preview=True)
                return

    # طرد لاعب بأمر مباشر
    if msg.startswith("طرد لاعب") and is_referee:
        target_username = None
        if update.message.reply_to_message:
            target_username = update.message.reply_to_message.from_user.id
        else:
             mentions = update.message.parse_entities(["mention", "text_mention"])
             # منطق بسيط لاستخراج اليوزر
             match = re.search(r'@(\w+)', msg)
             if match:
                 # نحتاج لتحويل اليوزر نيم لآيدي وهذا صعب بدون تخزين، لذا سنعتمد الرد
                 await update.message.reply_text("⚠️ لطرد اللاعب، قم بالرد على رسالته بـ 'طرد لاعب'.")
                 return
        
        if target_username:
            try:
                await context.bot.ban_chat_member(cid, target_username)
                await update.message.reply_text("✅ تم الطرد بنجاح.")
            except Exception as e:
                await update.message.reply_text(f"❌ لم أتمكن من الطرد: {e}")
        return

    # 4️⃣ --- بداية المواجهة (Strict Format) ---
    # يجب أن تكون الرسالة: CLAN X VS CLAN Y فقط
    if re.match(r'^CLAN\s+.+\s+VS\s+CLAN\s+.+$', msg_up, re.IGNORECASE):
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
            "tags": {} # لتخزين التاكات {player_tag: {last_tag_time: datetime, count: int, pending: bool}}
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
        # 1. إذا رد الخصم، نلغي التاك المعلق
        # 2. إذا مر 10 دقائق دون رد (يحسب عند الطلب أو نهاية الحرب)
        sender_clean = u_tag
        
        # منطق التاك: هل هذه الرسالة رد على تاك؟
        if update.message.reply_to_message:
            replied_to_user = f"@{update.message.reply_to_message.from_user.username}"
            if replied_to_user in w["tags"] and w["tags"][replied_to_user].get("pending_opponent") == sender_clean:
                # الخصم رد! الغاء التاك
                w["tags"][replied_to_user]["pending"] = False
                w["tags"][replied_to_user]["pending_time"] = None
                w["tags"][replied_to_user]["pending_opponent"] = None
                save_data()
        
        # هل الرسالة تحتوي على تاك جديد؟
        tag_match = re.findall(r'(@\w+)', msg)
        if tag_match:
            target = tag_match[0] # أول منشن فقط
            # شروط: مرة كل 30 دقيقة
            now = datetime.now()
            user_tag_data = w["tags"].get(sender_clean, {"count": 0, "last_valid": None})
            
            last_time = user_tag_data.get("last_valid")
            if last_time:
                last_time_dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                if now - last_time_dt < timedelta(minutes=30):
                    pass # لم تمر 30 دقيقة، تجاهل
                else:
                    # تاك جديد صالح مبدئياً
                    user_tag_data["last_valid"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    user_tag_data["pending"] = True
                    user_tag_data["pending_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    user_tag_data["pending_opponent"] = target # من يجب أن يرد
                    w["tags"][sender_clean] = user_tag_data
                    save_data()
            else:
                # أول تاك
                user_tag_data["last_valid"] = now.strftime("%Y-%m-%d %H:%M:%S")
                user_tag_data["pending"] = True
                user_tag_data["pending_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                user_tag_data["pending_opponent"] = target
                w["tags"][sender_clean] = user_tag_data
                save_data()

        # --- تسجيل القائمة (للكلانات) ---
        if "قائم" in msg and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"] in msg_up: target_k = "c1"
            elif w["c2"]["n"] in msg_up: target_k = "c2"
            
            if target_k:
                # التحقق من الصلاحية (الحكم أو صاحب الكلان فقط)
                if not is_referee and w[target_k]["leader"] != u_tag and w[target_k]["leader"] is not None:
                     return # ليس القائد ولا الحكم
                
                # أول مرة يعين كقائد إذا لم يكن هناك قائد
                if w[target_k]["leader"] is None: w[target_k]["leader"] = u_tag

                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']}")

                # نزول الجدول عند اكتمال القائمتين
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
        # الأمر: تبديل CLAN @OUT @IN
        if msg.startswith("تبديل"):
            parts = msg.split()
            # المتوقع: تبديل [اسم_الكلان] [خروج] [دخول] (الترتيب في الرسالة قد يختلف حسب المستخدم، سنبحث عن المنشن واسم الكلان)
            clan_in_msg = next((name for name in [w["c1"]["n"], w["c2"]["n"]] if name in msg_up), None)
            mentions = re.findall(r'(@\w+)', msg)
            
            if clan_in_msg and len(mentions) >= 2:
                tk = "c1" if w["c1"]["n"] == clan_in_msg else "c2"
                
                # التحقق من العدد (3 تبديلات)
                if w[tk]["subs_used"] >= 3:
                    await update.message.reply_text(f"❌ استنفذ كلان {clan_in_msg} جميع التبديلات (3/3).")
                    return
                
                # التحقق من الصلاحية (حكم أو قائد)
                if not is_referee and w[tk]["leader"] != u_tag:
                     return

                p_out, p_in = mentions[0], mentions[1] # نفترض الأول خروج والثاني دخول أو العكس، سنبحث في matches
                
                # البحث عن اللاعب في الجدول لاستبداله
                replaced = False
                for m in w["matches"]:
                    if m["p1"] == p_out:
                        m["p1"] = p_in
                        replaced = True
                    elif m["p2"] == p_out:
                        m["p2"] = p_in
                        replaced = True
                    # دعم العكس (لو كتب الدخول ثم الخروج)
                    elif m["p1"] == p_in: # خطأ المستخدم عكسهم
                        pass 
                
                if replaced:
                    w[tk]["subs_used"] += 1
                    save_data()
                    
                    # كليشة التبديل الجديدة
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
                    await update.message.reply_text("❌ اللاعب المراد إخراجه غير موجود في الجدول.")
            return

        # --- تحديد الحاسم (Decider) ---
        # الأمر: حاسم @user
        if msg.startswith("حاسم") or "الحاسم" in msg:
            mentions = re.findall(r'(@\w+)', msg)
            if mentions:
                new_hasim = mentions[0]
                # تحديد الكلان التابع له الحاسم (يجب أن يكون في القائمة أو يحدده القائد)
                # للتبسيط سنفترض أن القائد يحدد حاسم كلانه
                tk = None
                if w["c1"]["leader"] == u_tag: tk = "c1"
                elif w["c2"]["leader"] == u_tag: tk = "c2"
                elif is_referee: 
                    # الحكم يجب أن يحدد الكلان في الرسالة أو نعتمد سياق
                    pass 
                
                if tk:
                    # تحقق من عدد المرات (2) إلا لموسى وليفاي
                    limit = 2
                    if u_tag.replace("@", "") in SUPER_ADMINS: limit = 99
                    
                    if w[tk]["hasim_changes"] >= limit:
                        await update.message.reply_text(f"❌ تم تغيير الحاسم الحد الأقصى ({limit}) مرات.")
                        return
                    
                    w[tk]["hasim_changes"] += 1
                    w[tk]["current_hasim"] = new_hasim
                    save_data()
                    
                    # كليشة الحاسم الجديدة
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
                # التحقق من هوية المسجل (حكم أو قائد)
                if not (is_referee or u_tag == w[win_k]["leader"]):
                    return

                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                winner = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": winner, "goals": max(sc1, sc2), "rec": min(sc1, sc2)})
                
                # تحديث الجدول
                for m in w["matches"]:
                    # مقارنة case-insensitive
                    if m["p1"].lower() == u1.lower() or m["p1"].lower() == u2.lower():
                        if m["p1"].lower() == u1.lower():
                            m["s1"], m["s2"] = sc1, sc2
                        else:
                            m["s1"], m["s2"] = sc2, sc1
                
                save_data()
                await update.message.reply_text(f"✅ هدف لـ {w[win_k]['n']}")
                
                # تحديث عنوان الشات والجدول
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
                    
                    # حساب الحاسم والنجم
                    real_stats = w[win_k]["stats"]
                    last_scorer = real_stats[-1]["name"] if real_stats else "N/A"
                    # النجم: الأكثر تهديفاً والأقل استقبالاً
                    star = max(real_stats, key=lambda x: (x["goals"] - x["rec"]))["name"] if real_stats else "N/A"
                    
                    # حساب التاكات النهائية
                    tags_msg = "\n📊 **تقرير التاكات:**\n"
                    now = datetime.now()
                    for user_t, data in w["tags"].items():
                        count = data["count"]
                        # التحقق من آخر تاك معلق
                        if data.get("pending"):
                            pending_time = datetime.strptime(data["pending_time"], "%Y-%m-%d %H:%M:%S")
                            if now - pending_time > timedelta(minutes=10):
                                count += 1 # احتساب التاك المعلق
                        if count > 0:
                            tags_msg += f"- {user_t}: {count} تاك\n"

                    final_msg = (
                        f"🎊 انتهت المواجهة بفوز: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {last_scorer}\n"
                        f"⭐ النجم: {star}\n"
                        f"{tags_msg}"
                    )
                    await update.message.reply_text(final_msg)
                    
                    # --- الأرشفة (The Critical Step) ---
                    archive_war_data(cid, w) # نقل للأرشيف
                    del wars[cid] # حذف من الذاكرة الحية
                    save_data() # حفظ الملف نظيفاً

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    load_data()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    
    print("✅ البوت يعمل بالنظام المطور (أرشفة + توحيد UI)...")
    app.run_polling()
