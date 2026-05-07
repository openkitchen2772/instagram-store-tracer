import os
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

MONGO_DB_CONNECTION_STRING_ENV = "MONGO_DB_CONNECTION_STRING"
MONGO_DB_NAME_ENV = "MONGO_DB_NAME"
DEFAULT_MONGO_DB_NAME = "Staging"

_mongo_client: MongoClient[Any] | None = None
_mongo_db: Database[Any] | None = None
_mongo_lock = Lock()


def get_mongo_db() -> Database[Any]:
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    with _mongo_lock:
        if _mongo_db is not None:
            return _mongo_db

        mongo_connection_string = os.getenv(MONGO_DB_CONNECTION_STRING_ENV)
        if not mongo_connection_string:
            raise ValueError(
                "MongoDB connection string is missing! Please set MONGO_DB_CONNECTION_STRING in .env or environment variables."
            )

        mongo_database_name = os.getenv(MONGO_DB_NAME_ENV, DEFAULT_MONGO_DB_NAME)
        _mongo_client = MongoClient(mongo_connection_string, serverSelectionTimeoutMS=5000)
        _mongo_db = _mongo_client[mongo_database_name]
        return _mongo_db


def close_mongo_connection() -> None:
    global _mongo_client, _mongo_db
    with _mongo_lock:
        if _mongo_client is not None:
            _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
