from __future__ import annotations

import sys
from pathlib import Path


# 测试阶段直接把 src 加入导入路径，避免要求开发者先执行本地安装。
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

