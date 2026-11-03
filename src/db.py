import os  # read environment variables
from pathlib import Path  # file paths

import psycopg  # PostgreSQL driver
from dotenv import load_dotenv  # loads .env into environment variables

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # src/ -> project root
load_dotenv(PROJECT_ROOT / ".env")  # POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB


def get_connection(**kwargs) -> psycopg.Connection:
    """One place to connect to PostgreSQL, used by every script.

    On my PC: localhost:5433 (the defaults).
    Inside Docker (Airflow): POSTGRES_HOST=postgres, POSTGRES_PORT=5432.
    kwargs = extra options, like autocommit=True for the loader.
    """
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),  # getenv(name, default)
        port=int(os.getenv("POSTGRES_PORT", "5433")),  # env values are text -> int
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        **kwargs,
    )