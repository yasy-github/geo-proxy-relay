import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

API_KEY = os.getenv("API_KEY")

ALLOWED_HOSTS = {
    "nbc.gov.kh",
}


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def validate_target_url(url: str):
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Target host not allowed: {host}")
