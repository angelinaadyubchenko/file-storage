from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_failed"
    detail = "Could not validate credentials"


class InvalidCredentials(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_credentials"
    detail = "Incorrect email or password"


class PermissionDenied(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"
    detail = "You do not have permission to perform this action"


class InvalidGrant(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_grant"
    detail = "This grant type is not allowed for this storage"


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    detail = "Resource not found"


class StorageNotFound(NotFound):
    error_code = "storage_not_found"
    detail = "Storage not found"


class FileNotFound(NotFound):
    error_code = "file_not_found"
    detail = "File not found"


class GrantNotFound(NotFound):
    error_code = "grant_not_found"
    detail = "Grant not found"


class ShareTokenInvalid(NotFound):

    error_code = "share_token_invalid"
    detail = "Share link is invalid or no longer available"


class Conflict(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    detail = "Resource conflict"


class EmailAlreadyRegistered(Conflict):
    error_code = "email_already_registered"
    detail = "A user with this email already exists"


class GrantAlreadyExists(Conflict):
    error_code = "grant_already_exists"
    detail = "This grant already exists"


class FileTooLarge(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "file_too_large"
    detail = "File exceeds the maximum allowed size"


class StorageQuotaExceeded(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "storage_quota_exceeded"
    detail = "Storage quota exceeded"


class InvalidFileType(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    error_code = "invalid_file_type"
    detail = "This file type is not allowed by the storage policy"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
