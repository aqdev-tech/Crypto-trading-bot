import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown
from dotenv import load_dotenv

from signal_generator import get_trading_signal
from binance_api import get_current_price # Import to get live price for monitoring

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# In-memory storage
signal_history = []
pending_signals = [] # For active monitoring

# --- Helper Functions ---
def get_action_emoji(action):
    if action == 'BUY':
        return "🚀"
    if action == 'SELL':
        return "📉"
    return "🤔"

# --- Bot Commands & Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and stores user chat_id."""
    if 'chat_ids' not in context.bot_data:
        context.bot_data['chat_ids'] = set()
    context.bot_data['chat_ids'].add(update.message.chat_id)
    
    keyboard = [
        [InlineKeyboardButton("📈 BTC/USDT", callback_data='BTC/USDT')],
        [InlineKeyboardButton("📈 ETH/USDT", callback_data='ETH/USDT')],
        [InlineKeyboardButton("📈 SOL/USDT", callback_data='SOL/USDT')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the Advanced Crypto Signal Bot!\n\n" 
        "I'll send you proactive alerts and can now monitor pending trades for you.",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('monitor_'):
        # User wants to monitor a pending signal
        parts = data.split('_')
        signal_to_monitor = {
            "chat_id": query.message.chat_id,
            "symbol": parts[1],
            "entry": float(parts[2]),
            "action": parts[3],
            "message_id": query.message.message_id # Store message_id to update it later
        }
        pending_signals.append(signal_to_monitor)
        await query.edit_message_text(text=f"✅ Monitoring enabled for {parts[1]} at ${float(parts[2]):.2f}. I will alert you when the price is hit.")
    
    elif '/' in data: # It's a currency pair
        await generate_signal(query.message, context, data)
    
    elif data == 'signal_helpful_yes':
        await query.edit_message_text(text="😊 Great! Thanks for the feedback.")
    
    elif data == 'signal_helpful_no':
        await query.edit_message_text(text="😔 Sorry to hear that. We are always improving.")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /signal command."""
    try:
        symbol = context.args[0].upper() if context.args else 'BTC/USDT'
        await generate_signal(update.message, context, symbol)
    except (IndexError, ValueError):
        await update.message.reply_text(escape_markdown('⚠️ Usage: /signal <PAIR>', version=2), parse_mode='MarkdownV2')

async def generate_signal(source, context, symbol):
    """Generates and sends a trading signal."""
    reply_func = source.edit_text if hasattr(source, 'edit_text') else source.reply_text
    
    try:
        await reply_func(escape_markdown(f"⏳ Generating signal for `{symbol}`, please wait...", version=2), parse_mode='MarkdownV2')
        signal_data = await get_trading_signal(symbol)
        
        if "error" in signal_data:
            await reply_func(f"❌ Error: {escape_markdown(signal_data['error'], version=2)}")
            return

        signal_data['symbol'] = symbol
        signal_history.append(signal_data)
        action_emoji = get_action_emoji(signal_data['action'])

        keyboard = [] # Start with an empty keyboard
        if signal_data['signal_type'] == 'PENDING':
            title = f"⏳ *Pending Signal - {escape_markdown(signal_data['symbol'], version=2)}*"
            entry_line = f"*Entry Target:* ${escape_markdown(f'{signal_data["entry"]:.2f}', version=2)} (Wait for price)"
            # Add the monitor button for pending signals
            monitor_callback = f"monitor_{signal_data['symbol']}_{signal_data['entry']}_{signal_data['action']}"
            keyboard.append([InlineKeyboardButton("🔔 Monitor this Trade", callback_data=monitor_callback)])
        else: # MARKET
            title = f"{action_emoji} *{escape_markdown(signal_data['symbol'], version=2)} Signal*"
            entry_line = f"*Entry:* ${escape_markdown(f'{signal_data["entry"]:.2f}', version=2)}"

        confidence_note = ""
        if 'confidence_note' in signal_data:
            confidence_note = f"\n⚠️ *Note:* {escape_markdown(signal_data['confidence_note'], version=2)}"

        message = (
            f"{title}\n\n"
            f"*Action:* `{signal_data['action']}`\n"
            f"{entry_line}\n"
            f"🎯 *Take Profit:* ${escape_markdown(f'{signal_data['take_profit']:.2f}', version=2)}\n"
            f"🛡️ *Stop Loss:* ${escape_markdown(f'{signal_data['stop_loss']:.2f}', version=2)}\n"
            f"💪 *Confidence:* `{escape_markdown(f'{signal_data['confidence']:.2f}', version=2)}`{confidence_note}\n\n"
            f"*Reason:* {escape_markdown(signal_data['reason'], version=2)}\n\n"
            f"*Live Price:* ${escape_markdown(f'{signal_data['live_price']:.2f}', version=2)}"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await reply_func(message, parse_mode='MarkdownV2', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in generate_signal: {e}")
        await reply_func(escape_markdown("❌ An unexpected error occurred. Please try again.", version=2), parse_mode='MarkdownV2')

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the last 5 trading signals."""
    if not signal_history:
        await update.message.reply_text("📜 No signals in history yet.")
        return

    await update.message.reply_text("*--- Last 5 Signals ---*", parse_mode='MarkdownV2')
    for signal_data in signal_history[-5:]:
        action_emoji = get_action_emoji(signal_data['action'])
        message = (
            f"{action_emoji} *{escape_markdown(signal_data.get('symbol', 'N/A'), version=2)}*\n"
            f"`{signal_data['action']}` | Entry: ${escape_markdown(f'{signal_data["entry"]:.2f}', version=2)}\n"
            f"TP: ${escape_markdown(f'{signal_data['take_profit']:.2f}', version=2)} | SL: ${escape_markdown(f'{signal_data['stop_loss']:.2f}', version=2)}\n"
            f"Confidence: `{escape_markdown(f'{signal_data['confidence']:.2f}', version=2)}`"
        )
        await update.message.reply_text(message, parse_mode='MarkdownV2')

async def proactive_signals(context: ContextTypes.DEFAULT_TYPE):
    """Proactively sends high-confidence signals to all subscribed users."""
    if 'chat_ids' not in context.bot_data or not context.bot_data['chat_ids']:
        return

    for symbol in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
        signal_data = await get_trading_signal(symbol)
        await asyncio.sleep(10) # Add a 10-second delay to avoid rate limiting
        if "error" not in signal_data and signal_data.get('confidence', 0) > 0.85:
            action_emoji = get_action_emoji(signal_data['action'])
            message = (
                f"🔥 *High-Confidence Alert: {escape_markdown(symbol, version=2)}*\n\n"
                f"{action_emoji} *Action:* `{signal_data['action']}`\n"
                f"*Entry:* ${escape_markdown(f'{signal_data["entry"]:.2f}', version=2)}\n"
                f"🎯 *TP:* ${escape_markdown(f'{signal_data['take_profit']:.2f}', version=2)} | 🛡️ *SL:* ${escape_markdown(f'{signal_data['stop_loss']:.2f}', version=2)}\n"
                f"💪 *Confidence:* `{escape_markdown(f'{signal_data['confidence']:.2f}', version=2)}`\n"
                f"🧠 *Reason:* {escape_markdown(signal_data['reason'], version=2)}"
            )
            for chat_id in context.bot_data['chat_ids']:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='MarkdownV2')
                except Exception as e:
                    logger.error(f"Failed to send proactive signal to {chat_id}: {e}")

# --- Monitoring Engine ---
async def monitor_pending_signals(context: ContextTypes.DEFAULT_TYPE):
    """Monitors pending signals and alerts user when entry price is hit."""
    global pending_signals
    signals_to_remove = []

    for signal_to_monitor in pending_signals:
        symbol = signal_to_monitor['symbol']
        entry_price = signal_to_monitor['entry']
        action = signal_to_monitor['action']
        chat_id = signal_to_monitor['chat_id']
        message_id = signal_to_monitor['message_id']

        current_price = await get_current_price(symbol)
        if isinstance(current_price, dict) and "error" in current_price:
            logger.info(f"Error fetching current price for {symbol} during monitoring: {current_price['error']}")
            continue # Skip to next signal if price fetch fails

        price_hit = False
        if action == 'BUY' and current_price <= entry_price:
            price_hit = True
        elif action == 'SELL' and current_price >= entry_price:
            price_hit = True

        if price_hit:
            logger.info(f"Entry price hit for {symbol} ({action} at {entry_price}). Re-evaluating signal...")
            # Re-evaluate the signal with fresh data
            re_evaluated_signal = await get_trading_signal(symbol)

            if "error" not in re_evaluated_signal and re_evaluated_signal['signal_type'] == 'MARKET':
                # Trade confirmed
                message = (
                    f"✅ *TRADE CONFIRMED: {escape_markdown(symbol, version=2)}*\n\n"
                    f"*Action:* `{re_evaluated_signal['action']}`\n"
                    f"*Entry:* ${escape_markdown(f'{re_evaluated_signal["entry"]:.2f}', version=2)}\n"
                    f"🎯 *Take Profit:* ${escape_markdown(f'{re_evaluated_signal["take_profit"]:.2f}', version=2)}\n"
                    f"🛡️ *Stop Loss:* ${escape_markdown(f'{re_evaluated_signal["stop_loss"]:.2f}', version=2)}\n"
                    f"💪 *Confidence:* `{escape_markdown(f'{re_evaluated_signal["confidence"]:.2f}', version=2)}`\n\n"
                    f"*Reason:* {escape_markdown(re_evaluated_signal['reason'], version=2)}"
                )
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='MarkdownV2')
                signals_to_remove.append(signal_to_monitor)
            else:
                # Signal invalidated or error during re-evaluation
                reason = re_evaluated_signal.get('error', 'Indicators no longer align.')
                message = (
                    f"❌ *SIGNAL CANCELLED: {escape_markdown(symbol, version=2)}*\n\n"
                    f"The entry price of ${escape_markdown(f'{entry_price:.2f}', version=2)} was hit, but the trade setup is no longer valid.\n"
                    f"*Reason:* {escape_markdown(reason, version=2)}"
                )
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='MarkdownV2')
                signals_to_remove.append(signal_to_monitor)

    # Remove processed signals
    for signal in signals_to_remove:
        pending_signals.remove(signal)

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in .env file")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler('signal', signal_command))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CallbackQueryHandler(button))

    job_queue = application.job_queue
    job_queue.run_repeating(proactive_signals, interval=900, first=10)
    job_queue.run_repeating(monitor_pending_signals, interval=60) # Monitor every 60 seconds

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()