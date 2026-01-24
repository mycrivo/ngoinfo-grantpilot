import logging
import os
import sys
from functools import lru_cache
from typing import Iterable
from urllib.parse import urlparse

from pydantic import ValidationError
from pydantic_settings import BaseSettings

from app.core.logging import configure_logging


class Settings(BaseSettings):
    APP_ENV: str
    APP_NAME: str
    APP_BASE_URL: str
    CORS_ALLOWED_ORIGINS: str
    LOG_LEVEL: str

    DATABASE_URL: str

    AUTH_JWT_SIGNING_KEY: str
    AUTH_ACCESS_TOKEN_TTL_MIN: int
    AUTH_REFRESH_TOKEN_TTL_DAYS: int
    AUTH_MAGIC_LINK_TTL_MIN: int
    AUTH_ALLOWED_REDIRECT_URLS: str
    AUTH_RATE_LIMIT_ENABLED: bool

    GOOGLE_OAUTH_CLIENT_ID: str
    GOOGLE_OAUTH_CLIENT_SECRET: str
    GOOGLE_OAUTH_REDIRECT_URI: str
    GOOGLE_OAUTH_SCOPES: str | None = None

    EMAIL_PROVIDER: str
    EMAIL_FROM_NAME: str
    EMAIL_FROM_ADDRESS: str
    EMAIL_API_KEY: str

    OPENAI_API_KEY: str
    PROMPT_VERSION: str

    STRIPE_MODE: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_CHECKOUT_SUCCESS_URL: str
    STRIPE_CHECKOUT_CANCEL_URL: str
    STRIPE_PRICE_ID_GROWTH: str
    STRIPE_PRICE_ID_IMPACT: str

    TEST_MODE: bool = False
    TEST_MODE_SECRET: str | None = None


