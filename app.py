import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- CONFIG ---
NTFY_TOPIC = "ars_elite_signals_2026"
NV_KEY = st.secrets["NVIDIA_API_KEY"]
PAIRS = ["EURUSDT", "GBPUSDT", "USDJPY", "AUDUSDT", "USDCAD", "USDCHF", "EURGBP", "EURJPY", "GBPJPY"]

# --- AI BRAIN ---
def run_debate(df, symbol, history):
    prompt = f"Analyze {symbol}. MSS? Liquidity? 1:3 RR? History: {history}. Data: {df.tail(5).to_json()}. Output: DECISION: [CALL/PUT/REJECT], CONFIDENCE: [%], SL: [Price], TP: [Price]."
    headers = {"Authorization": f"Bearer {NV_KEY}", "Content-Type": "application/json"}
    payload = {"model": "meta/llama-3.1-70b-instruct", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    try:
        r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
        return r.json()['choices'][0]['message']['content']
    except: return "REJECT"

# --- UI ---
st.set_page_config(page_title="V2.1 Stable", page_icon="🏛️")
st.title("🏛️ Omni-Elite Stable")

if 'history' not in st.session_state: st.session_state.history = []

if st.button("🚀 START SCANNER"):
    st.success("Scanner Active. Keep this tab OPEN.")
    placeholder = st.empty()
    
    # Using a safer loop for mobile
    while True:
        for pair in PAIRS:
            with placeholder.container():
                st.info(f"Agents Analyzing: {pair}")
                try:
                    # Fetch
                    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1m&limit=10"
                    data = requests.get(url).json()
                    df = pd.DataFrame(data, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i'])
                    df['close'] = df['c'].astype(float)
                    
                    # Brain
                    ans = run_debate(df, pair, st.session_state.history)
                    
                    if "CALL" in ans or "PUT" in ans:
                        # Check confidence
                        if "DECISION: CALL" in ans or "DECISION: PUT" in ans:
                            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=f"{pair}\n{ans}".encode('utf-8'))
                            st.success(f"SIGNAL SENT: {pair}")
                            st.session_state.history.append(f"{pair}: {ans[:15]}")
                            time.sleep(5) # Give you time to see it
                except:
                    continue
                time.sleep(1) # Small rest between pairs to prevent overheat
        
        # Instead of st.rerun(), we just let the while loop continue
        st.write("Cycle Complete. Restarting...")
        time.sleep(2)
