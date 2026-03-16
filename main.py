import os
import httpx

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import Response, HTMLResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from slowapi import Limiter
from slowapi.util import get_remote_address

from utils import verify_api_key, validate_target_url
from cache import CacheManager

cache = CacheManager(int(os.getenv("CACHE_TTL", 14400)))    # 4 hours by default


TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=5.0,
)

limiter = Limiter(key_func=get_remote_address)  # rate limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
    app.state.limiter = limiter
    yield       # app runs here
    await app.state.client.aclose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


@app.get("/exchange-rate")
@limiter.limit("5/minute")
async def exchange_rate(request: Request, _: None = Depends(verify_api_key)):
    """
    Forward any request to a target URL.
    Caller must pass:
      - Header: X-API-Key
    """
    target_url = "https://nbc.gov.kh/english/economic_research/exchange_rate.php"
    validate_target_url(target_url)

    use_cache = request.method == "GET"
    if use_cache:
        cache_key = cache.make_key(target_url, dict(request.query_params))
        cached = cache.get(cache_key)
        if cached:
            return Response(
                content=cached['content'],
                status_code=cached['status_code'],
                headers=cached['headers'],
                media_type=cached['media_type'],
            )

    excluded = {"host", "x-api-key", "x-target-url", "content-length"}
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in excluded
    }

    body = await request.body()

    # Use the shared client from app.state — never instantiate a new one here
    client: httpx.AsyncClient = request.app.state.client

    try:
        proxied = await client.request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            content=body,
            params=dict(request.query_params),
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

    # Strip headers that conflict with the decompressed body
    excluded_response_headers = {
        "content-length",
        "transfer-encoding",
        "content-encoding",  # body is already decoded by httpx
    }
    response_headers = {
        k: v for k, v in proxied.headers.items()
        if k.lower() not in excluded_response_headers
    }

    if use_cache and proxied.status_code == 200:
        cache.set(
            cache_key,
            proxied.content,
            proxied.status_code,
            response_headers,
            proxied.headers.get("content-type"),
        )

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
        <html>
            <head>
                <title>ERP CAMBODIA - Proxy Server</title>
            </head>
            <body>
                <h1>Welcome to our proxy server</h1>
            </body>
        </html>
    """

@app.get("/health")
async def health():
    return {"status": "ok"}

# === CACHE ===

@app.delete('/cache')
async def clear_cache(_: None = Depends(verify_api_key)):
    count = cache.clear()
    return {"cleared": count}

@app.get('/cache/info')
async def cache_info(_: None = Depends(verify_api_key)):
    return {'size': cache.size(), 'ttl': cache.ttl}
