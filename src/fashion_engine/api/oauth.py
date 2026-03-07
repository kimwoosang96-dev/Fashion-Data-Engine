"""OAuth2 Authorization Code flow — 단일 사용자 개인 도구용.

Custom GPT Actions / OpenClaw 등 외부 에이전트가 /feed/ingest를 호출할 때
Bearer 토큰 인증을 받기 위한 최소 OAuth2 서버.

흐름:
  1. 에이전트 → GET /oauth/authorize?client_id=...&redirect_uri=...&state=...
  2. 사용자(본인)가 HTML 폼에서 ADMIN_BEARER_TOKEN 입력 후 승인
  3. 서버 → redirect_uri?code=<code>&state=<state>
  4. 에이전트 → POST /oauth/token (code + client_secret)
  5. 서버 → {"access_token": ..., "token_type": "bearer"}
  6. 에이전트가 이후 모든 요청에 Authorization: Bearer <token> 사용
"""
from __future__ import annotations

import secrets
import time
from html import escape

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from fashion_engine.config import settings

router = APIRouter(prefix="/oauth", tags=["oauth"])

# 인메모리 코드 저장소 (TTL 5분)
_auth_codes: dict[str, dict] = {}
_CODE_TTL = 300


def _clean_expired() -> None:
    now = time.time()
    for k in [k for k, v in _auth_codes.items() if v["expires_at"] < now]:
        del _auth_codes[k]


@router.get("/authorize", response_class=HTMLResponse)
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str | None = Query(None),
    response_type: str = Query("code"),
):
    """승인 페이지: 관리자 토큰 입력 → auth code 발급."""
    client_id_safe = escape(client_id)
    redirect_uri_safe = escape(redirect_uri)
    state_safe = escape(state or "")
    state_input = f'<input type="hidden" name="state" value="{state_safe}">' if state else ""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Fashion Data Engine — 연결 승인</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 420px;
           margin: 80px auto; padding: 24px; color: #111; }}
    h2 {{ margin-bottom: 8px; }}
    p {{ color: #555; font-size: 14px; }}
    input[type=password] {{ width: 100%; padding: 10px; margin: 12px 0;
                            border: 1px solid #ccc; border-radius: 4px;
                            box-sizing: border-box; font-size: 15px; }}
    button {{ width: 100%; padding: 12px; background: #000; color: #fff;
              border: none; border-radius: 4px; font-size: 15px; cursor: pointer; }}
    button:hover {{ background: #333; }}
    .client {{ font-family: monospace; background: #f4f4f4;
               padding: 4px 8px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h2>Fashion Data Engine</h2>
  <p>앱 <span class="client">{client_id_safe}</span>이 데이터 접근을 요청합니다.</p>
  <p>관리자 토큰을 입력해 승인하세요.</p>
  <form method="post" action="/oauth/approve">
    <input type="hidden" name="client_id" value="{client_id_safe}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri_safe}">
    {state_input}
    <input type="password" name="password" placeholder="관리자 토큰" autofocus required>
    <button type="submit">승인</button>
  </form>
</body>
</html>"""


@router.post("/approve")
async def approve(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    password: str = Form(...),
    state: str | None = Form(None),
):
    """패스워드 검증 후 auth code 발급 → redirect_uri로 리디렉션."""
    expected = (settings.admin_bearer_token or "").strip()
    if not expected or password != expected:
        raise HTTPException(status_code=401, detail="관리자 토큰이 올바르지 않습니다")

    _clean_expired()
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "expires_at": time.time() + _CODE_TTL,
    }

    sep = "&" if "?" in redirect_uri else "?"
    location = f"{redirect_uri}{sep}code={code}"
    if state:
        location += f"&state={state}"
    return RedirectResponse(location, status_code=302)


@router.post("/token")
async def token(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    redirect_uri: str | None = Form(None),
):
    """auth code → access token 교환.

    client_secret은 ADMIN_BEARER_TOKEN과 일치해야 합니다.
    발급되는 access_token도 ADMIN_BEARER_TOKEN 값으로, 만료 없이 유효합니다.
    """
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    _clean_expired()
    entry = _auth_codes.pop(code, None) if code else None
    if not entry:
        raise HTTPException(status_code=400, detail="invalid_grant")

    expected_secret = (settings.admin_bearer_token or "").strip()
    if not expected_secret or client_secret != expected_secret:
        raise HTTPException(status_code=401, detail="invalid_client")

    return JSONResponse({
        "access_token": expected_secret,
        "token_type": "bearer",
        "expires_in": 0,
        "scope": "feed:write",
    })
