import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode

from projects import create_project, get_project_by_name

logger = logging.getLogger("ideas-api.ideas")

CONNECTION_STRING = os.environ.get("IDEAS_TABLE_CONNECTION_STRING", "")
TABLE_NAME = "ideas"
VALID_STATUSES = {"open", "done", "dismissed"}
BOT_WRITABLE_FIELDS = {"bot_status", "bot_pr_url", "bot_error", "bot_blocked_by"}
VALID_BOT_STATUSES = {"queued", "running", "completed", "failed", "needs_info", "blocked"}


def _get_table_client():
    if not CONNECTION_STRING:
        raise RuntimeError("IDEAS_TABLE_CONNECTION_STRING is not configured")
    svc = TableServiceClient.from_connection_string(CONNECTION_STRING)
    svc.create_table_if_not_exists(TABLE_NAME)
    return svc.get_table_client(TABLE_NAME)


def _entity_to_dict(e: dict) -> dict:
    return {
        "id": e.get("RowKey", ""),
        "project": e.get("project") or e.get("feature_name", ""),
        "project_id": e.get("project_id", None),
        "title": e.get("title", ""),
        "body": e.get("body", ""),
        "status": e.get("status", "open"),
        "created_at": e.get("created_at", ""),
        "source": e.get("source", "manual"),
        "bot_status": e.get("bot_status", None),
        "bot_pr_url": e.get("bot_pr_url", None),
        "bot_error": e.get("bot_error", None),
        "bot_blocked_by": e.get("bot_blocked_by", None),
    }


def list_ideas(status: str | None = None) -> list[dict]:
    try:
        client = _get_table_client()
        if status:
            entities = client.query_entities(f"PartitionKey eq 'ideas' and status eq '{status}'")
        else:
            entities = client.query_entities("PartitionKey eq 'ideas'")
        ideas = [_entity_to_dict(e) for e in entities]
        ideas.sort(key=lambda x: x["created_at"], reverse=True)
        return ideas
    except Exception as exc:
        logger.error(f"list_ideas failed: {exc}")
        return []


def create_idea(data: dict) -> dict:
    project = data.get("project", "").strip()
    project_id = data.get("project_id", None)
    title = data.get("title", "").strip()
    if not project or not title:
        raise ValueError("project and title are required")

    # Every idea must resolve to a real, linkable project, regardless of how it was
    # created (UI composer, MCP server, bot subtasks). If the caller didn't already
    # resolve project_id, look one up by name or create it, so the project page
    # always exists.
    if not project_id:
        existing = get_project_by_name(project)
        if existing:
            project_id = existing["id"]
        else:
            try:
                project_id = create_project(project)["id"]
            except ValueError:
                # Lost a race with a concurrent create of the same new project name.
                existing = get_project_by_name(project)
                project_id = existing["id"] if existing else None

    client = _get_table_client()

    entity = {
        "PartitionKey": "ideas",
        "RowKey": str(uuid4()),
        "project": project,
        "project_id": project_id,
        "title": title,
        "body": data.get("body", ""),
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": data.get("source", "manual"),
    }
    client.create_entity(entity)
    return _entity_to_dict(entity)


def update_idea(idea_id: str, updates: dict, machine_write: bool = False) -> dict | None:
    allowed = {"status", "project", "project_id", "title", "body"}
    if machine_write:
        allowed |= BOT_WRITABLE_FIELDS

    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}. Allowed: {', '.join(sorted(allowed))}.")
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
    if "bot_status" in updates and updates["bot_status"] is not None and updates["bot_status"] not in VALID_BOT_STATUSES:
        raise ValueError(f"bot_status must be one of: {', '.join(sorted(VALID_BOT_STATUSES))}")

    try:
        client = _get_table_client()
        entity = client.get_entity(partition_key="ideas", row_key=idea_id)
        for k, v in updates.items():
            if v is None:
                entity.pop(k, None)
            else:
                entity[k] = v
        client.update_entity(entity, mode=UpdateMode.REPLACE)
        return _entity_to_dict(entity)
    except ResourceNotFoundError:
        return None
    except ValueError:
        raise
    except Exception as exc:
        logger.error(f"update_idea failed: {exc}")
        raise


def delete_idea(idea_id: str) -> bool:
    try:
        client = _get_table_client()
        client.delete_entity(partition_key="ideas", row_key=idea_id)
        return True
    except ResourceNotFoundError:
        return False
    except Exception as exc:
        logger.error(f"delete_idea failed: {exc}")
        raise
