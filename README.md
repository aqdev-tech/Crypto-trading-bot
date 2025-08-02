
# AI-Powered Crypto Trading Signal Bot

This Telegram bot provides AI-powered trading signals for various cryptocurrencies based on 1-hour candle data from Binance.

## Features

- **Multi-Pair Support:** Get signals for BTC/USDT, ETH/USDT, SOL/USDT, and other pairs.
- **Dynamic Price Analysis:** Uses real-time market prices to generate realistic signals.
- **Advanced Validation:** Rejects signals with unrealistic entry prices and nonsensical trading logic.
- **Proactive Alerts:** Get notified of high-confidence trading opportunities automatically every 15 minutes.
- **Signal History:** View a history of the last 10 signals.
- **Interactive Interface:** Use buttons to select popular pairs.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd crypto-trading-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file:**
    Create a file named `.env` in the root directory and add your API keys:
    ```
    TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
    GROQ_API_KEY=YOUR_GROQ_API_KEY
    ```

## Running the Bot

To start the bot, run the following command:

```bash
python telegram_bot.py
```

## How to Use

- **`/start`:** Displays a welcome message with buttons to select a trading pair. Any user who starts the bot will automatically receive proactive alerts.
- **`/signal <PAIR>`:** (e.g., `/signal ETH/USDT`) Generates a signal for the specified pair.
- **`/history`:** Shows the last 10 trading signals.

- **Proactive Alerts:** The bot will automatically send you a message if it detects a high-confidence signal (confidence > 0.8) for BTC/USDT, ETH/USDT, or SOL/USDT.
