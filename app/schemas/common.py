from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Resource not found", "error_code": "not_found"}}
    )

    detail: str
    error_code: str
