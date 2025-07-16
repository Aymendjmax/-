import os
import logging
import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import time
import schedule
import requests
from flask import Flask, Response
import json
import io

# تكوين السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@Aymen_dj_max')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1002807434205'))
DEVELOPER_USERNAME = os.getenv('DEVELOPER_USERNAME', '@Akio_co')
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = 8199450690  # تأكد من تطابق هذا الرقم مع حسابك

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)

# تهيئة Flask
app = Flask(__name__)

@app.route('/ping')
def ping():
    return Response("Bot is alive!", status=200, mimetype='text/plain')

# تخزين البيانات في الذاكرة
users_data = {}
user_messages = {}
data_lock = threading.Lock()

# هيكل بيانات المستخدم الافتراضي
default_user_data = {
    'subhan_count': 0,
    'alhamdulillah_count': 0,
    'la_ilaha_count': 0,
    'allahu_akbar_count': 0,
    'total_count': 0,
    'daily_streak': 0,
    'last_active': None,
    'level': 1,
    'notifications': True,
    'joined_date': datetime.now().strftime('%Y-%m-%d'),
    'progress': 0,
    'next_level_remaining': 1000,
    # قيم التراكم
    'subhan_cumulative': 0,
    'alhamdulillah_cumulative': 0,
    'la_ilaha_cumulative': 0,
    'allahu_akbar_cumulative': 0,
    'total_cumulative': 0
}

# حالة البوت (تشغيل/إيقاف)
bot_enabled = True

def get_user_data(user_id):
    with data_lock:
        # إرجاع نسخة من البيانات لمنع التعديل المباشر
        return users_data.get(user_id, {}).copy()

def update_user_data(user_id, data):
    with data_lock:
        # تحديث البيانات مع الحفاظ على القيم الافتراضية إذا لزم الأمر
        if user_id not in users_data:
            users_data[user_id] = default_user_data.copy()
        users_data[user_id].update(data)

def initialize_user_data(user_id):
    with data_lock:
        if user_id not in users_data:
            new_data = default_user_data.copy()
            new_data['last_active'] = datetime.now().strftime('%Y-%m-%d')
            new_data['joined_date'] = datetime.now().strftime('%Y-%m-%d')
            users_data[user_id] = new_data
        return users_data[user_id].copy()

