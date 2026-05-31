import os
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from config.settings import settings

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

        mongo_connection_string = settings.MONGO_DB_CONNECTION_STRING
        if not mongo_connection_string:
            raise ValueError(
                "MongoDB connection string is missing! Please set MONGO_DB_CONNECTION_STRING in .env or environment variables."
            )

        _mongo_client = MongoClient(mongo_connection_string, serverSelectionTimeoutMS=5000)
        _mongo_db = _mongo_client[settings.MONGO_DB_NAME]
        return _mongo_db


def close_mongo_connection() -> None:
    global _mongo_client, _mongo_db
    with _mongo_lock:
        if _mongo_client is not None:
            _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
