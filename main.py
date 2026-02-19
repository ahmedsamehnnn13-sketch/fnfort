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
    return "Bot is Running Live!"

def run_flask():
    web_app.run(host='0.0.0.0', port=7860)

# --- الإعدادات الثابتة وروابط الاتحاد ---
TOKEN = "8546666050:AAFt7buGH1xrVTTWa-lrIhOdesG_sk2n_bM"
CONSTITUTION_LINK = "https://t.me/arab_union3"
AU_LINK = "https://t.me/arab_union3"
DATA_FILE = "bot_data.json"  # اسم ملف حفظ البيانات

# قائمة الجروبات المتاحة للبوت
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

# سجل لربط رابط المنشور بالجروب المشغول حالياً
post_to_group = {}

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
BAN_WORDS = ["كسمك", "كسمه", "كسختك",]

# مخازن البيانات الشاملة
wars = {}
clans_mgmt = {}
user_warnings = {}
admin_warnings = {}
original_msg_store = {} 

# --- دوال الحفظ والاسترجاع (Persistence) ---
def save_data():
    data = {
        "wars": wars,
        "clans_mgmt": clans_mgmt,
        "user_warnings": user_warnings,
        "admin_warnings": admin_warnings,
        "post_to_group": post_to_group
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅ Data saved successfully.")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def load_data():
    global wars, clans_mgmt, user_warnings, admin_warnings, post_to_group
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
            if "post_to_group" in data:
                post_to_group = data["post_to_group"]
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

# --- ميزة طرد الجميع وتنظيف الجروب ---
async def cleanup_group(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    cid = job.chat_id
    
    try:
        target_war = wars.get(cid)
        if target_war:
            all_involved = set()
            if "c1" in target_war: all_involved.update(target_war["c1"]["p"])
            if "c2" in target_war: all_involved.update(target_war["c2"]["p"])
            # هنا يمكنك إضافة كود طرد الأعضاء إذا كان البوت مشرفاً

        await context.bot.send_message(cid, "🚨 **انتهت مهلة الـ 10 ساعات.**\nيتم الآن تنظيف الجروب وإتاحته لمواجهة جديدة.")
        
        # إعادة تهيئة الجروب في السجلات لفتحه
        if cid in wars:
            p_link = wars[cid].get("post_link")
            if p_link in post_to_group:
                del post_to_group[p_link]
            del wars[cid]
            save_data()
            
        try:
            await context.bot.set_chat_title(cid, "المواجهة القادمة - متاح")
        except: pass
    except Exception as e:
        print(f"Cleanup error: {e}")

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

async def handle_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    cid = update.effective_chat.id
    msg = update.message.text
    mid = update.message.id
    msg_up = msg.upper().strip()
    msg_cleaned = clean_text(msg)
    user = update.effective_user
    bot_username = context.bot.username
    u_tag = f"@{user.username}" if user.username else f"ID:{user.id}"

    original_msg_store[mid] = msg

    super_admins = ["mwsa_20", "levil_8"]
    try:
        chat_member = await context.bot.get_chat_member(cid, user.id)
        is_creator = (chat_member.status == 'creator')
        is_referee = (user.username in super_admins) or is_creator
    except:
        is_creator = False
        is_referee = (user.username in super_admins)

    # --- معالجة طلب المواجهة في الخاص ---
    if update.effective_chat.type == "private" and " VS " in msg_up:
        lines = msg.split('\n')
        if len(lines) < 2:
            await update.message.reply_text("❌ يرجى إرسال المواجهة بالصيغة التالية:\n\nCLAN A VS CLAN B\nرابط المنشور")
            return
        
        clan_part = lines[0].upper()
        post_link = lines[1].strip()
        
        parts = clan_part.split(" VS ")
        c1_name = parts[0].replace("CLAN ", "").strip()
        c2_name = parts[1].replace("CLAN ", "").strip()

        # التحقق من وجود المنشور مسبقاً
        if post_link in post_to_group:
            target_cid = post_to_group[post_link]
            try:
                group_chat = await context.bot.get_chat(target_cid)
                await update.message.reply_text(f"✅ هذه المواجهة موجودة بالفعل في:\n{group_chat.invite_link if group_chat.invite_link else 'الجروب المخصص'}")
                return
            except: pass

        target_cid = None
        for g_id in AVAILABLE_GROUPS:
            # الجروب يعتبر متاحاً فقط إذا لم يكن مسجلاً في wars أو حالته active هي False (تم تنظيفه)
            if g_id not in wars or wars[g_id].get("active") == False:
                target_cid = g_id
                break
        
        if target_cid:
            # البدء بتحديث البيانات لحجز الجروب فوراً
            wars[target_cid] = {
                "c1": {"n": c1_name, "s": 0, "p": [], "stats": [], "leader": None},
                "c2": {"n": c2_name, "s": 0, "p": [], "stats": [], "leader": None},
                "active": True, "mid": None, "matches": [], "post_link": post_link, "end_time": None
            }
            post_to_group[post_link] = target_cid
            save_data()
            
            try:
                # 1. تغيير اسم المجموعة أولاً (لضمان ظهور الاسم الجديد قبل الرسالة)
                try:
                    await context.bot.set_chat_title(target_cid, f"⚔️ {c1_name} 0 - 0 {c2_name} ⚔️")
                except Exception as e:
                    print(f"Title update error: {e}")
                
                # 2. إرسال رسالة البدء وتثبيتها بعد تغيير الاسم
                start_msg = await context.bot.send_message(target_cid, f"⚔️ بدأت الحرب الرسمية بين:\n🔥 {c1_name} ضد {c2_name} 🔥\n🔗 رابط المنشور: {post_link}")
                await context.bot.pin_chat_message(target_cid, start_msg.message_id)
                
                group_info = await context.bot.get_chat(target_cid)
                await update.message.reply_text(f"✅ تم تجهيز المواجهة!\nالجروب: {c1_name} VS {c2_name}\nالرابط: {group_info.invite_link if group_info.invite_link else 'ادخل الجروب المخصص'}")
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ أثناء تجهيز الجروب: {str(e)}")
        else:
            await update.message.reply_text("❌ نعتذر، جميع الجروبات مشغولة حالياً بمواجهات قائمة.")
        return

    # --- الرد على الاعتراضات والقوانين ---
    is_bot_mentioned = (f"@{bot_username}" in msg) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)
    if is_bot_mentioned:
        for keyword, law_text in DETAILED_LAWS.items():
            if keyword in msg_cleaned:
                await update.message.reply_text(law_text, disable_web_page_preview=True)
                return

    # --- إلغاء الإنذار ---
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
            await update.message.reply_text(f"✅ تم صفر إنذارات {target_t}.")
            return

    # --- نظام الطرد الآلي ---
    for word in BAN_WORDS:
        if word in msg.lower():
            if user.username not in super_admins:
                try:
                    await context.bot.ban_chat_member(cid, user.id)
                    await update.message.reply_text(f"🚫 تم طرد {u_tag} (سب/كفر).")
                except: pass
            return

    # --- الروليت ---
    if "روليت" in msg:
        roulette_match = re.findall(r'@\w+', msg)
        if len(roulette_match) >= 2:
            winner = random.choice(roulette_match)
            await update.message.reply_text(f"🎲 **القرعة:** {winner}")
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
            await update.message.reply_text(f"⚠️ **إنذار م** {t_tag} ({count}/3)")
            return
        if msg.strip() == "انذار" and is_referee:
            if cid not in user_warnings: user_warnings[cid] = {}
            count = user_warnings[cid].get(t_tag, 0) + 1
            user_warnings[cid][t_tag] = count
            save_data()
            await update.message.reply_text(f"⚠️ **إنذار** {t_tag} ({count}/3)")
            return

    # --- عمليات داخل الجروب النشط ---
    if cid in wars and wars[cid]["active"]:
        w = wars[cid]

        # تعيين قائد بديل
        sub_leader_match = re.search(r'مسؤول / قائد بدالي\s+(@\w+)\s+كلان\s+(.+)', msg)
        if sub_leader_match and is_referee:
            new_leader, target_clan_name = sub_leader_match.group(1), sub_leader_match.group(2).strip().upper()
            target_k = "c1" if w["c1"]["n"].upper() == target_clan_name else ("c2" if w["c2"]["n"].upper() == target_clan_name else None)
            if target_k:
                w[target_k]["leader"] = new_leader
                save_data()
                await update.message.reply_text(f"✅ {new_leader} قائداً لـ {w[target_k]['n']}.")
            return

        # تسجيل القائمة
        if "قائم" in msg_cleaned and update.message.reply_to_message:
            target_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if target_k:
                if not is_referee:
                    other_k = "c2" if target_k == "c1" else "c1"
                    if w[other_k]["leader"] == u_tag:
                        await update.message.reply_text("❌ لا يمكنك إرسال قائمة خصمك!")
                        return
                w[target_k]["leader"] = u_tag
                w[target_k]["p"] = [p.strip() for p in update.message.reply_to_message.text.split('\n') if p.startswith('@')]
                save_data()
                await update.message.reply_text(f"✅ تم اعتماد قائمة {w[target_k]['n']}.")
                if w["c1"]["p"] and w["c2"]["p"]:
                    p1, p2 = list(w["c1"]["p"]), list(w["c2"]["p"])
                    random.shuffle(p1); random.shuffle(p2)
                    w["matches"] = [{"p1": u1, "p2": u2, "s1": 0, "s2": 0} for u1, u2 in zip(p1, p2)]
                    save_data()
                    rows = [f"{i+1} | {m['p1']} {to_emoji(0)}|🆚|{to_emoji(0)} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                    sent = await update.message.reply_text(table, disable_web_page_preview=True)
                    w["mid"] = sent.message_id
                    save_data()
                    try: await context.bot.pin_chat_message(cid, sent.message_id)
                    except: pass
            return

        # تسجيل النقاط
        if "+ 1" in msg_up or "+1" in msg_up:
            players, scores = re.findall(r'@\w+', msg_up), re.findall(r'(\d+)', msg_up)
            win_k = "c1" if w["c1"]["n"].upper() in msg_up else ("c2" if w["c2"]["n"].upper() in msg_up else None)
            if win_k:
                if len(players) >= 2 and len(scores) >= 2:
                    asst_tag = clans_mgmt.get(cid, {}).get(w[win_k]["n"].upper(), {}).get("asst")
                    if not (is_referee or u_tag == w[win_k]["leader"] or u_tag == asst_tag):
                        await update.message.reply_text("❌ التسجيل للحكام أو القادة فقط.")
                        return
                    u1, u2, sc1, sc2 = players[0], players[1], int(scores[0]), int(scores[1])
                    p_win = u1 if sc1 > sc2 else u2
                    w[win_k]["s"] += 1
                    w[win_k]["stats"].append({"name": p_win, "goals": max(sc1, sc2), "rec": min(sc1, sc2), "is_free": False})
                    for m in w["matches"]:
                        if (u1.upper() == m["p1"].upper() or u1.upper() == m["p2"].upper()) and (u2.upper() == m["p1"].upper() or u2.upper() == m["p2"].upper()):
                            if u1.upper() == m["p1"].upper(): m["s1"], m["s2"] = sc1, sc2
                            else: m["s1"], m["s2"] = sc2, sc1
                    save_data()
                    await update.message.reply_text(f"✅ نقطة لـ {w[win_k]['n']}.")
                else:
                    if not is_referee: return
                    w[win_k]["s"] += 1
                    w[win_k]["stats"].append({"name": "Free Point", "goals": 0, "rec": 0, "is_free": True})
                    save_data()
                
                try:
                    await context.bot.set_chat_title(cid, f"⚔️ {w['c1']['n']} {w['c1']['s']} - {w['c2']['s']} {w['c2']['n']} ⚔️")
                except: pass
                
                if w["mid"]:
                    rows = [f"{i+1} | {m['p1']} {to_emoji(m['s1'])}|🆚|{to_emoji(m['s2'])} {m['p2']} |" for i, m in enumerate(w["matches"])]
                    updated_table = f"A- [ {w['c1']['n']} ] | 𝗩𝗦 | B- [ {w['c2']['n']} ]\n───\n" + "\n".join(rows) + f"\n───\n⌛ يومين\n🔗 {AU_LINK}"
                    try: await context.bot.edit_message_text(updated_table, cid, w["mid"], disable_web_page_preview=True)
                    except: pass
                
                if w[win_k]["s"] >= 4:
                    w["active"] = False
                    w["end_time"] = datetime.now().isoformat()
                    save_data()
                    
                    history = w[win_k]["stats"]
                    real_players = [h for h in history if not h["is_free"]]
                    if real_players:
                        hasm = real_players[-1]["name"]
                        star_p = max(real_players, key=lambda x: (x["goals"] - x["rec"]))
                        res = f"🎊 فوز {w[win_k]['n']} 🎊\n🎯 الحاسم: {hasm}\n⭐ النجم: {star_p['name']}"
                    else: res = f"🎊 فوز إداري لـ {w[win_k]['n']} 🎊"
                    
                    await update.message.reply_text(f"{res}\n\n⚠️ **تنبيه:** سيتم تنظيف الجروب وطرد الجميع تلقائياً بعد 10 ساعات من الآن.")
                    context.job_queue.run_once(cleanup_group, when=timedelta(hours=10), chat_id=cid)

# --- تشغيل البوت ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    load_data()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_war))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_msg))
    print("✅ البوت يعمل الآن...")
    app.run_polling()
