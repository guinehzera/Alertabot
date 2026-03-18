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

def get_top100_symbols():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot"
        r = requests.get(url, timeout=15)
        data = r.json()
        tickers = data["result"]["list"]
        usdt = [x for x in tickers if x["symbol"].endswith("USDT") and float(x.get("turnover24h", 0)) > 1000000]
        usdt.sort(key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
        symbols = [x["symbol"] for x in usdt[:100]]
        print(f"Encontradas {len(symbols)} moedas")
        return symbols
    except Exception as e:
        print(f"Erro get_symbols: {e}")
        return ["BTCUSDT","ETHUSDT","XRPUSDT","SOLUSDT","BNBUSDT","ADAUSDT","DOGEUSDT"]

def get_candles(symbol, interval="60", limit=150):
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=15)
        data = r.json()
        candles = data["result"]["list"]
        if not candles or len(candles) < 50:
            return None
        df = pd.DataFrame(candles, columns=["time","open","high","low","close","volume","turnover"])
        df["close"] = pd.to_numeric(df["close"])
        df["high"]  = pd.to_numeric(df["high"])
        df["low"]   = pd.to_numeric(df["low"])
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    except Exception as e:
        return None

def calcular_indicadores(df):
    try:
        if len(df) < 50:
            return None
        df = df.copy()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()
        df = df.dropna()
        if len(df) < 2:
            return None
        return df
    except Exception as e:
        return None

def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro telegram: {e}")

def checar_sinal(symbol, df):
    try:
        rsi   = df["rsi"].iloc[-1]
        stoch = df["stoch_k"].iloc[-1]
        preco = df["close"].iloc[-1]
        agora = datetime.now().strftime("%H:%M")
        chave = f"{symbol}_{datetime.now().strftime('%Y%m%d%H')}"

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
    except Exception as e:
        print(f"Erro checar_sinal {symbol}: {e}")

def main():
    print("Bot iniciado!")
    enviar_telegram("✅ <b>Bot de Alertas iniciado!</b>\nMonitorando Top 100 cripto no 1H...\nRSI 14 | Stoch 14/3/3")

    while True:
        try:
            symbols = get_top100_symbols()
            print(f"Verificando {len(symbols)} moedas...")

            for symbol in symbols:
                df = get_candles(symbol)
                if df is None:
                    continue
                df = calcular_indicadores(df)
                if df is None:
                    continue
                checar_sinal(symbol, df)
                time.sleep(0.5)

            print(f"Checagem concluida. Proxima em 15 minutos.")
            time.sleep(INTERVALO_CHECAGEM)

        except Exception as e:
            print(f"Erro main: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
