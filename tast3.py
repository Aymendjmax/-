import os
import logging
import telebot
from telebot import types
from datetime import datetime
import threading
import time
from flask import Flask, Response
import urllib.parse
import random

# تكوين السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@Aymen_dj_max')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1002807434205'))
BOT_TOKEN = os.getenv('BOT_TOKEN')

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
    'chat_id': None,
    'subhan_count': 0,
    'alhamdulillah_count': 0,
    'la_ilaha_count': 0,
    'allahu_akbar_count': 0,
    'total_count': 0
}

# قوائم الأذكار للتذكيرات
morning_dhikr = [
    "سبحان الله وبحمده، سبحان الله العظيم",
    "أصبحنا وأصبح الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
    "اللهم بك أصبحنا، وبك أمسينا، وبك نحيا، وبك نموت، وإليك النشور",
    "اللهم إني أصبحت أشهدك، وأشهد حملة عرشك، وملائكتك، وجميع خلقك، أنك أنت الله لا إله إلا أنت، وحدك لا شريك لك، وأن محمداً عبدك ورسولك"
]

evening_dhikr = [
    "أمسينا وأمسى الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
    "أعوذ بكلمات الله التامات من شر ما خلق",
    "اللهم بك أمسينا، وبك أصبحنا، وبك نحيا، وبك نموت، وإليك المصير",
    "اللهم إني أمسيت أشهدك، وأشهد حملة عرشك، وملائكتك، وجميع خلقك، أنك أنت الله لا إله إلا أنت، وحدك لا شريك لك، وأن محمداً عبدك ورسولك"
]

def get_user_data(user_id):
    with data_lock:
        return users_data.get(user_id, {}).copy()

def update_user_data(user_id, data):
    with data_lock:
        if user_id not in users_data:
            users_data[user_id] = default_user_data.copy()
        users_data[user_id].update(data)

def initialize_user_data(user_id, chat_id=None):
    with data_lock:
        if user_id not in users_data:
            users_data[user_id] = default_user_data.copy()
        if chat_id is not None:
            users_data[user_id]['chat_id'] = chat_id
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
    user_data = get_user_data(user_id)
    
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
        types.InlineKeyboardButton("📊 عرض إحصائياتي", callback_data="show_stats"),
        types.InlineKeyboardButton("🗑️ مسح عدادي", callback_data="reset_counters")
    )
    keyboard.add(
        types.InlineKeyboardButton("👨‍💻 المطور", callback_data="developer_info"),
        types.InlineKeyboardButton("📤 شارك البوت", callback_data="share_bot")
    )
    
    return keyboard

def get_main_message(user_id):
    """إنشاء نص الرسالة الرئيسية"""
    welcome_message = """
🌺 بسم الله الرحمن الرحيم 
اللهم صلي وسلم وبارك على سيدنا محمد 🌹

📿 *مرحباً بك في بوت نُور الذِّكْر* 
هنا تجني الأجر وتنال الثواب بإذن الله تعالى

✨ *طريقة الاستخدام:*
- اضغط على أي ذكر لزيادة العداد ورفع درجاتك في الجنة
- استخدم زر "📊 عرض إحصائياتي" لمشاهدة تفاصيل أذكارك
- شارك البوت مع أحبابك لنيل الأجر والثواب

🌿 *فوائد الذكر:*
• كل ذكر = 10 حسنات ⭐
• محو الذنوب والخطايا 🍃
• رفع الدرجات في الجنة 🕌
• طمأنينة القلب والروح 💖
• تقوية الإيمان واليقين ✨
    """
    
    return welcome_message

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    initialize_user_data(user_id, message.chat.id)
    
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
🕌 *مرحباً بك في بوت نُور الذِّكْر*

⚠️ للاستفادة من البوت، يجب الاشتراك في القناة أولاً

📢 القناة: {CHANNEL_USERNAME}

