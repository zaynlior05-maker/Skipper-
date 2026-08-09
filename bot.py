import os
import json
import logging
import uuid
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")  
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/yourchannel")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support")
UPDATES_CHANNEL_LINK = os.getenv("UPDATES_CHANNEL_LINK", "https://t.me/yourchannel")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123") 
LOG_GROUP_ID = os.getenv("LOG_GROUP_ID") 

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

# --- FOOLPROOF PERSISTENT STORAGE ROUTING ---
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_STATIC_URL"):
    DATA_DIR = os.getenv("DATA_DIR", "/app/data")
else:
    DATA_DIR = os.getenv("DATA_DIR", "bot_data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# Database Files
METHODS_FILE = os.path.join(DATA_DIR, "methods.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LABELS_FILE = os.path.join(DATA_DIR, "labels.json")
CARTS_FILE = os.path.join(DATA_DIR, "carts.json")
BALANCES_FILE = os.path.join(DATA_DIR, "balances.json")

DEFAULT_METHODS = [
    {"id": "1", "title": "Argos.co.uk", "desc": "BIN + METH (£1000+ SIKP) •♻️", "price": "100"},
    {"id": "2", "title": "Vinted.com", "desc": "Bin + cc Skips £1000+)", "price": "100"},
    {"id": "3", "title": "Ebay.com", "desc": "BIN + METH (£300)", "price": "60"}
]

DEFAULT_LABELS = {
    "method": "Method",
    "wallet": "Wallet",
    "rules": "Rules",
    "support": "Support",
    "channel": "Channel"
}

# Admin & User states tracking
WAITING_FOR_PASSWORD = 1
admin_sessions = {}
admin_states = {}
user_states = {}

async def log_action(context: ContextTypes.DEFAULT_TYPE, user, action: str):
    """Sends a live log of user activity to the specified log group."""
    if not LOG_GROUP_ID:
        return
    username = f"@{user.username}" if user.username else user.first_name
    text = f"📝 <b>USER LOG</b>\n👤 User: {username}\n🆔 ID: <code>{user.id}</code>\n⚡️ Action: {action}"
    try:
        await context.bot.send_message(chat_id=LOG_GROUP_ID, text=text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send log to group {LOG_GROUP_ID}: {e}")

def is_admin_authenticated(user_id: int) -> bool:
    if user_id in admin_sessions:
        if datetime.now() < admin_sessions[user_id]:
            return True
        else:
            del admin_sessions[user_id]
    return False

def make_safe_url(link: str) -> str:
    if not link: return "https://telegram.org"
    if link.startswith("http://") or link.startswith("https://"): return link
    return f"https://t.me/{link.replace('@', '')}"

def safe_html(text: str) -> str:
    """Escapes HTML tags to prevent parsing crashes."""
    return str(text).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

# --- Database Loaders & Savers ---
def load_json(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_methods(): return load_json(METHODS_FILE, DEFAULT_METHODS)
def save_methods(data): save_json(METHODS_FILE, data)
def load_labels(): return load_json(LABELS_FILE, DEFAULT_LABELS)
def save_labels(data): save_json(LABELS_FILE, data)
def load_users(): return load_json(USERS_FILE, [])
def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)
def load_carts(): return load_json(CARTS_FILE, [])
def save_carts(data): save_json(CARTS_FILE, data)

# --- Balance Management ---
def load_balances(): return load_json(BALANCES_FILE, {})
def save_balances(data): save_json(BALANCES_FILE, data)
def get_balance(user_id: int) -> float:
    bals = load_balances()
    return float(bals.get(str(user_id), 0.0))
def add_balance(user_id: int, amount: float):
    bals = load_balances()
    bals[str(user_id)] = bals.get(str(user_id), 0.0) + float(amount)
    save_balances(bals)
def deduct_balance(user_id: int, amount: float) -> bool:
    bals = load_balances()
    current = float(bals.get(str(user_id), 0.0))
    if current >= float(amount):
        bals[str(user_id)] = current - float(amount)
        save_balances(bals)
        return True
    return False

# --- Membership Check ---
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL_ID: return True
    channel_id = REQUIRED_CHANNEL_ID.strip()
    if channel_id.lstrip('-').isdigit(): channel_id = int(channel_id)
    elif not str(channel_id).startswith('@'): channel_id = f"@{channel_id}"
        
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True
    except TelegramError:
        return False
    return False

# --- Core Bot Menus & Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id)
    await log_action(context, user, "Started the bot (/start)")
    
    is_member = await check_membership(user.id, context)
    
    if is_member:
        await send_store_menu(update.message if update.message else update.callback_query, context)
        return

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
    labels = load_labels()
    keyboard = [
        [InlineKeyboardButton("🔑 Access Store", callback_data="access_store")],
        [InlineKeyboardButton(f"🛡️ {labels.get('rules', 'Rules')}", callback_data="rules_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def send_store_menu(query_or_message, context: ContextTypes.DEFAULT_TYPE):
    labels = load_labels()
    text = "Welcome to the Store! Select an option below:"
    keyboard = [
        [InlineKeyboardButton(f"📦 {labels.get('method', 'Method')}", callback_data="method")],
        [
            InlineKeyboardButton(f"💷 {labels.get('wallet', 'Wallet')}", callback_data="wallet"),
            InlineKeyboardButton(f"☎️ {labels.get('support', 'Support')} ↗️", url=make_safe_url(SUPPORT_LINK))
        ],
        [
            InlineKeyboardButton(f"🛡️ {labels.get('rules', 'Rules')}", callback_data="rules_store"),
            InlineKeyboardButton(f"📄 {labels.get('channel', 'Channel')} ↗️", url=make_safe_url(UPDATES_CHANNEL_LINK))
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=markup)
    else:
        await query_or_message.reply_text(text, reply_markup=markup)

async def send_methods_menu(query_or_message, context: ContextTypes.DEFAULT_TYPE):
    methods = load_methods()
    keyboard = [[InlineKeyboardButton(f"{m['title']}", callback_data=f"view_method_{m['id']}")] for m in methods]
    keyboard.append([InlineKeyboardButton("🔙 Back to Store", callback_data="access_store")])
    text = "📦 <b>Methods Catalog</b>\n\nSelect method below to view details:\n\n===================================="
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=markup, parse_mode="HTML")

async def send_wallet_menu(query_or_message, user_id: int):
    join_date = datetime.now().strftime("%d-%m-%Y") 
    balance = get_balance(user_id)
    text = (
        "====================================\n"
        f"💳 <b>ID:</b> {user_id}\n"
        f"💰 <b>Balance:</b> £{balance:.2f}\n"
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
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def send_payment_methods(query_or_message, amount: str):
    text = f"🕶️ <b>£{amount} Top-Up</b>\n\nChoose your payment method:"
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_{amount}_BTC")],
        [InlineKeyboardButton("Ⓞ SOL", callback_data=f"pay_{amount}_SOL")],
        [InlineKeyboardButton("Ł LTC", callback_data=f"pay_{amount}_LTC")],
        [InlineKeyboardButton("⬅️ Back", callback_data="wallet")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# --- Native Bot Menu Commands ---
async def skippers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await log_action(context, update.effective_user, "Used /skippers command")
    if await check_membership(user_id, context):
        await send_methods_menu(update.message, context)
    else:
        await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await log_action(context, update.effective_user, "Used /wallet command")
    if await check_membership(user_id, context):
        await send_wallet_menu(update.message, user_id)
    else:
        await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await log_action(context, update.effective_user, "Used /rules command")
    if await check_membership(user_id, context):
        await update.message.reply_text(f"🛡️ <b>Rules</b>\n\n{RULES_TEXT}", parse_mode="HTML")
    else:
        await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await log_action(context, update.effective_user, "Used /support command")
    await update.message.reply_text(f"☎️ <b>Contact Support:</b>\n{make_safe_url(SUPPORT_LINK)}", parse_mode="HTML")

# --- Admin Panel ---
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"), InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="admin_add_stock"), InlineKeyboardButton("🗑️ Delete Stock", callback_data="admin_delete_stock")],
        [InlineKeyboardButton("📝 Description", callback_data="admin_descriptions"), InlineKeyboardButton("💰 Prices", callback_data="admin_prices")],
        [InlineKeyboardButton("🏷 Labels", callback_data="admin_labels"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📦 Deliveries", callback_data="admin_deliveries"), InlineKeyboardButton("💳 Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ])

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin_authenticated(user_id):
        await update.message.reply_text("🛠 <b>Admin Panel</b>\n\nChoose a section:", reply_markup=get_admin_keyboard(), parse_mode="HTML")
        return ConversationHandler.END
    await update.message.reply_text("🔐 <b>Admin Login</b>\n\nEnter the admin password:", parse_mode="HTML")
    return WAITING_FOR_PASSWORD

async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        await update.message.delete()
    except Exception as e:
        logging.warning(f"Could not delete password message: {e}")
        
    if text == ADMIN_PASSWORD:
        admin_sessions[user_id] = datetime.now() + timedelta(hours=2)
        await update.message.reply_text("✅ <b>Access granted!</b> Session lasts 2 hours.\n\n🛠 <b>Admin Panel</b>\n\nChoose a section:", reply_markup=get_admin_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ <b>Incorrect password.</b> Admin access denied.", parse_mode="HTML")
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin login cancelled.")
    return ConversationHandler.END

# --- Manual Balance Adjustment Commands ---
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin_authenticated(user_id):
        await update.message.reply_text("❌ Please login via /admin first.")
        return
    
    try:
        target_user = int(context.args[0])
        amount = float(context.args[1])
        add_balance(target_user, amount)
        await update.message.reply_text(f"✅ Successfully added £{amount:.2f} to user {target_user}.\nNew balance: £{get_balance(target_user):.2f}")
        try:
            await context.bot.send_message(chat_id=target_user, text=f"💰 Your balance has been credited with £{amount:.2f} by an admin.")
        except Exception: pass
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ <b>Format:</b> <code>/addbalance USER_ID AMOUNT</code>", parse_mode="HTML")

async def admin_set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin_authenticated(user_id):
        await update.message.reply_text("❌ Please login via /admin first.")
        return
    
    try:
        target_user = int(context.args[0])
        amount = float(context.args[1])
        bals = load_balances()
        bals[str(target_user)] = amount
        save_balances(bals)
        await update.message.reply_text(f"✅ Successfully set user {target_user} balance to £{amount:.2f}.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ <b>Format:</b> <code>/setbalance USER_ID AMOUNT</code>", parse_mode="HTML")

# --- Text Message Handler ---
async def handle_general_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    
    if user_id in user_states:
        state = user_states.get(user_id).get("state")
        if state == "WAITING_CUSTOM_AMOUNT" and update.message.text:
            del user_states[user_id]
            amount = update.message.text.strip().replace('£', '')
            if amount.isdigit() or (amount.replace('.', '', 1).isdigit() and amount.count('.') < 2):
                await log_action(context, user, f"Initiated custom top-up for £{amount}")
                await send_payment_methods(update.message, amount)
            else:
                await update.message.reply_text("❌ Invalid amount. Please enter numbers only (e.g., 50 or 50.50).")
            return

    if user_id in admin_states:
        state_data = admin_states.pop(user_id)
        state = state_data.get("state")
        
        if state == "WAITING_NEW_STOCK" and update.message.text:
            lines = update.message.text.strip().split('\n')
            methods = load_methods()
            added_count = 0
            updated_count = 0
            skipped_count = 0
            failed_lines = []
            
            for raw_line in lines:
                if not raw_line.strip(): continue
                line = raw_line.replace('–', '-').replace('—', '-').replace('\xa0', ' ').strip()
                try:
                    title_part, rest = line.split('=', 1)
                    desc_part, price_part = rest.rsplit('-', 1)
                    title = title_part.strip()
                    desc = desc_part.strip()
                    price = price_part.replace('£', '').strip()

                    existing = next((m for m in methods if m['title'].lower() == title.lower()), None)
                    if existing:
                        if existing['desc'] == desc and existing['price'] == price:
                            skipped_count += 1
                        else:
                            existing['desc'] = desc
                            existing['price'] = price
                            updated_count += 1
                    else:
                        new_id = str(max([int(m['id']) for m in methods] + [0]) + 1)
                        methods.append({"id": new_id, "title": title, "desc": desc, "price": price})
                        added_count += 1
                except ValueError:
                    failed_lines.append(raw_line)
            
            save_methods(methods)
            response = f"✅ <b>Stock processed!</b>\n➕ Added: {added_count}\n🔄 Updated: {updated_count}\n⏭ Skipped (Duplicates): {skipped_count}"
            if failed_lines:
                response += "\n\n⚠️ Failed to parse these lines (Make sure you use format Title = Desc - Price):\n" + "\n".join(failed_lines)
            await update.message.reply_text(response, reply_markup=get_admin_keyboard(), parse_mode="HTML")

        elif state == "WAITING_DESC" and update.message.text:
            methods = load_methods()
            for m in methods:
                if str(m['id']) == str(state_data["method_id"]): m['desc'] = update.message.text
            save_methods(methods)
            await update.message.reply_text("✅ Description updated successfully!", reply_markup=get_admin_keyboard())
            
        elif state == "WAITING_PRICE" and update.message.text:
            methods = load_methods()
            for m in methods:
                if str(m['id']) == str(state_data["method_id"]): m['price'] = update.message.text.replace('£', '').strip()
            save_methods(methods)
            await update.message.reply_text("✅ Price updated successfully!", reply_markup=get_admin_keyboard())

        elif state == "WAITING_LABEL" and update.message.text:
            labels = load_labels()
            labels[state_data["label_key"]] = update.message.text.strip()
            save_labels(labels)
            await update.message.reply_text(f"✅ Label updated to '{update.message.text}' successfully!", reply_markup=get_admin_keyboard())
            
        elif state == "WAITING_METHOD_TITLE" and update.message.text:
            methods = load_methods()
            for m in methods:
                if str(m['id']) == str(state_data["method_id"]): m['title'] = update.message.text.strip()
            save_methods(methods)
            await update.message.reply_text("✅ Method Title updated successfully!", reply_markup=get_admin_keyboard())

        elif state == "WAITING_BROADCAST":
            users = load_users()
            sent = 0
            for u in users:
                try:
                    await context.bot.copy_message(chat_id=u, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    sent += 1
                except Exception: pass
            await update.message.reply_text(f"✅ Broadcast successfully sent to {sent} users!", reply_markup=get_admin_keyboard())
            
        elif state == "WAITING_DELIVERY":
            target_user = state_data["user_id"]
            cart_id = state_data["cart_id"]
            try:
                await context.bot.copy_message(chat_id=target_user, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
                await context.bot.send_message(chat_id=target_user, text=f"✅ Your order #{cart_id} has been delivered above!")
                
                carts = load_carts()
                carts = [c for c in carts if str(c["cart_id"]) != str(cart_id)]
                save_carts(carts)
                
                await update.message.reply_text("✅ Delivery sent to user successfully and removed from pending queue!", reply_markup=get_admin_keyboard())
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send delivery to user.\nError: {e}", reply_markup=get_admin_keyboard())
        return

    # Handle User Screenshot Receipts
    if update.message.photo:
        user_state = user_states.get(user_id, {})
        amount_expected = user_state.get("amount", "Unknown") if user_state.get("state") == "WAITING_FOR_SCREENSHOT" else "Unknown"
        
        if user_id in user_states:
            del user_states[user_id]
            
        await log_action(context, user, "Uploaded a payment screenshot")
        
        if LOG_GROUP_ID:
            photo_file = update.message.photo[-1].file_id
            name = user.first_name
            if user.last_name: name += f" {user.last_name}"
            username_str = f"(@{user.username})" if user.username else ""
            
            caption = (
                f"📸 NEW PAYMENT SCREENSHOT\n"
                f"👤 From: {name} {username_str} ({user.id})\n"
                f"💰 Expected Amount: £{amount_expected}\n\n"
                f"⚠️ Action required: Verify and Accept/Reject."
            )
            
            keyboard = [
                [InlineKeyboardButton(f"✅ Approve £{amount_expected}", callback_data=f"approve_{user.id}_{amount_expected}")],
                [InlineKeyboardButton("❌ Reject Payment", callback_data=f"reject_{user.id}")]
            ]
            
            try:
                await context.bot.send_photo(
                    chat_id=LOG_GROUP_ID,
                    photo=photo_file,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logging.error(f"Failed to forward screenshot to LOG_GROUP_ID: {e}")

        await update.message.reply_text(
            "✅ <b>Screenshot received!</b>\n\nOur admins will verify your transaction shortly. Once confirmed, your wallet balance will be updated.",
            parse_mode="HTML"
        )

# --- Main Callback Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    data = query.data

    # Log Group Admin Actions
    if data.startswith("approve_"):
        parts = data.split("_")
        target_user = parts[1]
        amount = parts[2]
        
        add_balance(target_user, amount)
        
        await query.answer("Payment Approved!")
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n✅ <b>STATUS: APPROVED (£{amount})</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(chat_id=target_user, text=f"✅ <b>Payment Approved!</b>\nYour top-up of £{amount} has been verified and added to your balance.", parse_mode="HTML")
        except Exception: pass
        return
        
    elif data.startswith("reject_"):
        target_user = data.split("_")[1]
        await query.answer("Payment Rejected!")
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ <b>STATUS: REJECTED</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(chat_id=target_user, text="❌ <b>Payment Rejected!</b>\nWe could not verify your payment screenshot. Please contact support.", parse_mode="HTML")
        except Exception: pass
        return

    # Standard Admin routing
    if data.startswith("admin_") or data.startswith("editdesc_") or data.startswith("editprice_") or data.startswith("editlabel_") or data.startswith("editmethodtitle_") or data.startswith("deliver_") or data.startswith("toggle_del_") or data == "confirm_del_stock":
        if not is_admin_authenticated(user_id):
            await query.answer("Session expired. Please login again via /admin", show_alert=True)
            return
            
        if data == "admin_close":
            await query.answer()
            await query.edit_message_text("Admin panel closed. Send /admin to reopen.")
        elif data == "admin_home":
            await query.answer()
            await query.edit_message_text("🛠 <b>Admin Panel</b>\n\nChoose a section:", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            
        elif data == "admin_add_stock":
            admin_states[user_id] = {"state": "WAITING_NEW_STOCK"}
            await query.answer()
            text = (
                "➕ <b>Add New Stock List</b>\n\n"
                "Please send your stock items in this exact format:\n"
                "<code>Store Name = Description - Price</code>\n\n"
                "<b>Example:</b>\n"
                "<code>Newbalance.co.uk = BIN + meth (£400) - £45</code>\n"
                "<code>Booking.com = bin + meth(£300) - 45</code>"
            )
            await query.edit_message_text(text, parse_mode="HTML")

        elif data == "admin_delete_stock":
            admin_states[user_id] = {"state": "DELETING_STOCK", "selected": []}
            await query.answer()
            methods = load_methods()
            keyboard = [[InlineKeyboardButton(f"⬜️ {m['title']}", callback_data=f"toggle_del_{m['id']}")] for m in methods]
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("🗑️ <b>Delete Stock</b>\n\nSelect the items you want to delete:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data.startswith("toggle_del_"):
            method_id = data.replace("toggle_del_", "")
            state_data = admin_states.get(user_id, {})
            if state_data.get("state") != "DELETING_STOCK":
                admin_states[user_id] = {"state": "DELETING_STOCK", "selected": [method_id]}
            else:
                selected = state_data.get("selected", [])
                if method_id in selected:
                    selected.remove(method_id)
                else:
                    selected.append(method_id)
                admin_states[user_id]["selected"] = selected
            
            await query.answer()
            methods = load_methods()
            selected = admin_states.get(user_id, {}).get("selected", [])
            keyboard = []
            for m in methods:
                mark = "✅" if str(m['id']) in selected else "⬜️"
                keyboard.append([InlineKeyboardButton(f"{mark} {m['title']}", callback_data=f"toggle_del_{m['id']}")])
            
            if selected:
                keyboard.append([InlineKeyboardButton(f"🗑️ Confirm Delete ({len(selected)})", callback_data="confirm_del_stock")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            
            text = "🗑️ <b>Delete Stock</b>\n\nSelect the items you want to delete. Click again to unselect.\nWhen ready, click Confirm Delete."
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "confirm_del_stock":
            selected = admin_states.get(user_id, {}).get("selected", [])
            if not selected:
                await query.answer("No items selected!", show_alert=True)
                return
            methods = load_methods()
            new_methods = [m for m in methods if str(m['id']) not in selected]
            save_methods(new_methods)
            admin_states.pop(user_id, None)
            await query.answer(f"Deleted {len(selected)} items!", show_alert=True)
            await query.edit_message_text(f"✅ Successfully deleted {len(selected)} items!", reply_markup=get_admin_keyboard(), parse_mode="HTML")

        elif data == "admin_descriptions":
            await query.answer()
            methods = load_methods()
            keyboard = [[InlineKeyboardButton(f"{m['title']}", callback_data=f"editdesc_{m['id']}")] for m in methods]
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("📝 <b>Edit Descriptions</b>\n\nSelect a method:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("editdesc_"):
            admin_states[user_id] = {"state": "WAITING_DESC", "method_id": data.split("_")[1]}
            await query.answer()
            await query.edit_message_text("📝 <b>Please type the new description for this method now:</b>", parse_mode="HTML")

        elif data == "admin_prices":
            await query.answer()
            methods = load_methods()
            keyboard = [[InlineKeyboardButton(f"{m['title']} (£{m['price']})", callback_data=f"editprice_{m['id']}")] for m in methods]
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("💰 <b>Edit Prices</b>\n\nSelect a method:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("editprice_"):
            admin_states[user_id] = {"state": "WAITING_PRICE", "method_id": data.split("_")[1]}
            await query.answer()
            await query.edit_message_text("💰 <b>Please type the new price (numbers only):</b>", parse_mode="HTML")

        elif data == "admin_labels":
            await query.answer()
            labels = load_labels()
            methods = load_methods()
            keyboard = [
                [InlineKeyboardButton(f"✏️ 📦 {labels.get('method', 'Method')}", callback_data="editlabel_method")],
                [InlineKeyboardButton(f"✏️ 💷 {labels.get('wallet', 'Wallet')}", callback_data="editlabel_wallet")],
                [InlineKeyboardButton(f"✏️ 🛡️ {labels.get('rules', 'Rules')}", callback_data="editlabel_rules")],
                [InlineKeyboardButton(f"✏️ ☎️ {labels.get('support', 'Support')}", callback_data="editlabel_support")],
                [InlineKeyboardButton(f"✏️ 📄 {labels.get('channel', 'Channel')}", callback_data="editlabel_channel")]
            ]
            for m in methods:
                keyboard.append([InlineKeyboardButton(f"✏️ 🔖 {m['title']}", callback_data=f"editmethodtitle_{m['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("🏷 <b>Labels Editor</b>\n\nClick a button to rename it:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
        elif data.startswith("editlabel_"):
            key = data.split("_")[1]
            admin_states[user_id] = {"state": "WAITING_LABEL", "label_key": key}
            await query.answer()
            await query.edit_message_text(f"🏷 <b>Type the new name for '{key.title()}':</b>", parse_mode="HTML")
            
        elif data.startswith("editmethodtitle_"):
            admin_states[user_id] = {"state": "WAITING_METHOD_TITLE", "method_id": data.split("_")[1]}
            await query.answer()
            await query.edit_message_text(f"🏷 <b>Type the new Title for this method:</b>", parse_mode="HTML")

        elif data == "admin_deliveries":
            await query.answer()
            carts = load_carts()
            if not carts:
                await query.edit_message_text("📦 <b>Pending Deliveries</b>\n\nNo pending orders found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Menu", callback_data="admin_home")]]), parse_mode="HTML")
                return
            text = f"📦 <b>Pending Deliveries</b> ({len(carts)} pending)\n\n"
            keyboard = []
            for c in carts:
                item_title = c.get("title", "Unknown Item")
                text += f"• <b>{item_title}</b> (User: <code>{c['user_id']}</code>)\nDate: {c['date']}\n\n"
                keyboard.append([InlineKeyboardButton(f"📤 Deliver {item_title}", callback_data=f"deliver_{c['cart_id']}_{c['user_id']}")])
            keyboard.append([InlineKeyboardButton("⬅️ Admin Menu", callback_data="admin_home")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
        elif data.startswith("deliver_"):
            parts = data.split("_")
            cart_id = parts[1]
            target_user = parts[2]
            
            carts = load_carts()
            item_title = "the order"
            for c in carts:
                if str(c["cart_id"]) == str(cart_id):
                    item_title = c.get("title", "the order")
                    break

            admin_states[user_id] = {"state": "WAITING_DELIVERY", "cart_id": cart_id, "user_id": target_user}
            await query.answer()
            await query.edit_message_text(f"📤 <b>Delivery Mode</b>\n\nDelivering: <b>{item_title}</b>\n\nPlease upload the delivery file/text now. It will be sent directly to user {target_user}.", parse_mode="HTML")

        elif data == "admin_broadcast":
            admin_states[user_id] = {"state": "WAITING_BROADCAST"}
            await query.answer()
            await query.edit_message_text("📢 <b>Broadcast Mode</b>\n\nPlease send the message or photo you want to broadcast:", parse_mode="HTML")
        return

    # --- NORMAL USER FLOW ---
    if data == "access_store":
        if await check_membership(user_id, context):
            await query.answer()
            await send_store_menu(query, context)
        else:
            await query.answer("Please join the channel first to access the store.", show_alert=True)
            text = "⚠️ <b>Access Restricted</b>\n\nTo access the store menu, you must first join our updates channel."
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=make_safe_url(CHANNEL_LINK))],
                [InlineKeyboardButton("✅ I Have Joined", callback_data="access_store")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            try: await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            except Exception: pass

    elif data == "wallet":
        await log_action(context, user, "Opened their Wallet")
        await query.answer()
        await send_wallet_menu(query, user_id)

    elif data.startswith("topup_"):
        await query.answer()
        amount = data.split("_")[1]
        await log_action(context, user, f"Selected £{amount} top-up amount")
        await send_payment_methods(query, amount)

    elif data == "custom_topup":
        user_states[user_id] = {"state": "WAITING_CUSTOM_AMOUNT"}
        await query.answer()
        await log_action(context, user, "Clicked Custom Top-Up")
        await query.edit_message_text("💰 <b>Custom Top-Up</b>\n\nPlease enter the amount you wish to deposit in £ (Numbers only, e.g., 50):", parse_mode="HTML")

    elif data.startswith("pay_"):
        await query.answer()
        parts = data.split("_")
        amount = parts[1]
        crypto = parts[2]
        
        await log_action(context, user, f"Generated {crypto} payment invoice for £{amount}")
        
        address = BTC_ADDRESS if crypto == "BTC" else SOL_ADDRESS if crypto == "SOL" else LTC_ADDRESS
        exchange_rate = 50000 if crypto == "BTC" else 120 if crypto == "SOL" else 60
        try: crypto_amount_calc = round(float(amount) / exchange_rate, 6)
        except ValueError: crypto_amount_calc = "0.00"

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
        await query.answer("❌ Error: Payment not found on the blockchain. Please allow 5-15 minutes for confirmations.", show_alert=True)

    elif data.startswith("send_screenshot_"):
        await query.answer()
        amount = data.split("_")[2]
        user_states[user_id] = {"state": "WAITING_FOR_SCREENSHOT", "amount": amount}
        await log_action(context, user, f"Clicked to send screenshot for £{amount} invoice")
        text = f"📸 <b>UPLOAD SCREENSHOT</b>\n– – – – – – – – – – – –\n\nPlease send the transaction screenshot/receipt for £{amount} now."
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="wallet")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "rules_main" or data == "rules_store":
        await query.answer()
        back_data = "main_menu" if data == "rules_main" else "access_store"
        await query.edit_message_text(f"🛡️ <b>Rules</b>\n\n{RULES_TEXT}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=back_data)]]), parse_mode="HTML")

    elif data == "method":
        await query.answer()
        await log_action(context, user, "Opened the Methods Catalog")
        await send_methods_menu(query, context)

    elif data.startswith("view_method_"):
        await query.answer()
        method_id = data.split("_")[2]
        method = next((m for m in load_methods() if str(m['id']) == str(method_id)), None)
        if method:
            safe_title = safe_html(method['title'])
            safe_desc = safe_html(method['desc'])
            
            await log_action(context, user, f"Viewed details for '{method['title']}'")
            text = f"📚 <b>{safe_title}</b> {safe_desc}\n£{method['price']}\n\n---------------------------------"
            keyboard = [
                [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{method['id']}")],
                [InlineKeyboardButton("🔙 Back to Catalog", callback_data="method")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.answer("This item is no longer available.", show_alert=True)

    elif data.startswith("buy_"):
        await query.answer()
        method_id = data.replace("buy_", "")
        method = next((m for m in load_methods() if str(m['id']) == str(method_id)), None)
        
        if not method:
            await query.edit_message_text("❌ This item is no longer available.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Store", callback_data="main_menu")]]))
            return

        try:
            # Bullet-proof price string cleaning to prevent python crashes
            clean_price_str = str(method['price']).replace('£', '').replace(',', '').strip()
            price = float(clean_price_str)
        except ValueError:
            await query.edit_message_text("❌ Error: Invalid price configuration for this item. Please contact admin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
            return
            
        balance = get_balance(user_id)
        safe_title = safe_html(method['title'])
        
        if balance >= price:
            deduct_balance(user_id, price)
            cart_id = str(uuid.uuid4().hex)[:10]
            carts = load_carts()
            carts.append({
                "cart_id": cart_id,
                "user_id": user_id,
                "items": 1,
                "title": method['title'],
                "price": str(price),
                "date": datetime.now().strftime("%d/%m %H:%M")
            })
            save_carts(carts)
            
            await log_action(context, user, f"✅ SUCCESSFULLY PURCHASED '{method['title']}'! Please deliver order now.")
            
            text = f"✅ <b>Purchase Successful!</b>\n\n<b>Item:</b> {safe_title}\n<b>Price:</b> £{price:.2f}\n\nYour order has been sent to our admins for delivery. You will receive your file here shortly."
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Store", callback_data="main_menu")]]), parse_mode="HTML")
        else:
            await log_action(context, user, f"Attempted to buy '{method['title']}' for £{price:.2f} (Insufficient Balance)")
            
            text = f"🛒 <b>Purchase Selection</b>\n\n<b>Item:</b> {safe_title}\n<b>Price:</b> £{price:.2f}\n\n❌ <b>Insufficient Balance!</b> Your balance is £{balance:.2f}.\nPlease top up your wallet to proceed."
            keyboard = [
                [InlineKeyboardButton("💷 Go to Wallet", callback_data="wallet")],
                [InlineKeyboardButton("🔙 Back to Details", callback_data=f"view_method_{method['id']}")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "main_menu":
        await query.answer()
        await start(update, context)

# --- Post Init (Menu Config) ---
async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "🏠 Main menu"),
        BotCommand("skippers", "📦 Browse skippers"),
        BotCommand("wallet", "💵 View wallet & top up"),
        BotCommand("rules", "🛡 Read the rules"),
        BotCommand("support", "☎️ Contact support")
    ])

def main():
    if not BOT_TOKEN: raise ValueError("BOT_TOKEN environment variable is not set!")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_start)],
        states={WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)]},
        fallbacks=[CommandHandler('cancel', cancel_admin)]
    )
    
    app.add_handler(admin_conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("skippers", skippers_command))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("support", support_command))
    
    app.add_handler(CommandHandler("addbalance", admin_add_balance))
    app.add_handler(CommandHandler("setbalance", admin_set_balance))
    
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_general_messages))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is successfully running...")
    app.run_polling()

if __name__ == "__main__":
    main()
