"""
公共路径常量

统一管理系统中的数据目录路径，避免各模块硬编码。
所有路径均从 DATA_DIR 环境变量派生，默认值为 "data"。

使用方式::

    from modules.core.paths import DATA_DIR, REGISTRY_DIR, REPORTS_DIR
"""

import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
REGISTRY_DIR = DATA_DIR / "registry"
REPORTS_DIR = DATA_DIR / "reports"
