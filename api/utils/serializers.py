"""dataclass → dict 序列化工具"""

from dataclasses import fields, asdict
from enum import Enum
from typing import Any


def safe_serialize(obj: Any) -> dict:
    """将 dataclass 安全序列化为 dict，处理 Enum、None、嵌套 dataclass"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for f in fields(obj):
            val = getattr(obj, f.name)
            result[f.name] = _serialize_value(val)
        return result
    return {"value": str(obj)}


def _serialize_value(val: Any) -> Any:
    """递归序列化值"""
    if val is None:
        return None
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_serialize_value(item) for item in val]
    if hasattr(val, "__dataclass_fields__"):
        return safe_serialize(val)
    return str(val)


def dataclass_to_dict(obj: Any) -> dict:
    """简单 dataclass → dict（适用于无嵌套的情况）"""
    if obj is None:
        return {}
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return {}
