import os
import logging
import telebot
from telebot import types
import threading
import time

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
    'total_count': 0
}

def get_user_data(user_id):
    with data_lock:
        return users_data.get(user_id, {}).copy()

def update_user_data(user_id, data):
    with data_lock:
        if user_id not in users_data:
            users_data[user_id] = default_user_data.copy()
        users_data[user_id].update(data)

def initialize_user_data(user_id):
    with data_lock:
        if user_id not in users_data:
            users_data[user_id] = default_user_data.copy()
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
        types.InlineKeyboardButton("👨‍💻 المطور", callback_data="developer_info"),
        types.InlineKeyboardButton("📤 شارك البوت", callback_data="share_bot")
    )
    
    return keyboard

def get_main_message(user_id):
    """إنشاء نص الرسالة الرئيسية"""
    welcome_message = """
🌺 بسم الله الرحمن الرحيم 
اللهم صلي وسلم وبارك على سيدنا محمد 🌹

📿 مرحباً بك في بوت نُور الذِّكْر 
هنا تجني الأجر وتنال الثواب بإذن الله تعالى

✨ طريقة الاستخدام:
اضغط على أي ذكر لزيادة العداد ورفع درجاتك في الجنة

🌿 فوائد الذكر:
• كل ذكر = 10 حسنات ⭐
• محو الذنوب والخطايا 🍃
• رفع الدرجات في الجنة 🕌
• طمأنينة القلب والروح 💖
    """
    
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

# معالجات الأذكار
@bot.callback_query_handler(func=lambda call: call.data.startswith('dhikr_'))
def handle_dhikr_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
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

@bot.callback_query_handler(func=lambda call: call.data == 'show_total')
def show_total(call):
    user_id = call.from_user.id
    user_data = initialize_user_data(user_id)
    
    total = user_data['total_count']
    hasanat = total * 10
    
    bot.answer_callback_query(
        call.id,
        f"📊 مجموع أذكارك: {total}\n💎 الحسنات: {hasanat} بإذن الله",
        show_alert=True
    )

@bot.callback_query_handler(func=lambda call: call.data == 'reset_counters')
def reset_counters_callback(call):
    user_id = call.from_user.id
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
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
    
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
        return
    
    user_data = initialize_user_data(user_id)
    
    share_lines = [
        "قال رسول الله ﷺ:",
        "\"من دعا إلى هدى كان له من الأجر مثل أجور من تبعه\"",
        "",
        "📿 بوت نُور الذِّكْر:",
        "https://t.me/Ryukn_bot",
        "",
        "✨ مميزات البوت:",
        "• عدّاد الأذكار التلقائي",
        "• إحصائيات مفصلة",
        "• تذكيرات يومية",
        "",
        f"💎 أذكاري: {user_data['total_count']}"
    ]
    
    share_text = "\n".join(share_lines)
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "📤 مشاركة البوت", 
            url=f"https://t.me/share/url?url=https://t.me/Ryukn_bot&text={share_text}"
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

# تشغيل البوت
if __name__ == '__main__':
    try:
        logger.info("Starting bot...")
        bot.infinity_polling(none_stop=True, timeout=30)
    except Exception as e:
        logger.error(f"Bot stopped: {e}")
