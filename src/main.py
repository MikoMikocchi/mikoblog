from fastapi import FastAPI, Depends, Form, HTTPException, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn

from core.config import settings
import schemas
import crud
from database import get_db


app = FastAPI(title="Mikoblog")


@app.get("/posts", response_model=list[schemas.PostOut])
async def get_all_posts(db: Session = Depends(get_db)):
    all_posts = crud.get_all_posts(db)
    return all_posts


@app.get("/posts/{post_id}")
async def get_post(post_id: int = Path(gt=0), db: Session = Depends(get_db)):
    post = crud.get_post_by_id(db=db, post_id=post_id)
    return post


@app.post("/posts")
async def create_post(new_post: schemas.PostBase, db: Session = Depends(get_db)):
    created_post = crud.create_post(
        db=db,
        title=new_post.title,
        content=new_post.content,
        is_published=new_post.is_published,
    )

    if created_post:
        return JSONResponse(
            content={
                "status": "success",
                "content": schemas.PostOut.model_validate(created_post).model_dump(),
            },
            status_code=status.HTTP_201_CREATED,
        )
    else:
        raise HTTPException(
            detail={"status": "unsuccess", "content": ""},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@app.put("/posts/{post_id}/title")
async def update_title(
    post_id: int = Path(gt=0), db: Session = Depends(get_db), title: str = Form(...)
):
    post = crud.get_post_by_id(db=db, post_id=post_id)

    if post is None:
        raise HTTPException(
            detail={"status": "not found", "content": ""},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    result = crud.update_title_by_id(db=db, post_id=post_id, title=title)

    if result:
        return JSONResponse(
            content={"status": "success", "content": ""},
            status_code=status.HTTP_200_OK,
        )
    else:
        raise HTTPException(
            detail={"status": "unsuccess", "content": ""},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@app.put("/posts/{post_id}/content")
async def update_content(
    post_id: int = Path(gt=0), db: Session = Depends(get_db), content: str = Form(...)
):
    post = crud.get_post_by_id(db=db, post_id=post_id)

    if post is None:
        raise HTTPException(
            detail={"status": "not found", "content": ""},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    result = crud.update_content_by_id(db=db, post_id=post_id, content=content)

    if result:
        return JSONResponse(
            content={"status": "success", "content": ""},
            status_code=status.HTTP_200_OK,
        )
    else:
        raise HTTPException(
            detail={"status": "unsuccess", "content": ""},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int = Path(gt=0), db: Session = Depends(get_db)):
    post = crud.get_post_by_id(db=db, post_id=post_id)

    if post is None:
        raise HTTPException(
            detail={"status": "not found", "content": ""},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    result = crud.delete_post_by_id(db=db, post_id=post_id)

    if result:
        return JSONResponse(
            content={"status": "success", "content": ""},
            status_code=status.HTTP_200_OK,
        )
    else:
        raise HTTPException(
            detail={"status": "unsuccess", "content": ""},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
