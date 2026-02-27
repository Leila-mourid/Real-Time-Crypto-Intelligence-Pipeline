# Real-Time Crypto Intelligence Pipeline
**DATA NEXT Consulting — pour INVISTIS**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCES                                   │
│   Binance WS          NewsAPI            FRED API               │
│   (Trades)            (Articles)         (Macro)                │
└──────┬─────────────────────┬──────────────────┬────────────────┘
       │                     │                  │
       ▼                     ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CONFLUENT CLOUD (Kafka)                        │
│                                                                  │
│   trades_topic       news_topic          fred_topic             │
│   (6 partitions)     (3 partitions)      (1 partition)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│            SPARK STRUCTURED STREAMING (Databricks)               │
│                                                                  │
│   • Parse JSON            • Stream-to-Stream Join ±5 min        │
│   • Watermark 5/10 min    • Enrichment FRED (broadcast join)    │
│   • Window 1 min / 5 min  • Volatility Score                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Multi-Sink Fan-Out (foreachBatch)
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    Data Lake          Supabase        alerts_topic
    (Parquet)        (PostgreSQL)      (Confluent)
```

---

## Structure du Repository

```
crypto-pipeline/
│
├── schemas/                              # Exigence 5 — Schémas formalisés
│   ├── trade_schema.json                 # trades_topic
│   ├── news_schema.json                  # news_topic
│   ├── fred_schema.json                  # fred_topic
│   ├── enriched_market_schema.json       # enriched_market_topic
│   └── alert_schema.json                 # alerts_topic
│
├── kafka/                                # Exigence 1 — Topic Design + Producers
│   ├── kafka_utils.py                    # Connexion Confluent, validation, create_topics()
│   ├── producer_binance.py               # Binance WebSocket → trades_topic
│   └── producer_news.py                  # NewsAPI → news_topic
│
├── spark/                                # Exigences 2 + 3 — Streaming + Fan-Out
│   ├── stream_join.py                    # Stream-to-stream join + windowing
│   ├── multi_sink_fanout.py              # foreachBatch → DataLake + Supabase + Kafka
│   ├── enrichment.py                     # Broadcast join FRED (batch → stream)
│   └── notebooks/
│       └── crypto_intel_pipeline.ipynb   # Version Databricks Community Edition
│
├── airflow/                              # Exigence 4 — Batch + Streaming Hybrid
│   └── dags/
│       └── fred_ingestion_dag.py         # DAG quotidien FRED → Data Lake
│
├── supabase/                             # Exigence 3 — Warehouse Layer
│   └── migrations/
│       ├── 001_create_enriched_market_data.sql
│       └── 002_create_alerts.sql
│
├── tests/                                # Exigence 5 — Validation end-to-end
│   ├── test_schema_validation.py         # Tests unitaires schemas
│   └── test_end_to_end.py               # Tests E2E Kafka + Supabase
│
├── .env.example                          # Template variables d'environnement
├── requirements.txt                      # Dépendances Python
└── README.md
```

---

## Exigences Techniques — Implémentation

### Exigence 1 — Kafka Topic Design

4 topics définis dans `kafka/kafka_utils.py` :

| Topic | Partitions | Rétention | Source |
|---|---|---|---|
| `trades_topic` | 6 | 7 jours | Binance WebSocket |
| `news_topic` | 3 | 7 jours | NewsAPI |
| `enriched_market_topic` | 6 | 30 jours | Spark output |
| `alerts_topic` | 3 | 30 jours | Spark alerts |

---

### Exigence 2 — Stream-to-Stream Join (`spark/stream_join.py`)

```python
# Watermark obligatoire sur les deux streams
trades = trades.withWatermark("trade_ts", "5 minutes")
news   = news.withWatermark("news_ts",   "10 minutes")

# Window 1 min tumbling → détection spike >5%
spikes = trades.groupBy("symbol", window("trade_ts", "1 minute"))...

