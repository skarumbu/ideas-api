import json
import logging
import os
from datetime import datetime

import azure.functions as func
from azure.identity import ManagedIdentityCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
from azure.mgmt.appcontainers.models import (
    JobExecutionTemplate,
    JobExecutionContainer,
    EnvironmentVar,
)

from auth import require_auth
from ideas import list_ideas, create_idea, update_idea, delete_idea
from projects import list_projects, create_project

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger("ideas-api")

IDEAS_WRITE_KEY = os.environ.get("IDEAS_WRITE_KEY", "")
BOT_JOB_SUBSCRIPTION_ID = os.environ.get("BOT_JOB_SUBSCRIPTION_ID", "")
BOT_JOB_RESOURCE_GROUP = os.environ.get("BOT_JOB_RESOURCE_GROUP", "")
BOT_JOB_NAME = os.environ.get("BOT_JOB_NAME", "")
BOT_JOB_IMAGE = os.environ.get("BOT_JOB_IMAGE", "")

def _machine_or_user_auth(req: func.HttpRequest) -> None:
    """Allow EasyAuth (browser) or the machine write key (ideator job)."""
    key = req.headers.get("X-Ideas-Key", "")
    if IDEAS_WRITE_KEY and key == IDEAS_WRITE_KEY:
        return
    require_auth(req)

def _json_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data),
        status_code=status_code,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )

def _unauthorized(message: str = "Unauthorized") -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=401,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )

@app.route(route="ideas/{id}/run-bot", methods=["POST"])
def run_bot(req: func.HttpRequest) -> func.HttpResponse:
    """Authenticated users trigger the bot job for an idea."""
    try:
        require_auth(req)
    except ValueError:
        return _unauthorized()

    idea_id = req.route_params.get("id", "")
    if not idea_id:
        return _json_response({"error": "Idea ID required"}, status_code=400)

    if not all([BOT_JOB_SUBSCRIPTION_ID, BOT_JOB_RESOURCE_GROUP, BOT_JOB_NAME]):
        return _json_response({"error": "Bot job not configured"}, status_code=503)

    try:
        updated = update_idea(idea_id, {"bot_status": "queued"}, machine_write=True)
    except Exception as e:
        logger.error(f"run_bot: failed to set queued: {e}")
        return _json_response({"error": "Failed to queue idea"}, status_code=500)

    if updated is None:
        return _json_response({"error": "Idea not found"}, status_code=404)

    # Triggering bot job execution
    try:
        credential = ManagedIdentityCredential()
        client = ContainerAppsAPIClient(credential, BOT_JOB_SUBSCRIPTION_ID)
        client.jobs.begin_run(
            resource_group_name=BOT_JOB_RESOURCE_GROUP,
            job_name=BOT_JOB_NAME,
            job_execution_template=JobExecutionTemplate(
                containers=[
                    JobExecutionContainer(
                        image=BOT_JOB_IMAGE,
                        env=[
                            EnvironmentVar(name="IDEA_ID", value=idea_id),
                            EnvironmentVar(name="IDEAS_WRITE_KEY", value=IDEAS_WRITE_KEY),
                        ],
                    )
                ]
            ),
        )
        logger.info(f"run_bot: triggered job for idea {idea_id}")
    except Exception as exc:
        error_detail = str(exc)
        logger.error(f"run_bot: Container App Job trigger failed: {error_detail}")
        update_idea(
            idea_id,
            {"bot_status": "failed", "bot_error": error_detail[:400]},
            machine_write=True,
        )
        return _json_response(
            {"error": "Failed to trigger bot job", "detail": error_detail[:400]},
            status_code=500,
        )

    return func.HttpResponse(status_code=202)