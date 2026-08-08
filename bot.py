import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")  
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/yourchannel")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support")
UPDATES_CHANNEL_LINK = os.getenv("UPDATES_CHANNEL_LINK", "https://t.me/yourchannel")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123") 

BTC_ADDRESS = os.getenv("BTC_ADDRESS", "your_btc_address_here")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "your_sol_address_here")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "your_ltc_address_here")

STORE_NAME = os.getenv("STORE_NAME", "Mazza X Gaara's Store")
DEVELOPER_TAG = os.getenv("DEVELOPER_TAG", "@Kr3ptoV1")
MANAGER_TAG = os.getenv("MANAGER_TAG", "@mazza4444")
RULES_TEXT = os.getenv("RULES_TEXT", "1. No spamming\n2. Follow channel rules\n3. All purchases are final.")

TOPUP_AMOUNTS = [
    (70, 100),
    (150, 200),
    (250, 300),
    (350, 400),
    (450, 500),
    (750, 1000)
]

METHODS_FILE = "methods.json"
DEFAULT_METHODS = [
    {"id": "1", "title": "Argos.co.uk", "desc": "BIN + METH (£1000+ SIKP) •♻️", "price": "100"},
    {"id": "2", "title": "Vinted.com", "desc": "Bin + cc Skips £1000+)", "price": "100"},
    {"id": "3", "title": "Ebay.com", "desc": "BIN + METH (£300)", "price": "60"},
    {"id": "4", "title": "Apple Pay", "desc": "BIN + METH", "price": "80"},
    {"id": "5", "title": "Amazon.com", "desc": "BIN + METH", "price": "75"}
]

authenticated_admins = set()

def make_safe_url(link: str) -> str:
    if not link:
        return "https://telegram.org"
    if link.startswith("http://") or link.startswith("https://"):
        return link
    return f"https://t.me/{link.replace('@', '')}"

