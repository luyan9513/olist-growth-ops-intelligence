"""验证公共作品集仓库的结构、体积和敏感文件边界。"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
REQUIRED_FILES = (
    ".github/workflows/ci.yml",
    ".python-version",
    ".streamlit/config.toml",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "RELEASE_CHECKLIST.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/09_release_and_role_packaging.md",
    "docs/10_real_world_rollout_playbook.md",
    "reports/resume_bullets_by_role.md",
)
FORBIDDEN_SUFFIXES = {".duckdb", ".joblib", ".pkl", ".pickle", ".parquet"}
FORBIDDEN_NAMES = {".env", "secrets.toml"}
FORBIDDEN_PREFIXES = ("data/raw/", "data/processed/", "artifacts/")
ALLOWED_BOUNDARY_FILES = {
    "artifacts/.gitkeep",
    "data/processed/.gitkeep",
    "data/raw/.gitkeep",
    "data/raw/README.md",
}
SECRET_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
)


def repository_files() -> list[Path]:
    """返回 Git 将纳入版本控制的已跟踪和未忽略文件。"""

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / value for value in result.stdout.splitlines() if value]


def validate() -> dict[str, object]:
    errors: list[str] = []
    files = repository_files()
    relative_files = {path.relative_to(ROOT).as_posix() for path in files}

    for required in REQUIRED_FILES:
        if required not in relative_files:
            errors.append(f"缺少必需文件：{required}")

    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(FORBIDDEN_PREFIXES) and relative not in ALLOWED_BOUNDARY_FILES:
            errors.append(f"不应进入仓库的数据或模型产物：{relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name in FORBIDDEN_NAMES:
            errors.append(f"不应进入仓库的文件类型：{relative}")
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"文件超过 5 MiB：{relative}")
        if (
            path.resolve() != Path(__file__).resolve()
            and path.suffix.lower() in {".md", ".py", ".yml", ".yaml", ".toml", ".txt"}
        ):
            content = path.read_text(encoding="utf-8", errors="replace")
            for marker in SECRET_MARKERS:
                if marker in content:
                    errors.append(f"疑似私钥内容：{relative}")

    workflow_path = ROOT / ".github/workflows/ci.yml"
    if workflow_path.exists():
        yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    role_path = ROOT / "reports/resume_bullets_by_role.md"
    if role_path.exists():
        role_content = role_path.read_text(encoding="utf-8")
        for role in ("数据分析", "增长分析", "商业分析", "电商运营分析"):
            match = re.search(
                rf"## {role}岗位\n(?P<body>.*?)(?=\n## |\Z)", role_content, re.DOTALL
            )
            count = len(re.findall(r"^\d+\. ", match.group("body"), re.MULTILINE)) if match else 0
            if count != 5:
                errors.append(f"{role}岗位应有 5 条简历 Bullet，实际 {count} 条")

    result: dict[str, object] = {
        "status": "pass" if not errors else "fail",
        "candidate_file_count": len(files),
        "max_file_bytes": MAX_FILE_BYTES,
        "errors": errors,
        "boundaries": [
            "原始数据、处理后数据和模型产物不得进入版本控制",
            "CI 不依赖被忽略的大体积数据或模型文件",
            "本检查只能识别预先定义的文件和密钥特征，不能替代人工发布审核",
        ],
    }
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    print(json.dumps(validate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
