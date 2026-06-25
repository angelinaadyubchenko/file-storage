from app.exceptions import AppError
from app.schemas.common import ErrorResponse


def error_responses(*exceptions: type[AppError]) -> dict:
    grouped: dict[int, list[type[AppError]]] = {}
    for exc in exceptions:
        grouped.setdefault(exc.status_code, []).append(exc)

    responses: dict = {}
    for status_code, excs in grouped.items():
        examples = {
            exc.error_code: {
                "summary": exc.error_code,
                "value": {"detail": exc.detail, "error_code": exc.error_code},
            }
            for exc in excs
        }
        responses[status_code] = {
            "model": ErrorResponse,
            "description": ", ".join(exc.error_code for exc in excs),
            "content": {"application/json": {"examples": examples}},
        }
    return responses