def is_user_subscribed(user_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

def get_main_keyboard(user_id):
    """إنشاء لوحة المفاتيح الرئيسية للأذكار"""
    user_data = initialize_user_data(user_id)
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # أزرار الأذكار
    keyboard.add(
        types.InlineKeyboardButton(f"سبحان الله ({user_data['subhan_count']})", callback_data="dhikr_subhan"),
        types.InlineKeyboardButton(f"الحمد لله ({user_data['alhamdulillah_count']})", callback_data="dhikr_alhamdulillah")
    )
    keyboard.add(
        types.InlineKeyboardButton(f"لا إله إلا الله ({user_data['la_ilaha_count']})", callback_data="dhikr_la_ilaha"),
        types.InlineKeyboardButton(f"الله اكبر ({user_data['allahu_akbar_count']})", callback_data="dhikr_allahu_akbar")
    )
    
    # أزرار الخيارات
    keyboard.add(
        types.InlineKeyboardButton(f"📊 مجموع ذكرك ({user_data['total_count']})", callback_data="show_total"),
        types.InlineKeyboardButton("🗑️ مسح عدادي", callback_data="reset_counters")
    )
    keyboard.add(
        types.InlineKeyboardButton("📈 إحصائيات", callback_data="show_stats"),
        types.InlineKeyboardButton("👨‍💻 المطور", callback_data="developer_info")
    )
    keyboard.add(
        types.InlineKeyboardButton("📤 شارك البوت", callback_data="share_bot"),
        types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings_menu")
    )
    
    return keyboard

def get_main_message(user_id):
    """إنشاء نص الرسالة الرئيسية"""
    user_data = initialize_user_data(user_id)
    
    # التحقق من المكافآت اليومية
    reward_msg = check_daily_rewards(user_id)
    
    welcome_message = f"""
🌺 بسم الله الرحمن الرحيم 
اللهم صلي وسلم وبارك على سيدنا محمد 🌹

📿 مرحباً بك في بوت نُور الذِّكْر 
هنا تجني الأجر وتنال الثواب بإذن الله تعالى

🎚️ مستواك الحالي: {user_data['level']}
🔥 سلسلة الأيام: {user_data['daily_streak']} يوم

✨ طريقة الاستخدام:
اضغط على أي ذكر لزيادة العداد ورفع درجاتك في الجنة

🌿 فوائد الذكر:
• كل ذكر = 10 حسنات ⭐
• محو الذنوب والخطايا 🍃
• رفع الدرجات في الجنة 🕌
• طمأنينة القلب والروح 💖
    """
    
    if reward_msg:
        welcome_message += f"\n🎁 {reward_msg}"
    
    return welcome_message

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    # التحقق من الاشتراك
    if is_user_subscribed(user_id):
        show_main_menu(message)
    else:
        show_subscription_message(message)

def show_subscription_message(message):
    """عرض رسالة الاشتراك"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔔 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    )
    keyboard.add(
        types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")
    )
    
    subscription_message = f"""
🕌 مرحباً بك في بوت نُور الذِّكْر

⚠️ للاستفادة من البوت، يجب الاشتراك في القناة أولاً

📢 القناة: {CHANNEL_USERNAME}

اضغط على الزر أدناه للاشتراك، ثم اضغط "تحقق من الاشتراك"
    """
    
    bot.send_message(
        message.chat.id,
        subscription_message,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def check_subscription(call):
    user_id = call.from_user.id
    
    if is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك بنجاح!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("🔔 اشترك الآن", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        )
        keyboard.add(
            types.InlineKeyboardButton("✅ تحقق مجدداً", callback_data="check_sub")
        )
        
        bot.edit_message_text(
            f"❌ لم يتم الاشتراك بعد!\n\nالرجاء الاشتراك في القناة {CHANNEL_USERNAME} ثم الضغط على 'تحقق مجدداً'",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك أولاً")

def show_main_menu(message):
    """عرض القائمة الرئيسية"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    main_message = get_main_message(user_id)
    keyboard = get_main_keyboard(user_id)
    
    # إرسال الرسالة الرئيسية وحفظ معرفها
    sent_message = bot.send_message(message.chat.id, main_message, reply_markup=keyboard)
    user_messages[user_id] = sent_message.message_id

def update_main_menu(user_id, chat_id):
    """تحديث القائمة الرئيسية"""
    try:
        if user_id in user_messages:
            main_message = get_main_message(user_id)
            keyboard = get_main_keyboard(user_id)
            
            bot.edit_message_text(
                main_message,
                chat_id,
                user_messages[user_id],
                reply_markup=keyboard
            )
        else:
            # إعادة إنشاء القائمة إذا تم حذف الرسالة
            show_main_menu(types.Message(message_id=0, chat=types.Chat(id=chat_id), from_user=types.User(id=user_id)))
    except Exception as e:
        logger.error(f"Error updating main menu: {e}")

def check_daily_rewards(user_id):
    """التحقق من المكافآت اليومية"""
    try:
        today = datetime.now().date()
        user_data = get_user_data(user_id)
        
        if not user_data or not user_data['last_active']:
            return None
        
        last_active = datetime.strptime(user_data['last_active'], '%Y-%m-%d').date()
        
        days_diff = (today - last_active).days
        if days_diff == 1:
            user_data['daily_streak'] += 1
        elif days_diff > 1:
            user_data['daily_streak'] = 1
        
        user_data['last_active'] = today.strftime('%Y-%m-%d')
        
        # منح مكافآت بناءً على السلسلة اليومية
        streak = user_data['daily_streak']
        reward_msg = None
        
        if streak > 0 and streak % 7 == 0:  # مكافأة أسبوعية
            bonus = 100
            user_data['total_count'] += bonus
            user_data['total_cumulative'] += bonus
            reward_msg = f"مكافأة أسبوعية! {bonus} نقطة إضافية لاستمرارك {streak} يوم"
        elif streak > 0 and streak % 3 == 0:  # مكافأة كل 3 أيام
            bonus = 50
            user_data['total_count'] += bonus
            user_data['total_cumulative'] += bonus
            reward_msg = f"مكافأة استمرار! {bonus} نقطة إضافية لاستمرارك {streak} يوم"
        
        # تحديث البيانات
        update_user_data(user_id, user_data)
        
        # تحديث المستوى بعد منح المكافأة
        level_msg = update_user_level(user_id)
        if level_msg:
            reward_msg = (reward_msg + "\n" + level_msg) if reward_msg else level_msg
        
        return reward_msg
    except Exception as e:
        logger.error(f"Error in check_daily_rewards: {e}")
        return None

# معالجات الأذكار
@bot.callback_query_handler(func=lambda call: call.data.startswith('dhikr_'))
def handle_dhikr_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
    dhikr_type = call.data.split('_', 1)[1]  # التعديل الهام هنا
    
    dhikr_responses = {
        'subhan': {
            'key': 'subhan_count',
            'cum_key': 'subhan_cumulative',
            'response': "سبحان الله وبحمده، سبحان الله العظيم 🌟"
        },
        'alhamdulillah': {
            'key': 'alhamdulillah_count',
            'cum_key': 'alhamdulillah_cumulative',
            'response': "الحمد لله رب العالمين 🤲"
        },
        'la_ilaha': {
            'key': 'la_ilaha_count',
            'cum_key': 'la_ilaha_cumulative',
            'response': "لا إله إلا الله وحده لا شريك له 🕌"
        },
        'allahu_akbar': {
            'key': 'allahu_akbar_count',
            'cum_key': 'allahu_akbar_cumulative',
            'response': "الله اكبر كبيراً والحمد لله كثيراً 🌙"
        }
    }
    
    if dhikr_type in dhikr_responses:
        info = dhikr_responses[dhikr_type]
        
        # تحديث العداد
        user_data[info['key']] += 1
        user_data[info['cum_key']] += 1  # التراكم
        user_data['total_count'] += 1
        user_data['total_cumulative'] += 1  # التراكم الكلي
        
        # تحديث البيانات في الذاكرة
        update_user_data(user_id, user_data)
        
        # تحديث المستوى
        level_msg = update_user_level(user_id)
        
        # رسالة التأكيد (إشعار غير مزعج)
        confirm_msg = f"✅ {info['response']}\n💎 +10 حسنات بإذن الله"
        
        if level_msg:
            confirm_msg += f"\n🎉 {level_msg}"
        
        # إرسال إشعار غير مزعج (بدون show_alert)
        bot.answer_callback_query(call.id, confirm_msg, show_alert=False)
        
        # تحديث القائمة الرئيسية
        update_main_menu(user_id, call.message.chat.id)

def update_user_level(user_id):
    """تحديث مستوى المستخدم بناءً على التراكمي"""
    try:
        user_data = get_user_data(user_id)
        if not user_data:
            return None
            
        total = user_data['total_cumulative']  # التراكمي
        current_level = user_data['level']
        
        # ترقية المستوى كل 1000 ذكر
        new_level = (total // 1000) + 1
        if new_level > current_level:
            user_data['level'] = new_level
            # تحديث التقدم والمتبقي للمستوى الجديد
            current_level_points = (new_level - 1) * 1000
            user_data['progress'] = total - current_level_points
            user_data['next_level_remaining'] = new_level * 1000 - total
            update_user_data(user_id, user_data)
            return f"تهانينا! وصلت للمستوى {new_level} 🏆"
        return None
    except Exception as e:
        logger.error(f"Error updating user level: {e}")
        return None

@bot.callback_query_handler(func=lambda call: call.data == 'show_total')
def show_total(call):
    user_id = call.from_user.id
    user_data = initialize_user_data(user_id)
    
    total = user_data['total_cumulative']  # إظهار التراكمي
    hasanat = total * 10
    
    bot.answer_callback_query(
        call.id,
        f"📊 مجموع أذكارك التراكمي: {total}\n💎 الحسنات: {hasanat} بإذن الله",
        show_alert=True
    )

@bot.callback_query_handler(func=lambda call: call.data == 'reset_counters')
def reset_counters_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
    # إعادة تعيين العدادات فقط (مع الحفاظ على التراكم)
    user_data['subhan_count'] = 0
    user_data['alhamdulillah_count'] = 0
    user_data['la_ilaha_count'] = 0
    user_data['allahu_akbar_count'] = 0
    user_data['total_count'] = 0
    
    # تحديث البيانات
    update_user_data(user_id, user_data)
    
    bot.answer_callback_query(call.id, "✅ تم مسح جميع العدادات بنجاح!", show_alert=True)
    
    # تحديث القائمة الرئيسية
    update_main_menu(user_id, call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'share_bot')
def share_bot_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
    # حساب التقدم والمتبقي للمستوى بناءً على التراكمي
    total_cumulative = user_data['total_cumulative']
    current_level = user_data['level']
    progress = user_data['progress']
    next_level_remaining = user_data['next_level_remaining']
    progress_percent = min(100, int((progress / 1000) * 100)) if progress > 0 else 0
    
    share_lines = [
        "قال رسول الله ﷺ:",
        "\"من دعا إلى هدى كان له من الأجر مثل أجور من تبعه\"",
        "",
        "📿 بوت نُور الذِّكْر:",
        "https://t.me/Ryukn_bot",
        "",
        "✨ مميزات البوت:",
        "• عدّاد الأذكار التلقائي",
        "• نظام المكافآت والمستويات",
        "• إحصائيات مفصلة",
        "• تذكيرات يومية",
        "",
        f"🏆 مستواي الحالي: {current_level}",
        f"🔥 سلسلة أيامي: {user_data['daily_streak']} يوم",
        "",
        f"🎯 تقدمي: {progress}/1000 ({progress_percent}%)",
        f"⏳ المتبقي للمستوى التالي: {next_level_remaining} ذكر",
        f"💎 أذكاري التراكمية: {total_cumulative}"
    ]
    
    share_text = "\n".join(share_lines)
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "📤 مشاركة البوت", 
            url=f"https://t.me/share/url?url=https://t.me/Ryukn_bot&text={requests.utils.quote(share_text)}"
        )
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        share_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'developer_info')
def developer_info_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("💬 مراسلة المطور", url=f"https://t.me/Akio_co")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        f"👨‍💻 مطور البوت: @Akio_co\n\n"
        "🔧 لأي استفسار، اقتراح، أو مشكلة تقنية\n"
        "📞 تواصل معنا في أي وقت",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'show_stats')
