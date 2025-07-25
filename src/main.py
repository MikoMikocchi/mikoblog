from fastapi import FastAPI, Depends, Form, HTTPException, Path, status
from sqlalchemy.orm import Session
import uvicorn

from core.config import settings
import schemas
import crud
from models.post import Post
from database import get_db, init_db
from responses import APIResponse

init_db()

app = FastAPI(title="Mikoblog")


def get_existing_post(db: Session = Depends(get_db), post_id: int = Path(gt=0)) -> Post:
    post = crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.get("/posts", response_model=APIResponse)
async def get_all_posts(db: Session = Depends(get_db)):
    posts = crud.get_all_posts(db)
    if posts is None:
        posts = []
    return APIResponse(
        status="success",
        content=[schemas.PostOut.model_validate(p).model_dump() for p in posts],
    )


@app.get("/posts/{post_id}", response_model=APIResponse)
async def get_post(post: Post = Depends(get_existing_post)):
    return APIResponse(
        status="success", content=schemas.PostOut.model_validate(post).model_dump()
    )


@app.post("/posts", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_post(new_post: schemas.PostBase, db: Session = Depends(get_db)):
    post = crud.create_post(
        db=db,
        title=new_post.title,
        content=new_post.content,
        is_published=new_post.is_published,
    )
    if post:
        return APIResponse(
            status="success",
            content=schemas.PostOut.model_validate(post).model_dump(),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create post"
        )


@app.patch("/posts/{post_id}/title", response_model=APIResponse)
async def update_title(
    title: str = Form(...),
    post: Post = Depends(get_existing_post),
    db: Session = Depends(get_db),
):
    result = crud.update_title_by_id(db=db, post_id=post.id, title=title)
    if result:
        return APIResponse(status="success", content="Title updated")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update title"
        )


@app.patch("/posts/{post_id}/content", response_model=APIResponse)
async def update_content(
    content: str = Form(...),
    post: Post = Depends(get_existing_post),
    db: Session = Depends(get_db),
):
    result = crud.update_content_by_id(db=db, post_id=post.id, content=content)
    if result:
        return APIResponse(status="success", content="Content updated")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update content"
        )


@app.delete("/posts/{post_id}", response_model=APIResponse)
async def delete_post(
    post: Post = Depends(get_existing_post), db: Session = Depends(get_db)
):
    result = crud.delete_post_by_id(db=db, post_id=post.id)
    if result:
        return APIResponse(status="success", content="Post deleted")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete post"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
