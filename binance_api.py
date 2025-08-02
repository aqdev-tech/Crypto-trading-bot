import ccxt.async_support as ccxt
import asyncio
import logging

logger = logging.getLogger(__name__)

async def get_candles(symbol='BTC/USDT', time_frame='1h', limit=50, max_retries=3):
    """Fetches candle data from Binance with an automatic retry mechanism."""
    binance = ccxt.binance()
    try:
        for attempt in range(max_retries):
            try:
                ohlcv = await binance.fetch_ohlcv(symbol, time_frame, limit=limit)
                formatted_data = [
                    {
                        "timestamp": candle[0],
                        "open": candle[1],
                        "high": candle[2],
                        "low": candle[3],
                        "close": candle[4],
                        "volume": candle[5]
                    }
                    for candle in ohlcv
                ]
                return formatted_data
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} for get_candles failed: {e}")
                if attempt == max_retries - 1:
                    raise e # Re-raise the final exception
                await asyncio.sleep(2 * (attempt + 1)) # Wait longer after each failure
    except Exception as e:
        return {"error": f"Failed to fetch candle data for {symbol} from Binance after {max_retries} attempts. Reason: {e}"}
    finally:
        await binance.close()

async def get_current_price(symbol='BTC/USDT', max_retries=3):
    """Fetches the current price from Binance with an automatic retry mechanism."""
    binance = ccxt.binance()
    try:
        for attempt in range(max_retries):
            try:
                ticker = await binance.fetch_ticker(symbol)
                return ticker['last']
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} for get_current_price failed: {e}")
                if attempt == max_retries - 1:
                    raise e # Re-raise the final exception
                await asyncio.sleep(2 * (attempt + 1)) # Wait longer after each failure
    except Exception as e:
        return {"error": f"Failed to fetch current price for {symbol} from Binance after {max_retries} attempts. Reason: {e}"}
    finally:
        await binance.close()