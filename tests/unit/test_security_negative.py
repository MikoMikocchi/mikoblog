import os

from httpx import AsyncClient
import jwt as pyjwt
import pytest

from src.core.jwt_keys import load_keypair


@pytest.fixture(autouse=True, scope="module")
def _env_keys():
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "tests/keys/jwt_private.pem")
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "tests/keys/jwt_public.pem")
    os.environ.setdefault("JWT_ACCESS_MINUTES", "1")
    load_keypair()
    yield


@pytest.mark.unit
@pytest.mark.anyio
async def test_bearer_with_none_alg_token_is_rejected(client: AsyncClient):
    # alg=none payload -> PyJWT encodes without signature when algorithm=None
    payload = {"sub": "1", "typ": "access"}
    forged = pyjwt.encode(payload, key=None, algorithm=None)  # type: ignore[arg-type]
    r = await client.get("/api/v1/posts", headers={"Authorization": f"Bearer {forged}"})
    # Our dependency requires valid RS256 signature -> 401
    assert r.status_code == 401


@pytest.mark.unit
@pytest.mark.anyio
async def test_bearer_with_wrong_algorithm_hs256_is_rejected(client: AsyncClient):
    forged = pyjwt.encode({"sub": "1", "typ": "access"}, "hs-secret", algorithm="HS256")
    r = await client.get("/api/v1/posts", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


@pytest.mark.unit
@pytest.mark.anyio
async def test_bearer_with_random_garbage_token_is_rejected(client: AsyncClient):
    r = await client.get("/api/v1/posts", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


@pytest.mark.unit
@pytest.mark.anyio
async def test_bearer_without_typ_claim_is_rejected(client: AsyncClient):
    private, _ = load_keypair()
    token = pyjwt.encode({"sub": "1"}, private, algorithm="RS256")
    r = await client.get("/api/v1/posts", headers={"Authorization": f"Bearer {token}"})
    # validate_typ must fail -> 401
    assert r.status_code == 401


@pytest.mark.unit
@pytest.mark.anyio
async def test_bearer_without_sub_claim_is_rejected(client: AsyncClient):
    private, _ = load_keypair()
    token = pyjwt.encode({"typ": "access"}, private, algorithm="RS256")
    r = await client.get("/api/v1/posts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
