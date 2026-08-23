"""Z哥点评相关 Pydantic 模型"""

from pydantic import BaseModel


class CommentaryResponse(BaseModel):
    ts_code: str = ""
    trade_date: str = ""
    commentary_text: str = ""
    generated_at: str = ""
    model_used: str = ""
    cached: bool = False
    error: str = ""
