import random
import re
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
JUDGES_GROUP_ID = -1003481668972 # ⚠️ ضع هنا آيدي كروب الحكام للاعتراضات

# --- قاموس القوانين التفصيلية ---
DETAILED_LAWS = {
    "قوائم": """⚖️ قوانين القوائم والنجم والحاسم:
1️⃣ القواعد الأساسية:
- أي فوز قوائم يمنع كتابة النجم والحاسم.
- النجم والحاسم يحددان من الحكم (الأهداف، التأثير، السلوك).
- يمنع جدولة القوائم (إرسالها والقائد غير متصل أو آخر دقيقة بدون قراءة).
- المنشن للحكم إلزامي عند إرسال القائمة، بدونه تعتبر لاغية (مدة الاعتراض 10 ساعات).

2️⃣ التوقيت:
- نصف النهائي/النهائي: 18 ساعة (+15د سماح).
- باقي الأدوار: 14 ساعة (+15د سماح).
🔗 للمزيد: https://t.me/arab_union3""",

    "سكربت": """⚖️ قوانين السكربت:
⬆️ طاقات 92 أو أقل = سكربت (حتى لو ميسي).
⬆️ طاقات أعلى من 92 = ليس سكربت (باستثناء بدون وجه).
⬆️ الاعتراض في بداية المباراة فقط (الخروج فوراً مع دليل).
⬆️ في المنتصف: تغيير التشكيلة أو المدرب لا يعتبر سكربت.
🔗 للمزيد: https://t.me/arab_union3""",

    "وقت": """⚖️ توقيت المواجهات والتمديد:
⏰ الوقت الرسمي: من 9 صباحاً حتى 1 صباحاً.
🚫 لا يجبر الخصم على اللعب في وقت غير رسمي (2-8 صباحاً).

🔥 التمديد:
- يوم واحد (للأدوار العادية)، يومين (نصف/نهائي).
- يمدد تلقائياً إذا: (حاسمة، اتفاق طرفين، شروط التمديد المنطبقة).
🔗 للمزيد: https://t.me/arab_union3""",

    "تواجد": """⚖️ قوانين التواجد والغياب:
🤔 غياب 20 ساعة بدون اتفاق = تبديل مباشر.
🤔 غياب الطرفين = يتم تبديل الطرف الأقل محاولة للاتفاق.
🤔 وضع تفاعل (Reaction) على الموعد يعتبر اتفاقاً.
🤔 الرد خلال 10 دقائق بدون تحديد موعد يعتبر تهرباً (يستوجب التبديل).
🔗 للمزيد: https://t.me/arab_union3""",

    "تصوير": """⚖️ قوانين التصوير (محدث):
1- وقت التصوير في البداية فقط.
2- الآيفون: فيديو (روم المحادثة + الرقم التسلسلي من "حول الهاتف").
3- يمنع التصوير نهاية المباراة لتجنب الغش.
4- إرسال التصوير متاح في أي وقت (بداية أو نهاية).
🔗 للمزيد: https://t.me/arab_union3""",

    "انسحاب": """⚖️ قوانين الانسحاب والخروج:
🤔 خروج الخاسر بدون دليل + اختفاء ساعتين = هدف مباشر.
🤔 خروج متعمد (اعتراف) = هدف مباشر.
🤔 سوء نت: فيديو 30 ثانية يوضح اللاق والإشعارات.
🤔 الخروج بدون فسخ عقد = حظر بمدة العقد المتبقية.
🔗 للمزيد: https://t.me/arab_union3""",

    "سب": """⚖️ قوانين السب والإساءة:
🚫 سب الأهل/الكفر = طرد وحظر (يمكن تقليله بالتنازل).
🚫 السب في الخاص (أثناء المواجهة) = تبديل + حظر (يتطلب دليل فيديو لليوزر).
🚫 استفزاز الخصم أو الحكم = عقوبة تقديرية (تبديل/حظر).
🔗 للمزيد: https://t.me/arab_union3""",

    "فار": """⚖️ قوانين الـ VAR:
✅ يحق طلب الـ VAR مرة واحدة فقط في (نصف النهائي، ربع النهائي، دور 16).
✅ الاعتماد الأساسي على حكم المباراة.
🔗 للمزيد: https://t.me/arab_union3""",

    "انتقالات": """⚖️ قوانين الانتقالات:
📺 مسموحة فقط يومي (الخميس والجمعة).
🤔 أي انتقال في يوم آخر يعتبر غير رسمي ويتم تبديل اللاعب.
🤔 اللاعب الحر (بدون عقد) يمكنه الانتقال في أي وقت.
🔗 للمزيد: https://t.me/arab_union3""",
    
    "عقود": """⚖️ قوانين العقود:
🤔 أقصى حد للمسؤولين في العقود: 8 قادة.
🤔 القائد الـ 9 يعتبر وهمي ويطرد.
🤔 فسخ العقد حصراً من القادة المسجلين.
🤔 الاعتراض على العقد بعد المباراة: الخيار للخصم (سحب نقطة أو استكمال).
🔗 للمزيد: https://t.me/arab_union3"""
}

