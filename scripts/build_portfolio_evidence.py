"""从已落盘分析与模型产物生成统一作品集证据。"""

from __future__ import annotations

import json
from pathlib import Path

from src.portfolio import build_portfolio_artifact, build_portfolio_evidence, render_portfolio_case_study


def read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    evidence = build_portfolio_evidence(
        read_json("artifacts/analysis_snapshot.json"),
        read_json("artifacts/lead_conversion/metrics.json"),
        read_json("artifacts/review_risk/metrics.json"),
        read_json("artifacts/demand_forecast/metrics.json"),
        read_json("artifacts/demand_forecast/seller_ops_metadata.json"),
    )
    outputs = {
        Path("reports/portfolio_evidence.json"): json.dumps(evidence, ensure_ascii=False, indent=2),
        Path("reports/portfolio_case_study.md"): render_portfolio_case_study(evidence),
        Path("reports/portfolio_artifact.json"): json.dumps(build_portfolio_artifact(evidence), ensure_ascii=False, indent=2),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
    print(json.dumps({"status": "ok", "outputs": [str(path) for path in outputs]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
