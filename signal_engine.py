
from binance_api import get_btc_usdt_candles
from groq_agent import get_llm_analysis

async def get_trading_signal():
    """
    Orchestrates fetching candle data, getting LLM analysis,
    and returning the final trading signal.
    """
    candles = await get_btc_usdt_candles()
    if "error" in candles:
        return candles

    analysis = await get_llm_analysis(candles)
    if "error" in analysis:
        return analysis
        
    # Basic validation of the analysis dictionary
    required_keys = ["action", "entry", "take_profit", "stop_loss", "confidence", "reason"]
    if not all(key in analysis for key in required_keys):
        return {"error": "LLM response is missing required fields."}

    return analysis
