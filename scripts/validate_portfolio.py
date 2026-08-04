"""校验作品集证据、投递材料、内部链接与演示截图。"""

from __future__ import annotations

import json
import re
import struct
from copy import deepcopy
from pathlib import Path

from src.portfolio import build_portfolio_evidence, validate_portfolio_evidence


ROOT = Path(__file__).resolve().parents[1]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"不是有效 PNG: {path}")
    return struct.unpack(">II", data[16:24])


def main() -> None:
    evidence = json.loads((ROOT / "reports/portfolio_evidence.json").read_text(encoding="utf-8"))
    validate_portfolio_evidence(evidence)
    expected = build_portfolio_evidence(
        json.loads((ROOT / "artifacts/analysis_snapshot.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "artifacts/lead_conversion/metrics.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "artifacts/review_risk/metrics.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "artifacts/demand_forecast/metrics.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "artifacts/demand_forecast/seller_ops_metadata.json").read_text(encoding="utf-8")),
    )
    comparable_evidence, comparable_expected = deepcopy(evidence), deepcopy(expected)
    comparable_evidence.pop("generated_at_utc")
    comparable_expected.pop("generated_at_utc")
    if comparable_evidence != comparable_expected:
        raise ValueError("作品集证据与当前分析/模型/行动产物不一致，请先运行 make portfolio-build")

    bullets = (ROOT / "reports/resume_bullets.md").read_text(encoding="utf-8")
    bullet_count = len(re.findall(r"^\d+\. ", bullets, flags=re.MULTILINE))
    interview = (ROOT / "docs/interview_guide.md").read_text(encoding="utf-8")
    question_count = len(re.findall(r"^\d+\. \*\*", interview, flags=re.MULTILINE))
    if bullet_count != 5:
        raise ValueError(f"简历 bullet 必须恰好 5 条，当前 {bullet_count} 条")
    if question_count != 20:
        raise ValueError(f"面试问题必须恰好 20 个，当前 {question_count} 个")

    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    broken_links = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#")):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).resolve().exists():
                broken_links.append(f"{path.relative_to(ROOT)} -> {target}")
    if broken_links:
        raise ValueError("发现无效内部链接:\n" + "\n".join(broken_links))

    screenshot_dir = ROOT / "docs/assets/portfolio"
    screenshots = [
        screenshot_dir / "01_growth_overview.png",
        screenshot_dir / "02_seller_ops_actions.png",
        screenshot_dir / "03_experiment_design.png",
        screenshot_dir / "04_data_quality.png",
    ]
    sizes = {}
    for path in screenshots:
        width, height = png_size(path)
        if width < 1200 or height < 700:
            raise ValueError(f"截图尺寸不足: {path} = {width}x{height}")
        sizes[path.name] = f"{width}x{height}"

    print(json.dumps({
        "status": "ok", "schema_version": evidence["schema_version"],
        "resume_bullets": bullet_count, "interview_questions": question_count,
        "screenshots": sizes, "broken_links": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
