import logging
from typing import Any
from uuid import uuid4

from bson import ObjectId
from dtos.bookmarks import BookmarksDTO
from dtos.store import StoreDTO
from models.bookmarks import Bookmarks
from models.collections import CollectionName
from models.store import Store
from pymongo.errors import PyMongoError
from services.database import get_mongo_db


def create_bookmark(
    bookmarks_uuid: str,
    logger: logging.Logger,
) -> tuple[Bookmarks | None, str | None]:
    normalized_uuid = bookmarks_uuid.strip()
    if normalized_uuid == "":
        return None, "Bookmarks uuid is required."

    try:
        mongo_db = get_mongo_db()
        bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
        existing = bookmarks_collection.find_one({"uuid": normalized_uuid}, {"_id": 0})
        if existing is not None:
            return None, "Bookmarks already exists for this uuid."

        bookmarks = Bookmarks(id=str(uuid4()), uuid=normalized_uuid, store_ids=[])
        bookmarks_collection.insert_one(bookmarks.model_dump())
        logger.info("Bookmarks create success for uuid=%s", normalized_uuid)
        return bookmarks, None
    except PyMongoError as error:
        logger.error("Bookmarks create failed for uuid=%s: %s", normalized_uuid, str(error))
        return None, "Database operation failed while creating bookmarks."


def get_bookmarks(
    bookmarks_uuid: str,
    logger: logging.Logger,
) -> tuple[BookmarksDTO | None, str | None]:
    normalized_uuid = bookmarks_uuid.strip()
    if normalized_uuid == "":
        return None, "Bookmarks uuid is required."

    try:
        mongo_db = get_mongo_db()
        bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
        stores_collection = mongo_db[CollectionName.STORE.value]
        raw_bookmarks = bookmarks_collection.find_one({"uuid": normalized_uuid}, {"_id": 0})
        if raw_bookmarks is None:
            return None, "Bookmarks not found."

        # Bookmark records may store `store_ids` as ObjectId values in Mongo.
        # Normalize to strings so the Pydantic model remains JSON-safe.
        raw_store_ids = raw_bookmarks.get("store_ids", [])
        raw_bookmarks["store_ids"] = [str(store_id) for store_id in raw_store_ids]
        bookmarks = Bookmarks(**raw_bookmarks)
        stores_by_bookmark_store_id: dict[str, tuple[Store, str]] = {}
        if bookmarks.store_ids:
            object_ids = []
            logical_store_ids = []
            for store_id in bookmarks.store_ids:
                if ObjectId.is_valid(store_id):
                    object_ids.append(ObjectId(store_id))
                else:
                    logical_store_ids.append(store_id)

            if object_ids:
                cursor = stores_collection.find({"_id": {"$in": object_ids}})
                for record in cursor:
                    store = Store(**dict(record))
                    mongo_object_id = str(record.get("_id", ""))
                    stores_by_bookmark_store_id[mongo_object_id] = (store, mongo_object_id)

            if logical_store_ids:
                cursor = stores_collection.find({"id": {"$in": logical_store_ids}})
                for record in cursor:
                    store = Store(**dict(record))
                    mongo_object_id = str(record.get("_id", ""))
                    stores_by_bookmark_store_id[store.id] = (store, mongo_object_id)

        store_dtos = [
            StoreDTO.from_store(store, object_id=mongo_object_id)
            for store_id in bookmarks.store_ids
            if store_id in stores_by_bookmark_store_id
            for store, mongo_object_id in [stores_by_bookmark_store_id[store_id]]
        ]
        return BookmarksDTO(uuid=bookmarks.uuid, stores=store_dtos), None
    except PyMongoError as error:
        logger.error("Bookmarks lookup failed for uuid=%s: %s", normalized_uuid, str(error))
        return None, "Database operation failed while retrieving bookmarks."


def remove_store_from_bookmarks(
    bookmarks_uuid: str,
    store_id: str,
    logger: logging.Logger,
) -> tuple[bool, str | None]:
    normalized_uuid = bookmarks_uuid.strip()
    normalized_store_id = store_id.strip()
    if normalized_uuid == "":
        return False, "Bookmarks uuid is required."
    if normalized_store_id == "":
        return False, "Store id is required."

    try:
        mongo_db = get_mongo_db()
        bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
        stores_collection = mongo_db[CollectionName.STORE.value]

        store_object_id: ObjectId | None = None
        if ObjectId.is_valid(normalized_store_id):
            store_record = stores_collection.find_one(
                {"_id": ObjectId(normalized_store_id)},
                {"_id": 1},
            )
            if store_record is not None:
                store_object_id = store_record["_id"]

        if store_object_id is None:
            store_record = stores_collection.find_one(
                {"id": normalized_store_id},
                {"_id": 1},
            )
            if store_record is not None:
                store_object_id = store_record["_id"]

        if store_object_id is None:
            logger.warning(
                "Remove store from bookmarks failed: store not found for store_id=%s",
                normalized_store_id,
            )
            return False, "Store not found."

        update_result = bookmarks_collection.update_one(
            {"uuid": normalized_uuid},
            {"$pull": {"store_ids": store_object_id}},
        )
        if update_result.matched_count == 0:
            logger.warning(
                "Remove store from bookmarks failed: bookmarks not found for uuid=%s",
                normalized_uuid,
            )
            return False, "Bookmarks not found."

        if update_result.modified_count == 0:
            logger.info(
                "Remove store from bookmarks skipped: store not in list for uuid=%s store_id=%s",
                normalized_uuid,
                normalized_store_id,
            )
        else:
            logger.info(
                "Remove store from bookmarks success for uuid=%s store_id=%s",
                normalized_uuid,
                normalized_store_id,
            )
        return True, None
    except PyMongoError as error:
        logger.error(
            "Remove store from bookmarks failed for uuid=%s store_id=%s: %s",
            normalized_uuid,
            normalized_store_id,
            str(error),
        )
        return False, "Database operation failed while removing store from bookmarks."
