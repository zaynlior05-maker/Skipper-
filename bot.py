import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") # Your personal user ID to receive receipts

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

# Database Files - Directed to /app/data to persist on Railway Volumes
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
METHODS_FILE = os.path.join(DATA_DIR, "methods.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LABELS_FILE = os.path.join(DATA_DIR, "labels.json")
CARTS_FILE = os.path.join(DATA_DIR, "carts.json")
BALANCES_FILE = os.path.join(DATA_DIR, "balances.json")

DEFAULT_METHODS = [
    {"id": "1", "title": "Argos.co.uk", "desc": "BIN + METH (£1000+ SIKP) •♻️", "price": "100"},
    {"id": "2", "title": "Vinted.com", "desc": "Bin + cc Skips £1000+)", "price": "100"},
    {"id": "3", "title": "Ebay.com", "desc": "BIN + METH (£300)", "price": "60"},
    {"id": "4", "title": "Apple Pay", "desc": "BIN + METH", "price": "80"},
    {"id": "5", "title": "Amazon.com", "desc": "BIN + METH", "price": "75"}
]

DEFAULT_LABELS = {
    "wallet": "Wallet",
    "rules": "Rules",
    "support": "Support",
    "channel": "Channel"
}

WAITING_FOR_PASSWORD = 1
admin_sessions = {}
user_states = {} # Tracks inputs for both admins and normal users

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

# --- Database Management ---
def load_json(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return default_data

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_methods(): return load_json(METHODS_FILE, DEFAULT_METHODS)
def save_methods(data): save_json(METHODS_FILE, data)

def load_labels(): return load_json(LABELS_FILE, DEFAULT_LABELS)
def save_labels(data): save_json(LABELS_FILE, data)

def load_balances(): return load_json(BALANCES_FILE, {})
def save_balances(data): save_json(BALANCES_FILE, data)

def load_users(): return load_json(USERS_FILE, [])
def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)

def load_carts(): return load_json(CARTS_FILE, [])
def save_carts(data): save_json(CARTS_FILE, data)

# --- Membership & Utilities ---
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL_ID: return True
    channel_id = REQUIRED_CHANNEL_ID.strip()
    if channel_id.lstrip('-').isdigit(): channel_id = int(channel_id)
    elif not str(channel_id).startswith('@'): channel_id = f"@{channel_id}"
        
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True
    except TelegramError as e:
        logging.error(f"Membership check failed: {e}")
        return False
    return False

# --- Core Bot Menus ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id)
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

    if update.message: await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def send_store_menu(query, context: ContextTypes.DEFAULT_TYPE):
    labels = load_labels()
    text = "Welcome to the Store! Select an option below:"
    keyboard = [
        [InlineKeyboardButton("📦 Method", callback_data="method")],
        [
            InlineKeyboardButton(f"💷 {labels.get('wallet', 'Wallet')}", callback_data="wallet"),
            InlineKeyboardButton(f"☎️ {labels.get('support', 'Support')} ↗️", url=make_safe_url(SUPPORT_LINK))
        ],
        [
            InlineKeyboardButton(f"🛡️ {labels.get('rules', 'Rules')}", callback_data="rules_store"),
            InlineKeyboardButton(f"📄 {labels.get('channel', 'Channel')} ↗️", url=make_safe_url(UPDATES_CHANNEL_LINK))
        ],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_wallet_menu(query_or_message, user_id: int):
    join_date = datetime.now().strftime("%d-%m-%Y") 
    balances = load_balances()
    current_balance = balances.get(str(user_id), 0.0)
    
    text = (
        "====================================\n"
        f"💳 <b>ID:</b> {user_id}\n"
        f"💰 <b>Balance:</b> £{current_balance:.2f}\n"
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
    
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_membership(user_id, context): await send_wallet_menu(update.message, user_id)
    else: await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def send_payment_methods(query_or_message, amount: str):
    text = f"🕶️ <b>£{amount} Top-Up</b>\n\nChoose your payment method:"
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_{amount}_BTC")],
        [InlineKeyboardButton("Ⓞ SOL", callback_data=f"pay_{amount}_SOL")],
        [InlineKeyboardButton("Ł LTC", callback_data=f"pay_{amount}_LTC")],
        [InlineKeyboardButton("⬅️ Back", callback_data="wallet")]
    ]
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await query_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# --- Admin Panel Login Logic ---
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"), InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="admin_add_stock"), InlineKeyboardButton("💰 Prices", callback_data="admin_prices")],
        [InlineKeyboardButton("📝 Description", callback_data="admin_descriptions"), InlineKeyboardButton("🏷 Labels", callback_data="admin_labels")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"), InlineKeyboardButton("📦 Deliveries", callback_data="admin_deliveries")],
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
    if update.message.text == ADMIN_PASSWORD:
        admin_sessions[user_id] = datetime.now() + timedelta(hours=2)
        await update.message.reply_text("✅ <b>Access granted!</b> Session lasts 2 hours.\n\n🛠 <b>Admin Panel</b>\n\nChoose a section:", reply_markup=get_admin_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ <b>Incorrect password.</b> Admin access denied.", parse_mode="HTML")
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin login cancelled.")
    return ConversationHandler.END

# --- Text & Photo Input Handler ---
async def handle_general_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_states:
        state_data = user_states.pop(user_id)
        state = state_data.get("state")
        
        # --- Normal User Input ---
        if state == "WAITING_CUSTOM_AMOUNT" and update.message.text:
            try:
                amount = float(update.message.text.strip())
                if amount < 70:
                    await update.message.reply_text("❌ Minimum custom amount is £70. Please try again:")
                    user_states[user_id] = {"state": "WAITING_CUSTOM_AMOUNT"}
                    return
                amount_str = f"{amount:g}"
                await send_payment_methods(update.message, amount_str)
            except ValueError:
                await update.message.reply_text("❌ Invalid format. Numbers only, e.g., 70:")
                user_states[user_id] = {"state": "WAITING_CUSTOM_AMOUNT"}
            return

        elif state == "WAITING_SCREENSHOT" and update.message.photo:
            amount = state_data["amount"]
            await update.message.reply_text("✅ <b>Screenshot received!</b>\n\nOur admins will verify your transaction shortly. Once confirmed, your wallet balance will be updated.", parse_mode="HTML")
            
            if ADMIN_CHAT_ID:
                keyboard = [
                    [InlineKeyboardButton("✅ Accept", callback_data=f"receipt_accept_{user_id}_{amount}"),
                     InlineKeyboardButton("❌ Decline", callback_data=f"receipt_reject_{user_id}")]
                ]
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=f"🧾 <b>New Payment Receipt</b>\nUser ID: <code>{user_id}</code>\nAmount: £{amount}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
            else:
                logging.warning("ADMIN_CHAT_ID not configured! Receipts will not be delivered.")
            return

        # --- Admin Inputs ---
        elif state == "WAITING_NEW_STOCK" and update.message.text:
            lines = update.message.text.strip().split('\n')
            methods = load_methods()
            added_count = 0
            failed_lines = []
            
            for line in lines:
                if not line.strip(): continue
                try:
                    title_part, rest = line.split('=', 1)
                    desc_part, price_part = rest.rsplit('-', 1)
                    title, desc, price = title_part.strip(), desc_part.strip(), price_part.replace('£', '').strip()
                    new_id = str(max([int(m['id']) for m in methods] + [0]) + 1)
                    methods.append({"id": new_id, "title": title, "desc": desc, "price": price})
                    added_count += 1
                except ValueError: failed_lines.append(line)
            
            save_methods(methods)
            response = f"✅ Successfully added {added_count} new stock items!"
            if failed_lines: response += "\n\n⚠️ Failed to parse the following lines:\n" + "\n".join(failed_lines)
            await update.message.reply_text(response, reply_markup=get_admin_keyboard())

        elif state == "WAITING_DESC" and update.message.text:
            method_id = state_data["method_id"]
            methods = load_methods()
            for m in methods:
                if m['id'] == method_id: m['desc'] = update.message.text
            save_methods(methods)
            await update.message.reply_text("✅ Description updated successfully!", reply_markup=get_admin_keyboard())
            
        elif state == "WAITING_PRICE" and update.message.text:
            method_id = state_data["method_id"]
            methods = load_methods()
            for m in methods:
                if m['id'] == method_id: m['price'] = update.message.text.replace('£', '').strip()
            save_methods(methods)
            await update.message.reply_text("✅ Price updated successfully!", reply_markup=get_admin_keyboard())

        elif state == "WAITING_LABEL" and update.message.text:
            label_key = state_data["label_key"]
            labels = load_labels()
            labels[label_key] = update.message.text.strip()
            save_labels(labels)
            await update.message.reply_text(f"✅ Label updated to '{update.message.text}' successfully!", reply_markup=get_admin_keyboard())
            
        elif state == "WAITING_METHOD_TITLE" and update.message.text:
            method_id = state_data["method_id"]
            methods = load_methods()
            for m in methods:
                if m['id'] == method_id: m['title'] = update.message.text.strip()
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
                await update.message.reply_text(f"❌ Failed to send delivery to user. They might have blocked the bot.\nError: {e}", reply_markup=get_admin_keyboard())
        return

# --- Main Callback Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # --- ADMIN ACTIONS ---
    if data.startswith("admin_") or data.startswith("editdesc_") or data.startswith("editprice_") or data.startswith("editlabel_") or data.startswith("editmethodtitle_") or data.startswith("deliver_") or data.startswith("receipt_"):
        
        # Process Receipt Approvals (Handled by Admin)
        if data.startswith("receipt_accept_"):
            parts = data.split("_")
            target_user = str(parts[2])
            amount = float(parts[3])
            
            balances = load_balances()
            current = balances.get(target_user, 0.0)
            balances[target_user] = current + amount
            save_balances(balances)
            
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ <b>ACCEPTED</b> by Admin", parse_mode="HTML")
            try:
                await context.bot.send_message(chat_id=target_user, text=f"🎉 <b>Payment Approved!</b>\n\nYour wallet has been credited with £{amount}.\nYour new balance is £{balances[target_user]:.2f}.", parse_mode="HTML")
            except: pass
            return

        elif data.startswith("receipt_reject_"):
            parts = data.split("_")
            target_user = parts[2]
            
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ <b>DECLINED</b> by Admin", parse_mode="HTML")
            try:
                await context.bot.send_message(chat_id=target_user, text="❌ <b>Payment Declined</b>\n\nWe were unable to verify your recent transaction. Please ensure the funds were successfully sent to the correct address on the correct network. Contact support for further assistance.", parse_mode="HTML")
            except: pass
            return

        # Security check for regular admin buttons
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
            user_states[user_id] = {"state": "WAITING_NEW_STOCK"}
            await query.answer()
            text = "➕ <b>Add New Stock List</b>\n\nPlease send your stock items in this exact format:\n<code>Store Name = Description - Price</code>\n\n<b>Example:</b>\n<code>Newbalance.co.uk = BIN + meth (£400) - £45</code>\n<code>Booking.com = bin + meth(£300) - 45</code>"
            await query.edit_message_text(text, parse_mode="HTML")
        elif data == "admin_descriptions":
            await query.answer()
            methods = load_methods()
            keyboard = [[InlineKeyboardButton(f"{m['title']}", callback_data=f"editdesc_{m['id']}")] for m in methods]
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("📝 <b>Edit Descriptions</b>\n\nSelect a method below to update its description:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("editdesc_"):
            user_states[user_id] = {"state": "WAITING_DESC", "method_id": data.split("_")[1]}
            await query.answer()
            await query.edit_message_text("📝 <b>Please type the new description for this method now:</b>", parse_mode="HTML")
        elif data == "admin_prices":
            await query.answer()
            methods = load_methods()
            keyboard = [[InlineKeyboardButton(f"{m['title']} (£{m['price']})", callback_data=f"editprice_{m['id']}")] for m in methods]
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("💰 <b>Edit Prices</b>\n\nSelect a method below to update its price:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("editprice_"):
            user_states[user_id] = {"state": "WAITING_PRICE", "method_id": data.split("_")[1]}
            await query.answer()
            await query.edit_message_text("💰 <b>Please type the new price (numbers only):</b>", parse_mode="HTML")
        elif data == "admin_labels":
            await query.answer()
            labels = load_labels()
            methods = load_methods()
            keyboard = [
                [InlineKeyboardButton(f"✏️ 💷 {labels.get('wallet', 'Wallet')}", callback_data="editlabel_wallet")],
                [InlineKeyboardButton(f"✏️ 🛡️ {labels.get('rules', 'Rules')}", callback_data="editlabel_rules")],
                [InlineKeyboardButton(f"✏️ ☎️ {labels.get('support', 'Support')}", callback_data="editlabel_support")],
                [InlineKeyboardButton(f"✏️ 📄 {labels.get('channel', 'Channel')}", callback_data="editlabel_channel")]
            ]
            for m in methods:
                keyboard.append([InlineKeyboardButton(f"✏️ 📦 {m['title']}", callback_data=f"editmethodtitle_{m['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_home")])
            await query.edit_message_text("🏷 <b>Labels & Titles Editor</b>\n\nClick a button below to rename Menu Items or Method Names:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("editlabel_"):
            key = data.split("_")[1]
            user_states[user_id] = {"state": "WAITING_LABEL", "label_key": key}
            await query.answer()
            await query.edit_message_text(f"🏷 <b>Type the new name for '{key.title()}':</b>", parse_mode="HTML")
        elif data.startswith("editmethodtitle_"):
            method_id = data.split("_")[1]
            user_states[user_id] = {"state": "WAITING_METHOD_TITLE", "method_id": method_id}
            await query.answer()
            await query.edit_message_text(f"🏷 <b>Type the new Title for this method:</b>", parse_mode="HTML")
        elif data == "admin_deliveries":
            await query.answer()
            carts = load_carts()
            if not carts:
                await query.edit_message_text("📦 <b>Pending Deliveries</b> (0 carts)\n\nNo pending orders found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Menu", callback_data="admin_home")]]), parse_mode="HTML")
                return
            text = f"📦 <b>Pending Deliveries</b> ({len(carts)} carts)\n\n"
            keyboard = []
            for c in carts:
                text += f"• Cart {c['cart_id']}  User: {c['user_id']}\n{c['items']} item  £{c['price']}  {c['date']}\n"
                keyboard.append([InlineKeyboardButton(f"📤 Deliver Cart #{c['cart_id']}  ({c['items']} item)", callback_data=f"deliver_{c['cart_id']}_{c['user_id']}")])
            keyboard.append([InlineKeyboardButton("⬅️ Admin Menu", callback_data="admin_home")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif data.startswith("deliver_"):
            parts = data.split("_")
            cart_id = parts[1]
            target_user = parts[2]
            user_states[user_id] = {"state": "WAITING_DELIVERY", "cart_id": cart_id, "user_id": target_user}
            await query.answer()
            await query.edit_message_text(f"📤 <b>Delivery Mode (Cart #{cart_id})</b>\n\nPlease upload the delivery file or type the details now. It will be sent directly to user {target_user}.", parse_mode="HTML")
        elif data == "admin_broadcast":
            user_states[user_id] = {"state": "WAITING_BROADCAST"}
            await query.answer()
            await query.edit_message_text("📢 <b>Broadcast Mode</b>\n\nPlease send the message or photo you want to broadcast to all users:", parse_mode="HTML")
        else:
            await query.answer("Section under construction!", show_alert=True)
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
        await query.answer()
        await send_wallet_menu(query, user_id)

    elif data == "custom_topup":
        user_states[user_id] = {"state": "WAITING_CUSTOM_AMOUNT"}
        await query.answer()
        text = "💰 <b>Custom Top-Up</b>\n\nPlease enter the amount you wish to deposit in £ (Numbers only, e.g., 70):"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data.startswith("topup_"):
        await query.answer()
        amount = data.split("_")[1]
        await send_payment_methods(query, amount)

    elif data.startswith("pay_"):
        await query.answer()
        parts = data.split("_")
        amount = parts[1]
        crypto = parts[2]
        
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
        user_states[user_id] = {"state": "WAITING_SCREENSHOT", "amount": amount}
        text = f"📸 <b>UPLOAD SCREENSHOT</b>\n– – – – – – – – – – – –\n\nPlease send the transaction screenshot/receipt for £{amount} now."
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="wallet")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "rules_main" or data == "rules_store":
        await query.answer()
        back_data = "main_menu" if data == "rules_main" else "access_store"
        await query.edit_message_text(f"🛡️ <b>Rules</b>\n\n{RULES_TEXT}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=back_data)]]), parse_mode="HTML")

    elif data == "method":
        await query.answer()
        methods = load_methods()
        keyboard = [[InlineKeyboardButton(f"{m['title']}", callback_data=f"view_method_{m['id']}")] for m in methods]
        keyboard.append([InlineKeyboardButton("🔙 Back to Store", callback_data="access_store")])
        await query.edit_message_text("📦 <b>Methods Catalog</b>\n\nSelect method below to view details:\n\n====================================", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("view_method_"):
        await query.answer()
        method_id = data.split("_")[2]
        method = next((m for m in load_methods() if m['id'] == method_id), None)
        if method:
            text = f"📚 <b>{method['title']}</b> {method['desc']}\n£{method['price']}\n\n---------------------------------"
            keyboard = [
                [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{method['id']}")],
                [InlineKeyboardButton("🔙 Back to Catalog", callback_data="method")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("buy_"):
        await query.answer()
        method_id = data.split("_")[1]
        method = next((m for m in load_methods() if m['id'] == method_id), None)
        if method:
            balances = load_balances()
            current_balance = balances.get(str(user_id), 0.0)
            try: price = float(method['price'])
            except: price = 0.0

            if current_balance >= price:
                balances[str(user_id)] = current_balance - price
                save_balances(balances)
                
                cart_id = os.urandom(4).hex()
                carts = load_carts()
                carts.append({
                    "cart_id": cart_id,
                    "user_id": user_id,
                    "items": 1,
                    "price": f"{price:.2f}",
                    "date": datetime.now().strftime("%d/%m %H:%M")
                })
                save_carts(carts)

                text = f"✅ <b>Purchase Successful!</b>\n\nYou have purchased <b>{method['title']}</b> for £{price:.2f}.\n\nAn admin will process your order and deliver it to you shortly."
                await query.edit_message_text(text, parse_mode="HTML")

                if ADMIN_CHAT_ID:
                    try:
                        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🛒 <b>New Order Received</b>\nCart #{cart_id}\nUser: <code>{user_id}</code>\nItem: {method['title']}\nPrice: £{price}", parse_mode="HTML")
                    except: pass
            else:
                text = f"🛒 <b>Purchase Selection</b>\n\n<b>Item:</b> {method['title']}\n<b>Price:</b> £{method['price']}\n\n❌ <b>Insufficient Balance</b> (Current: £{current_balance:.2f})\n\nPlease top up your wallet to proceed with this purchase."
                keyboard = [
                    [InlineKeyboardButton("💷 Go to Wallet", callback_data="wallet")],
                    [InlineKeyboardButton("🔙 Back to Details", callback_data=f"view_method_{method['id']}")]
                ]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "main_menu":
        await query.answer()
        await start(update, context)

def main():
    if not BOT_TOKEN: raise ValueError("BOT_TOKEN environment variable is not set!")
    app = Application.builder().token(BOT_TOKEN).build()

    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_start)],
        states={WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)]},
        fallbacks=[CommandHandler('cancel', cancel_admin)]
    )
    
    app.add_handler(admin_conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_general_messages))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is successfully running...")
    app.run_polling()

if __name__ == "__main__":
    main()
