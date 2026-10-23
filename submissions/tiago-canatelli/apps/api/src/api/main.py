"""API HTTP: dados do painel, prompts/perfis editáveis, assistente e MCP em /mcp.

Rodar: uv run uvicorn api.main:app --reload
"""

import hmac
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api import assistant, db
from api.mcp_server import mcp

api = FastAPI(title="RavenStack Churn API", version="0.1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in db.settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_access(code: str | None) -> None:
    expected = db.settings.access_code
    if expected is None:
        return
    if code is None or not hmac.compare_digest(code, expected.get_secret_value()):
        raise HTTPException(status_code=401, detail="código de acesso inválido")


@api.get("/health")
def health() -> dict[str, Any]:
    row = db.rows("select as_of_date from api.kpi_overview")
    return {
        "status": "ok",
        "as_of_date": str(row[0]["as_of_date"]) if row else None,
        "assistant": db.settings.anthropic_api_key is not None,
        "model": db.settings.claude_model,
    }


@api.get("/data/{view}")
def data(
    view: str, account_id: str | None = None, run_id: str | None = None, limit: int = 2000
) -> list[dict[str, Any]]:
    where = {k: v for k, v in {"account_id": account_id, "run_id": run_id}.items() if v}
    try:
        return db.read_view(view, where, min(limit, 5000))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"view desconhecida: {view}") from exc


class TextUpdate(BaseModel):
    text: str


@api.put("/prompts/{slug}")
def update_prompt(
    slug: str, body: TextUpdate, x_access_code: str | None = Header(None)
) -> dict[str, str]:
    _check_access(x_access_code)
    db.execute(
        "update app.prompt_templates set body = %s, version = version + 1, updated_at = now() where slug = %s",
        (body.text, slug),
    )
    return {"status": "salvo"}


@api.post("/prompts/{slug}/restore")
def restore_prompt(slug: str, x_access_code: str | None = Header(None)) -> dict[str, str]:
    _check_access(x_access_code)
    db.execute(
        "update app.prompt_templates set body = default_body, version = version + 1, updated_at = now() "
        "where slug = %s",
        (slug,),
    )
    return {"status": "restaurado"}


@api.put("/profiles/{slug}")
def update_profile(
    slug: str, body: TextUpdate, x_access_code: str | None = Header(None)
) -> dict[str, str]:
    _check_access(x_access_code)
    db.execute(
        "update app.analysis_profiles set instructions = %s, version = version + 1, updated_at = now() "
        "where slug = %s",
        (body.text, slug),
    )
    return {"status": "salvo"}


@api.post("/profiles/{slug}/restore")
def restore_profile(slug: str, x_access_code: str | None = Header(None)) -> dict[str, str]:
    _check_access(x_access_code)
    db.execute(
        "update app.analysis_profiles set instructions = default_instructions, version = version + 1, "
        "updated_at = now() where slug = %s",
        (slug,),
    )
    return {"status": "restaurado"}


class Question(BaseModel):
    question: str
    profile_slug: str | None = None
    prompt_slug: str | None = None


@api.post("/assistant")
def ask(q: Question, x_access_code: str | None = Header(None)) -> dict[str, Any]:
    _check_access(x_access_code)
    if len(q.question) > 4000:
        raise HTTPException(status_code=400, detail="pergunta longa demais")
    try:
        return assistant.ask(q.question, q.profile_slug, q.prompt_slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# MCP (streamable HTTP) como app externo; a API FastAPI fica montada na raiz.
app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


class MCPAuth(BaseHTTPMiddleware):
    """Exige `Authorization: Bearer <MCP_TOKEN>` nas rotas /mcp (quando o token está configurado)."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        token = db.settings.mcp_token
        if request.url.path.startswith("/mcp") and token is not None:
            header = request.headers.get("authorization", "")
            if not hmac.compare_digest(header, f"Bearer {token.get_secret_value()}"):
                return JSONResponse({"detail": "token MCP inválido"}, status_code=401)
        response: Response = await call_next(request)
        return response


app.add_middleware(MCPAuth)
app.mount("/", api)
