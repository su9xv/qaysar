import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler
)
import sqlite3
from datetime import datetime

# تكوين السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بيانات البوت
TOKEN = '7902496433:AAHySiP8qLbqwXYG6KPffZ3BqHT2wi9uLqU'
ADMIN_ID = 5945190100
CHANNEL_USERNAME = '@qaysarjo'
CHANNEL_LINK = 'https://t.me/qaysarjo'

# حالات المحادثة
(
    SELECTING_ACTION, SELECTING_CATEGORY, SELECTING_GAME,
    SELECTING_PRODUCT, ENTERING_PLAYER_ID, CONFIRMING_PURCHASE,
    SELECTING_PAYMENT_METHOD, ENTERING_DEPOSIT_AMOUNT, ENTERING_DEPOSIT_NAME,
    ADMIN_MAIN, ADMIN_ADD_CATEGORY, ADMIN_EDIT_CATEGORY,
    ADMIN_ADD_GAME, ADMIN_ADD_PRODUCT, ADMIN_ADD_PAYMENT_METHOD,
    ADMIN_MANAGE_DEPOSITS, ADMIN_MANAGE_ORDERS, ADMIN_SEND_NOTIFICATION,
    ADMIN_ADD_ADMIN, ADMIN_VIEW_USERS, ADMIN_TRANSFER_BALANCE
) = range(21)

