import os
import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import Response
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

API_KEY = os.getenv("API_KEY")
TIMEOUT = 30.0


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.api_route("/forward", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def forward(request: Request, _: None = Depends(verify_api_key)):
    """
    Forward any request to a target URL.
    Caller must pass:
      - Header: X-API-Key
      - Header: X-Target-URL  (the actual Cambodian endpoint to hit)
    """
    target_url = request.headers.get("X-Target-URL")
    if not target_url:
        raise HTTPException(status_code=400, detail="Missing X-Target-URL header")

    # Forward original headers, strip hop-by-hop and our custom ones
    excluded = {"host", "x-api-key", "x-target-url", "content-length"}
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in excluded
    }

    body = await request.body()

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            proxied = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body,
                params=dict(request.query_params),
                follow_redirects=True,
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=dict(proxied.headers),
        media_type=proxied.headers.get("content-type"),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
