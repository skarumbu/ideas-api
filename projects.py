import json
import logging
import os
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient

logger = logging.getLogger("ideas-api.projects")

CONNECTION_STRING = os.environ.get("IDEAS_TABLE_CONNECTION_STRING", "")
TABLE_NAME = "projects"


def _get_table_client():
    if not CONNECTION_STRING:
        raise RuntimeError("IDEAS_TABLE_CONNECTION_STRING is not configured")
    svc = TableServiceClient.from_connection_string(CONNECTION_STRING)
    svc.create_table_if_not_exists(TABLE_NAME)
    return svc.get_table_client(TABLE_NAME)


def _entity_to_dict(e: dict) -> dict:
    # New schema: single `repo` string.
    # Backward compat: if old `repos` JSON list exists, take the first entry.
    repo = e.get("repo", "")
    if not repo:
        repos_raw = e.get("repos", "[]")
        try:
            old_list = json.loads(repos_raw) if repos_raw else []
            repo = old_list[0] if old_list else ""
        except Exception:
            repo = ""
    return {
        "id": e.get("RowKey", ""),
        "name": e.get("name", ""),
        "repo": repo,
    }


def list_projects() -> list[dict]:
    try:
        client = _get_table_client()
        entities = client.query_entities("PartitionKey eq 'projects'")
        projects = [_entity_to_dict(e) for e in entities]
        projects.sort(key=lambda x: x["name"].lower())
        return projects
    except Exception as exc:
        logger.error(f"list_projects failed: {exc}")
        return []


def create_project(name: str, repo: str = "") -> dict:
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    if len(name) > 60:
        raise ValueError("name must be 60 characters or fewer")

    client = _get_table_client()

    existing = list(client.query_entities(
        f"PartitionKey eq 'projects' and name eq '{name}'"
    ))
    if existing:
        raise ValueError("duplicate")

    entity = {
        "PartitionKey": "projects",
        "RowKey": str(uuid4()),
        "name": name,
        "repo": repo.strip(),
    }
    client.create_entity(entity)
    return _entity_to_dict(entity)


def update_project(project_id: str, repo: str) -> dict | None:
    client = _get_table_client()
    try:
        entity = client.get_entity("projects", project_id)
    except ResourceNotFoundError:
        return None
    entity["repo"] = repo.strip()
    client.update_entity(entity)
    return _entity_to_dict(entity)