_VALID_APP_ENVS = {"dev", "staging", "prod"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_STRIPE_MODES = {"test", "live"}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _log_errors(errors: Iterable[str]) -> None:
    logger = logging.getLogger("config")
    for error in errors:
        logger.error(error)


def validate_config() -> Settings:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in _VALID_LOG_LEVELS:
        log_level = "INFO"
    configure_logging(log_level)

    try:
        settings = Settings()
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            field = ".".join(str(part) for part in err.get("loc", []))
            message = err.get("msg", "invalid value")
            errors.append(f"CONFIG_ERROR {field}: {message}")
        _log_errors(errors)
        sys.exit(1)

    errors = []

    required_strings = {
        "APP_ENV": settings.APP_ENV,
        "APP_NAME": settings.APP_NAME,
        "APP_BASE_URL": settings.APP_BASE_URL,
        "CORS_ALLOWED_ORIGINS": settings.CORS_ALLOWED_ORIGINS,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "DATABASE_URL": settings.DATABASE_URL,
        "AUTH_JWT_SIGNING_KEY": settings.AUTH_JWT_SIGNING_KEY,
        "AUTH_ALLOWED_REDIRECT_URLS": settings.AUTH_ALLOWED_REDIRECT_URLS,
        "GOOGLE_OAUTH_CLIENT_ID": settings.GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "GOOGLE_OAUTH_REDIRECT_URI": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "EMAIL_PROVIDER": settings.EMAIL_PROVIDER,
        "EMAIL_FROM_NAME": settings.EMAIL_FROM_NAME,
        "EMAIL_FROM_ADDRESS": settings.EMAIL_FROM_ADDRESS,
        "EMAIL_API_KEY": settings.EMAIL_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "PROMPT_VERSION": settings.PROMPT_VERSION,
        "STRIPE_MODE": settings.STRIPE_MODE,
        "STRIPE_SECRET_KEY": settings.STRIPE_SECRET_KEY,
        "STRIPE_WEBHOOK_SECRET": settings.STRIPE_WEBHOOK_SECRET,
        "STRIPE_CHECKOUT_SUCCESS_URL": settings.STRIPE_CHECKOUT_SUCCESS_URL,
        "STRIPE_CHECKOUT_CANCEL_URL": settings.STRIPE_CHECKOUT_CANCEL_URL,
        "STRIPE_PRICE_ID_GROWTH": settings.STRIPE_PRICE_ID_GROWTH,
        "STRIPE_PRICE_ID_IMPACT": settings.STRIPE_PRICE_ID_IMPACT,
    }

    for name, value in required_strings.items():
        if not value.strip():
            errors.append(f"CONFIG_ERROR {name}: must not be empty")

    if settings.APP_ENV not in _VALID_APP_ENVS:
        errors.append("CONFIG_ERROR APP_ENV: must be dev, staging, or prod")

    if settings.LOG_LEVEL.upper() not in _VALID_LOG_LEVELS:
        errors.append("CONFIG_ERROR LOG_LEVEL: invalid log level")

    if not _is_valid_url(settings.APP_BASE_URL):
        errors.append("CONFIG_ERROR APP_BASE_URL: must be a valid http(s) URL")

    cors_origins = _split_csv(settings.CORS_ALLOWED_ORIGINS)
    if not cors_origins:
        errors.append("CONFIG_ERROR CORS_ALLOWED_ORIGINS: must include at least one origin")
    elif not all(_is_valid_url(origin) for origin in cors_origins):
        errors.append("CONFIG_ERROR CORS_ALLOWED_ORIGINS: all origins must be valid http(s) URLs")

    redirect_urls = _split_csv(settings.AUTH_ALLOWED_REDIRECT_URLS)
    if not redirect_urls:
        errors.append("CONFIG_ERROR AUTH_ALLOWED_REDIRECT_URLS: must include at least one URL")
    elif not all(_is_valid_url(url) for url in redirect_urls):
        errors.append("CONFIG_ERROR AUTH_ALLOWED_REDIRECT_URLS: all URLs must be valid http(s) URLs")

    if settings.AUTH_ACCESS_TOKEN_TTL_MIN <= 0:
        errors.append("CONFIG_ERROR AUTH_ACCESS_TOKEN_TTL_MIN: must be > 0")
    if settings.AUTH_REFRESH_TOKEN_TTL_DAYS <= 0:
        errors.append("CONFIG_ERROR AUTH_REFRESH_TOKEN_TTL_DAYS: must be > 0")
    if settings.AUTH_MAGIC_LINK_TTL_MIN <= 0:
        errors.append("CONFIG_ERROR AUTH_MAGIC_LINK_TTL_MIN: must be > 0")

    if settings.EMAIL_PROVIDER.lower() != "resend":
        errors.append("CONFIG_ERROR EMAIL_PROVIDER: must be resend for MVP")
    if "@" not in settings.EMAIL_FROM_ADDRESS:
        errors.append("CONFIG_ERROR EMAIL_FROM_ADDRESS: must be a valid email address")

    if not _is_valid_url(settings.GOOGLE_OAUTH_REDIRECT_URI):
        errors.append("CONFIG_ERROR GOOGLE_OAUTH_REDIRECT_URI: must be a valid http(s) URL")

    if settings.STRIPE_MODE.lower() not in _VALID_STRIPE_MODES:
        errors.append("CONFIG_ERROR STRIPE_MODE: must be test or live")
    if not settings.STRIPE_SECRET_KEY.startswith("sk_"):
        errors.append("CONFIG_ERROR STRIPE_SECRET_KEY: must start with sk_")
    if not settings.STRIPE_WEBHOOK_SECRET.startswith("whsec_"):
        errors.append("CONFIG_ERROR STRIPE_WEBHOOK_SECRET: must start with whsec_")
    if not _is_valid_url(settings.STRIPE_CHECKOUT_SUCCESS_URL):
        errors.append("CONFIG_ERROR STRIPE_CHECKOUT_SUCCESS_URL: must be a valid http(s) URL")
    if not _is_valid_url(settings.STRIPE_CHECKOUT_CANCEL_URL):
        errors.append("CONFIG_ERROR STRIPE_CHECKOUT_CANCEL_URL: must be a valid http(s) URL")

    if errors:
        _log_errors(errors)
        sys.exit(1)

    if settings.TEST_MODE:
        if not settings.TEST_MODE_SECRET or len(settings.TEST_MODE_SECRET.strip()) < 32:
            _log_errors(
                ["CONFIG_ERROR TEST_MODE_SECRET: must be set and at least 32 chars when TEST_MODE=true"]
            )
            sys.exit(1)

    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