# Join news ±5 min autour du spike
joined = spikes.join(news,
    expr("news_ts BETWEEN window_start - INTERVAL 5 MINUTES"
         "           AND window_end   + INTERVAL 5 MINUTES"),
    how="left"
)
```

---

### Exigence 3 — Multi-Sink Fan-Out (`spark/multi_sink_fanout.py`)

```python
# Un seul job Spark, foreachBatch → 3 sinks simultanés
def process_batch(batch, batch_id):
    sink_data_lake(batch, batch_id)     # → Parquet /tmp ou DBFS
    sink_supabase(batch, batch_id)      # → PostgreSQL JDBC
    sink_alerts_kafka(batch, batch_id)  # → alerts_topic Confluent

stream.writeStream.foreachBatch(process_batch).start()
```

---

### Exigence 4 — Batch + Streaming Hybrid (`airflow/dags/fred_ingestion_dag.py`)

```
Airflow DAG — 06:00 UTC / jour
  fetch_fred_data      → appel API FRED (FEDFUNDS, CPIAUCSL, UNRATE...)
       ↓
  validate_fred_data   → validation JSON Schema
       ↓
  store_to_data_lake   → Parquet /tmp/data-lake/batch/fred/
       ↓
  spark/enrichment.py lira ce Parquet
  et le broadcast-join dans le stream (batch → streaming)
```

---

## Setup & Installation

### 1. Cloner

```bash
git clone https://github.com/Leila-mourid/Real-Time-Crypto-Intelligence-Pipeline
cd Real-Time-Crypto-Intelligence-Pipeline

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Créer les topics Confluent Cloud

```python
from confluent_kafka.admin import AdminClient
from kafka.kafka_utils import create_topics
import os

admin = AdminClient({
    "bootstrap.servers": os.environ["CONFLUENT_BOOTSTRAP_SERVERS"],
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms":   "PLAIN",
    "sasl.username":     os.environ["CONFLUENT_API_KEY"],
    "sasl.password":     os.environ["CONFLUENT_API_SECRET"],
})
create_topics(admin)
```

### 4. Supabase — Exécuter les migrations

Dans Supabase → **SQL Editor**, exécuter dans l'ordre :

```
supabase/migrations/001_create_enriched_market_data.sql
```

### 5. Lancer les producers Kafka

```bash
python kafka/producer_binance.py &   
python kafka/producer_news.py &      
```

### 6. Lancer le pipeline Spark sur Databricks

Importer `spark/notebooks/crypto_intel_pipeline.ipynb` dans Databricks et exécuter les cellules dans l'ordre.

### 7. Lancer Airflow (batch FRED)

```bash
docker-compose up -d
# UI : http://localhost:8080  (admin / admin)
# Activer le DAG : fred_ingestion_daily
```

---

## Variables d'environnement

| Variable | Description | Où la trouver |
|---|---|---|
| `CONFLUENT_BOOTSTRAP_SERVERS` | Adresse du cluster Kafka | Confluent → Cluster Settings |
| `CONFLUENT_API_KEY` | Clé API Confluent | Confluent → API Keys |
| `CONFLUENT_API_SECRET` | Secret API Confluent | Confluent → API Keys |
| `NEWSAPI_KEY` | Clé NewsAPI | newsapi.org → Dashboard |
| `FRED_API_KEY` | Clé FRED API | fredaccount.stlouisfed.org |
| `SUPABASE_HOST` | Host PostgreSQL | Supabase → Settings → Database |
| `SUPABASE_PASSWORD` | Mot de passe DB | Supabase → Settings → Database |
| `SUPABASE_JDBC_URL` | URL JDBC pour Spark | Supabase → Settings → Database |
| `DATA_LAKE_PATH` | Chemin Data Lake | `/tmp/data/crypto-intel` (local) |
| `CHECKPOINT_PATH` | Chemin checkpoints Spark | `/tmp/checkpoints/crypto-intel` (local) |

---

## Schemas des messages Kafka

| Schéma | Topic | Champs obligatoires |
|---|---|---|
| `trade_schema.json` | `trades_topic` | symbol, price, quantity, trade_time |
| `news_schema.json` | `news_topic` | article_id, title, url, published_at |
| `fred_schema.json` | *(batch Airflow)* | series_id, value, observation_date |
| `enriched_market_schema.json` | `enriched_market_topic` | symbol, window_start, is_spike |
| `alert_schema.json` | `alerts_topic` | alert_type, severity, symbol, triggered_at |



*DATA NEXT Consulting — Real-Time Crypto Intelligence Pipeline — INVISTIS 2026*