def load_methods():
    if not os.path.exists(METHODS_FILE):
        with open(METHODS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_METHODS, f, ensure_ascii=False, indent=4)
        return DEFAULT_METHODS
    with open(METHODS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_methods(methods_list):
    with open(METHODS_FILE, 'w', encoding='utf-8') as f:
        json.dump(methods_list, f, ensure_ascii=False, indent=4)

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL_ID:
        return True
        
    channel_id = REQUIRED_CHANNEL_ID.strip()
    
    if channel_id.lstrip('-').isdigit():
        channel_id = int(channel_id)
    elif not str(channel_id).startswith('@'):
        channel_id = f"@{channel_id}"
        
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True
    except TelegramError as e:
        logging.error(f"Membership check failed for user {user_id} in chat {channel_id}: {e}")
        return False
        
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    
    text = (
        f"Welcome to {STORE_NAME}\n\n"
        f"Made/Coded by {DEVELOPER_TAG} [pm for coding needs ]\n"
        f"Managed by {MANAGER_TAG}\n\n"
        f"Username : {username}\n"
        f"ID: {user.id}\n\n"
        f"Use the menu below to interact with the bot 🤖\n\n"
        f"===================================="
    )

    keyboard = [
        [InlineKeyboardButton("🔑 Access Store", callback_data="access_store")],
        [InlineKeyboardButton("🛡️ Rules", callback_data="rules_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def send_store_menu(query, context: ContextTypes.DEFAULT_TYPE):
    text = "Welcome to the Store! Select an option below:"
    keyboard = [
        [InlineKeyboardButton("📦 Method", callback_data="method")],
        [
            InlineKeyboardButton("💷 Wallet", callback_data="wallet"),
            InlineKeyboardButton("☎️ Support ↗️", url=make_safe_url(SUPPORT_LINK))
        ],
        [
            InlineKeyboardButton("🛡️ Rules", callback_data="rules_store"),
            InlineKeyboardButton("📁 Updates Chan... ↗️", url=make_safe_url(UPDATES_CHANNEL_LINK))
        ],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_wallet_menu(query_or_message, user_id: int):
    join_date = datetime.now().strftime("%d-%m-%Y") 
    
    text = (
        "====================================\n"
        f"💳 <b>ID:</b> {user_id}\n"
        f"💰 <b>Balance:</b> £0.00\n"
        f"📅 <b>Join Date:</b> {join_date}\n"
        "====================================\n\n"
        "Select a top-up amount below:\n"
        "<i>Minimum top-up: £70</i>"
    )
    
    keyboard = []
    for left_amt, right_amt in TOPUP_AMOUNTS:
        keyboard.append([
            InlineKeyboardButton(f"🕶️ £{left_amt} 🕶️", callback_data=f"topup_{left_amt}"),
            InlineKeyboardButton(f"🕶️ £{right_amt} 🕶️", callback_data=f"topup_{right_amt}")
        ])
    
    keyboard.append([InlineKeyboardButton("💰 Custom Amount", callback_data="custom_topup")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="access_store")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_membership(user_id, context):
        await send_wallet_menu(update.message, user_id)
    else:
        await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def send_payment_methods(query, amount: str):
    text = f"🕶️ <b>£{amount} Top-Up</b>\n\nChoose your payment method:"
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_{amount}_BTC")],
        [InlineKeyboardButton("Ⓞ SOL", callback_data=f"pay_{amount}_SOL")],
        [InlineKeyboardButton("Ł LTC", callback_data=f"pay_{amount}_LTC")],
        [InlineKeyboardButton("⬅️ Back", callback_data="wallet")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide the password.")
        return
    if context.args[0] == ADMIN_PASSWORD:
        authenticated_admins.add(update.effective_user.id)
        await update.message.reply_text("Admin access granted.")
    else:
        await update.message.reply_text("Incorrect password.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_admins:
        await update.message.reply_text("Unauthorised. Please login using /adminlogin <password>")
        return
    text = (
        "🛠 <b>Admin Panel</b>\n\n"
        "Use these commands to manage your methods:\n"
        "<code>/adminlist</code> - View all methods\n"
        "<code>/adminadd Title | Description | Price</code> - Add a method\n"
        "<code>/adminedit ID | New Title | New Description | New Price</code> - Edit a method\n"
        "<code>/admindelete ID</code> - Delete a method"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_admins:
        return
    methods = load_methods()
    if not methods:
        await update.message.reply_text("No methods found.")
        return
    text = "📦 <b>Current Methods</b>\n\n"
    for m in methods:
        text += f"<b>ID:</b> {m['id']}\n<b>Title:</b> {m['title']}\n<b>Desc:</b> {m['desc']}\n<b>Price:</b> £{m['price']}\n\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_admins:
        return
    args_text = " ".join(context.args)
    parts = [p.strip() for p in args_text.split("|")]
    if len(parts) != 3:
        await update.message.reply_text("Format: <code>/adminadd Title | Description | Price</code>", parse_mode="HTML")
        return
    title, desc, price = parts
    methods = load_methods()
    new_id = str(max([int(m['id']) for m in methods] + [0]) + 1)
    methods.append({"id": new_id, "title": title, "desc": desc, "price": price})
    save_methods(methods)
    await update.message.reply_text(f"✅ Added Method ID {new_id}")

async def admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_admins:
        return
    args_text = " ".join(context.args)
    parts = [p.strip() for p in args_text.split("|")]
    if len(parts) != 4:
        await update.message.reply_text("Format: <code>/adminedit ID | New Title | New Description | New Price</code>", parse_mode="HTML")
        return
    method_id, new_title, new_desc, new_price = parts
    methods = load_methods()
    found = False
    for m in methods:
        if m['id'] == method_id:
            m['title'] = new_title
            m['desc'] = new_desc
            m['price'] = new_price
            found = True
            break
    if found:
        save_methods(methods)
        await update.message.reply_text(f"✅ Edited Method ID {method_id}")
    else:
        await update.message.reply_text("❌ Method ID not found.")

async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_admins:
        return
    if not context.args:
        await update.message.reply_text("Format: <code>/admindelete ID</code>", parse_mode="HTML")
        return
    method_id = context.args[0].strip()
    methods = load_methods()
    new_methods = [m for m in methods if m['id'] != method_id]
    if len(methods) != len(new_methods):
        save_methods(new_methods)
        await update.message.reply_text(f"✅ Deleted Method ID {method_id}")
    else:
        await update.message.reply_text("❌ Method ID not found.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "access_store":
        if await check_membership(user_id, context):
            await query.answer()
            await send_store_menu(query, context)
        else:
            await query.answer("Please join the channel first to access the store.", show_alert=True)
            safe_url = make_safe_url(CHANNEL_LINK)
            text = (
                "⚠️ <b>Access Restricted</b>\n\n"
                "To access the store menu, you must first join our updates channel."
            )
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=safe_url)],
                [InlineKeyboardButton("✅ I Have Joined", callback_data="access_store")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            except Exception:
                pass

    elif data == "wallet":
        await query.answer()
        await send_wallet_menu(query, user_id)

    elif data.startswith("topup_"):
        await query.answer()
        amount = data.split("_")[1]
        await send_payment_methods(query, amount)

    elif data.startswith("pay_"):
        await query.answer()
        parts = data.split("_")
        amount = parts[1]
        crypto = parts[2]
        
        if crypto == "BTC":
            address = BTC_ADDRESS
            exchange_rate = 50000 
        elif crypto == "SOL":
            address = SOL_ADDRESS
            exchange_rate = 120 
        else:
            address = LTC_ADDRESS
            exchange_rate = 60 

        try:
            crypto_amount_calc = round(float(amount) / exchange_rate, 6)
        except ValueError:
            crypto_amount_calc = "0.00"

        text = (
            f"📦 <b>PAYMENT INVOICE GENERATED</b>\n"
            f"– – – – – – – – – – – –\n\n"
            f"🌐 <b>NETWORK:</b> {crypto}\n"
            f"⚠️ <b>WARNING:</b> Send ONLY {crypto}.\n\n"
            f"💰 <b>AMOUNT DUE:</b> {crypto_amount_calc} {crypto} (£{amount})\n"
            f"📬 <b>DEPOSIT ADDRESS:</b>\n"
            f"<code>{address}</code>\n\n"
            f"– – – – – – – – – – – –\n\n"
            f"⏳ <b>Status:</b> Waiting for payment..."
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Check Payment", callback_data="check_payment")],
            [InlineKeyboardButton("📸 Send Screenshot", callback_data=f"send_screenshot_{amount}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="wallet")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "check_payment":
        await query.answer(
            "❌ Error: Payment not found on the blockchain. Please allow 5-15 minutes for confirmations, or use 'Send Screenshot' if you have already paid.",
            show_alert=True
        )

    elif data.startswith("send_screenshot_"):
        await query.answer()
        amount = data.split("_")[2]
        text = (
            f"📸 <b>UPLOAD SCREENSHOT</b>\n"
            f"– – – – – – – – – – – –\n\n"
            f"Please send the transaction screenshot/receipt for £{amount} now."
        )
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="wallet")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "custom_topup":
        await query.answer("Custom amount feature coming soon!", show_alert=True)

    elif data == "rules_main" or data == "rules_store":
        await query.answer()
        back_data = "main_menu" if data == "rules_main" else "access_store"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=back_data)]]
        await query.edit_message_text(f"🛡️ <b>Rules</b>\n\n{RULES_TEXT}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # NEW: Methods Catalog View
    elif data == "method":
        await query.answer()
        methods = load_methods()
        keyboard = []
        for m in methods:
            # Display only the title in the catalog menu
            keyboard.append([InlineKeyboardButton(f"{m['title']}", callback_data=f"view_method_{m['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Store", callback_data="access_store")])
        
        text = (
            "📦 <b>Methods Catalog</b>\n\n"
            "Select method below to view details:\n\n"
            "===================================="
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    # NEW: Method Details View
    elif data.startswith("view_method_"):
        await query.answer()
        method_id = data.split("_")[2]
        methods = load_methods()
        method = next((m for m in methods if m['id'] == method_id), None)
        
        if method:
            text = (
                f"📚 <b>{method['title']}</b> {method['desc']}\n"
                f"£{method['price']}\n\n"
                f"---------------------------------"
            )
            keyboard = [
                [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{method['id']}")],
                [InlineKeyboardButton("🔙 Back to Catalog", callback_data="method")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("buy_"):
        await query.answer()
        method_id = data.split("_")[1]
        methods = load_methods()
        method = next((m for m in methods if m['id'] == method_id), None)
        
        if method:
            text = (
                f"🛒 <b>Purchase Selection</b>\n\n"
                f"<b>Item:</b> {method['title']}\n"
                f"<b>Price:</b> £{method['price']}\n\n"
                f"Please top up your wallet to proceed with this purchase."
            )
            keyboard = [
                [InlineKeyboardButton("💷 Go to Wallet", callback_data="wallet")],
                [InlineKeyboardButton("🔙 Back to Details", callback_data=f"view_method_{method['id']}")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "main_menu":
        await query.answer()
        await start(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        await update.message.reply_text(
            "✅ <b>Screenshot received!</b>\n\nOur admins will verify your transaction shortly. Once confirmed, your wallet balance will be updated.",
            parse_mode="HTML"
        )

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CommandHandler("adminlogin", admin_login))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("adminlist", admin_list))
    app.add_handler(CommandHandler("adminadd", admin_add))
    app.add_handler(CommandHandler("adminedit", admin_edit))
    app.add_handler(CommandHandler("admindelete", admin_delete))
    
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot is successfully running...")
    app.run_polling()

if __name__ == "__main__":
    main()
