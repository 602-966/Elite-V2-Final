import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
NTFY_TOPIC = "ars_elite_signals_2026"
NV_KEY = st.secrets["NVIDIA_API_KEY"]

# Pairs mapped for Binance API compatibility 
PAIRS = [
    "EURUSDT", "GBPUSDT", "USDJPY", "AUDUSDT", "USDCAD", "USDCHF", 
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCAD", 
    "AUDCAD", "GBPAUD", "GBPCHF", "CADCHF", "CHFJPY"
]

# ==========================================
# 2. THE AI BRAIN (LLAMA 3.1 70B)
# ==========================================
def run_elite_debate(df, symbol, learning_history):
    last_price = df['close'].iloc[-1]
    
    # Format the last 8 trades so the AI can learn from recent mistakes/wins
    history_context = "\n".join(learning_history[-8:]) 
    
    prompt = f"""
    You are a Virtual Trading Floor of 4 Elite Agents debating {symbol} at ${last_price}.
    
    RECENT TRADING HISTORY (Adjust your strictness based on this):
    {history_context if history_context else "No history yet. Be strict and conservative."}

    PROFESSIONAL CHECKLIST:
    1. MARKET REGIME: Is it trending cleanly or chopping?
    2. TECHNICALS: Find Market Structure Shifts (MSS) & Liquidity Sweeps.
    3. MATH: Calculate a strict 1:3 Risk-to-Reward ratio.

    DATA (Last 10 minutes): {df.tail(10).to_json()}

    OUTPUT FORMAT EXACTLY LIKE THIS:
    DECISION: [CALL, PUT, or REJECT]
    CONFIDENCE: [0-100%]
    SL: [Price] | TP: [Price]
    REASON: [1 short sentence explaining the MSS or Liquidity Sweep]
    """

    headers = {
        "Authorization": f"Bearer {NV_KEY}", 
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.1-70b-instruct", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.1
    }
    
    try:
        response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=8)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return "DECISION: REJECT"

# ==========================================
# 3. FAST DATA & ALERTS
# ==========================================
def send_ntfy(msg, confidence):
    # If AI is highly confident, trigger the highest priority alarm on your phone
    priority = "urgent" if "100" in confidence or "90" in confidence else "high"
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                  data=msg.encode('utf-8'),
                  headers={"Title": "💎 ELITE SIGNAL", "Priority": priority, "Tags": "chart_with_upwards_trend,moneybag"})

def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=15"
    res = requests.get(url).json()
    df = pd.DataFrame(res, columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'q', 'n', 'tb', 'tq', 'i'])
    df['close'] = df['c'].astype(float)
    return df

# ==========================================
# 4. USER INTERFACE & MAIN LOOP
# ==========================================
st.set_page_config(page_title="Omni-Elite AI", page_icon="🏛️")
st.title("🏛️ Omni-Elite Trading Floor")

# Initialize AI Memory
if 'history' not in st.session_state: 
    st.session_state.history = []
if 'active_trades' not in st.session_state: 
    st.session_state.active_trades = {}

st.sidebar.header("🧠 AI Training Memory")
st.sidebar.write("Recent outcomes the AI is using to learn:")
st.sidebar.write(st.session_state.history)

if st.button("🚀 ACTIVATE AUTO-LEARNING SCANNER"):
    st.success("System Live. Scanning all pairs independently...")
    status_text = st.empty()
    
    while True:
        for pair in PAIRS:
            try:
                status_text.info(f"Agents analyzing: {pair}...")
                df = get_data(pair)
                current_price = df['close'].iloc[-1]
                
                # --- AUTO-TRAINING VERIFICATION ---
                # Check if a past trade finished, so we can teach the AI if it won or lost
                if pair in st.session_state.active_trades:
                    trade_data = st.session_state.active_trades[pair]
                    if datetime.now() >= trade_data['check_at']:
                        is_win = (current_price > trade_data['entry'] and trade_data['dir'] == "CALL") or \
                                 (current_price < trade_data['entry'] and trade_data['dir'] == "PUT")
                        
                        result = "WIN ✅" if is_win else "LOSS ❌"
                        st.session_state.history.append(f"{pair} {trade_data['dir']} -> {result}")
                        del st.session_state.active_trades[pair] # Remove from pending
                        st.write(f"Memory Updated: {pair} resulted in {result}")

                # --- NEW SIGNAL SCANNING ---
                analysis = run_elite_debate(df, pair, st.session_state.history)
                
                if "DECISION: CALL" in analysis or "DECISION: PUT" in analysis:
                    direction = "CALL" if "CALL" in analysis else "PUT"
                    
                    # Store trade in memory to check the result 65 seconds later
                    st.session_state.active_trades[pair] = {
                        "entry": current_price,
                        "dir": direction,
                        "check_at": datetime.now() + timedelta(seconds=65)
                    }
                    
                    # Send alert to your phone
                    signal_time = datetime.now().strftime('%H:%M:%S')
                    conf = analysis.split("CONFIDENCE:")[1].split("\n")[0].strip() if "CONFIDENCE:" in analysis else "N/A"
                    
                    alert_msg = f"PAIR: {pair}\nTIME: {signal_time}\n{analysis}"
                    send_ntfy(alert_msg, conf)
                    st.success(f"🔥 Signal Sent: {pair} at {signal_time}")

                time.sleep(0.5) # Fast scan delay
                
            except Exception as e:
                # If a pair isn't supported by the API, quietly skip it and keep running
                continue
                
        # Small pause before restarting the loop
        time.sleep(1)
        st.rerun()
