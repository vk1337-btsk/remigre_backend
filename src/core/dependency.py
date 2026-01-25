import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.config import settings


security = HTTPBasic()


def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username,
        settings.project.docs_username,
    )
    correct_password = secrets.compare_digest(
        credentials.password,
        settings.project.docs_password,
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


async def verify_api_key(x_api_key: str = Header(..., alias="X-Api-Key")):
    if x_api_key != settings.project.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
