"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler as _default_http_exc_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from src.api.schemas.errors import ErrorDetail, ErrorEnvelope
from src.domain.exceptions import (
    DuplicateActiveRegistrationError,
    EmailAlreadyExistsError,
    EventDateInPastError,
    EventNotFoundError,
    InvalidCredentialsError,
    NoActiveRegistrationError,
    QuotaBelowParticipantsError,
    QuotaFullError,
    RegistrationDeadlinePassedError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="API-X Authentication", version="1.0.0")


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_envelope_handler(
    request: Request, exc: HTTPException
) -> JSONResponse | Response:
    """Pass through our custom error envelopes (dict with 'error' key) directly.

    For all other HTTPExceptions (e.g. FastAPI's built-in 404/405), fall back
    to the default FastAPI handler.
    """
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            headers=dict(exc.headers) if exc.headers else None,
            content=exc.detail,
        )
    return await _default_http_exc_handler(request, exc)


@app.exception_handler(EmailAlreadyExistsError)
async def email_already_exists_handler(
    request: Request, exc: EmailAlreadyExistsError
) -> JSONResponse:
    logger.info("Registration conflict: %s", exc)
    return JSONResponse(
        status_code=409,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="EMAIL_ALREADY_EXISTS",
                message="An account with this email already exists.",
                httpStatus=409,
            )
        ).model_dump(),
    )


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="UNAUTHORIZED",
                message="Could not validate credentials.",
                httpStatus=401,
            )
        ).model_dump(),
    )


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(
    request: Request, exc: UserNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="UNAUTHORIZED",
                message="Could not validate credentials.",
                httpStatus=401,
            )
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = str(first_error.get("msg", "Validation error."))
    return JSONResponse(
        status_code=422,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=msg,
                httpStatus=422,
            )
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Routers — imported here to avoid circular imports
# ---------------------------------------------------------------------------
from src.api.routers import admin, auth  # noqa: E402
from src.api.routers.events import admin_router as events_admin_router  # noqa: E402
from src.api.routers.events import public_router as events_public_router  # noqa: E402
from src.api.routers.registrations import router as registrations_router  # noqa: E402
from src.api.routers.reports import router as reports_router  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(events_admin_router)
app.include_router(events_public_router)
app.include_router(registrations_router)
app.include_router(reports_router)


# ---------------------------------------------------------------------------
# Event management exception handlers (002-event-management)
# ---------------------------------------------------------------------------


@app.exception_handler(EventNotFoundError)
async def event_not_found_handler(
    request: Request, exc: EventNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="EVENT_NOT_FOUND",
                message=str(exc),
                httpStatus=404,
            )
        ).model_dump(),
    )


@app.exception_handler(QuotaBelowParticipantsError)
async def quota_below_participants_handler(
    request: Request, exc: QuotaBelowParticipantsError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="QUOTA_BELOW_PARTICIPANTS",
                message=str(exc),
                httpStatus=409,
            )
        ).model_dump(),
    )


@app.exception_handler(EventDateInPastError)
async def event_date_in_past_handler(
    request: Request, exc: EventDateInPastError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="INVALID_DATE_RANGE",
                message=str(exc),
                httpStatus=422,
            )
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Event registration exception handlers (003-event-registration)
# ---------------------------------------------------------------------------


@app.exception_handler(QuotaFullError)
async def quota_full_handler(request: Request, exc: QuotaFullError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="QUOTA_FULL",
                message=str(exc),
                httpStatus=422,
            )
        ).model_dump(),
    )


@app.exception_handler(DuplicateActiveRegistrationError)
async def duplicate_registration_handler(
    request: Request, exc: DuplicateActiveRegistrationError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="DUPLICATE_REGISTRATION",
                message=str(exc),
                httpStatus=409,
            )
        ).model_dump(),
    )


@app.exception_handler(NoActiveRegistrationError)
async def no_active_registration_handler(
    request: Request, exc: NoActiveRegistrationError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="REGISTRATION_NOT_FOUND",
                message=str(exc),
                httpStatus=404,
            )
        ).model_dump(),
    )


@app.exception_handler(RegistrationDeadlinePassedError)
async def registration_deadline_passed_handler(
    request: Request, exc: RegistrationDeadlinePassedError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorEnvelope(
            error=ErrorDetail(
                code="REGISTRATION_DEADLINE_PASSED",
                message=str(exc),
                httpStatus=422,
            )
        ).model_dump(),
    )