اضغط على الزر أدناه للاشتراك، ثم اضغط "تحقق من الاشتراك"
    """
    
    bot.send_message(
        message.chat.id,
        subscription_message,
        parse_mode="Markdown",
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
    initialize_user_data(user_id, message.chat.id)
    
    main_message = get_main_message(user_id)
    keyboard = get_main_keyboard(user_id)
    
    # إرسال الرسالة الرئيسية وحفظ معرفها
    sent_message = bot.send_message(message.chat.id, main_message, parse_mode="Markdown", reply_markup=keyboard)
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
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            # إعادة إنشاء القائمة إذا تم حذف الرسالة
            main_message = get_main_message(user_id)
            keyboard = get_main_keyboard(user_id)
            sent_message = bot.send_message(chat_id, main_message, parse_mode="Markdown", reply_markup=keyboard)
            user_messages[user_id] = sent_message.message_id
    except Exception as e:
        logger.error(f"Error updating main menu: {e}")

# معالجات الأذكار
@bot.callback_query_handler(func=lambda call: call.data.startswith('dhikr_'))
def handle_dhikr_callback(call):
    user_id = call.from_user.id
    initialize_user_data(user_id, call.message.chat.id)
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = get_user_data(user_id)
    
    dhikr_type = call.data.split('_', 1)[1]
    
    dhikr_responses = {
        'subhan': {
            'key': 'subhan_count',
            'response': "سبحان الله وبحمده، سبحان الله العظيم 🌟"
        },
        'alhamdulillah': {
            'key': 'alhamdulillah_count',
            'response': "الحمد لله رب العالمين 🤲"
        },
        'la_ilaha': {
            'key': 'la_ilaha_count',
            'response': "لا إله إلا الله وحده لا شريك له 🕌"
        },
        'allahu_akbar': {
            'key': 'allahu_akbar_count',
            'response': "الله اكبر كبيراً والحمد لله كثيراً 🌙"
        }
    }
    
    if dhikr_type in dhikr_responses:
        info = dhikr_responses[dhikr_type]
        
        # تحديث العداد
        user_data[info['key']] += 1
        user_data['total_count'] += 1
        
        # تحديث البيانات في الذاكرة
        update_user_data(user_id, user_data)
        
        # رسالة التأكيد
        confirm_msg = f"✅ {info['response']}\n💎 +10 حسنات بإذن الله"
        
        # إرسال إشعار غير مزعج
        bot.answer_callback_query(call.id, confirm_msg, show_alert=False)
        
        # تحديث القائمة الرئيسية
        update_main_menu(user_id, call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'show_stats')
def show_stats(call):
    user_id = call.from_user.id
    initialize_user_data(user_id, call.message.chat.id)
    user_data = get_user_data(user_id)
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    total = user_data['total_count']
    hasanat = total * 10
    
    stats_message = f"""
📊 *إحصائيات أذكارك التفصيلية:*

• سبحان الله: {user_data['subhan_count']} مرة 🌟
• الحمد لله: {user_data['alhamdulillah_count']} مرة 🤲
• لا إله إلا الله: {user_data['la_ilaha_count']} مرة 🕌
• الله أكبر: {user_data['allahu_akbar_count']} مرة 🌙

📈 *المجموع الكلي:* {total} ذكر
💎 *الحسنات المكتسبة:* {hasanat} حسنة بإذن الله

