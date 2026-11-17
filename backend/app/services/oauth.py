"""Google / Naver / Kakao OAuth 2.0 Authorization Code 흐름."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from ..config import settings


@dataclass(frozen=True)
class Provider:
    name: str
    authorize_url: str
    token_url: str
    profile_url: str
    scope: str


PROVIDERS = {
    "google": Provider(
        "google",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://openidconnect.googleapis.com/v1/userinfo",
        "openid email profile",
    ),
    "naver": Provider(
        "naver",
        "https://nid.naver.com/oauth2.0/authorize",
        "https://nid.naver.com/oauth2.0/token",
        "https://openapi.naver.com/v1/nid/me",
        "",
    ),
    "kakao": Provider(
        "kakao",
        "https://kauth.kakao.com/oauth/authorize",
        "https://kauth.kakao.com/oauth/token",
        "https://kapi.kakao.com/v2/user/me",
        "profile_nickname account_email",
    ),
}


class OAuthError(RuntimeError):
    pass


@dataclass
class OAuthProfile:
    provider_id: str
    email: str
    name: str


def credentials(provider: str) -> tuple[str, str]:
    return settings.oauth.get(provider, ("", ""))


def is_configured(provider: str) -> bool:
    client_id, client_secret = credentials(provider)
    # 카카오는 Client Secret 이 선택 사항
    return bool(client_id and (client_secret or provider == "kakao"))


def redirect_uri(provider: str) -> str:
    return f"{settings.backend_url}/api/auth/oauth/{provider}/callback"


def authorize_url(provider: str, state: str) -> str:
    p = PROVIDERS[provider]
    params = {
        "response_type": "code",
        "client_id": credentials(provider)[0],
        "redirect_uri": redirect_uri(provider),
        "state": state,
    }
    if p.scope:
        params["scope"] = p.scope
    if provider == "google":
        params["prompt"] = "select_account"
    return f"{p.authorize_url}?{urlencode(params)}"


def _exchange_code(provider: str, code: str, state: str) -> str:
    client_id, client_secret = credentials(provider)
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider),
        "code": code,
        "state": state,
    }
    if client_secret:
        data["client_secret"] = client_secret
    response = requests.post(PROVIDERS[provider].token_url, data=data, timeout=10)
    body = response.json() if response.content else {}
    if response.status_code != 200 or "access_token" not in body:
        detail = body.get("error_description") or body.get("error") or response.text[:200]
        raise OAuthError(f"토큰 발급 실패: {detail}")
    return body["access_token"]


def _profile(provider: str, access_token: str) -> OAuthProfile:
    response = requests.get(
        PROVIDERS[provider].profile_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if response.status_code != 200:
        raise OAuthError(f"프로필 조회 실패 ({response.status_code})")
    body = response.json()

    if provider == "google":
        if not body.get("email_verified"):
            raise OAuthError("Google 계정 이메일이 인증되지 않았습니다.")
        return OAuthProfile(body["sub"], body["email"], body.get("name") or body["email"].split("@")[0])

    if provider == "naver":
        info = body.get("response") or {}
        if not info.get("id"):
            raise OAuthError("네이버 프로필 응답이 올바르지 않습니다.")
        email = info.get("email") or f"naver_{info['id']}@oauth.dataquill.local"
        return OAuthProfile(info["id"], email, info.get("name") or info.get("nickname") or "네이버 사용자")

    account = body.get("kakao_account") or {}
    kakao_id = str(body["id"])
    email = account.get("email") if account.get("is_email_verified") else None
    nickname = (account.get("profile") or {}).get("nickname") or "카카오 사용자"
    return OAuthProfile(kakao_id, email or f"kakao_{kakao_id}@oauth.dataquill.local", nickname)


def fetch_profile(provider: str, code: str, state: str) -> OAuthProfile:
    try:
        return _profile(provider, _exchange_code(provider, code, state))
    except requests.RequestException as exc:
        raise OAuthError(f"{provider} 서버와 통신하지 못했습니다.") from exc
