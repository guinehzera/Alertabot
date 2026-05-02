import requests
import pandas as pd
import ta
import time
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = "8771549016:AAENyF7OFcpIxLdUPZU2gRsV49kXhL0RBko"
TELEGRAM_CHAT_ID = "6532282065"

RSI_SOBREVENDIDO = 30
RSI_SOBRECOMPRADO = 70
STOCH_SOBREVENDIDO = 20
STOCH_SOBRECOMPRADO = 80
INTERVALO_CHECAGEM = 60 * 15

alertas_enviados = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot rodando!")
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
    def log_message(self, format, *args):
        pass

def iniciar_servidor():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

def get_top100_symbols():
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        r = requests.get(url, timeout=15)
        data = r.json()
        usdt = [x for x in data if x["currency_pair"].endswith("_USDT") and float(x.get("quote_volume", 0)) > 1000000]
        usdt.sort(key=lambda x: float(x.get("quote_volume", 0)), reverse=True)
        symbols = [x["currency_pair"].replace("_", "") for x in usdt[:100]]
        print(f"Encontradas {len(symbols)} moedas")
        return symbols
    except Exception as e:
        print(f"Erro get_symbols: {e}")
        return ["BTCUSDT","ETHUSDT","XRPUSDT","SOLUSDT","BNBUSDT","ADAUSDT","DOGEUSDT"]

def get_candles(symbol, interval="4h", limit=150):
    try:
        pair = symbol[:-4] + "_USDT"
        url = f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=15)
        data = r.json()
        if not data or len(data) < 50:
            return None
        df = pd.DataFrame(data, columns=["time","volume","close","high","low","open","base_volume","is_closed"])
        df["close"] = pd.to_numeric(df["close"])
        df["high"]  = pd.to_numeric(df["high"])
        df["low"]   = pd.to_numeric(df["low"])
        return df
    except:
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
    except:
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
                f"⏰ {agora} | Grafico 4H\n"
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
                f"⏰ {agora} | Grafico 4H\n"
                f"👉 Analise o 15min para entrada!"
            )
            enviar_telegram(msg)
            alertas_enviados[chave] = True
            print(f"[SELL] {symbol} RSI:{rsi:.1f} Stoch:{stoch:.1f}")
    except Exception as e:
        print(f"Erro checar_sinal {symbol}: {e}")

def main():
    t = threading.Thread(target=iniciar_servidor)
    t.daemon = True
    t.start()
    print("Servidor HTTP iniciado!")

    enviar_telegram("✅ <b>Bot iniciado!</b>\nMonitorando Top 100 cripto no 4H\nRSI 14 | Stoch 14/3/3")

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
            print("Checagem concluida. Proxima em 15 minutos.")
            time.sleep(INTERVALO_CHECAGEM)
        except Exception as e:
            print(f"Erro main: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()


