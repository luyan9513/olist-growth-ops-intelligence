"""看板数据读取。页面不得直接拼接 SQL。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


DATABASE_PATH = Path(os.getenv("OLIST_DB_PATH", "data/processed/olist.duckdb"))
ARTIFACTS_PATH = Path("artifacts")


def database_ready() -> bool:
    return DATABASE_PATH.is_file()


@st.cache_data(show_spinner=False)
def load_mart(table_name: str) -> pd.DataFrame:
    if not table_name.replace("_", "").isalnum():
        raise ValueError("mart 名称只能包含字母、数字和下划线")
    if not database_ready():
        raise FileNotFoundError(f"数据库不存在：{DATABASE_PATH}")
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        return connection.execute(f"select * from marts.{table_name}").fetchdf()


@st.cache_data(show_spinner=False)
def load_csv_artifact(relative_path: str) -> pd.DataFrame:
    path = ARTIFACTS_PATH / relative_path
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_json_artifact(relative_path: str) -> dict[str, object]:
    path = ARTIFACTS_PATH / relative_path
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def data_as_of(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for column in candidates:
        if column in frame.columns:
            values = pd.to_datetime(frame[column], errors="coerce").dropna()
            if not values.empty:
                return values.max().strftime("%Y-%m-%d")
    return "未知"
