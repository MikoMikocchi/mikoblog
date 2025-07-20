from fastapi import FastAPI
import uvicorn

from core.config import settings


app = FastAPI(title="Mikoblog")


@app.get("/posts")
async def get_all_posts():
    return []


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
