from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.services.auth_service import (
    get_or_create_user_for_google,
    get_or_create_user_for_magic_link,
    normalize_email,
)


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(32)"


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_normalize_email():
    assert normalize_email("  TeSt@Example.org ") == "test@example.org"


def test_google_then_magic_link_links_same_user():
    """AUTH_AND_SSO_STRATEGY: Google then Magic Link, same email → same account; google_sub preserved."""
    db = _db_session()
    google_user, _ = get_or_create_user_for_google(
        db,
        email="Test@Example.org",
        google_sub="sub-1",
        full_name="Test User",
        avatar_url=None,
    )
    magic_user, _ = get_or_create_user_for_magic_link(db, email="  test@example.org ")
    assert magic_user.id == google_user.id
    assert magic_user.google_sub == "sub-1"
    assert magic_user.email == "test@example.org"
    assert google_user.email == "test@example.org"


def test_magic_link_then_google_links_same_user():
    """AUTH_AND_SSO_STRATEGY: Magic Link then Google, same email → same account; google_sub set."""
    db = _db_session()
    magic_user, _ = get_or_create_user_for_magic_link(db, email="User@Example.org")
    google_user, _ = get_or_create_user_for_google(
        db,
        email="user@example.org",
        google_sub="sub-2",
        full_name=None,
        avatar_url=None,
    )
    assert magic_user.id == google_user.id
    assert google_user.google_sub == "sub-2"
    assert google_user.email == "user@example.org"
