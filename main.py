import random
import re
import logging
import os
import asyncio
import json
import threading
import requests  # لإحضار محتوى المنشور
from bs4 import BeautifulSoup # لفحص محتوى المنشور
from datetime import datetime, time, timedelta
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
DATA_FILE = "bot_data.json"

AVAILABLE_GROUPS = [
    -1003806873470, -1003770118909, -1003425140606, -1003848876282, -1003849589753,
    -1003778471416, -1003777313009, -1003881611757, -1003842710764, -1003896740715,
    -1003697570029, -1003764856424, -1003777881446, -1003876875877, -1003630010725,
    -1003410963940, -1003820176985, -1003898252504, -1003853259608, -1003580838480,
    -1003825865677, -1003671396940, -1003883290441, -1003426023493, -1003653988672,
    -1003443387454, -1003849371837, -1003683326141, -1003648259769, -1003055323704,
    -1003782082743, -1003657695669, -1003854127540, -1003892320819, -1003575024561,
    -1003843562160, -1003509629104, -1003701215403, -1003729544746, -1003706596904,
    -1003645207975, -1003775126310, -1003888797989, -1003655311013, -1003826640673,
    -1003799518112, -1003515595420, -1003883618970, -1003536434969, -1003664111767,
    -1003781850262, -1003867683988, -1003843800595, -1003881587855, -1003622910094,
    -1003807401101, -1003765764748, -1003708801293, -1003593515011, -1003409541903,
    -1003532620680, -1003515775111, -1003858084099, -1003666475266
]

post_to_group = {}

