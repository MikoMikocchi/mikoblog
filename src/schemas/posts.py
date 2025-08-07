from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .users import UserOut

MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 128
MIN_CONTENT_LENGTH = 10
MAX_CONTENT_LENGTH = 50000
MIN_WORDS_IN_CONTENT = 3
WORDS_PER_MINUTE = 200


FORBIDDEN_WORDS: set[str] = {"spam", "advertisement", "click here"}


def clean_whitespace(text: str) -> str:
    return " ".join(text.split())


def contains_forbidden_words(text: str) -> bool:
    return any(word in text.lower() for word in FORBIDDEN_WORDS)


def sanitize_content(content: str) -> str:
    lines = [line.strip() for line in content.split("\n")]
    return "\n".join(line for line in lines if line)


def count_words(text: str) -> int:
    return len(text.split())


class TitleValidationMixin:
    @field_validator("title")
    @classmethod
    def validate_title(cls, title: str) -> str:
        title = clean_whitespace(title)
        if contains_forbidden_words(title):
            raise ValueError("Title contains inappropriate content")
        return title


class ContentValidationMixin:
    @field_validator("content")
    @classmethod
    def validate_content(cls, content: str) -> str:
        content = sanitize_content(content)
        if count_words(content) < MIN_WORDS_IN_CONTENT:
            raise ValueError(f"Content must contain at least {MIN_WORDS_IN_CONTENT} words")
        return content


class PostBase(TitleValidationMixin, ContentValidationMixin, BaseModel):
    title: str = Field(
        ...,
        min_length=MIN_TITLE_LENGTH,
        max_length=MAX_TITLE_LENGTH,
        description="Post title between 5 and 128 characters",
    )
    content: str = Field(
        ...,
        min_length=MIN_CONTENT_LENGTH,
        max_length=MAX_CONTENT_LENGTH,
        description="Post content between 10 and 50,000 characters",
    )
    is_published: bool = Field(default=True, description="Whether the post is published")


class PostCreate(PostBase):
    author_id: int = Field(..., gt=0, description="ID of the post author")


class PostUpdate(TitleValidationMixin, ContentValidationMixin, BaseModel):
    title: str | None = Field(
        None,
        min_length=MIN_TITLE_LENGTH,
        max_length=MAX_TITLE_LENGTH,
        description="New post title",
    )
    content: str | None = Field(
        None,
        min_length=MIN_CONTENT_LENGTH,
        max_length=MAX_CONTENT_LENGTH,
        description="New post content",
    )
    is_published: bool | None = Field(None, description="New publication status")


class PostOut(PostBase):
    id: int = Field(..., description="Post ID")
    author_id: int = Field(..., description="Author ID")
    author: UserOut = Field(..., description="Post author information")
    created_at: datetime = Field(..., description="Post creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    word_count: int | None = Field(None, description="Number of words in content")
    reading_time: int | None = Field(None, description="Estimated reading time in minutes")

    model_config = {"from_attributes": True}

    def model_post_init(self, __context):
        self.word_count = count_words(self.content)
        self.reading_time = max(1, round(self.word_count / WORDS_PER_MINUTE))


class PostSummary(BaseModel):
    id: int = Field(..., description="Post ID")
    title: str = Field(..., description="Post title")
    excerpt: str = Field(..., description="Post excerpt")
    author: UserOut = Field(..., description="Post author information")
    is_published: bool = Field(..., description="Publication status")
    created_at: datetime = Field(..., description="Creation timestamp")
    word_count: int = Field(..., description="Number of words")
    reading_time: int = Field(..., description="Estimated reading time in minutes")

    model_config = {"from_attributes": True}


class PostTitleUpdate(TitleValidationMixin, BaseModel):
    title: str = Field(
        ...,
        min_length=MIN_TITLE_LENGTH,
        max_length=MAX_TITLE_LENGTH,
        description="New post title",
    )


class PostContentUpdate(ContentValidationMixin, BaseModel):
    content: str = Field(
        ...,
        min_length=MIN_CONTENT_LENGTH,
        max_length=MAX_CONTENT_LENGTH,
        description="New post content",
    )


class PostPublishToggle(BaseModel):
    is_published: bool = Field(..., description="New publication status")


class PostStatistics(BaseModel):
    total_posts: int = Field(..., description="Total number of posts")
    published_posts: int = Field(..., description="Number of published posts")
    draft_posts: int = Field(..., description="Number of draft posts")
    author_id: int | None = Field(None, description="Author ID for author-specific stats")
    average_words_per_post: float | None = Field(None, description="Average words per post")
    most_active_author: UserOut | None = Field(None, description="Most active author")


class SortOption(str, Enum):
    newest = "newest"
    oldest = "oldest"
    popular = "popular"


class PostSearchQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=100, description="Search query")
    published_only: bool = Field(default=True, description="Search only published posts")
    author_id: int | None = Field(None, gt=0, description="Filter by author ID")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    sort: SortOption = Field(default=SortOption.newest, description="Sorting option")
