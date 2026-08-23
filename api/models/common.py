"""通用响应模型"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


class StatusResponse(BaseModel):
    status: str
    message: str = ""
