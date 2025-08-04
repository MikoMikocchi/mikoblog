from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..database import Base


JTI_MAX_LENGTH = 36
USER_AGENT_MAX_LENGTH = 255
IP_MAX_LENGTH = 45


class RefreshToken(Base):
    """
    Refresh token entity to support RS256 JWT refresh flow with rotation and revocation.

    Fields:
        id: PK
        user_id: FK to users.id (CASCADE on delete)
        jti: Unique identifier (uuid4 string), unique, not null
        issued_at: UTC timestamp when the refresh token was issued
        expires_at: UTC timestamp when the refresh token expires
        rotated_from_jti: jti of the previous token in rotation chain (nullable initially; becomes not null upon rotation)
        revoked_at: UTC timestamp when token was revoked (nullable if active)
        user_agent: Optional user agent string to aid audits
        ip: Optional client IP
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True, doc="Refresh token primary key")

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user id",
    )

    jti = Column(
        String(JTI_MAX_LENGTH),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique token identifier (uuid4)",
    )

    issued_at = Column(
        DateTime,
        nullable=False,
        index=True,
        default=datetime.utcnow,
        doc="Issued at (UTC)",
    )

    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
        doc="Expiration time (UTC)",
    )

    rotated_from_jti = Column(
        String(JTI_MAX_LENGTH),
        nullable=True,
        index=True,
        doc="JTI of the previous refresh in rotation chain (not null upon rotation)",
    )

    revoked_at = Column(
        DateTime,
        nullable=True,
        index=True,
        doc="Revocation time (UTC), null means active",
    )

    user_agent = Column(
        String(USER_AGENT_MAX_LENGTH),
        nullable=True,
        doc="Optional user agent string",
    )

    ip = Column(
        String(IP_MAX_LENGTH),
        nullable=True,
        doc="Optional client IP address",
    )

    user = relationship(
        "User",
        backref="refresh_tokens",
        lazy="selectin",
        doc="Owner user relationship",
    )

    __table_args__ = (
        UniqueConstraint("jti", name="uq_refresh_token_jti"),
        Index("ix_refresh_user", "user_id"),
        Index("ix_refresh_expires_at", "expires_at"),
        Index("ix_refresh_revoked_at", "revoked_at"),
        Index("ix_refresh_user_active", "user_id", "revoked_at"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, jti={self.jti})>"
