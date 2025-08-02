
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

from signal_engine import get_trading_signal

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text("Welcome to the Crypto Trading Signal Bot! Use /signal to get the latest BTC/USDT trading signal.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the trading signal."""
    try:
        await update.message.reply_text("Generating signal, please wait...")
        signal_data = await get_trading_signal()
        
        if "error" in signal_data:
            await update.message.reply_text(f"Error: {signal_data['error']}")
            return

        message = f"""**BTC/USDT Signal**

**Action:** {signal_data['action']}
**Entry:** ${signal_data['entry']}
**Take Profit:** ${signal_data['take_profit']}
**Stop Loss:** ${signal_data['stop_loss']}
**Confidence:** {signal_data['confidence']}
**Reason:** {signal_data['reason']}"""
        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in /signal command: {e}")
        await update.message.reply_text("An error occurred while generating the signal. Please try again later.")

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in .env file")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal))

    application.run_polling()

if __name__ == "__main__":
    main()