# اتصال قاعدة البيانات
conn = sqlite3.connect('qaysar_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """تهيئة قاعدة البيانات"""
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        balance REAL DEFAULT 0,
        total_spent REAL DEFAULT 0,
        join_date TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER,
        name TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (category_id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        name TEXT,
        price REAL,
        FOREIGN KEY (game_id) REFERENCES games (game_id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        player_id TEXT,
        status TEXT,
        order_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payment_methods (
        method_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposits (
        deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method_id INTEGER,
        sender_name TEXT,
        status TEXT,
        deposit_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (method_id) REFERENCES payment_methods (method_id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY,
        username TEXT,
        added_by INTEGER,
        add_date TEXT,
        FOREIGN KEY (added_by) REFERENCES admins (admin_id)
    )''')

    # إضافة الأدمن الرئيسي إذا لم يكن موجودًا
    cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (ADMIN_ID,))
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO admins (admin_id, username, added_by, add_date)
        VALUES (?, ?, ?, ?)
        ''', (ADMIN_ID, 'المالك', ADMIN_ID, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()

init_db()

def is_user_member(update: Update, context: CallbackContext, user_id: int):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

def get_user_info(user_id: int):
    """الحصول على معلومات المستخدم"""
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def register_user(update: Update):
    """تسجيل مستخدم جديد"""
    user = update.effective_user
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO users (user_id, username, first_name, last_name, join_date)
        VALUES (?, ?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, user.last_name, 
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()

def get_categories():
    """الحصول على جميع الأقسام"""
    cursor.execute('SELECT * FROM categories')
    return cursor.fetchall()

def get_category_games(category_id: int):
    """الحصول على ألعاب/تطبيقات قسم معين"""
    cursor.execute('SELECT * FROM games WHERE category_id = ?', (category_id,))
    return cursor.fetchall()

def get_game_products(game_id: int):
    """الحصول على منتجات لعبة/تطبيق معين"""
    cursor.execute('SELECT * FROM products WHERE game_id = ?', (game_id,))
    return cursor.fetchall()

def get_product(product_id: int):
    """الحصول على معلومات منتج"""
    cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
    return cursor.fetchone()

def get_payment_methods():
    """الحصول على طرق الدفع"""
    cursor.execute('SELECT * FROM payment_methods')
    return cursor.fetchall()

def get_payment_method(method_id: int):
    """الحصول على طريقة دفع معينة"""
    cursor.execute('SELECT * FROM payment_methods WHERE method_id = ?', (method_id,))
    return cursor.fetchone()

def get_user_orders(user_id: int):
    """الحصول على طلبات المستخدم"""
    cursor.execute('''
    SELECT o.order_id, p.name, p.price, o.player_id, o.status, o.order_date 
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    WHERE o.user_id = ?
    ORDER BY o.order_date DESC
    ''', (user_id,))
    return cursor.fetchall()

def get_pending_deposits():
    """الحصول على طلبات الإيداع المعلقة"""
    cursor.execute('''
    SELECT d.deposit_id, u.user_id, u.username, d.amount, m.name, d.sender_name, d.deposit_date
    FROM deposits d
    JOIN users u ON d.user_id = u.user_id
    JOIN payment_methods m ON d.method_id = m.method_id
    WHERE d.status = 'pending'
    ORDER BY d.deposit_date DESC
    ''')
    return cursor.fetchall()

def get_pending_orders():
    """الحصول على طلبات الشحن المعلقة"""
    cursor.execute('''
    SELECT o.order_id, u.user_id, u.username, c.name as category, g.name as game, 
           p.name as product, p.price, o.player_id, o.order_date
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    JOIN games g ON p.game_id = g.game_id
    JOIN categories c ON g.category_id = c.category_id
    JOIN users u ON o.user_id = u.user_id
    WHERE o.status = 'pending'
    ORDER BY o.order_date DESC
    ''')
    return cursor.fetchall()

def is_admin(user_id: int):
    """التحقق من إذا كان المستخدم أدمن"""
    cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (user_id,))
    return cursor.fetchone() is not None

def start(update: Update, context: CallbackContext):
    """بدء المحادثة"""
    user = update.effective_user
    register_user(update)
    
    if not is_user_member(update, context, user.id):
        keyboard = [[InlineKeyboardButton("اشترك في القناة", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            '⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت:',
            reply_markup=reply_markup
        )
        return
    
    if is_admin(user.id):
        show_admin_menu(update, context)
        return ADMIN_MAIN
    
    show_main_menu(update)
    return SELECTING_ACTION

def show_main_menu(update, message=None):
    """عرض القائمة الرئيسية"""
    keyboard = [
        [KeyboardButton("شحن الألعاب 🎮"), KeyboardButton("شحن تطبيقات 📱")],
        [KeyboardButton("الإيداع 💳"), KeyboardButton("هل لديك مشكلة ❓")],
        [KeyboardButton("معلومات حسابي 👤")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if message:
        update.message.reply_text(message, reply_markup=reply_markup)
    else:
        update.message.reply_text(
            "مرحباً بك في متجر قيصـر ⚡\n"
            "اختر من القائمة أدناه:",
            reply_markup=reply_markup
        )

def handle_main_commands(update: Update, context: CallbackContext):
    """معالجة أوامر القائمة الرئيسية"""
    text = update.message.text
    
    if text == "شحن الألعاب 🎮":
        show_categories(update, "الألعاب")
        return SELECTING_CATEGORY
        
    elif text == "شحن تطبيقات 📱":
        show_categories(update, "التطبيقات")
        return SELECTING_CATEGORY
        
    elif text == "الإيداع 💳":
        show_payment_methods(update)
        return SELECTING_PAYMENT_METHOD
        
    elif text == "هل لديك مشكلة ❓":
        update.message.reply_text(
            "إذا كنت بحاجة إلى مساعدة، يرجى التواصل مع مدير البوت:\n"
            f"{CHANNEL_USERNAME}"
        )
        return SELECTING_ACTION
        
    elif text == "معلومات حسابي 👤":
        show_user_info(update)
        return SELECTING_ACTION

def show_categories(update: Update, category_type: str):
    """عرض الأقسام"""
    categories = get_categories()
    filtered_categories = [cat for cat in categories if category_type in cat[1]]
    
    if not filtered_categories:
        update.message.reply_text("لا توجد أقسام متاحة حالياً.")
        return SELECTING_ACTION
    
    keyboard = []
    for cat in filtered_categories:
        keyboard.append([InlineKeyboardButton(cat[1], callback_data=f'cat_{cat[0]}')])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"اختر من الأقسام التالية ({category_type}):",
        reply_markup=reply_markup
    )

def select_category(update: Update, context: CallbackContext, category_type: str):
    """اختيار قسم"""
    query = update.callback_query
    query.answer()
    category_id = int(query.data.split('_')[1])
    context.user_data['selected_category'] = category_id
    show_category_games(update, context, category_id)
    return SELECTING_GAME

def show_category_games(update: Update, context: CallbackContext, category_id: int):
    """عرض الألعاب/التطبيقات في القسم"""
    games = get_category_games(category_id)
    
    if not games:
        update.callback_query.edit_message_text("لا توجد ألعاب/تطبيقات متاحة في هذا القسم حالياً.")
        return SELECTING_CATEGORY
    
    keyboard = []
    for game in games:
        keyboard.append([InlineKeyboardButton(game[2], callback_data=f'game_{game[0]}')])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data='back_to_categories')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        "اختر اللعبة/التطبيق:",
        reply_markup=reply_markup
    )

def select_game(update: Update, context: CallbackContext, game_type: str):
    """اختيار لعبة/تطبيق"""
    query = update.callback_query
    query.answer()
    game_id = int(query.data.split('_')[1])
    context.user_data['selected_game'] = game_id
    show_game_products(update, context, game_id)
    return SELECTING_PRODUCT

def show_game_products(update: Update, context: CallbackContext, game_id: int):
    """عرض منتجات اللعبة/التطبيق"""
    products = get_game_products(game_id)
    
    if not products:
        update.callback_query.edit_message_text("لا توجد منتجات متاحة لهذه اللعبة/التطبيق حالياً.")
        return SELECTING_GAME
    
    keyboard = []
    for product in products:
        keyboard.append([InlineKeyboardButton(f"{product[2]} - {product[3]} دينار أردني", callback_data=f'prod_{product[0]}')])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data='back_to_games')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        "اختر المنتج:",
        reply_markup=reply_markup
    )

def select_product(update: Update, context: CallbackContext):
    """اختيار منتج"""
    query = update.callback_query
    query.answer()
    product_id = int(query.data.split('_')[1])
    context.user_data['selected_product'] = product_id
    show_product_details(update, context, product_id)
    return ENTERING_PLAYER_ID

def show_product_details(update: Update, context: CallbackContext, product_id: int):
    """عرض تفاصيل المنتج"""
    product = get_product(product_id)
    game = cursor.execute('SELECT * FROM games WHERE game_id = ?', (product[1],)).fetchone()
    category = cursor.execute('SELECT * FROM categories WHERE category_id = ?', (game[1],)).fetchone()
    
    context.user_data['selected_product'] = product_id
    
    message = (
        f"تفاصيل المنتج:\n\n"
        f"القسم: {category[1]}\n"
        f"اللعبة/التطبيق: {game[2]}\n"
        f"المنتج: {product[2]}\n"
        f"السعر: {product[3]} دينار أردني 🇯🇴\n\n"
        "الرجاء إرسال معرف اللاعب/الحساب:"
    )
    
    update.callback_query.edit_message_text(message)
    return ENTERING_PLAYER_ID

def handle_player_id(update: Update, context: CallbackContext):
    """معالجة معرف اللاعب"""
    player_id = update.message.text
    product_id = context.user_data['selected_product']
    product = get_product(product_id)
    
    context.user_data['player_id'] = player_id
    
    message = (
        f"تأكيد الطلب:\n\n"
        f"المنتج: {product[2]}\n"
        f"السعر: {product[3]} دينار أردني 🇯🇴\n"
        f"معرف اللاعب: {player_id}\n\n"
        "هل تريد تأكيد الطلب؟"
    )
    
    keyboard = [
        [InlineKeyboardButton("تأكيد الشراء", callback_data='confirm_purchase')],
        [InlineKeyboardButton("إلغاء الطلب", callback_data='cancel_purchase')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(message, reply_markup=reply_markup)
    return CONFIRMING_PURCHASE

def confirm_purchase(update: Update, context: CallbackContext):
    """تأكيد عملية الشراء"""
    query = update.callback_query
    user_id = query.from_user.id
    product_id = context.user_data['selected_product']
    player_id = context.user_data['player_id']
    
    product = get_product(product_id)
    user = get_user_info(user_id)
    
    if user[4] >= product[3]:  # إذا كان الرصيد كافي
        # خصم المبلغ من رصيد المستخدم
        new_balance = user[4] - product[3]
        total_spent = user[5] + product[3]
        
        cursor.execute('''
        UPDATE users 
        SET balance = ?, total_spent = ?
        WHERE user_id = ?
        ''', (new_balance, total_spent, user_id))
        
        # تسجيل الطلب
        cursor.execute('''
        INSERT INTO orders (user_id, product_id, player_id, status, order_date)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, product_id, player_id, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        
        # إرسال رسالة التأكيد للمستخدم
        query.edit_message_text(
            f"✅ تم إرسال طلب الشحن بنجاح!\n\n"
            f"المنتج: {product[2]}\n"
            f"السعر: {product[3]} دينار أردني 🇯🇴\n"
            f"معرف اللاعب: {player_id}\n\n"
            "سيتم الرد عليك عند قبول الطلب من قبل الإدارة.\n"
            f"رصيدك الحالي: {new_balance} دينار أردني 🇯🇴"
        )
        
        # إعلام الإداريين بوجود طلب جديد
        admins = cursor.execute('SELECT admin_id FROM admins').fetchall()
        for admin in admins:
            context.bot.send_message(
                admin[0],
                f"⚠️ هناك طلب شحن جديد!\n\n"
                f"المستخدم: @{user[1]}\n"
                f"المنتج: {product[2]}\n"
                f"السعر: {product[3]} دينار أردني 🇯🇴\n"
                f"معرف اللاعب: {player_id}"
            )
    else:
        query.edit_message_text(
            "❌ رصيدك غير كافي لإتمام هذه العملية.\n"
            f"سعر المنتج: {product[3]} دينار أردني 🇯🇴\n"
            f"رصيدك الحالي: {user[4]} دينار أردني 🇯🇴\n\n"
            "الرجاء شحن الرصيد أولاً."
        )
    
    return SELECTING_ACTION

def cancel_purchase(update: Update, context: CallbackContext):
    """إلغاء عملية الشراء"""
    query = update.callback_query
    query.edit_message_text("تم إلغاء الطلب.")
    show_main_menu(update, "اختر من القائمة أدناه:")
    return SELECTING_ACTION

def show_payment_methods(update: Update):
    """عرض طرق الدفع"""
    methods = get_payment_methods()
    
    if not methods:
        update.message.reply_text("لا توجد طرق دفع متاحة حالياً.")
        return SELECTING_ACTION
    
    keyboard = []
    for method in methods:
        keyboard.append([InlineKeyboardButton(method[1], callback_data=f'method_{method[0]}')])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "اختر طريقة الدفع:",
        reply_markup=reply_markup
    )

def select_payment_method(update: Update, context: CallbackContext):
    """اختيار طريقة دفع"""
    query = update.callback_query
    query.answer()
    method_id = int(query.data.split('_')[1])
    context.user_data['selected_method'] = method_id
    show_method_details(update, context, method_id)
    return ENTERING_DEPOSIT_AMOUNT

def show_method_details(update: Update, context: CallbackContext, method_id: int):
    """عرض تفاصيل طريقة الدفع"""
    method = get_payment_method(method_id)
    context.user_data['selected_method'] = method_id
    
    keyboard = [[InlineKeyboardButton("هل قمت بالتحويل؟", callback_data='did_transfer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        f"طريقة الدفع: {method[1]}\n\n"
        f"{method[2]}\n\n"
        "بعد إتمام التحويل، اضغط على الزر أدناه:",
        reply_markup=reply_markup
    )

def ask_for_deposit_details(update: Update, context: CallbackContext):
    """طلب تفاصيل الإيداع"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال المبلغ الذي قمت بتحويله (بالدينار الأردني):"
    )
    return ENTERING_DEPOSIT_AMOUNT

def handle_deposit_amount(update: Update, context: CallbackContext):
    """معالجة مبلغ الإيداع"""
    amount_text = update.message.text
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("الرجاء إدخال مبلغ صحيح موجب (مثال: 10.5)")
        return ENTERING_DEPOSIT_AMOUNT
    
    context.user_data['deposit_amount'] = amount
    update.message.reply_text(
        "الرجاء إرسال اسم صاحب الحساب الذي تم التحويل منه (كما هو مسجل في البنك):"
    )
    return ENTERING_DEPOSIT_NAME

def handle_deposit_name(update: Update, context: CallbackContext):
    """معالجة اسم المرسل"""
    sender_name = update.message.text
    user_id = update.effective_user.id
    method_id = context.user_data['selected_method']
    amount = context.user_data['deposit_amount']
    
    # تسجيل طلب الإيداع
    cursor.execute('''
    INSERT INTO deposits (user_id, amount, method_id, sender_name, status, deposit_date)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, method_id, sender_name, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    
    # إعلام المستخدم
    update.message.reply_text(
        "✅ تم إرسال طلب الإيداع للتحقق اليدوي من قبل الإدارة.\n"
        "سيتم إعلامك عند الموافقة على الطلب."
    )
    
    # إعلام الإداريين
    admins = cursor.execute('SELECT admin_id FROM admins').fetchall()
    user = get_user_info(user_id)
    method = get_payment_method(method_id)
    
    for admin in admins:
        context.bot.send_message(
            admin[0],
            f"⚠️ هناك طلب إيداع جديد!\n\n"
            f"المستخدم: @{user[1]}\n"
            f"المبلغ: {amount} دينار أردني 🇯🇴\n"
            f"طريقة الدفع: {method[1]}\n"
            f"اسم المرسل: {sender_name}"
        )
    
    return SELECTING_ACTION

def show_user_info(update: Update):
    """عرض معلومات المستخدم"""
    user_id = update.effective_user.id
    user = get_user_info(user_id)
    orders = get_user_orders(user_id)
    
    message = (
        f"معلومات حسابك 👤\n\n"
        f"الاسم: {user[2]} {user[3] or ''}\n"
        f"اسم المستخدم: @{user[1]}\n"
        f"رقم المعرف: {user[0]}\n"
        f"تاريخ الانضمام: {user[6]}\n\n"
        f"الرصيد الحالي: {user[4]} دينار أردني 🇯🇴\n"
        f"إجمالي المصروفات: {user[5]} دينار أردني 🇯🇴\n\n"
        f"عدد الطلبات السابقة: {len(orders)}"
    )
    
    update.message.reply_text(message)

def show_admin_menu(update: Update, context: CallbackContext):
    """عرض قائمة الإدارة"""
    keyboard = [
        [InlineKeyboardButton("إضافة أقسام", callback_data='add_category')],
        [InlineKeyboardButton("تعديل الأقسام", callback_data='edit_category')],
        [InlineKeyboardButton("إضافة وسيلة دفع", callback_data='add_payment_method')],
        [InlineKeyboardButton("طلبات الإيداع", callback_data='manage_deposits')],
        [InlineKeyboardButton("طلبات الشحن", callback_data='manage_orders')],
        [InlineKeyboardButton("تحويل رصيد 💰", callback_data='transfer_balance')],
        [InlineKeyboardButton("إرسال إشعارات", callback_data='send_notification')],
        [InlineKeyboardButton("إضافة أدمن", callback_data='add_admin')],
        [InlineKeyboardButton("عرض المستخدمين", callback_data='view_users')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "👑 لوحة التحكم الإدارية:\n"
        "اختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

def admin_add_category(update: Update, context: CallbackContext):
    """إضافة قسم جديد"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال اسم القسم الجديد:"
    )
    return ADMIN_ADD_CATEGORY

def handle_category_name(update: Update, context: CallbackContext):
    """معالجة اسم القسم"""
    category_name = update.message.text
    context.user_data['new_category_name'] = category_name
    
    update.message.reply_text(
        "الرجاء إرسال وصف القسم:"
    )
    return ADMIN_ADD_CATEGORY

def handle_category_description(update: Update, context: CallbackContext):
    """معالجة وصف القسم"""
    category_name = context.user_data['new_category_name']
    description = update.message.text
    
    # حفظ القسم في قاعدة البيانات
    cursor.execute('''
    INSERT INTO categories (name, description)
    VALUES (?, ?)
    ''', (category_name, description))
    
    conn.commit()
    
    update.message.reply_text(
        f"✅ تم إضافة القسم '{category_name}' بنجاح!"
    )
    show_admin_menu(update, context)
    return ADMIN_MAIN

def admin_edit_category(update: Update, context: CallbackContext):
    """تعديل الأقسام"""
    categories = get_categories()
    
    if not categories:
        update.callback_query.edit_message_text("لا توجد أقسام متاحة للتعديل.")
        show_admin_menu(update, context)
        return ADMIN_MAIN
    
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat[1], callback_data=f'editcat_{cat[0]}')])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data='back_to_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        "اختر القسم للتعديل:",
        reply_markup=reply_markup
    )

def admin_manage_category(update: Update, context: CallbackContext, category_id: int):
    """إدارة القسم"""
    category = cursor.execute('SELECT * FROM categories WHERE category_id = ?', (category_id,)).fetchone()
    context.user_data['editing_category'] = category_id
    
    keyboard = [
        [InlineKeyboardButton("تعديل الاسم", callback_data='edit_category_name')],
        [InlineKeyboardButton("تعديل الوصف", callback_data='edit_category_desc')],
        [InlineKeyboardButton("إضافة لعبة/تطبيق", callback_data='add_game_to_category')],
        [InlineKeyboardButton("عرض الألعاب/التطبيقات", callback_data='view_category_games')],
        [InlineKeyboardButton("رجوع", callback_data='back_to_edit_category')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        f"إدارة القسم: {category[1]}\n\n"
        f"الوصف: {category[2]}\n\n"
        "اختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

def admin_edit_category_name(update: Update, context: CallbackContext):
    """تعديل اسم القسم"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال الاسم الجديد للقسم:"
    )
    return ADMIN_EDIT_CATEGORY

def admin_save_category_name(update: Update, context: CallbackContext):
    """حفظ اسم القسم الجديد"""
    new_name = update.message.text
    category_id = context.user_data['editing_category']
    
    cursor.execute('''
    UPDATE categories
    SET name = ?
    WHERE category_id = ?
    ''', (new_name, category_id))
    
    conn.commit()
    
    update.message.reply_text("✅ تم تحديث اسم القسم بنجاح!")
    admin_manage_category(update, context, category_id)
    return ADMIN_MAIN

def admin_edit_category_desc(update: Update, context: CallbackContext):
    """تعديل وصف القسم"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال الوصف الجديد للقسم:"
    )
    return ADMIN_EDIT_CATEGORY

def admin_save_category_desc(update: Update, context: CallbackContext):
    """حفظ وصف القسم الجديد"""
    new_desc = update.message.text
    category_id = context.user_data['editing_category']
    
    cursor.execute('''
    UPDATE categories
    SET description = ?
    WHERE category_id = ?
    ''', (new_desc, category_id))
    
    conn.commit()
    
    update.message.reply_text("✅ تم تحديث وصف القسم بنجاح!")
    admin_manage_category(update, context, category_id)
    return ADMIN_MAIN

def admin_add_game(update: Update, context: CallbackContext):
    """إضافة لعبة/تطبيق جديد"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال اسم اللعبة/التطبيق الجديد:"
    )
    return ADMIN_ADD_GAME

def admin_save_game(update: Update, context: CallbackContext):
    """حفظ اللعبة/التطبيق الجديد"""
    game_name = update.message.text
    category_id = context.user_data['editing_category']
    
    cursor.execute('''
    INSERT INTO games (category_id, name)
    VALUES (?, ?)
    ''', (category_id, game_name))
    
    conn.commit()
    
    update.message.reply_text(
        f"✅ تم إضافة اللعبة/التطبيق '{game_name}' بنجاح!"
    )
    admin_manage_category(update, context, category_id)
    return ADMIN_MAIN

def admin_view_category_games(update: Update, context: CallbackContext, category_id: int):
    """عرض ألعاب/تطبيقات القسم"""
    games = get_category_games(category_id)
    
    if not games:
        update.callback_query.edit_message_text("لا توجد ألعاب/تطبيقات في هذا القسم.")
        return
    
    message = "الألعاب/التطبيقات في هذا القسم:\n\n"
    for game in games:
        products = get_game_products(game[0])
        message += f"- {game[2]} (عدد المنتجات: {len(products)})\n"
    
    keyboard = [[InlineKeyboardButton("رجوع", callback_data=f'back_to_category_{category_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

def admin_manage_game(update: Update, context: CallbackContext, game_id: int):
    """إدارة لعبة/تطبيق"""
    game = cursor.execute('SELECT * FROM games WHERE game_id = ?', (game_id,)).fetchone()
    context.user_data['editing_game'] = game_id
    
    products = get_game_products(game_id)
    
    keyboard = [
        [InlineKeyboardButton("إضافة منتج", callback_data='add_product_to_game')],
        [InlineKeyboardButton("عرض المنتجات", callback_data='view_game_products')],
        [InlineKeyboardButton("حذف اللعبة/التطبيق", callback_data='delete_game')],
        [InlineKeyboardButton("رجوع", callback_data=f'back_to_category_{game[1]}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        f"إدارة اللعبة/التطبيق: {game[2]}\n\n"
        f"عدد المنتجات: {len(products)}\n\n"
        "اختر الإجراء المطلوب:",
        reply_markup=reply_markup
    )

def admin_add_product(update: Update, context: CallbackContext):
    """إضافة منتج جديد"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال اسم المنتج الجديد:"
    )
    return ADMIN_ADD_PRODUCT

def admin_save_product_name(update: Update, context: CallbackContext):
    """حفظ اسم المنتج الجديد"""
    product_name = update.message.text
    context.user_data['new_product_name'] = product_name
    
    update.message.reply_text(
        "الرجاء إرسال سعر المنتج (بالدينار الأردني):"
    )
    return ADMIN_ADD_PRODUCT

def admin_save_product_price(update: Update, context: CallbackContext):
    """حفظ سعر المنتج الجديد"""
    price_text = update.message.text
    try:
        price = float(price_text)
        if price <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("الرجاء إدخال سعر صحيح موجب (مثال: 10.5)")
        return ADMIN_ADD_PRODUCT
    
    product_name = context.user_data['new_product_name']
    game_id = context.user_data['editing_game']
    
    cursor.execute('''
    INSERT INTO products (game_id, name, price)
    VALUES (?, ?, ?)
    ''', (game_id, product_name, price))
    
    conn.commit()
    
    update.message.reply_text(
        f"✅ تم إضافة المنتج '{product_name}' بسعر {price} دينار أردني بنجاح!"
    )
    admin_manage_game(update, context, game_id)
    return ADMIN_MAIN

def admin_view_game_products(update: Update, context: CallbackContext, game_id: int):
    """عرض منتجات لعبة/تطبيق"""
    products = get_game_products(game_id)
    
    if not products:
        update.callback_query.edit_message_text("لا توجد منتجات متاحة لهذه اللعبة/التطبيق.")
        return
    
    message = "منتجات هذه اللعبة/التطبيق:\n\n"
    for product in products:
        message += f"- {product[2]} - {product[3]} دينار أردني 🇯🇴\n"
    
    keyboard = [[InlineKeyboardButton("رجوع", callback_data=f'back_to_game_{game_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

def admin_add_payment_method(update: Update, context: CallbackContext):
    """إضافة طريقة دفع جديدة"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال اسم طريقة الدفع الجديدة:"
    )
    return ADMIN_ADD_PAYMENT_METHOD

def admin_save_payment_method_name(update: Update, context: CallbackContext):
    """حفظ اسم طريقة الدفع الجديدة"""
    method_name = update.message.text
    context.user_data['new_method_name'] = method_name
    
    update.message.reply_text(
        "الرجاء إرسال وصف طريقة الدفع (تعليمات التحويل):"
    )
    return ADMIN_ADD_PAYMENT_METHOD

def admin_save_payment_method_desc(update: Update, context: CallbackContext):
    """حفظ وصف طريقة الدفع الجديدة"""
    method_name = context.user_data['new_method_name']
    description = update.message.text
    
    cursor.execute('''
    INSERT INTO payment_methods (name, description)
    VALUES (?, ?)
    ''', (method_name, description))
    
    conn.commit()
    
    update.message.reply_text(
        f"✅ تم إضافة طريقة الدفع '{method_name}' بنجاح!"
    )
    show_admin_menu(update, context)
    return ADMIN_MAIN

def admin_manage_deposits(update: Update, context: CallbackContext):
    """إدارة طلبات الإيداع"""
    deposits = get_pending_deposits()
    
    if not deposits:
        update.callback_query.edit_message_text("لا توجد طلبات إيداع معلقة حالياً.")
        show_admin_menu(update, context)
        return ADMIN_MAIN
    
    keyboard = [[InlineKeyboardButton("عرض طلبات الإيداع", callback_data='view_deposit_requests')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        f"هناك {len(deposits)} طلبات إيداع معلقة.\n"
        "اضغط على الزر أدناه لعرضها:",
        reply_markup=reply_markup
    )

def admin_view_deposit_requests(update: Update, context: CallbackContext):
    """عرض طلبات الإيداع"""
    deposits = get_pending_deposits()
    
    for i, deposit in enumerate(deposits, 1):
        message = (
            f"طلب الإيداع #{i}\n\n"
            f"المستخدم: @{deposit[2]}\n"
            f"المبلغ: {deposit[3]} دينار أردني 🇯🇴\n"
            f"طريقة الدفع: {deposit[4]}\n"
            f"اسم المرسل: {deposit[5]}\n"
            f"تاريخ الطلب: {deposit[6]}\n\n"
            "اختر الإجراء:"
        )
        
        keyboard = [
            [InlineKeyboardButton("قبول", callback_data=f'accept_deposit_{deposit[0]}')],
            [InlineKeyboardButton("رفض", callback_data=f'reject_deposit_{deposit[0]}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            update.callback_query.from_user.id,
            message,
            reply_markup=reply_markup
        )
    
    update.callback_query.edit_message_text(
        f"تم عرض {len(deposits)} طلبات إيداع."
    )

def admin_handle_deposit_decision(update: Update, context: CallbackContext, deposit_id: int, decision: str):
    """معالجة قرار الإيداع"""
    deposit = cursor.execute('''
    SELECT d.*, u.user_id, u.username, u.balance
    FROM deposits d
    JOIN users u ON d.user_id = u.user_id
    WHERE d.deposit_id = ?
    ''', (deposit_id,)).fetchone()
    
    if decision == 'accept':
        # تحديث رصيد المستخدم
        new_balance = deposit[8] + deposit[2]
        cursor.execute('''
        UPDATE users
        SET balance = ?
        WHERE user_id = ?
        ''', (new_balance, deposit[6]))
        
        # تحديث حالة الإيداع
        cursor.execute('''
        UPDATE deposits
        SET status = 'completed'
        WHERE deposit_id = ?
        ''', (deposit_id,))
        
        conn.commit()
        
        # إعلام المستخدم
        context.bot.send_message(
            deposit[6],
            f"✅ تم قبول طلب الإيداع الخاص بك!\n\n"
            f"المبلغ: {deposit[2]} دينار أردني 🇯🇴\n"
            f"رصيدك الحالي: {new_balance} دينار أردني 🇯🇴\n\n"
            "شكراً لاستخدامك متجر قيصـر ⚡"
        )
        
        update.callback_query.edit_message_text(
            f"تم قبول طلب الإيداع وقامت بإضافة {deposit[2]} دينار أردني إلى رصيد المستخدم @{deposit[7]}"
        )
    else:
        # تحديث حالة الإيداع
        cursor.execute('''
        UPDATE deposits
        SET status = 'rejected'
        WHERE deposit_id = ?
        ''', (deposit_id,))
        
        conn.commit()
        
        # إعلام المستخدم
        context.bot.send_message(
            deposit[6],
            f"❌ تم رفض طلب الإيداع الخاص بك!\n\n"
            f"المبلغ: {deposit[2]} دينار أردني 🇯🇴\n"
            f"رصيدك الحالي: {deposit[8]} دينار أردني 🇯🇴\n\n"
            "للمساعدة، يرجى التواصل مع الإدارة."
        )
        
        update.callback_query.edit_message_text(
            f"تم رفض طلب الإيداع للمستخدم @{deposit[7]}"
        )

def admin_manage_orders(update: Update, context: CallbackContext):
    """إدارة طلبات الشحن"""
    orders = get_pending_orders()
    
    if not orders:
        update.callback_query.edit_message_text("لا توجد طلبات شحن معلقة حالياً.")
        show_admin_menu(update, context)
        return ADMIN_MAIN
    
    keyboard = [[InlineKeyboardButton("عرض طلبات الشحن", callback_data='view_order_requests')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        f"هناك {len(orders)} طلبات شحن معلقة.\n"
        "اضغط على الزر أدناه لعرضها:",
        reply_markup=reply_markup
    )

def admin_view_order_requests(update: Update, context: CallbackContext):
    """عرض طلبات الشحن"""
    orders = get_pending_orders()
    
    for i, order in enumerate(orders, 1):
        message = (
            f"طلب الشحن #{i}\n\n"
            f"المستخدم: @{order[2]}\n"
            f"القسم: {order[3]}\n"
            f"اللعبة/التطبيق: {order[4]}\n"
            f"المنتج: {order[5]} - {order[6]} دينار أردني 🇯🇴\n"
            f"معرف اللاعب: {order[7]}\n"
            f"تاريخ الطلب: {order[8]}\n\n"
            "اختر الإجراء:"
        )
        
        keyboard = [
            [InlineKeyboardButton("قبول", callback_data=f'accept_order_{order[0]}')],
            [InlineKeyboardButton("رفض", callback_data=f'reject_order_{order[0]}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            update.callback_query.from_user.id,
            message,
            reply_markup=reply_markup
        )
    
    update.callback_query.edit_message_text(
        f"تم عرض {len(orders)} طلبات شحن."
    )

def admin_handle_order_decision(update: Update, context: CallbackContext, order_id: int, decision: str):
    """معالجة قرار الشحن"""
    order = cursor.execute('''
    SELECT o.*, u.user_id, u.username, u.balance, p.name, p.price
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
    JOIN products p ON o.product_id = p.product_id
    WHERE o.order_id = ?
    ''', (order_id,)).fetchone()
    
    if decision == 'accept':
        # تحديث حالة الطلب
        cursor.execute('''
        UPDATE orders
        SET status = 'completed'
        WHERE order_id = ?
        ''', (order_id,))
        
        conn.commit()
        
        # إعلام المستخدم
        context.bot.send_message(
            order[7],
            f"✅ تم شحن طلبك بنجاح!\n\n"
            f"المنتج: {order[11]}\n"
            f"السعر: {order[12]} دينار أردني 🇯🇴\n"
            f"معرف اللاعب: {order[4]}\n\n"
            "شكراً لاستخدامك متجر قيصـر ⚡"
        )
        
        update.callback_query.edit_message_text(
            f"تم قبول طلب الشحن للمستخدم @{order[8]}"
        )
    else:
        # استعادة الرصيد للمستخدم
        new_balance = order[9] + order[12]
        cursor.execute('''
        UPDATE users
        SET balance = ?, total_spent = total_spent - ?
        WHERE user_id = ?
        ''', (new_balance, order[12], order[7]))
        
        # تحديث حالة الطلب
        cursor.execute('''
        UPDATE orders
        SET status = 'rejected'
        WHERE order_id = ?
        ''', (order_id,))
        
        conn.commit()
        
        # إعلام المستخدم
        context.bot.send_message(
            order[7],
            f"❌ تم رفض طلب الشحن الخاص بك!\n\n"
            f"المنتج: {order[11]}\n"
            f"تم إعادة {order[12]} دينار أردني إلى رصيدك.\n"
            f"رصيدك الحالي: {new_balance} دينار أردني 🇯🇴\n\n"
            "للمساعدة، يرجى التواصل مع الإدارة."
        )
        
        update.callback_query.edit_message_text(
            f"تم رفض طلب الشحن للمستخدم @{order[8]} وإعادة {order[12]} دينار أردني إلى رصيده"
        )

def admin_transfer_balance(update: Update, context: CallbackContext):
    """تحويل رصيد"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال معرف المستلم (user ID):"
    )
    return ADMIN_TRANSFER_BALANCE

def admin_handle_transfer_user(update: Update, context: CallbackContext):
    """معالجة معرف المستلم"""
    user_id_text = update.message.text
    try:
        user_id = int(user_id_text)
    except ValueError:
        update.message.reply_text("الرجاء إدخال معرف مستخدم صحيح (أرقام فقط)")
        return ADMIN_TRANSFER_BALANCE
    
    user = get_user_info(user_id)
    if not user:
        update.message.reply_text("لم يتم العثور على المستخدم. الرجاء التأكد من المعرف.")
        return ADMIN_TRANSFER_BALANCE
    
    context.user_data['transfer_user_id'] = user_id
    context.user_data['transfer_username'] = user[1]
    
    update.message.reply_text(
        f"المستخدم: @{user[1]}\n"
        "الرجاء إرسال المبلغ المراد تحويله (بالدينار الأردني):"
    )
    return ADMIN_TRANSFER_BALANCE

def admin_handle_transfer_amount(update: Update, context: CallbackContext):
    """معالجة مبلغ التحويل"""
    amount_text = update.message.text
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("الرجاء إدخال مبلغ صحيح موجب (مثال: 10.5)")
        return ADMIN_TRANSFER_BALANCE
    
    user_id = context.user_data['transfer_user_id']
    username = context.user_data['transfer_username']
    
    # تحديث رصيد المستخدم
    user = get_user_info(user_id)
    new_balance = user[4] + amount
    
    cursor.execute('''
    UPDATE users
    SET balance = ?
    WHERE user_id = ?
    ''', (new_balance, user_id))
    
    conn.commit()
    
    # إعلام المستخدم
    context.bot.send_message(
        user_id,
        f"✅ تم إضافة رصيد إلى حسابك!\n\n"
        f"المبلغ: {amount} دينار أردني 🇯🇴\n"
        f"رصيدك الحالي: {new_balance} دينار أردني 🇯🇴\n\n"
        "شكراً لاستخدامك متجر قيصـر ⚡"
    )
    
    update.message.reply_text(
        f"تم تحويل {amount} دينار أردني بنجاح إلى المستخدم @{username}"
    )
    show_admin_menu(update, context)
    return ADMIN_MAIN

def admin_send_notification(update: Update, context: CallbackContext):
    """إرسال إشعار"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال الرسالة التي تريد إرسالها لجميع المستخدمين:"
    )
    return ADMIN_SEND_NOTIFICATION

def admin_handle_notification(update: Update, context: CallbackContext):
    """معالجة الإشعار"""
    message = update.message.text
    users = cursor.execute('SELECT user_id FROM users').fetchall()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            context.bot.send_message(
                user[0],
                f"📢 إشعار من إدارة متجر قيصـر ⚡:\n\n{message}"
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send notification to {user[0]}: {e}")
            failed += 1
    
    update.message.reply_text(
        f"تم إرسال الإشعار بنجاح إلى {success} مستخدم.\n"
        f"فشل الإرسال إلى {failed} مستخدم."
    )
    show_admin_menu(update, context)
    return ADMIN_MAIN

def admin_add_admin(update: Update, context: CallbackContext):
    """إضافة أدمن"""
    query = update.callback_query
    query.edit_message_text(
        "الرجاء إرسال معرف المستخدم (user ID) الذي تريد ترقيته إلى أدمن:"
    )
    return ADMIN_ADD_ADMIN

def admin_handle_new_admin(update: Update, context: CallbackContext):
    """معالجة إضافة أدمن جديد"""
    admin_id_text = update.message.text
    try:
        admin_id = int(admin_id_text)
    except ValueError:
        update.message.reply_text("الرجاء إدخال معرف مستخدم صحيح (أرقام فقط)")
        return ADMIN_ADD_ADMIN
    
    # التحقق من عدم وجود المستخدم بالفعل كأدمن
    cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (admin_id,))
    if cursor.fetchone():
        update.message.reply_text("هذا المستخدم مسجل بالفعل كأدمن!")
        show_admin_menu(update, context)
        return ADMIN_MAIN
    
    # الحصول على معلومات المستخدم
    try:
        user = context.bot.get_chat(admin_id)
        username = user.username if user.username else "لا يوجد"
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        update.message.reply_text("حدث خطأ أثناء جلب معلومات المستخدم. الرجاء التأكد من المعرف.")
        return ADMIN_ADD_ADMIN
    
    # إضافة الأدمن الجديد
    adding_admin = update.effective_user.id
    cursor.execute('''
    INSERT INTO admins (admin_id, username, added_by, add_date)
    VALUES (?, ?, ?, ?)
    ''', (admin_id, username, adding_admin, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    
    # إعلام الأدمن الجديد
    try:
        context.bot.send_message(
            admin_id,
            "🎉 تم ترقيتك إلى أدمن في متجر قيصـر ⚡!\n\n"
            "يمكنك الآن الوصول إلى لوحة التحكم الإدارية."
        )
    except Exception as e:
        logger.error(f"Failed to notify new admin: {e}")
    
    update.message.reply_text(
        f"✅ تمت ترقية المستخدم @{username} إلى أدمن بنجاح!"
    )
    show_admin_menu(update, context)
    return ADMIN_MAIN

def admin_view_users(update: Update, context: CallbackContext):
    """عرض المستخدمين"""
    users = cursor.execute('''
    SELECT user_id, username, first_name, last_name, balance, total_spent, join_date
    FROM users
    ORDER BY join_date DESC
    LIMIT 50
    ''').fetchall()
    
    if not users:
        update.callback_query.edit_message_text("لا يوجد مستخدمين مسجلين بعد.")
        return
    
    message = "آخر 50 مستخدم:\n\n"
    for user in users:
        message += (
            f"👤 {user[2]} {user[3] or ''}\n"
            f"🆔 ID: {user[0]}\n"
            f"📧 @{user[1]}\n"
            f"💰 الرصيد: {user[4]} دينار أردني 🇯🇴\n"
            f"💸 إجمالي المصروفات: {user[5]} دينار أردني 🇯🇴\n"
            f"📅 تاريخ الانضمام: {user[6]}\n\n"
        )
    
    update.callback_query.edit_message_text(message[:4000])

def back_to_main(update: Update, context: CallbackContext):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    show_main_menu(update)
    query.answer()
    return SELECTING_ACTION

def back_to_categories(update: Update, context: CallbackContext):
    """العودة للأقسام"""
    query = update.callback_query
    show_main_menu(update)
    query.answer()
    return SELECTING_ACTION

def back_to_games(update: Update, context: CallbackContext):
    """العودة للألعاب"""
    query = update.callback_query
    category_id = context.user_data.get('selected_category')
    show_category_games(update, context, category_id)
    query.answer()
    return SELECTING_GAME

def back_to_admin(update: Update, context: CallbackContext):
    """العودة لقائمة الإدارة"""
    query = update.callback_query
    show_admin_menu(update, context)
    query.answer()
    return ADMIN_MAIN

def back_to_edit_category(update: Update, context: CallbackContext):
    """العودة لتعديل الأقسام"""
    query = update.callback_query
    admin_edit_category(update, context)
    query.answer()
    return ADMIN_EDIT_CATEGORY

def error(update: Update, context: CallbackContext):
    """معالجة الأخطاء"""
    logger.warning(f'Update "{update}" caused error "{context.error}"')

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # محادثة المستخدم
    user_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(Filters.regex('^(شحن الألعاب 🎮|شحن تطبيقات 📱|الإيداع 💳|هل لديك مشكلة ❓|معلومات حسابي 👤)$'), 
                handle_main_commands),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$')
            ],
            SELECTING_CATEGORY: [
                CallbackQueryHandler(select_category, pattern='^cat_'),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$')
            ],
            SELECTING_GAME: [
                CallbackQueryHandler(select_game, pattern='^game_'),
                CallbackQueryHandler(back_to_categories, pattern='^back_to_categories$')
            ],
            SELECTING_PRODUCT: [
                CallbackQueryHandler(select_product, pattern='^prod_'),
                CallbackQueryHandler(back_to_games, pattern='^back_to_games$')
            ],
            ENTERING_PLAYER_ID: [
                MessageHandler(Filters.text & ~Filters.command, handle_player_id)
            ],
            CONFIRMING_PURCHASE: [
                CallbackQueryHandler(confirm_purchase, pattern='^confirm_purchase$'),
                CallbackQueryHandler(cancel_purchase, pattern='^cancel_purchase$')
            ],
            SELECTING_PAYMENT_METHOD: [
                CallbackQueryHandler(select_payment_method, pattern='^method_'),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$')
            ],
            ENTERING_DEPOSIT_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, handle_deposit_amount)
            ],
            ENTERING_DEPOSIT_NAME: [
                MessageHandler(Filters.text & ~Filters.command, handle_deposit_name)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    # محادثة الإدارة
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('admin', start)],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(admin_add_category, pattern='^add_category$'),
                CallbackQueryHandler(admin_edit_category, pattern='^edit_category$'),
                CallbackQueryHandler(admin_add_payment_method, pattern='^add_payment_method$'),
                CallbackQueryHandler(admin_manage_deposits, pattern='^manage_deposits$'),
                CallbackQueryHandler(admin_manage_orders, pattern='^manage_orders$'),
                CallbackQueryHandler(admin_transfer_balance, pattern='^transfer_balance$'),
                CallbackQueryHandler(admin_send_notification, pattern='^send_notification$'),
                CallbackQueryHandler(admin_add_admin, pattern='^add_admin$'),
                CallbackQueryHandler(admin_view_users, pattern='^view_users$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$')
            ],
            ADMIN_ADD_CATEGORY: [
                MessageHandler(Filters.text & ~Filters.command, handle_category_name),
                MessageHandler(Filters.text & ~Filters.command, handle_category_description)
            ],
            ADMIN_EDIT_CATEGORY: [
                CallbackQueryHandler(admin_manage_category, pattern='^editcat_'),
                CallbackQueryHandler(admin_edit_category_name, pattern='^edit_category_name$'),
                CallbackQueryHandler(admin_edit_category_desc, pattern='^edit_category_desc$'),
                CallbackQueryHandler(admin_add_game, pattern='^add_game_to_category$'),
                CallbackQueryHandler(admin_view_category_games, pattern='^view_category_games$'),
                CallbackQueryHandler(back_to_edit_category, pattern='^back_to_edit_category$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                MessageHandler(Filters.text & ~Filters.command, admin_save_category_name),
                MessageHandler(Filters.text & ~Filters.command, admin_save_category_desc)
            ],
            ADMIN_ADD_GAME: [
                MessageHandler(Filters.text & ~Filters.command, admin_save_game)
            ],
            ADMIN_ADD_PRODUCT: [
                MessageHandler(Filters.text & ~Filters.command, admin_save_product_name),
                MessageHandler(Filters.text & ~Filters.command, admin_save_product_price)
            ],
            ADMIN_ADD_PAYMENT_METHOD: [
                MessageHandler(Filters.text & ~Filters.command, admin_save_payment_method_name),
                MessageHandler(Filters.text & ~Filters.command, admin_save_payment_method_desc)
            ],
            ADMIN_MANAGE_DEPOSITS: [
                CallbackQueryHandler(admin_view_deposit_requests, pattern='^view_deposit_requests$'),
                CallbackQueryHandler(lambda update, context: admin_handle_deposit_decision(update, context, int(context.match.group(1)), 'accept'), pattern='^accept_deposit_'),
                CallbackQueryHandler(lambda update, context: admin_handle_deposit_decision(update, context, int(context.match.group(1)), 'reject'), pattern='^reject_deposit_'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$')
            ],
            ADMIN_MANAGE_ORDERS: [
                CallbackQueryHandler(admin_view_order_requests, pattern='^view_order_requests$'),
                CallbackQueryHandler(lambda update, context: admin_handle_order_decision(update, context, int(context.match.group(1)), 'accept'), pattern='^accept_order_'),
                CallbackQueryHandler(lambda update, context: admin_handle_order_decision(update, context, int(context.match.group(1)), 'reject'), pattern='^reject_order_'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$')
            ],
            ADMIN_TRANSFER_BALANCE: [
                MessageHandler(Filters.text & ~Filters.command, admin_handle_transfer_user),
                MessageHandler(Filters.text & ~Filters.command, admin_handle_transfer_amount)
            ],
            ADMIN_SEND_NOTIFICATION: [
                MessageHandler(Filters.text & ~Filters.command, admin_handle_notification)
            ],
            ADMIN_ADD_ADMIN: [
                MessageHandler(Filters.text & ~Filters.command, admin_handle_new_admin)
            ]
        },
        fallbacks=[CommandHandler('admin', start)]
    )

    dp.add_handler(user_conv)
    dp.add_handler(admin_conv)
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
