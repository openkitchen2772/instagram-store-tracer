import logging
from typing import Any
from uuid import uuid4

from dtos.bookmarks import BookmarksDTO
from dtos.store import StoreDTO
from models.bookmarks import Bookmarks
from models.collections import CollectionName
from models.store import Store
from pymongo.errors import PyMongoError
from services.database import get_mongo_db


def _to_store_dto(store: Store) -> StoreDTO:
    try:
        latitude = float(store.latitude)
    except (TypeError, ValueError):
        latitude = 0.0

    try:
        longitude = float(store.longitude)
    except (TypeError, ValueError):
        longitude = 0.0

    return StoreDTO(
        id=store.id,
        name=store.full_name or store.id,
        imageUrl=store.hd_profile_pic_url,
        latitude=latitude,
        longitude=longitude,
    )


def create_bookmarks(
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

        bookmarks = Bookmarks(**raw_bookmarks)
        stores_by_id: dict[str, Store] = {}
        if bookmarks.store_ids:
            cursor = stores_collection.find({"id": {"$in": bookmarks.store_ids}}, {"_id": 0})
            for record in cursor:
                store = Store(**dict(record))
                stores_by_id[store.id] = store

        ordered_stores = [stores_by_id[store_id] for store_id in bookmarks.store_ids if store_id in stores_by_id]
        store_dtos = [_to_store_dto(store) for store in ordered_stores]
        return BookmarksDTO(uuid=bookmarks.uuid, stores=store_dtos), None
    except PyMongoError as error:
        logger.error("Bookmarks lookup failed for uuid=%s: %s", normalized_uuid, str(error))
        return None, "Database operation failed while retrieving bookmarks."
