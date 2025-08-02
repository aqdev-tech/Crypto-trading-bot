import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

async def get_llm_analysis(candle_data, current_price):
    """
    Sends candle data to GROQ LLM for trading analysis, instructing it
    to generate realistic entry prices based on the live market price.
    """
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not found in .env file"}

    # This prompt is now highly specific, demanding the LLM justify any price
    # that isn't an immediate market order.
    prompt = (
        "You are an expert crypto trading analyst. Your analysis must be sharp, actionable, and grounded in the live data provided."
        f"The current market price for the asset is exactly ${current_price:.2f}. This is the most critical piece of information."
        "Analyze the 1H candle data provided in this context."
        "Your response MUST be a JSON object with the following fields:"
        "- action: (BUY/SELL/HOLD) The trade direction."
        "- entry: (string) The target entry price. If this price is not within 0.5% of the current market price, you MUST provide a clear reason in the 'reason' field for why it is a pending/limit order (e.g., 'waiting for a breakout above resistance' or 'buying a dip at support')."
        "- take_profit: (string) The take profit price."
        "- stop_loss: (string) The stop loss price."
        "- confidence: (float) Your confidence in this signal, from 0.0 to 1.0."
        "- reason: (string) A concise explanation of the technical indicators (RSI, MACD, EMA, Support/Resistance) that justify this signal. If it's a pending order, this field MUST explain the strategy."
        "Generate a signal that a real trader would find useful. Do not invent prices wildly."
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": f"Candle data: {json.dumps(candle_data)}",
                },
            ],
            model="deepseek-r1-distill-llama-70b",
            response_format={"type": "json_object"},
        )
        
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)

    except Exception as e:
        return {"error": f"Failed to get analysis from GROQ: {str(e)}"}