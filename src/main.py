from fastapi import FastAPI
import uvicorn

from core.config import settings
from db.database import init_db
from api import posts_router, users_router

init_db()

app = FastAPI()
app.include_router(posts_router)
app.include_router(users_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
