import requests
import pandas as pd
import ta
import time
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

RSI_SOBREVENDIDO = 30
RSI_SOBRECOMPRADO = 70
STOCH_SOBREVENDIDO = 20
STOCH_SOBRECOMPRADO = 80
INTERVALO_CHECAGEM = 60 * 15

alertas_enviados = {}

def get_top50_symbols():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        usdt = [x for x in data if x["symbol"].endswith("USDT") and float(x["quoteVolume"]) > 10000000]
        usdt.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
        return [x["symbol"] for x in usdt[:50]]
    except:
        return ["BTCUSDT","ETHUSDT","XRPUSDT","SOLUSDT","BNBUSDT","ADAUSDT","DOGEUSDT"]

def get_candles(symbol, interval="1h", limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=["time","open","high","low","close","volume","ct","qav","nt","tbbav","tbqav","ignore"])
        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        return df
    except:
        return None

def calcular_indicadores(df):
    try:
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()
        return df
    except:
        return None

def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def checar_sinal(symbol, df):
    rsi = df["rsi"].iloc[-1]
    stoch = df["stoch_k"].iloc[-1]
    preco = df["close"].iloc[-1]
    agora = datetime.now().strftime("%H:%M")
    chave = f"{symbol}_{agora[:13]}"

    if alertas_enviados.get(chave):
        return

    if rsi <= RSI_SOBREVENDIDO and stoch <= STOCH_SOBREVENDIDO:
        msg = (
            f"🟢 <b>SOBREVENDIDO EXTREMO</b>\n"
            f"💰 {symbol.replace('USDT','')}/USDT\n"
            f"📊 RSI 14: {rsi:.1f} | Stoch 14: {stoch:.1f}\n"
            f"💵 Preco: ${preco:,.4f}\n"
            f"⏰ {agora} | Grafico 1H\n"
            f"👉 Analise o 15min para entrada!"
        )
        enviar_telegram(msg)
        alertas_enviados[chave] = True
        print(f"[BUY] {symbol} RSI:{rsi:.1f} Stoch:{stoch:.1f}")

    elif rsi >= RSI_SOBRECOMPRADO and stoch >= STOCH_SOBRECOMPRADO:
        msg = (
            f"🔴 <b>SOBRECOMPRADO EXTREMO</b>\n"
            f"💰 {symbol.replace('USDT','')}/USDT\n"
            f"📊 RSI 14: {rsi:.1f} | Stoch 14: {stoch:.1f}\n"
            f"💵 Preco: ${preco:,.4f}\n"
            f"⏰ {agora} | Grafico 1H\n"
            f"👉 Analise o 15min para entrada!"
        )
        enviar_telegram(msg)
        alertas_enviados[chave] = True
        print(f"[SELL] {symbol} RSI:{rsi:.1f} Stoch:{stoch:.1f}")

def main():
    print("Bot iniciado!")
    enviar_telegram("✅ <b>Bot de Alertas iniciado!</b>\nMonitorando Top 50 cripto no 1H...\nRSI 14 | Stoch 14/3/3")

    while True:
        try:
            symbols = get_top50_symbols()
            print(f"Verificando {len(symbols)} moedas...")

            for symbol in symbols:
                df = get_candles(symbol)
                if df is None:
                    continue
                df = calcular_indicadores(df)
                if df is None:
                    continue
                checar_sinal(symbol, df)
                time.sleep(0.3)

            print(f"Checagem concluida. Proxima em 15 minutos.")
            time.sleep(INTERVALO_CHECAGEM)

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
