from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base

USERNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 100
PASSWORD_HASH_MAX_LENGTH = 255

USER_INDEXES = (
    # Optimize login and profile lookups by username
    Index("ix_user_username", "username"),
    # Optimize login and profile lookups by email
    Index("ix_user_email", "email"),
    # Optimize recent user listings by creation time (DESC)
    Index(
        "ix_user_created_at",
        "created_at",
        postgresql_ops={"created_at": "DESC"},
    ),
)


class User(Base):
    """SQLAlchemy model representing an application user.

    Attributes:
        id (int): Unique user identifier.
        username (str): Unique username, max 50 chars.
        email (str): Unique email address, max 100 chars.
        hashed_password (str): Password hash, stored as string.
        created_at (datetime): Creation timestamp (UTC).
        updated_at (datetime): Last modification timestamp (UTC).
        posts (list[Post]): Collection of posts authored by the user.
    """

    __tablename__ = "users"
    __table_args__ = USER_INDEXES

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique user identifier",
    )
    username = Column(
        String(USERNAME_MAX_LENGTH),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username with maximum 50 characters",
    )
    email = Column(
        String(EMAIL_MAX_LENGTH),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique email address with maximum 100 characters",
    )
    hashed_password = Column(
        String(PASSWORD_HASH_MAX_LENGTH),
        nullable=False,
        doc="Hashed user password (algorithm-specific storage)",
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="User creation timestamp",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Last modification timestamp",
    )

    role = Column(
        String(16),
        nullable=False,
        default="user",
        doc="User role: 'user' or 'admin'",
    )

    posts = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
        doc="Posts authored by this user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return the formal string representation for debugging."""
        uname = getattr(self, "username", None)
        return f"<User(id={self.id}, username={uname!r})>"

    def __str__(self) -> str:
        """Return a user-friendly string describing the user."""
        uname = getattr(self, "username", "") or ""
        email = getattr(self, "email", "") or ""
        return f"User '{uname}' <{email}>"

    @property
    def display_name(self) -> str:
        """Return a display-friendly name.

        Returns:
            str: Username if present; otherwise the email's local-part.
        """
        uname = getattr(self, "username", None)
        if uname:
            return uname
        email = getattr(self, "email", "") or ""
        return email.split("@", 1)[0] if "@" in email else email
