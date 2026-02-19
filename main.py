import random
import re
import json
import os
import threading
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask

# -------------------- إعدادات Flask --------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Publisher Bot is Running in Private Mode!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7861)

# -------------------- الثوابت --------------------
TOKEN = "8251539959:AAH0Ktql1qVSEuu_k0CGUeYqLVmW85LGf0Q"  # توكن بوت النشر
REFEREE_BOT_USERNAME = "@OACRef_bot"  # يوزر بوت الحكم
ORGANIZER_CHAT_ID = -1002029492622  # معرف مجموعة المنظمين
DATA_FILE = "publisher_data.json"

# قائمة الكروبات المتاحة (72 كروب)
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

# -------------------- هياكل البيانات --------------------
groups_status = {chat_id: {"status": "available", "cooldown_until": None,
                           "post_url": None, "war_start": None, "clans": None}
                 for chat_id in AVAILABLE_GROUPS}

active_posts = {}

# -------------------- دوال الحفظ والتحميل --------------------
def save_data():
    data = {
        "groups_status": groups_status,
        "active_posts": active_posts
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, default=str)
        print("✅ Publisher data saved.")
    except Exception as e:
        print(f"❌ Save error: {e}")

def load_data():
    global groups_status, active_posts
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "groups_status" in data:
                loaded_groups = {}
                for key, value in data["groups_status"].items():
                    cid = int(key)
                    if value.get("cooldown_until"):
                        value["cooldown_until"] = datetime.fromisoformat(value["cooldown_until"])
                    if value.get("war_start"):
                        value["war_start"] = datetime.fromisoformat(value["war_start"])
                    default_group = {"status": "available", "cooldown_until": None,
                                     "post_url": None, "war_start": None, "clans": None}
                    merged = {**default_group, **value}
                    loaded_groups[cid] = merged
                groups_status = loaded_groups
            if "active_posts" in data:
                active_posts = data["active_posts"]
                for post, info in active_posts.items():
                    if "used_chats" in info:
                        info["used_chats"] = [int(cid) for cid in info["used_chats"]]
        print("✅ Publisher data loaded.")
    except Exception as e:
        print(f"❌ Load error: {e}")

def get_available_group():
    for cid, info in groups_status.items():
        if info["status"] == "available":
            return cid
    return None

