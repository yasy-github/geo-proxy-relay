import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=5.0,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
    yield                          # app runs here
    await app.state.client.aclose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.api_route("/exchange-rate", methods=["GET"])
async def forward(request: Request, _: None = Depends(verify_api_key)):
    """
    Forward any request to a target URL.
    Caller must pass:
      - Header: X-API-Key
    """
    target_url = "https://nbc.gov.kh/english/economic_research/exchange_rate.php"

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

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}