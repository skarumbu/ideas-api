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


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json_response({"status": "ok"})


@app.route(route="projects", methods=["GET"])
def get_projects(req: func.HttpRequest) -> func.HttpResponse:
    try:
        require_auth(req)
    except ValueError:
        return _unauthorized()

    projects = list_projects()
    return _json_response({"projects": projects})


@app.route(route="projects", methods=["POST"])
def post_project(req: func.HttpRequest) -> func.HttpResponse:
    try:
        require_auth(req)
    except ValueError:
        return _unauthorized()

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    try:
        project = create_project(body.get("name", ""))
    except ValueError as e:
        status = 409 if str(e) == "duplicate" else 400
        msg = "A project with this name already exists" if str(e) == "duplicate" else str(e)
        return _json_response({"error": msg}, status_code=status)
    except Exception as e:
        logger.error(f"post_project failed: {e}")
        return _json_response({"error": "Failed to create project"}, status_code=500)

    return _json_response(project, status_code=201)


@app.route(route="ideas", methods=["GET"])
def get_ideas(req: func.HttpRequest) -> func.HttpResponse:
    try:
        _machine_or_user_auth(req)
    except ValueError:
        return _unauthorized()

    status_filter = req.params.get("status", None)
    if status_filter and status_filter not in ("open", "done", "dismissed"):
        return _json_response({"error": "status must be open, done, or dismissed"}, status_code=400)

    ideas = list_ideas(status=status_filter)
    return _json_response({
        "ideas": ideas,
        "count": len(ideas),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    })


@app.route(route="ideas", methods=["POST"])
def post_idea(req: func.HttpRequest) -> func.HttpResponse:
    try:
        _machine_or_user_auth(req)
    except ValueError:
        return _unauthorized()

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    try:
        idea = create_idea(body)
    except ValueError as e:
        return _json_response({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"post_idea failed: {e}")
        return _json_response({"error": "Failed to create idea"}, status_code=500)

    return _json_response(idea, status_code=201)


@app.route(route="ideas/{id}", methods=["PATCH"])
def patch_idea(req: func.HttpRequest) -> func.HttpResponse:
    try:
        require_auth(req)
    except ValueError:
        return _unauthorized()

    idea_id = req.route_params.get("id", "")
    if not idea_id:
        return _json_response({"error": "Idea ID required"}, status_code=400)

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    try:
        updated = update_idea(idea_id, body)
    except ValueError as e:
        return _json_response({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"patch_idea failed: {e}")
        return _json_response({"error": "Failed to update idea"}, status_code=500)

    if updated is None:
        return _json_response({"error": "Idea not found"}, status_code=404)

    return _json_response(updated)


@app.route(route="ideas/{id}", methods=["DELETE"])
def delete_idea_route(req: func.HttpRequest) -> func.HttpResponse:
    try:
        require_auth(req)
    except ValueError:
        return _unauthorized()

    idea_id = req.route_params.get("id", "")
    if not idea_id:
        return _json_response({"error": "Idea ID required"}, status_code=400)

    try:
        found = delete_idea(idea_id)
    except Exception as e:
        logger.error(f"delete_idea_route failed: {e}")
        return _json_response({"error": "Failed to delete idea"}, status_code=500)

    if not found:
        return _json_response({"error": "Idea not found"}, status_code=404)

    return func.HttpResponse(status_code=204, headers={"Access-Control-Allow-Origin": "*"})


@app.route(route="ideas/{id}/bot", methods=["PATCH"])
def patch_idea_bot(req: func.HttpRequest) -> func.HttpResponse:
    """Machine-key-only: bot writes back bot_status / bot_pr_url / bot_error."""
    key = req.headers.get("X-Ideas-Key", "")
    if not IDEAS_WRITE_KEY or key != IDEAS_WRITE_KEY:
        return _unauthorized("Machine write key required")

    idea_id = req.route_params.get("id", "")
    if not idea_id:
        return _json_response({"error": "Idea ID required"}, status_code=400)

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    try:
        updated = update_idea(idea_id, body, machine_write=True)
    except ValueError as e:
        return _json_response({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"patch_idea_bot failed: {e}")
        return _json_response({"error": "Failed to update idea"}, status_code=500)

    if updated is None:
        return _json_response({"error": "Idea not found"}, status_code=404)

    return _json_response(updated)


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

    try:
        credential = ManagedIdentityCredential()
        client = ContainerAppsAPIClient(credential, BOT_JOB_SUBSCRIPTION_ID)

        # Read the job's existing container config so we preserve all env vars
        # (execution template overrides replace the container entirely, not merge)
        job = client.jobs.get(BOT_JOB_RESOURCE_GROUP, BOT_JOB_NAME)
        base = job.template.containers[0]
        merged_env = [e for e in (base.env or []) if e.name != "IDEA_ID"]
        merged_env.append(EnvironmentVar(name="IDEA_ID", value=idea_id))

        template = JobExecutionTemplate(
            containers=[
                JobExecutionContainer(
                    name=base.name,
                    image=base.image,
                    env=merged_env,
                )
            ]
        )
        client.jobs.begin_start(
            resource_group_name=BOT_JOB_RESOURCE_GROUP,
            job_name=BOT_JOB_NAME,
            template=template,
        )
        logger.info(f"run_bot: triggered job for idea {idea_id}")
    except Exception as e:
        error_detail = f"{type(e).__name__}: {e}"
        logger.error(f"run_bot: Container App Job trigger failed: {error_detail}")
        try:
            update_idea(idea_id, {"bot_status": None, "bot_error": error_detail[:400]}, machine_write=True)
        except Exception:
            pass
        return _json_response({"error": "Failed to trigger bot job", "detail": error_detail[:400]}, status_code=500)

    return _json_response(updated, status_code=202)
