"""
weather_pipeline_dag.py
-----------------------
Airflow DAG that runs our European weather pipeline once per hour.

The actual work lives in src/weather_fetcher.py — this file is just the
"scheduling glue" that tells Airflow WHEN and IN WHAT ORDER to run things.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Because we set PYTHONPATH=/opt/airflow/src in docker-compose.yml,
# we can import our module directly.
from weather_fetcher import run_pipeline

# ── Default arguments applied to every task in this DAG ────────────────────────
default_args = {
    "owner": "data-eng",
    "retries": 2,                       # Retry a failed task twice...
    "retry_delay": timedelta(minutes=1),  # ...waiting 1 min between tries
}

# ── DAG definition ─────────────────────────────────────────────────────────────
with DAG(
    dag_id="european_weather_pipeline",
    description="Fetch current weather for European cities and store in PostgreSQL",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),    # Earliest date Airflow will schedule from
    schedule="@hourly",                  # Run once per hour
    catchup=False,                       # Don't backfill missed runs on first start
    tags=["weather", "etl"],
) as dag:

    # A single task that calls our pipeline function.
    fetch_and_store = PythonOperator(
        task_id="fetch_and_store_weather",
        python_callable=run_pipeline,
    )

    # With only one task there are no dependencies to declare yet.
    # In a bigger pipeline you'd write: task_a >> task_b >> task_c
    fetch_and_store