async def reopen_group(context: ContextTypes.DEFAULT_TYPE):
    cid = context.job.data["chat_id"]
    if cid in groups_status and groups_status[cid]["status"] == "cooldown":
        groups_status[cid] = {"status": "available", "cooldown_until": None,
                              "post_url": None, "war_start": None, "clans": None}
        save_data()
        try:
            await context.bot.set_chat_title(chat_id=cid, title="OAC MATCHES")
        except Exception as e:
            print(f"❌ Failed to rename group {cid}: {e}")
        print(f"✅ Group {cid} is now available again.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    welcome = """مرحباً بك في بوت النشر الرسمي!

لنشر مواجهة جديدة، أرسل المعلومات بالتنسيق التالي في الخاص:

السطر الأول: اسماء الكلانين (مثال: CLAN RED VS BLUE)
السطر الثاني: (اختياري) نوع المواجهة مثل "نصف نهائي"
السطر الثالث: رابط المنشور

مثال:
CLAN RED VS BLUE
نصف نهائي
https://t.me/arab_union3/123

سيتم اختيار كروب متاح وبدء المواجهة هناك."""
    await update.message.reply_text(welcome)

async def handle_new_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    text = update.message.text.strip()
    lines = text.split('\n')
    if len(lines) < 2:
        await update.message.reply_text("❌ صيغة غير صحيحة. يجب إرسال سطرين على الأقل: الكلانين والرابط.")
        return

    clans_line = lines[0].upper()
    if " VS " not in clans_line:
        await update.message.reply_text("❌ يجب أن تحتوي على VS بين الكلانين (مثال: CLAN RED VS BLUE).")
        return

    url_line = lines[-1].strip()
    if not url_line.startswith("https://t.me/"):
        await update.message.reply_text("❌ الرابط غير صالح. يجب أن يكون رابط منشور تليجرام.")
        return

    war_type = ""
    if len(lines) == 3:
        war_type = lines[1].strip()

    chosen_group = None
    reused = False

    if url_line in active_posts:
        post_info = active_posts[url_line]
        for cid in post_info["used_chats"]:
            if (groups_status[cid]["status"] == "busy" and
                groups_status[cid].get("clans") == clans_line):
                chosen_group = cid
                reused = True
                break
        if not chosen_group:
            if len(post_info["used_chats"]) >= post_info["max_groups"]:
                await update.message.reply_text("❌ هذا المنشور استنفذ العدد الأقصى من الكروبات (8).")
                return
            chosen_group = get_available_group()
            if not chosen_group:
                await update.message.reply_text("❌ لا توجد كروبات متاحة حالياً.")
                return
            post_info["used_chats"].append(chosen_group)
    else:
        chosen_group = get_available_group()
        if not chosen_group:
            await update.message.reply_text("❌ لا توجد كروبات متاحة حالياً.")
            return
        active_posts[url_line] = {
            "max_groups": 8,
            "used_chats": [chosen_group],
            "war_type": war_type,
            "created_at": datetime.now().isoformat()
        }

    groups_status[chosen_group]["status"] = "busy"
    groups_status[chosen_group]["post_url"] = url_line
    groups_status[chosen_group]["war_start"] = datetime.now()
    groups_status[chosen_group]["cooldown_until"] = None
    groups_status[chosen_group]["clans"] = clans_line
    save_data()

    # إنشاء رابط دعوة صالح لمدة يوم
    invite_link = None
    try:
        expire_time = datetime.now() + timedelta(days=1)
        invite = await context.bot.create_chat_invite_link(
            chat_id=chosen_group,
            expire_date=expire_time,
            member_limit=10
        )
        invite_link = invite.invite_link
    except Exception as e:
        print(f"❌ Failed to create invite link for group {chosen_group}: {e}")

    # إرسال الأمر لبوت الحكم داخل الكروب
    try:
        referee_msg = f"بدء مواجهة:\nالرابط: {url_line}\nالنوع: {war_type}\nالكلانات: {clans_line}"
        await context.bot.send_message(chat_id=chosen_group, text=referee_msg)

        if invite_link:
            await update.message.reply_text(f"🔗 رابط الكروب: {invite_link}")
        else:
            await update.message.reply_text(f"🔗 معرف الكروب: `{chosen_group}`\n⚠️ لم نتمكن من إنشاء رابط تلقائي، سيتم إضافتك يدوياً.")

        if reused:
            await update.message.reply_text("🔄 تم استخدام كروب سابق لنفس المنشور ونفس الكلانين.")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل التواصل مع بوت الحكم: {e}")
        groups_status[chosen_group]["status"] = "available"
        groups_status[chosen_group]["post_url"] = None
        groups_status[chosen_group]["war_start"] = None
        groups_status[chosen_group]["clans"] = None
        if url_line in active_posts:
            active_posts[url_line]["used_chats"].remove(chosen_group)
            if not active_posts[url_line]["used_chats"]:
                del active_posts[url_line]
        save_data()

async def handle_war_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if not text.startswith("انتهت_مواجهة"):
        return

    parts = text.split()
    if len(parts) < 7:
        return
    chat_id = int(parts[1])
    winner = parts[2]
    score1 = parts[3]
    score2 = parts[4]
    star = parts[5]
    hasm = parts[6]
    post_url = parts[7] if len(parts) > 7 else ""

    if chat_id not in groups_status:
        return

    cooldown_until = datetime.now() + timedelta(hours=10)
    groups_status[chat_id]["status"] = "cooldown"
    groups_status[chat_id]["cooldown_until"] = cooldown_until
    groups_status[chat_id]["post_url"] = None
    groups_status[chat_id]["war_start"] = None
    groups_status[chat_id]["clans"] = None
    save_data()

    context.job_queue.run_once(reopen_group, when=timedelta(hours=10), data={"chat_id": chat_id})

    report = f"🏆 انتهت المواجهة في الكروب {chat_id}\n"
    report += f"الرابط: {post_url}\n"
    report += f"الفائز: {winner} ({score1} - {score2})\n"
    report += f"النجم: {star}\n"
    report += f"الحاسم: {hasm}\n"
    report += f"سيتم إعادة فتح الكروب بعد 10 ساعات."
    try:
        await context.bot.send_message(chat_id=ORGANIZER_CHAT_ID, text=report)
    except Exception as e:
        print(f"❌ Failed to send report to organizer: {e}")

    try:
        await context.bot.set_chat_title(chat_id=chat_id, title="⏳ OAC MATCHES (قيد التهدئة)")
    except:
        pass

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    load_data()

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_new_match))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^انتهت_مواجهة'), handle_war_end))

    print("✅ Publisher Bot is running in PRIVATE mode only...")
    app.run_polling()
