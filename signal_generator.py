import re
import asyncio
from binance_api import get_candles, get_current_price
from groq_agent import get_llm_analysis

def clean_price(price_str):
    """Removes non-numeric characters from a price string."""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    cleaned_str = re.sub(r"[^\d.]", "", str(price_str))
    return float(cleaned_str) if cleaned_str else 0.0

async def get_trading_signal(symbol='BTC/USDT', max_retries=3):
    """
    Orchestrates fetching data, getting LLM analysis, validating it,
    and returning the final, classified trading signal with a confidence note.
    """
    candles = await get_candles(symbol)
    if "error" in candles:
        return candles

    current_price = await get_current_price(symbol)
    if isinstance(current_price, dict) and "error" in current_price:
        return current_price

    for attempt in range(max_retries):
        analysis = await get_llm_analysis(candles, current_price)
        if "error" in analysis:
            if attempt == max_retries - 1:
                return analysis
            await asyncio.sleep(2)
            continue

        required_keys = ["action", "entry", "take_profit", "stop_loss", "confidence", "reason"]
        if not all(key in analysis for key in required_keys):
            if attempt == max_retries - 1:
                return {"error": "LLM response is missing required fields."}
            await asyncio.sleep(2)
            continue

        try:
            analysis['entry'] = clean_price(analysis['entry'])
            analysis['take_profit'] = clean_price(analysis['take_profit'])
            analysis['stop_loss'] = clean_price(analysis['stop_loss'])
        except (ValueError, TypeError):
            if attempt == max_retries - 1:
                return {"error": "Invalid price format in LLM response after cleaning."}
            await asyncio.sleep(2)
            continue

        if analysis['action'] == 'BUY' and (analysis['take_profit'] <= analysis['entry'] or analysis['stop_loss'] >= analysis['entry']):
            if attempt == max_retries - 1:
                return {"error": "Invalid BUY signal logic."}
            await asyncio.sleep(2)
            continue
        
        if analysis['action'] == 'SELL' and (analysis['take_profit'] >= analysis['entry'] or analysis['stop_loss'] <= analysis['entry']):
            if attempt == max_retries - 1:
                return {"error": "Invalid SELL signal logic."}
            await asyncio.sleep(2)
            continue

        price_diff_percentage = abs(analysis['entry'] - current_price) / current_price
        analysis['signal_type'] = 'PENDING' if price_diff_percentage > 0.005 else 'MARKET'

        # Add context-aware confidence note if below threshold
        if analysis['confidence'] < 0.70:
            if analysis['action'] == 'BUY':
                analysis['confidence_note'] = "Low confidence – Entry should only be acted on after bullish confirmation (e.g., a strong green candle closing above a key level)."
            elif analysis['action'] == 'SELL':
                analysis['confidence_note'] = "Low confidence – Entry should only be acted on after bearish confirmation (e.g., a strong red candle closing below a key level)."

        analysis['live_price'] = current_price
        return analysis

    return {"error": "Failed to generate a valid signal after multiple retries."}