# كلمات الطرد (السب والكفر) وكلمات الاستفزاز (الذكاء الاصطناعي)
BAN_WORDS = ["كسمك", "كسمه", "كسختك"]
PROVOCATION_WORDS = ["فاشل", "نوب", "خايف", "هربان", "دعستك", "ورع", "طقع"]

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {} # لا يتم حفظ هذا في الملف لتقليل الحجم
tag_timers = {} # حفظ مؤقت للتاكات لمعرفة من رد ومن لم يرد

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

# --- مهام الخلفية (التاكات والـ 3 أيام) ---
async def check_tag_response(chat_id, tagger, target, message_id, context):
    await asyncio.sleep(600) # 10 دقائق
    if chat_id in tag_timers and target in tag_timers[chat_id]:
        if not tag_timers[chat_id][target]["responded"]:
            # لم يرد، احتساب تاك رسمي
            w = wars.get(chat_id)
            if w and w.get("active") and not w.get("hasm_mode"):
                w.setdefault("tags_scores", {})
                w["tags_scores"][tagger] = w["tags_scores"].get(tagger, 0) + 1
                save_data()
                await context.bot.send_message(chat_id, f"⏰ مرت 10 دقائق ولم يرد {target}.\n✅ تم احتساب تاك رسمي لصالح {tagger}.")
        # تنظيف
        if target in tag_timers.get(chat_id, {}):
            del tag_timers[chat_id][target]

