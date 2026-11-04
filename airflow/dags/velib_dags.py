from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator  # runs a shell command
from airflow.sdk import dag  # the @dag decorator

PROJECT = "/opt/velib"  # our project folder, as seen from inside the container
PY = "/home/airflow/velib_venv/bin/python"  # the pipeline's Python (not Airflow's)
DBT = "/home/airflow/velib_venv/bin/dbt"

# Settings shared by every task: if a task fails, try once more after 1 minute
DEFAULT_ARGS = {"retries": 1, "retry_delay": timedelta(minutes=1)}


@dag(
    dag_id="velib_ingest",
    schedule="*/5 * * * *",  # cron: every 5 minutes
    start_date=datetime(2026, 11, 1),
    catchup=False,  # don't run all the missed 5-minute slots since start_date
    max_active_runs=1,  # never two runs at the same time
    default_args=DEFAULT_ARGS,
    tags=["velib"],
)
def velib_ingest():
    fetch = BashOperator(
        task_id="fetch_snapshot",
        bash_command=f"cd {PROJECT} && {PY} src/fetch_snapshot.py",
    )
    load = BashOperator(
        task_id="load_raw",
        bash_command=f"cd {PROJECT} && {PY} src/load_raw.py",
        trigger_rule="all_done",  # run even if fetch failed: still loads any backlog (like run_fetch.bat)
    )
    check = BashOperator(
        task_id="check_quality",
        bash_command=f"cd {PROJECT} && {PY} src/check_quality.py",  # exit code 1 = task turns red
    )
    fetch >> load >> check  # the order


@dag(
    dag_id="velib_hourly",
    schedule="10 * * * *",  # cron: every hour at minute 10
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["velib"],
)
def velib_hourly():
    weather = BashOperator(
        task_id="fetch_weather",
        bash_command=f"cd {PROJECT} && {PY} src/fetch_weather.py",
    )
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {PROJECT}/velib_dbt && {DBT} build --profiles-dir .",
    )
    train = BashOperator(
        task_id="train_model",
        bash_command=f"cd {PROJECT} && {PY} src/train_model.py",
    )
    weather >> dbt_build >> train


velib_ingest()  # calling the function registers the DAG
velib_hourly()