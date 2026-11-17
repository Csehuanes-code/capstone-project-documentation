"""Publicación de las claves públicas que verifican los JWT ES256."""

from typing import cast

from fastapi import APIRouter, HTTPException, Request

from auth_service.application.ports import JwkProvider

router = APIRouter(tags=["Auth"])


@router.get("/.well-known/jwks.json")
def jwks(request: Request) -> dict[str, list[dict[str, str]]]:
    provider = request.app.state.jwk_provider
    if provider is None:
        raise HTTPException(status_code=503, detail="Publicación JWKS no está configurada.")
    issuer = cast(JwkProvider, provider)
    return {"keys": [issuer.public_jwk()]}