# --- دالة فحص المنشور للتأكد من المواجهة والمنظم ---
def verify_post_content(url, clan_a, clan_b):
    try:
        # تحويل رابط التلجرام لرابط ويب للمعاينة
        web_url = url + "?embed=1"
        response = requests.get(web_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().upper()
            
            # التأكد من وجود الكلانين في المنشور
            if clan_a.upper() in text and clan_b.upper() in text:
                # محاولة استخراج المنظم (يفترض وجوده في نهاية الكليشة مسبوقاً بـ @)
                organizer_matches = re.findall(r'@\w+', text)
                organizer = organizer_matches[-1] if organizer_matches else "@mwsa_20"
                return True, organizer
    except Exception as e:
        print(f"Verify error: {e}")
    return False, "@mwsa_20"

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

BAN_WORDS = ["كسمك", "كسمه", "كسختك",]
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {} 

def save_data():
    data = {"wars": wars, "clans_mgmt": clans_mgmt, "user_warnings": user_warnings, "admin_warnings": admin_warnings, "post_to_group": post_to_group}
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"❌ Error saving: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings, post_to_group
    if not os.path.exists(DATA_FILE): return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wars = {int(k): v for k, v in data.get("wars", {}).items()}
            clans_mgmt = {int(k): v for k, v in data.get("clans_mgmt", {}).items()}
            user_warnings = {int(k): v for k, v in data.get("user_warnings", {}).items()}
            admin_warnings = {int(k): v for k, v in data.get("admin_warnings", {}).items()}
            post_to_group = data.get("post_to_group", {})
    except Exception as e: print(f"❌ Error loading: {e}")

def to_emoji(num):
    n_str = str(num)
    dic = {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'}
    return "".join([dic.get(char, char) for char in n_str])

def clean_text(text):
    if not text: return ""
    text = text.lower().replace('ة', 'ه').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    return re.sub(r'^(ال)', '', text)

# --- ميزة طرد الجميع وتنظيف الجروب وإرسال النتيجة للمنظم ---
async def cleanup_group(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    cid = job.chat_id
    
    try:
        target_war = wars.get(cid)
        if target_war:
            # 1. إرسال النتيجة للمنظم قبل المسح
            organizer = target_war.get("organizer", "@mwsa_20")
            result_msg = (
                f"📊 **تقرير نهاية المواجهة الرسمي**\n"
                f"───\n"
                f"⚔️ المباراة: {target_war['c1']['n']} VS {target_war['c2']['n']}\n"
                f"🏆 النتيجة: {target_war['c1']['s']} - {target_war['c2']['s']}\n"
                f"🔗 رابط المنشور: {target_war['post_link']}\n"
                f"───\n"
                f"✅ تم تنظيف الجروب بنجاح."
            )
            try: await context.bot.send_message(organizer, result_msg)
            except: pass

            # 2. تنظيف البيانات
            p_link = target_war.get("post_link")
            if p_link in post_to_group: del post_to_group[p_link]
            del wars[cid]
            save_data()

        await context.bot.send_message(cid, "🚨 **انتهت مهلة الـ 10 ساعات.**\nيتم الآن تنظيف الجروب وإتاحته لمواجهة جديدة.")
        try: await context.bot.set_chat_title(cid, "المواجهة القادمة - متاح")
        except: pass
    except Exception as e: print(f"Cleanup error: {e}")

async def handle_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.text: return
    mid = update.edited_message.message_id
    if mid in original_msg_store:
        old_text = original_msg_store[mid]
        new_text = update.edited_message.text
        if old_text != new_text:
            await update.edited_message.reply_text(f"🚨 **تنبيه: تم تعديل رسالة!**\n\n📜 **قبل:** `{old_text}`\n🔄 **بعد:** `{new_text}`")

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    cid, msg, mid = update.effective_chat.id, update.message.text, update.message.id
    msg_up, msg_cleaned = msg.upper().strip(), clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"
    original_msg_store[mid] = msg
    super_admins = ["mwsa_20", "levil_8"]

    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_referee = (user.username in super_admins) or (chat_member.status == 'creator')
    except: is_referee = (user.username in super_admins)

    # --- معالجة طلب المواجهة في الخاص ---
    if update.effective_chat.type == "private" and " VS " in msg_up:
        lines = msg.split('\n')
        if len(lines) < 2:
            await update.message.reply_text("❌ الصيغة:\nCLAN A VS CLAN B\nرابط المنشور")
            return
        
        clan_part, post_link = lines[0].upper(), lines[1].strip()
        parts = clan_part.split(" VS ")
        c1_name, c2_name = parts[0].replace("CLAN ", "").strip(), parts[1].replace("CLAN ", "").strip()

        # فحص الرابط ومحتواه
        is_valid, organizer = verify_post_content(post_link, c1_name, c2_name)
        if not is_valid:
            await update.message.reply_text(f"❌ خطأ: المواجهة بين {c1_name} و {c2_name} غير موجودة في هذا الرابط أو الرابط غير صحيح.")
            return

        if post_link in post_to_group:
            await update.message.reply_text("⚠️ هذه المواجهة قائمة بالفعل.")
            return

        target_cid = next((g for g in AVAILABLE_GROUPS if g not in wars or not wars[g].get("active")), None)
        
        if target_cid:
            # تغيير الاسم فوراً
            try: await context.bot.set_chat_title(target_cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
            except: pass

            wars[target_cid] = {
                "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [], "post_link": post_link, "organizer": organizer
            }
            post_to_group[post_link] = target_cid
            save_data()
            
            start_msg = await context.bot.send_message(target_cid, f"⚔️ بدأت المواجهة!\n🔥 {c1_name} VS {c2_name}\n🔗 الرابط: {post_link}\n👤 المنظم: {organizer}")
            await context.bot.pin_chat_message(target_cid, start_msg.message_id)
            
            g_chat = await context.bot.get_chat(target_cid)
            await update.message.reply_text(f"✅ تم التجهيز!\nالجروب: {c1_name} VS {c2_name}\nالرابط: {g_chat.invite_link}")
        else:
            await update.message.reply_text("❌ جميع الجروبات مشغولة.")
        return

    # --- القوانين ---
    if f"@{bot_username}" in msg or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):
        for k, law in DETAILED_LAWS.items():
            if k in msg_cleaned:
                await update.message.reply_text(law, disable_web_page_preview=True)
                return

    # --- نظام الحماية ---
    for word in BAN_WORDS:
        if word in msg.lower() and user.username not in super_admins:
            try: await context.bot.ban_chat_member(cid, user.id)
            except: pass

    # --- عمليات الجروب ---
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # تسجيل القائمة
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if target_k:
                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ اعتمدت قائمة {w[target_k]['n']}.")
                if w["c1"]["p"] and w["c2"]["p"]:
                    p1, p2 = list(w["c1"]["p"]), list(w["c2"]["p"])
                    random.shuffle(p1); random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    rows = [f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table)
                    w["mid"] = sent.message_id
                    save_data()
            return

        # تسجيل الأهداف
        if "+ 1" in msg_up or "+1" in msg_up:
            players, scores = re.findall(r'@\w+', msg_up), re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if win_k and len(players) >= 2 and len(scores) >= 2:
                sc1, sc2 = int(scores[0]), int(scores[1])
                w[win_k]["s"] += 1
                w[win_k]["stats"].append({"name": players[0], "goals": sc1, "rec": sc2, "is_free": False})
                for m in w["matches"]:
                    if players[0] in [m["p1"], m["p2"]] and players[1] in [m["p1"], m["p2"]]:
                        if players[0] == m["p1"]: m["s1"], m["s2"] = sc1, sc2
                        else: m["s1"], m["s2"] = sc2, sc1
                save_data()
                try: await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except: pass
                
                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(table, cid, w["mid"])
                    except: pass
                
                if w[win_k]["s"] >= 4:
                    w["active"] = False
                    save_data()
                    await update.message.reply_text(f"🎊 انتهت بفوز {w[win_k]['n']} 🎊\nسيتم إرسال النتيجة للمنظم وتنظيف الجروب خلال 10 ساعات.")
                    context.job_queue.run_once(cleanup_group, when=timedelta(hours=10), chat_id=cid)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    load_data()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    app.run_polling()
