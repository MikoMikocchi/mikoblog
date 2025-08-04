from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..database import Base

DEFAULT_EXCERPT_LENGTH = 200

POST_INDEXES = (
    # Optimize fetching posts by author and publication status
    Index("ix_post_author_published", "author_id", "is_published"),
    # Optimize feeds and timeline queries by published status and recency
    Index(
        "ix_post_published_created",
        "is_published",
        "created_at",
        postgresql_ops={"created_at": "DESC"},
    ),
    # Optimize author timelines by recency
    Index(
        "ix_post_author_created",
        "author_id",
        "created_at",
        postgresql_ops={"created_at": "DESC"},
    ),
    # Enable trigram search on title (pg_trgm required)
    Index(
        "ix_post_title_search",
        "title",
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    ),
)


class Post(Base):
    """SQLAlchemy model representing a blog post.

    Attributes:
        id (int): Unique post identifier.
        title (str): Post title, max 128 characters.
        content (str): Full post content (unbounded text).
        is_published (bool): Publication status; True if visible publicly.
        created_at (datetime): Creation timestamp (UTC).
        updated_at (datetime): Last modification timestamp (UTC).
        author_id (int): ID of the user who authored this post.
        author (User): Relationship to the post author.
    """

    __tablename__ = "posts"
    __table_args__ = POST_INDEXES

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique post identifier",
    )
    title = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Post title with maximum 128 characters",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Full post content",
    )
    is_published = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether the post is published",
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Post creation timestamp",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Last modification timestamp",
    )
    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user who authored this post",
    )
    author = relationship(
        "User",
        back_populates="posts",
        lazy="joined",
        doc="Author of this post",
    )

    def __repr__(self) -> str:
        """Return the formal string representation for debugging."""
        title_value = getattr(self, "title", None)
        if isinstance(title_value, str) and title_value:
            title_repr = (
                title_value[:30] + "..." if len(title_value) > 30 else title_value
            )
        else:
            title_repr = ""
        return f"<Post(id={self.id}, title={title_repr!r}, author_id={self.author_id})>"

    def __str__(self) -> str:
        """Return a user-friendly string describing the post."""
        status = "Published" if getattr(self, "is_published", False) else "Draft"
        author_name = (
            getattr(self.author, "username", "Unknown") if self.author else "Unknown"
        )
        title = getattr(self, "title", "") or ""
        return f"Post '{title}' by {author_name} ({status})"

    @hybrid_property
    def is_draft(self) -> bool:
        """Return True if the post is a draft (not published)."""
        return not getattr(self, "is_published", False)

    def get_excerpt(self, length: int = DEFAULT_EXCERPT_LENGTH) -> str:
        """Return a shortened preview of the post content.

        Args:
            length (int): Maximum length of the excerpt.

        Returns:
            str: Truncated content with ellipsis if necessary.
        """
        content = getattr(self, "content", "") or ""
        if len(content) <= length:
            return content
        return content[:length] + "..."
