import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode

logger = logging.getLogger("ideas-api.updates")

CONNECTION_STRING = os.environ.get("IDEAS_TABLE_CONNECTION_STRING", "")
TABLE_NAME = "updates"


def _get_table_client():
    if not CONNECTION_STRING:
        raise RuntimeError("IDEAS_TABLE_CONNECTION_STRING is not configured")
    svc = TableServiceClient.from_connection_string(CONNECTION_STRING)
    return svc.get_table_client(TABLE_NAME)


def _entity_to_dict(e: dict) -> dict:
    return {
        "id": e.get("RowKey", ""),
        "idea_id": e.get("PartitionKey", ""),
        "content": e.get("content", ""),
        "created_at": e.get("created_at", ""),
        "author_email": e.get("author_email", ""),
        "author_name": e.get("author_name", ""),
    }


def list_updates(idea_id: str) -> list[dict]:
    try:
        client = _get_table_client()
        entities = client.query_entities(f"PartitionKey eq '{idea_id}'")
        updates = [_entity_to_dict(e) for e in entities]
        updates.sort(key=lambda x: x["created_at"])
        return updates
    except Exception as exc:
        logger.error(f"list_updates failed: {exc}")
        return []


def create_update(idea_id: str, content: str, author_email: str, author_name: str) -> dict:
    entity = {
        "PartitionKey": idea_id,
        "RowKey": str(uuid4()),
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author_email": author_email,
        "author_name": author_name,
    }
    client = _get_table_client()
    client.create_entity(entity)
    return _entity_to_dict(entity)


def delete_update(idea_id: str, update_id: str) -> bool:
    try:
        client = _get_table_client()
        client.delete_entity(partition_key=idea_id, row_key=update_id)
        return True
    except ResourceNotFoundError:
        return False
    except Exception as exc:
        logger.error(f"delete_update failed: {exc}")
        raise