def show_stats_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
    # حساب التقدم للمستوى التالي بناءً على التراكمي
    progress = user_data['progress']
    next_level_remaining = user_data['next_level_remaining']
    progress_percent = min(100, int((progress / 1000) * 100)) if progress > 0 else 0
    
    stats_message = f"""
📊 إحصائياتك الشخصية:

🔢 عدد الأذكار (التراكمي):
• سبحان الله: {user_data['subhan_cumulative']} مرة
• الحمد لله: {user_data['alhamdulillah_cumulative']} مرة
• لا إله إلا الله: {user_data['la_ilaha_cumulative']} مرة
• الله اكبر: {user_data['allahu_akbar_cumulative']} مرة

🔢 عدد الأذكار (الحالي):
• سبحان الله: {user_data['subhan_count']} مرة
• الحمد لله: {user_data['alhamdulillah_count']} مرة
• لا إله إلا الله: {user_data['la_ilaha_count']} مرة
• الله اكبر: {user_data['allahu_akbar_count']} مرة

📈 الإجمالي التراكمي: {user_data['total_cumulative']} ذكر
📈 الإجمالي الحالي: {user_data['total_count']} ذكر
🏆 المستوى: {user_data['level']}
📅 سلسلة الأيام: {user_data['daily_streak']} يوم

🎯 التقدم: {progress}/1000 ({progress_percent}%)
⏳ المتبقي للمستوى التالي: {next_level_remaining} ذكر

💎 الحسنات المكتسبة: {user_data['total_cumulative'] * 10} حسنة بإذن الله
    """
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("📄 تصدير البيانات", callback_data="export_data")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        stats_message,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'settings_menu')
def settings_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    notifications = user_data['notifications']
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            f"🔔 التذكيرات اليومية: {'✅' if notifications else '❌'}",
            callback_data="toggle_notifications"
        )
    )
    keyboard.add(
        types.InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="show_stats")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        "⚙️ إعدادات البوت:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'export_data')
