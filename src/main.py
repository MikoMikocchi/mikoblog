from fastapi import FastAPI
import uvicorn

from core.config import settings
from db.database import init_db
from api.post_controller import posts_router

init_db()

app = FastAPI()
app.include_router(posts_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
