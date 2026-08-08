import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Load sensitive configuration from Railway Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")  
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/yourchannel")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support")
UPDATES_CHANNEL_LINK = os.getenv("UPDATES_CHANNEL_LINK", "https://t.me/yourchannel")

# Wallet Addresses from Variables
BTC_ADDRESS = os.getenv("BTC_ADDRESS", "your_btc_address_here")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "your_sol_address_here")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "your_ltc_address_here")

# Customizable text content
STORE_NAME = os.getenv("STORE_NAME", "Mazza X Gaara's Store")
DEVELOPER_TAG = os.getenv("DEVELOPER_TAG", "@Kr3ptoV1")
MANAGER_TAG = os.getenv("MANAGER_TAG", "@mazza4444")
RULES_TEXT = os.getenv("RULES_TEXT", "1. No spamming\n2. Follow channel rules\n3. All purchases are final.")
METHOD_TEXT = os.getenv("METHOD_TEXT", "Available Methods:\n- Method 1: Crypto Transfer\n- Method 2: Manual Direct Payment")

# Top-up grid configuration
TOPUP_AMOUNTS = [
    (70, 100),
    (150, 200),
    (250, 300),
    (350, 400),
    (450, 500),
    (750, 1000)
]

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user is a member of the required channel."""
    if not REQUIRED_CHANNEL_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except TelegramError as e:
        logging.error(f"Error verifying channel membership: {e}")
        return False
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the initial main menu screen."""
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
    """Displays the store menu screen after channel join verification."""
    text = "Welcome to the Store! Select an option below:"
    keyboard = [
        [InlineKeyboardButton("📦 Method", callback_data="method")],
        [
            InlineKeyboardButton("💷 Wallet", callback_data="wallet"),
            InlineKeyboardButton("☎️ Support ↗️", url=SUPPORT_LINK)
        ],
        [
            InlineKeyboardButton("🛡️ Rules", callback_data="rules_store"),
            InlineKeyboardButton("📁 Updates Chan... ↗️", url=UPDATES_CHANNEL_LINK)
        ],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_wallet_menu(query_or_message, user_id: int):
    """Displays the wallet top-up menu matching image_3.png."""
    # Note: In a production bot, join_date and balance would be fetched from your database
    join_date = datetime.now().strftime("%d-%m-%Y") 
    
    text = (
        "====================================\n"
        f"💳 **ID:** {user_id}\n"
        f"💰 **Balance:** £0.00\n"
        f"📅 **Join Date:** {join_date}\n"
        "====================================\n\n"
        "Select a top-up amount below:\n"
        "_Minimum top-up: £70_"
    )
    
    keyboard = []
    for left_amt, right_amt in TOPUP_AMOUNTS:
        keyboard.append([
            InlineKeyboardButton(f"🔶 £{left_amt} 🔶", callback_data=f"topup_{left_amt}"),
            InlineKeyboardButton(f"🔶 £{right_amt} 🔶", callback_data=f"topup_{right_amt}")
        ])
    
    keyboard.append([InlineKeyboardButton("💰 Custom Amount", callback_data="custom_topup")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="access_store")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await query_or_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /wallet command directly."""
    user_id = update.effective_user.id
    if await check_membership(user_id, context):
        await send_wallet_menu(update.message, user_id)
    else:
        await update.message.reply_text("You must join the channel first. Send /start to begin.")

async def send_payment_methods(query, amount: str):
    """Displays the payment method selection matching image_4.png."""
    text = f"🔶 **£{amount} Top-Up**\n\nChoose your payment method:"
    
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_{amount}_BTC")],
        [InlineKeyboardButton("Ⓞ SOL", callback_data=f"pay_{amount}_SOL")],
        [InlineKeyboardButton("Ł LTC", callback_data=f"pay_{amount}_LTC")],
        [InlineKeyboardButton("⬅️ Back", callback_data="wallet")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline button interactions."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "access_store":
        if await check_membership(user_id, context):
            await query.answer()
            await send_store_menu(query, context)
        else:
            await query.answer("You must join our channel to access the store!", show_alert=True)
            text = (
                "⚠️ **Access Restricted**\n\n"
                "To access the store menu, you must first join our updates channel."
            )
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel First", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I Have Joined (Verify)", callback_data="access_store")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
        
        # Select the correct wallet address based on variable settings
        if crypto == "BTC":
            address = BTC_ADDRESS
        elif crypto == "SOL":
            address = SOL_ADDRESS
        else:
            address = LTC_ADDRESS

        text = (
            f"📥 **Payment Details**\n\n"
            f"Amount: £{amount}\n"
            f"Method: {crypto}\n\n"
            f"Please send the equivalent crypto amount to the address below:\n"
            f"`{address}`\n\n"
            f"*(Tap the address to copy it)*\n\n"
            f"After sending, please contact support with your transaction hash."
        )
        keyboard = [
            [InlineKeyboardButton("☎️ Contact Support", url=SUPPORT_LINK)],
            [InlineKeyboardButton("⬅️ Back to Methods", callback_data=f"topup_{amount}")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "custom_topup":
        await query.answer("Custom amount feature coming soon!", show_alert=True)

    elif data == "rules_main" or data == "rules_store":
        await query.answer()
        back_data = "main_menu" if data == "rules_main" else "access_store"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=back_data)]]
        await query.edit_message_text(f"🛡️ **Rules**\n\n{RULES_TEXT}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "method":
        await query.answer()
        keyboard = [[InlineKeyboardButton("🔙 Back to Store", callback_data="access_store")]]
        await query.edit_message_text(f"📦 **Method**\n\n{METHOD_TEXT}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "main_menu":
        await query.answer()
        await start(update, context)

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is successfully running...")
    app.run_polling()

if __name__ == "__main__":
    main()