def export_data_callback(call):
    user_id = call.from_user.id
    user_data = initialize_user_data(user_id)
    
    export_text = f"""
📋 بيانات الأذكار الخاصة بك:

📿 عدد الأذكار (التراكمي):
سبحان الله: {user_data['subhan_cumulative']}
الحمد لله: {user_data['alhamdulillah_cumulative']}
لا إله إلا الله: {user_data['la_ilaha_cumulative']}
الله اكبر: {user_data['allahu_akbar_cumulative']}

📿 عدد الأذكار (الحالي):
سبحان الله: {user_data['subhan_count']}
الحمد لله: {user_data['alhamdulillah_count']}
لا إله إلا الله: {user_data['la_ilaha_count']}
الله اكبر: {user_data['allahu_akbar_count']}

📊 الإجمالي التراكمي: {user_data['total_cumulative']}
📊 الإجمالي الحالي: {user_data['total_count']}
🏆 المستوى: {user_data['level']}
🔥 سلسلة الأيام: {user_data['daily_streak']}
📅 تاريخ الانضمام: {user_data['joined_date']}
📅 آخر نشاط: {user_data['last_active']}

🎯 التقدم: {user_data['progress']}/1000
⏳ المتبقي للمستوى التالي: {user_data['next_level_remaining']} ذكر

💎 الحسنات المكتسبة: {user_data['total_cumulative'] * 10}
    """
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للإحصائيات", callback_data="show_stats")
    )
    
    bot.edit_message_text(
        f"<pre>{export_text}</pre>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'toggle_notifications')
def toggle_notifications_callback(call):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    
    user_data['notifications'] = not user_data['notifications']
    update_user_data(user_id, user_data)
    
    status = "✅ مفعلة" if user_data['notifications'] else "❌ معطلة"
    bot.answer_callback_query(call.id, f"التذكيرات اليومية الآن {status}")
    
    # تحديث قائمة الإعدادات
    settings_menu_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main_callback(call):
    user_id = call.from_user.id
    initialize_user_data(user_id)
    
    main_message = get_main_message(user_id)
    keyboard = get_main_keyboard(user_id)
    
    bot.edit_message_text(
        main_message,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

# معالج الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    
    # التحقق من حالة البوت
    if not bot_enabled and user_id != ADMIN_USER_ID:
        bot.reply_to(message, "⛔ البوت متوقف حاليًا عن العمل، يرجى المحاولة لاحقًا")
        return
    
    if not is_user_subscribed(user_id):
        show_subscription_message(message)
        return
    
    # حذف الرسالة النصية من المستخدم لتجنب التكديس
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    # إذا لم تكن هناك رسالة رئيسية، إنشاء واحدة جديدة
    if user_id not in user_messages:
        show_main_menu(message)
    else:
        # إرسال رسالة تنبيه مؤقتة
        temp_msg = bot.send_message(
            message.chat.id,
            "❓ استخدم الأزرار أدناه للتنقل في البوت"
        )
        # حذف الرسالة المؤقتة بعد 3 ثوانٍ
        threading.Timer(3.0, lambda: bot.delete_message(message.chat.id, temp_msg.message_id)).start()

# دالة التذكيرات اليومية
def send_daily_reminders():
    """إرسال تذكيرات يومية للمستخدمين"""
    try:
        with data_lock:
            users = [user_id for user_id, data in users_data.items() 
                    if data.get('notifications', True)]
            
            current_hour = datetime.now().hour
            greeting = "🌅 صباح الخير!" if current_hour < 12 else "🌇 مساء الخير!"
            message_text = "📿 لا تنس أذكار الصباح" if current_hour < 12 else "📿 لا تنس أذكار المساء"
            
            for user_id in users:
                try:
                    bot.send_message(
                        user_id,
                        f"{greeting}\n{message_text}\n🎯 ابدأ يومك بالذكر والتسبيح"
                    )
                except Exception as e:
                    logger.error(f"Error sending reminder to user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error in daily reminders: {e}")

def schedule_reminders():
    """جدولة التذكيرات اليومية"""
    # جدولة التذكير الصباحي (9 صباحاً)
    schedule.every().day.at("09:00").do(send_daily_reminders)
    
    # جدولة التذكير المسائي (9 مساءً)
    schedule.every().day.at("21:00").do(send_daily_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_flask_app():
    """تشغيل خادم Flask"""
    app.run(host='0.0.0.0', port=10000)

# نظام الإدارة
def is_admin(user_id):
    """التحقق من هوية الأدمن"""
    return user_id == ADMIN_USER_ID

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ هذا الأمر مخصص للإدارة فقط")
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(f"{'⏸️ إيقاف البوت' if bot_enabled else '▶️ تشغيل البوت'}", callback_data="toggle_bot"),
        types.InlineKeyboardButton("📥 تصدير البيانات", callback_data="export_all_data")
    )
    keyboard.add(
        types.InlineKeyboardButton("📤 استيراد البيانات", callback_data="import_data"),
        types.InlineKeyboardButton("📨 إنشاء رسالة", callback_data="create_message")
    )
    
    bot.send_message(
        message.chat.id,
        "👨‍💻 لوحة إدارة البوت\nاختر الإجراء المطلوب:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'toggle_bot')
def toggle_bot(call):
    global bot_enabled
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح لك بهذا الإجراء")
        return
    
    bot_enabled = not bot_enabled
    status = "✅ تم تشغيل البوت" if bot_enabled else "⏸️ تم إيقاف البوت"
    bot.answer_callback_query(call.id, status)
    
    # تحديث لوحة الإدارة
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'export_all_data')
def export_all_data(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح لك بهذا الإجراء")
        return
    
    try:
        # تحويل البيانات إلى JSON
        with data_lock:
            data_json = json.dumps(users_data, indent=2, ensure_ascii=False)
        
        # إرسال البيانات كملف
        with io.BytesIO(data_json.encode('utf-8')) as data_file:
            data_file.name = 'users_data.json'
            bot.send_document(
                call.message.chat.id,
                data_file,
                caption="📦 بيانات جميع المستخدمين (JSON)"
            )
        bot.answer_callback_query(call.id, "✅ تم تصدير البيانات بنجاح")
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        bot.answer_callback_query(call.id, "❌ فشل في تصدير البيانات")

@bot.callback_query_handler(func=lambda call: call.data == 'import_data')
def import_data(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح لك بهذا الإجراء")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📤 أرسل ملف البيانات الآن (يجب أن يكون ملف JSON باسم users_data.json)"
    )
    bot.register_next_step_handler(msg, process_import_file)

def process_import_file(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if not message.document:
        bot.reply_to(message, "❌ لم يتم إرسال ملف، يرجى المحاولة مرة أخرى")
        return
    
    try:
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # تحميل البيانات
        new_data = json.loads(downloaded_file.decode('utf-8'))
        
        # استبدال البيانات الحالية
        with data_lock:
            global users_data
            users_data = new_data
        
        bot.reply_to(message, "✅ تم استيراد البيانات بنجاح")
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        bot.reply_to(message, f"❌ فشل في استيراد البيانات: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'create_message')
def create_message(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح لك بهذا الإجراء")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "✍️ اكتب الرسالة التي تريد إرسالها لجميع المستخدمين:"
    )
    bot.register_next_step_handler(msg, broadcast_message)

def broadcast_message(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # الحصول على جميع المستخدمين
    with data_lock:
        users = list(users_data.keys())
    
    total_users = len(users)
    success = 0
    failed = 0
    
    # إرسال الرسالة لكل مستخدم
    for user_id in users:
        try:
            bot.send_message(user_id, message.text)
            success += 1
        except Exception as e:
            logger.error(f"Error broadcasting to user {user_id}: {e}")
            failed += 1
    
    # إرسال التقرير
    report = f"""
📤 تقرير إرسال الرسالة:
• إجمالي المستخدمين: {total_users}
• تم الإرسال بنجاح: {success}
• فشل في الإرسال: {failed}
"""
    bot.reply_to(message, report)

# تشغيل البوت
if __name__ == '__main__':
    try:
        logger.info("Starting bot...")
        
        # بدء خيط التذكيرات اليومية
        reminder_thread = threading.Thread(target=schedule_reminders, daemon=True)
        reminder_thread.start()
        
        # بدء خيط خادم الويب
        web_thread = threading.Thread(target=run_flask_app, daemon=True)
        web_thread.start()
        
        # تشغيل البوت
        bot.infinity_polling(none_stop=True, timeout=30)
    except Exception as e:
        logger.error(f"Bot stopped: {e}")
