import json
import logging
import os
from datetime import datetime

import azure.functions as func

from auth import require_auth
from ideas import list_ideas, create_idea, update_idea, delete_idea

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logger = logging.getLogger("ideas-api")

IDEAS_WRITE_KEY = os.environ.get("IDEAS_WRITE_KEY", "")


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
        status = 409 if str(e) == "duplicate" else 400
        msg = "An open idea with this feature_name already exists" if str(e) == "duplicate" else str(e)
        return _json_response({"error": msg}, status_code=status)
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
