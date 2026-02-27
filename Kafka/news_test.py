import json
import websocket
import logging
from datetime import datetime
from confluent_kafka import Producer

# ===============================
# CONFIGURATION KAFKA
# ===============================

conf = {
    'bootstrap.servers': 'pkc-921jm.us-east-2.aws.confluent.cloud:9092',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': 'GLLKB5UTLMEPUJHW',
    'sasl.password': 'cfltI+pm4Cwo5YSUgSp5kOmT/LJII/hlASGiIDOENx8iF3+QCsax3TD550sbE79A',
    'client.id': 'binance-producer'
}

producer = Producer(conf)
TOPIC = "trades_topic"

# ===============================
# LOGGING
# ===============================

logging.basicConfig(level=logging.INFO)

# ===============================
# SYMBOLS
# ===============================

SYMBOLS = ["btcusdt", "ethusdt", "bnbusdt", "solusdt", "adausdt"]
stream = "/".join([f"{s}@trade" for s in SYMBOLS])
socket_url = f"wss://stream.binance.com:9443/stream?streams={stream}"

# ===============================
# DELIVERY REPORT
# ===============================

def delivery_report(err, msg):
    if err is not None:
        logging.error(f"Message delivery failed: {err}")
    else:
        logging.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

# ===============================
# ON MESSAGE
# ===============================

def on_message(ws, message):
    try:
        msg = json.loads(message)
        data = msg["data"]

        trade_data = {
            "symbol": data["s"],
            "price": float(data["p"]),
            "quantity": float(data["q"]),
            "trade_id": data["t"],
            "event_time": datetime.utcfromtimestamp(data["T"]/1000).isoformat(),
            "ingestion_time": datetime.utcnow().isoformat()
        }

        producer.produce(
            topic=TOPIC,
            key=trade_data["symbol"],
            value=json.dumps(trade_data),
            callback=delivery_report
        )

        producer.poll(0)

    except Exception as e:
        logging.error(f"Error processing message: {e}")

# ===============================
# CONNECTION EVENTS
# ===============================

def on_open(ws):
    logging.info("Connected to Binance WebSocket and streaming prices...")

def on_error(ws, error):
    logging.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.warning("WebSocket connection closed")

# ===============================
# START WEBSOCKET
# ===============================

ws = websocket.WebSocketApp(
    socket_url,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
)

ws.run_forever()