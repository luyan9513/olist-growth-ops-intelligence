"""检查运行环境和关键依赖版本，不读取任何密钥。"""

from __future__ import annotations

import importlib.metadata
import platform
import sys


PACKAGES = (
    "dbt-core",
    "dbt-duckdb",
    "duckdb",
    "pandas",
    "pyarrow",
    "scikit-learn",
    "plotly",
    "streamlit",
    "pytest",
)


def main() -> None:
    if sys.version_info < (3, 11):
        raise SystemExit("需要 Python 3.11 或更高版本")
    print(f"Python: {platform.python_version()}")
    for package in PACKAGES:
        print(f"{package}: {importlib.metadata.version(package)}")


if __name__ == "__main__":
    main()
