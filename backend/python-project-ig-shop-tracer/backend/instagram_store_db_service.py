import logging
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import PyMongoError


def insert_store_profile_if_absent(
    stores_collection: Collection[Any],
    profile_data: dict[str, Any],
    logger: logging.Logger,
) -> tuple[bool, str | None]:
    profile_id = str(profile_data.get("id", "") or "")
    if profile_id == "":
        return False, "Store profile is missing required id field."

    logger.info("DB operation start: check existing profile for id=%s", profile_id)

    try:
        existing_profile = stores_collection.find_one({"id": profile_id}, {"_id": 1})
        if existing_profile is None:
            logger.info("DB operation: no existing profile found, inserting id=%s", profile_id)
            insert_result = stores_collection.insert_one(profile_data)
            logger.info(
                "DB operation result: insert success for id=%s, inserted_id=%s",
                profile_id,
                insert_result.inserted_id,
            )
        else:
            logger.info("DB operation: profile exists, refreshing document for id=%s", profile_id)
            update_result = stores_collection.update_one(
                {"id": profile_id},
                {"$set": profile_data},
            )
            logger.info(
                "DB operation result: refresh success for id=%s, matched=%s, modified=%s",
                profile_id,
                update_result.matched_count,
                update_result.modified_count,
            )
        return True, None
    except PyMongoError as error:
        logger.error("DB operation failed for id=%s: %s", profile_id, str(error))
        return False, "Database operation failed while saving store profile."