✨ واصل ذكر الله لترتفع درجاتك في الجنة
    """
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        stats_message,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'reset_counters')
def reset_counters_callback(call):
    user_id = call.from_user.id
    initialize_user_data(user_id, call.message.chat.id)
    user_data = get_user_data(user_id)
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    # إعادة تعيين العدادات
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
    initialize_user_data(user_id, call.message.chat.id)
    user_data = get_user_data(user_id)
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    share_lines = [
        "📿 *بوت نُور الذِّكْر*",
        "أداة رائعة لذكر الله وتحصيل الأجر",
        "",
        "قال رسول الله ﷺ:",
        "\"من دعا إلى هدى كان له من الأجر مثل أجور من تبعه\"",
        "",
        "✨ *مميزات البوت:*",
        "• عدّاد الأذكار التلقائي",
        "• إحصائيات مفصلة",
        "• تذكيرات يومية",
        "• سهولة الاستخدام",
        "",
        f"💎 أذكاري: {user_data['total_count']}",
        "",
        "انضم الآن: https://t.me/Ryukn_bot"
    ]
    
    share_text = "\n".join(share_lines)
    
    # ترميز النص للمشاركة
    encoded_text = urllib.parse.quote(share_text)
    share_url = f"https://t.me/share/url?url=https://t.me/Ryukn_bot&text={encoded_text}"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "📤 مشاركة البوت", 
            url=share_url
        )
    )
    keyboard.add(
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    bot.edit_message_text(
        "📤 *شارك البوت مع أحبابك لنيل الأجر والثواب*\n\n"
        "اضغط على الزر أدناه لمشاركة البوت عبر التليجرام",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == 'developer_info')
def developer_info_callback(call):
    try:
        user_id = call.from_user.id
        initialize_user_data(user_id, call.message.chat.id)
        
        if not is_user_subscribed(user_id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً", show_alert=True)
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("💬 مراسلة المطور", url="https://t.me/Akio_co")
        )
        keyboard.add(
            types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
        )
        
        developer_text = (
            "👨‍💻 معلومات المطور:\n\n"
            "• الاسم: @Akio_co\n"
            "• المهمة: تطوير وتحديث البوت\n\n"
            "🔧 لأي استفسار، اقتراح، أو مشكلة تقنية\n"
            "📞 تواصل معنا في أي وقت"
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=developer_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"حدث خطأ في زر المطور: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main_callback(call):
    user_id = call.from_user.id
    initialize_user_data(user_id, call.message.chat.id)
    
    main_message = get_main_message(user_id)
    keyboard = get_main_keyboard(user_id)
    
    bot.edit_message_text(
        main_message,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# معالج الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    initialize_user_data(user_id, message.chat.id)
    
    if not is_user_subscribed(user_id):
        show_subscription_message(message)
        return
    
    # حذف الرسالة النصية من المستخدم لتجنب التكديس
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # إذا لم تكن هناك رسالة رئيسية، إنشاء واحدة جديدة
    if user_id not in user_messages:
        show_main_menu(message)
    else:
        # إرسال رسالة تنبيه مؤقتة
        try:
            temp_msg = bot.send_message(
                message.chat.id,
                "❓ استخدم الأزرار أدناه للتنقل في البوت"
            )
            # حذف الرسالة المؤقتة بعد 3 ثوانٍ
            threading.Timer(3.0, lambda: bot.delete_message(message.chat.id, temp_msg.message_id)).start()
        except Exception as e:
            logger.error(f"Error sending temporary message: {e}")

# ==================== نظام التذكيرات اليومية ====================
def send_daily_notifications(morning=True):
    """إرسال تذكيرات يومية لجميع المستخدمين"""
    try:
        # نسخ قائمة المستخدمين لتجنب تغييرها أثناء التكرار
        with data_lock:
            user_ids = list(users_data.keys())
        
        for user_id in user_ids:
            try:
                user_data = users_data.get(user_id)
                if not user_data:
                    continue
                    
                chat_id = user_data.get('chat_id')
                if chat_id is None:
                    continue
                
                # التحقق من الاشتراك
                if not is_user_subscribed(user_id):
                    continue
                
                # إعداد الرسالة المناسبة
                if morning:
                    # رسالة الصباح
                    message_text = "🌅 *صباح الخير! حان وقت شروق شمس الأجر* 🌞\n\n"
                    message_text += "☀️ أسأل الله أن يجعل يومك بركة وذكراً وتقوى\n\n"
                    message_text += "🌸 *ذكر الصباح المختار:*\n"
                    message_text += f"➖ {random.choice(morning_dhikr)}\n\n"
                    message_text += "🌟 *فائدة اليوم:*\n"
                    message_text += "> \"من قال حين يصبح: سبحان الله وبحمده، مائة مرة، لم يأت أحد يوم القيامة بأفضل مما جاء به إلا أحد قال مثل ذلك أو زاد\" (رواه مسلم)\n\n"
                    message_text += "📿 استمر في الذكر لتحصد الأجر المضاعف"
                else:
                    # رسالة المساء
                    message_text = "🌄 *مساء الخير! حان وقت غروب شمس الثواب* 🌙\n\n"
                    message_text += "🌠 أسأل الله أن يغفر لك ذنوبك ويرفع درجاتك\n\n"
                    message_text += "🌸 *ذكر المساء المختار:*\n"
                    message_text += f"➖ {random.choice(evening_dhikr)}\n\n"
                    message_text += "🌟 *فائدة اليوم:*\n"
                    message_text += "> \"من قال حين يمسي: سبحان الله وبحمده، مائة مرة، لم يأت أحد يوم القيامة بأفضل مما جاء به إلا أحد قال مثل ذلك أو زاد\" (رواه مسلم)\n\n"
                    message_text += "📿 استمر في الذكر لتحصد الأجر المضاعف"
                
                # تصميم زر للوصول السريع للبوت
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton("📿 افتح بوت الذكر الآن", url="https://t.me/Ryukn_bot")
                )
                
                # إرسال الرسالة بتنسيق جميل
                bot.send_message(
                    chat_id,
                    message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                # تأجيل صغير لتجنب الضغط على الخادم
                time.sleep(0.1)
                
            except telebot.apihelper.ApiException as e:
                if e.result.status_code == 403:  # المستخدم حظر البوت
                    logger.warning(f"User {user_id} blocked the bot. Removing from users_data.")
                    with data_lock:
                        if user_id in users_data:
                            del users_data[user_id]
                else:
                    logger.error(f"Error sending notification to user {user_id}: {e}")
            except Exception as e:
                logger.error(f"Error in sending notification to user {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Error in daily notifications: {e}")

def schedule_daily_notifications():
    """جدولة التذكيرات اليومية"""
    while True:
        try:
            now = datetime.utcnow()
            current_hour = now.hour
            current_minute = now.minute
            
            # تذكير الصباح الساعة 7 صباحاً (توقيت غرينتش)
            if current_hour == 7 and current_minute == 0:
                send_daily_notifications(morning=True)
                logger.info("Sent morning notifications")
            
            # تذكير المساء الساعة 7 مساءً (توقيت غرينتش)
            elif current_hour == 19 and current_minute == 0:
                send_daily_notifications(morning=False)
                logger.info("Sent evening notifications")
            
            # الانتظار 60 ثانية قبل التحقق مرة أخرى
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in notification scheduler: {e}")
            time.sleep(60)  # انتظار قبل إعادة المحاولة

def run_flask_app():
    """تشغيل خادم Flask"""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# تشغيل البوت
if __name__ == '__main__':
    try:
        logger.info("Starting bot...")
        
        # بدء خيط خادم الويب
        web_thread = threading.Thread(target=run_flask_app, daemon=True)
        web_thread.start()
        
        # بدء خيط التذكيرات اليومية
        notification_thread = threading.Thread(target=schedule_daily_notifications, daemon=True)
        notification_thread.start()
        
        # تشغيل البوت
        bot.infinity_polling(none_stop=True, timeout=30)
    except Exception as e:
        logger.error(f"Bot stopped: {e}")
