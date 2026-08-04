"""只读访问 dbt 生成的 DuckDB。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


DEFAULT_DATABASE = Path("data/processed/olist.duckdb")


def require_database(path: Path = DEFAULT_DATABASE) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"DuckDB 不存在：{path}。请先准备数据并运行 make dbt-build。")
    return path


def read_table(table: str, path: Path = DEFAULT_DATABASE) -> pd.DataFrame:
    """读取允许字符组成的表名，避免把任意 SQL 作为表名执行。"""

    if not table.replace("_", "").replace(".", "").isalnum():
        raise ValueError("表名只能包含字母、数字、下划线和点")
    database = require_database(path)
    with duckdb.connect(str(database), read_only=True) as connection:
        return connection.execute(f"select * from {table}").fetchdf()