async def three_days_checker(chat_id, context):
    await asyncio.sleep(3 * 24 * 3600) # 3 أيام
    w = wars.get(chat_id)
    if w and w.get("active"):
        tags = w.get("tags_scores", {})
        if not tags: return
        
        msg_text = "⏳ مرت 3 أيام ولم تنتهِ المواجهة.\n📊 نتيجة التاكات الكلية:\n"
        for player, score in tags.items():
            msg_text += f"👤 {player} : {score} تاكات\n"
        
        keyboard = [[InlineKeyboardButton("الكلان الأول (A)", callback_data="tag_win_c1"),
                     InlineKeyboardButton("الكلان الثاني (B)", callback_data="tag_win_c2")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, msg_text + "\n❓ أرجو من القادة تحديد الفائز بالتاكات لمنحه النقطة (لن تؤثر على النجم/الحاسم):", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = query.message.chat_id
    data = query.data
    w = wars.get(cid)
    
    if w and w.get("active"):
        if data == "tag_win_c1":
            w["c1"]["s"] += 1
            w["c1"]["stats"].append({"name": "نقاط تاكات (فري)", "goals": 0, "rec": 0, "is_free": True})
            await query.edit_message_text(f"✅ تم احتساب نقطة التاكات لصالح كلان {w['c1']['n']}.")
        elif data == "tag_win_c2":
            w["c2"]["s"] += 1
            w["c2"]["stats"].append({"name": "نقاط تاكات (فري)", "goals": 0, "rec": 0, "is_free": True})
            await query.edit_message_text(f"✅ تم احتساب نقطة التاكات لصالح كلان {w['c2']['n']}.")
        save_data()
        try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
        except: pass

async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text: return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(
                f"🚨 تنبيه: تم تعديل رسالة في جروب المواجهة!\n\n"
                f"📜 الرسالة قبل التعديل:\n{old_text}\n\n"
                f"🔄 الرسالة بعد التعديل:\n{new_text}\n\n"
                f"⚠️ التلاعب بالرسائل والقوائم ممنوع."
            )

# --- معالج ردود الحكام لإرجاع الاعتراض ---
async def handle_judge_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إذا قام حكم بالرد على رسالة اعتراض، يتم إرسال رده إلى الجروب الأصلي"""
    if not update.message.reply_to_message: return
    if update.effective_chat.id != JUDGES_GROUP_ID: return
    
    original_judge_msg = update.message.reply_to_message.text
    chat_id_match = re.search(r'ID_GROUP: (-?\d+)', original_judge_msg)
    
    if chat_id_match:
        original_cid = int(chat_id_match.group(1))
        judge_response = update.message.text
        try:
            await context.bot.send_message(original_cid, f"⚖️ رد الحكام على الاعتراض المقدم:\n\n{judge_response}")
            await update.message.reply_text("✅ تم توجيه ردك إلى جروب المواجهة بنجاح.")
        except:
            await update.message.reply_text("❌ فشل إرسال الرد، قد يكون البوت غادر الجروب أو تم حظره.")

# --- المعالج الرئيسي للمواجهة ---
async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.message_id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    # إذا كنا في جروب الحكام، نستخدم معالج الردود الخاص بهم
    if cid == JUDGES_GROUP_ID:
        await handle_judge_reply(update, context)
        return

    original_msg_store[mid] = msg

    super_admins = ["mwsa_20", "levil_8"]
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in super_admins) or is_creator
    except:
        is_creator = False
        is_referee = (user.username in super_admins)

    w = wars.get(cid)

    # --- إلغاء حالة التاكات لو رد المستخدم ---
    if cid in tag_timers and u_tag in tag_timers[cid]:
        tag_timers[cid][u_tag]["responded"] = True

    # --- الذكاء الاصطناعي (تحليل الاستفزاز) ---
    if not is_referee:
        for word in PROVOCATION_WORDS:
            if word in msg_cleaned:
                await update.message.reply_text(f"⚠️ {u_tag}، رصد الذكاء الاصطناعي كلمة استفزازية ({word}). يرجى الالتزام بالروح الرياضية وإلا ستتعرض لعقوبة.")
                break

    # --- نظام التاكات المعقد ---
    if w and w.get("active") and not w.get("hasm_mode") and w.get("matches"):
        mentions = re.findall(r'@\w+', msg)
        for target in mentions:
            if target != f"@{bot_username}":
                # فحص: هل الشخص المستهدف هو الخصم المباشر (أو بديله) لهذا اللاعب؟
                is_opponent = False
                for m in w["matches"]:
                    if (m["p1"].upper() == u_tag.upper() and m["p2"].upper() == target.upper()) or \
                       (m["p2"].upper() == u_tag.upper() and m["p1"].upper() == target.upper()):
                        is_opponent = True
                        break
                
                # لا يرسل تنبيه الوقت إلا إذا كان التاك للخصم
                if is_opponent:
                    w.setdefault("last_tag_time", {})
                    last_time_str = w["last_tag_time"].get(u_tag)
                    now = datetime.now()
                    
                    can_tag = True
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
                        if now - last_time < timedelta(minutes=30):
                            can_tag = False
                            await update.message.reply_text(f"⏳ مسموح بتاك واحد فقط كل 30 دقيقة يا {u_tag}.")
                    
                    if can_tag:
                        w["last_tag_time"][u_tag] = now.isoformat()
                        save_data()
                        if cid not in tag_timers: tag_timers[cid] = {}
                        tag_timers[cid][target] = {"responded": False}
                        asyncio.create_task(check_tag_response(cid, u_tag, target, mid, context))
                # إذا لم يكن خصماً، يتم تجاهل التاك تماماً ولا يرسل رسالة "مسموح" أو "ممنوع"

    # --- نظام الاعتراضات (للقادة والمساعدين) ---
    if ("اعتراض" in msg_cleaned or "عندي اعتراض" in msg_cleaned) and (is_referee or w and (u_tag in [w["c1"]["leader"], w["c2"]["leader"]])):
        await update.message.reply_text("📝 اكتب اعتراضك الآن في رسالة واحدة، أو أرسل 'الغاء' للتراجع.")
        context.user_data['waiting_objection'] = True
        return
        
    if context.user_data.get('waiting_objection'):
        if "الغاء" in msg_cleaned:
            await update.message.reply_text("✅ تم إلغاء تقديم الاعتراض.")
        else:
            await context.bot.send_message(JUDGES_GROUP_ID, f"⚖️ اعتراض جديد!\nID_GROUP: {cid}\nمن الجروب: {update.effective_chat.title}\nالشاكي: {u_tag}\nنص الاعتراض:\n{msg}")
            await update.message.reply_text("✅ بفضل الذكاء الاصطناعي تم استلام اعتراضك وتحويله مباشرة لجروب الحكام للبت فيه.")
        context.user_data['waiting_objection'] = False
        return

    # --- نظام التبديلات الذكي ---
    if w and w.get("active"):
        if "تبديل " in msg_up:
            target_clan = msg_up.replace("تبديل ", "").strip()
            k = "c1" if w["c1"]["n"] == target_clan else ("c2" if w["c2"]["n"] == target_clan else None)
            if k:
                w.setdefault(f"{k}_subs", 0)
                if w[f"{k}_subs"] >= 3:
                    await update.message.reply_text(f"🚫 تحذير! كلان {target_clan} استنفذ التبديلات الثلاثة (3/3). لا يمكن تبديل المزيد.")
                else:
                    w[f"{k}_subs"] += 1
                    save_data()
                    await update.message.reply_text(f"🔄 تبديل مقبول لكلان {target_clan} رقم ({w[f'{k}_subs']}/3).\nأرسل الآن يوزر اللاعب الأساسي يليه يوزر البديل (مثال: @old @new).")
                    context.user_data['waiting_sub'] = k
            return
            
        if context.user_data.get('waiting_sub'):
            k = context.user_data['waiting_sub']
            players = re.findall(r'@\w+', msg)
            if len(players) >= 2:
                old_p, new_p = players[0], players[1]
                for m in w["matches"]:
                    if m["p1"] == old_p: m["p1"] = new_p
                    if m["p2"] == old_p: m["p2"] = new_p
                save_data()
                
                # تحديث الجدول فوراً
                if w.get("mid"):
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                    except: pass
                
                await update.message.reply_text(f"✅ تم خروج {old_p} ودخول {new_p} وتم تحديث رسالة القرعة بنجاح.")
                context.user_data['waiting_sub'] = False
            return

        # --- نظام الحاسم (3-3) ---
        if w["c1"]["s"] == 3 and w["c2"]["s"] == 3 and not w.get("hasm_mode"):
            w["hasm_mode"] = True
            w.setdefault("hasm_ready", [])
            save_data()
            await update.message.reply_text("🔥 النتيجة 3-3! توقف نظام التاكات القديم ودخلنا طور المباراة الحاسمة.\nيجب على كل كلان كتابة: (حاسم اسم_الكلان).")
            
        if w.get("hasm_mode") and "حاسم " in msg_up:
            target_clan = msg_up.replace("حاسم ", "").strip()
            if target_clan in [w["c1"]["n"], w["c2"]["n"]] and target_clan not in w.get("hasm_ready", []):
                w.setdefault("hasm_ready", []).append(target_clan)
                save_data()
                await update.message.reply_text(f"🎯 تم استلام جاهزية الحاسم لكلان {target_clan}.")
                if len(w["hasm_ready"]) == 2:
                    await update.message.reply_text("⚡ اكتمل الحاسم لدى الكلانين! تبدأ الآن مواجهة الحاسم فقط بنظام تاكات جديد ومستقل.")

    # --- الرد على القوانين ---
    is_bot_mentioned_flag = (f"@{bot_username}" in msg) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)
    if is_bot_mentioned_flag:
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return

    # --- إلغاء إنذار ---
    if "الغاء انذار" in msg_cleaned and is_referee:
        target_t = None
        if update.message.reply_to_message:
            t_user = update.message.reply_to_message.from_user
            target_t = f"@{t_user.username}" if t_user.username else f"ID:{t_user.id}"
        else:
            mentions = re.findall(r'@\w+', msg)
            if mentions: target_t = mentions[0]
        if target_t:
            if cid in user_warnings and target_t in user_warnings[cid]: user_warnings[cid][target_t] = 0
            if cid in admin_warnings and target_t in admin_warnings[cid]: admin_warnings[cid][target_t] = 0
            save_data()
            await update.message.reply_text(f"✅ تم صفر (إلغاء) كافة إنذارات {target_t} بواسطة الإدارة.")
            return

    # --- الطرد للسب ---
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in super_admins:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} فوراً لانتهاك قوانين الاتحاد (سب/كفر).")
                except: pass
            return

    # --- الروليت ---
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 قرعة الروليت:\n\n🏆 الفائز هو: {winner}")
            return

    # --- الإنذارات ---
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        t_tag = f"@{target_user.username}" if target_user.username else f"ID:{target_user.id}"
        
        if msg.strip() == "انذار م" and is_referee:
            if cid not in admin_warnings: admin_warnings[cid] = {}
            count = admin_warnings[cid].get(t_tag, 0) + 1
            admin_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(f"⚠️ إنذار مسؤول (م)\n👤 المسؤول: {t_tag}\n🔢 العدد: ({count}/3)")
            if count >= 3:
                await update.message.reply_text(f"🚫 تم سحب صلاحيات المسؤول {t_tag} بواسطة الإدارة.")
            return

        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(f"⚠️ إنذار لاعب\n👤 اللاعب: {t_tag}\n🔢 العدد: ({count}/3)")
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
            "active": True, "mid": None, "matches": []
        }
        save_data()
        await update.message.reply_text(f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥")
        try: await context.bot.set_chat_title(cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
        except: pass
        asyncio.create_task(three_days_checker(cid, context)) # بدء مؤقت 3 أيام
        return

    if w and w.get("active"):
        # تعيين قائد بديل يدوياً
        sub_leader_match = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader_match and is_referee:
            new_leader = sub_leader_match.group(1)
            target_clan_name = sub_leader_match.group(2).strip().upper()
            target_k = None
            if w["c1"]["n"].upper() == target_clan_name: target_k = "c1"
            elif w["c2"]["n"].upper() == target_clan_name: target_k = "c2"
            
            if target_k:
                w[target_k]["leader"] = new_leader
                save_data()
                await update.message.reply_text(f"✅ تم تعيين {new_leader} قائداً رسمياً لكلان {w[target_k]['n']} بدلاً من القائد السابق.")
            else:
                await update.message.reply_text(f"❌ لم يتم العثور على كلان بهذا الاسم في الحرب الحالية.")
            return

        # تسجيل القائمة
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = None
            if w["c1"]["n"].upper() in msg_up: target_k = "c1"
            elif w["c2"]["n"].upper() in msg_up: target_k = "c2"
            
            if target_k:
                if not is_referee:
                    other_k = "c2" if target_k == "c1" else "c1"
                    if w[other_k]["leader"] == u_tag:
                        await update.message.reply_text("❌ أنت قائد الكلان الخصم، لا يمكنك إرسال قائمة منافسك!")
                        return

                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد القائمة لـ {w[target_k]['n']} (بواسطة {u_tag}).")

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
                    except Exception as e: print(f"Error pinning message: {e}")
            return

        # تحديد المساعد
        asst_match = re.search(r'مساعدي\s+(@\w+)\s+كلان\s+(\w+)', msg)
        if asst_match:
            target_asst = asst_match.group(1)
            clan_name = asst_match.group(2).upper()
            target_key = "c1" if w["c1"]["n"].upper() == clan_name else ("c2" if w["c2"]["n"].upper() == clan_name else None)
            
            if target_key and (w[target_key]["leader"] == u_tag or is_referee):
                if cid not in clans_mgmt: clans_mgmt[cid] = {}
                clans_mgmt[cid][clan_name] = {"asst": target_asst}
                save_data()
                await update.message.reply_text(f"✅ تم تعيين المساعد {target_asst} لكلان {clan_name}.")
            elif target_key:
                await update.message.reply_text("❌ فقط قائد الكلان أو الحكم يمكنه تحديد المساعد.")
            return

        # نظام إضافة النقاط وتحديث المباريات والطرد (Kick)
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

                u1, u2 = players[0], players[1]
                sc1, sc2 = int(scores[0]), int(scores[1])
                p_win = u1 if sc1 > sc2 else u2
                
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                
                for m in w["matches"]:
                    mp1_u, mp2_u = m["p1"].upper(), m["p2"].upper()
                    if (u1.upper() == mp1_u or u1.upper() == mp2_u) and (u2.upper() == mp1_u or u2.upper() == mp2_u):
                        if u1.upper() == mp1_u: m["s1"], m["s2"] = sc1, sc2
                        else: m["s1"], m["s2"] = sc2, sc1
                
                save_data()
                await update.message.reply_text(f"✅ تم تسجيل نقطة مباراة لـ {w[win_k]['n']}.")

                # --- طرد اللاعبين (Kick وليس Ban) ---
                for pl in players:
                    try:
                        mem = await context.bot.get_chat_member(cid, pl)
                        uid = mem.user.id
                        await context.bot.ban_chat_member(cid, uid)
                        await context.bot.unban_chat_member(cid, uid)
                    except: pass

            else:
                if not is_referee:
                    await update.message.reply_text("❌ النقطة الفري حصرية للإدارة.")
                    return
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                save_data()
                await update.message.reply_text(f"⚖️ قرار إداري: إضافة نقطة فري لكلان {w[win_k]['n']} بواسطة {u_tag}.")

            try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
            except: pass

            if w["mid"]:
                rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين وينتهي الوقت\n🔗 {AU_LINK}"
                try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                except: pass
            
            # إنهاء الحرب وإرسال النتائج النهائية
            if w[win_k]["s"] >= 4:
                w["active"] = False
                save_data()
                history = w[win_k]["stats"]
                real_players = [h for h in history if not h["is_free"]]
                
                if real_players:
                    hasm = real_players[-1]["name"]
                    star_player_data = max(real_players, key=lambda x: (x["goals"] - x["rec"]))
                    star = star_player_data["name"]
                    star_goals = star_player_data["goals"]
                    star_rec = star_player_data["rec"]

                    result_msg = (
                        f"🎊 انتهت الحرب بفوز كلان: {w[win_k]['n']} 🎊\n\n"
                        f"🎯 الحاسم: {hasm} (آخر من سجل)\n"
                        f"⭐ النجم: {star} (سجل {star_goals} واستقبل {star_rec})"
                    )
                else:
                    result_msg = f"🎊 انتهت الحرب بفوز إداري لكلان: {w[win_k]['n']} 🎊"
                
                await update.message.reply_text(result_msg)

                match_results_str = ""
                for i, m in enumerate(w["matches"]):
                    line = f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |"
                    match_results_str += line + "\n─── ─── ─── ─── ───\n"
                
                await update.message.reply_text(f"📊 تفاصيل النتائج:\n\n{match_results_str}")

    # --- استقبال أوامر بوت النشر ---
    if "بدء مواجهة:" in msg:
        link_match = re.search(r'الرابط: (.+)', msg)
        type_match = re.search(r'النوع: (.+)', msg)
        clans_match = re.search(r'الكلانات: (.+)', msg)
        
        if link_match and clans_match:
            source_url = link_match.group(1)
            war_type = type_match.group(1)
            clans_text = clans_match.group(1)
            
            parts = clans_text.upper().split(" VS ")
            c1_n = parts[0].replace("CLAN ", "").strip()
            c2_n = parts[1].replace("CLAN ", "").strip()

            wars[cid] = {
                "c1": {"n": c1_n, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_n, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [], "source_link": source_url
            }
            save_data()
            try:
                await context.bot.set_chat_title(cid, f"⚔️ {c1_n} 0 - 0 {c2_n} {war_type}")
                await context.bot.set_chat_description(cid, f"مواجهة رسمية بين {c1_n} و {c2_n}\nالمنظم: موجود\nرابط المنشور: {source_url}")
            except Exception as e: print(f"Error updating chat: {e}")

            await update.message.reply_text(f"🚀 تم استلام البيانات من بوت النشر.\nتم تحديث اسم الجروب والوصف وبدء الحرب!")
            asyncio.create_task(three_days_checker(cid, context)) # بدء مؤقت 3 أيام
            return

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    load_data()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.add_handler(CallbackQueryHandler(handle_callback)) # لاستقبال ضغطات الأزرار الشفافة
    
    print("✅ البوت يعمل الآن (مع خاصية حفظ البيانات وتحديث النتائج واقعياً)...")
    app.run_polling()
