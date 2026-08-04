"""校验 Olist 原始文件并生成不含数据内容的可复现清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FILES = (
    "olist_marketing_qualified_leads_dataset.csv",
    "olist_closed_deals_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_customers_dataset.csv",
)

OPTIONAL_FILES = (
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(raw_dir: Path) -> dict[str, object]:
    missing = [name for name in REQUIRED_FILES if not (raw_dir / name).is_file()]
    if missing:
        formatted = "\n- ".join(missing)
        raise FileNotFoundError(f"缺少必需的原始数据文件:\n- {formatted}")

    records = []
    for name in (*REQUIRED_FILES, *OPTIONAL_FILES):
        path = raw_dir / name
        if not path.is_file():
            continue
        records.append(
            {
                "filename": name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "required": name in REQUIRED_FILES,
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_directory": str(raw_dir),
        "files": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/raw_manifest.json"))
    args = parser.parse_args()
    manifest = build_manifest(args.raw_dir)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"原始数据清单已生成: {args.manifest}")


if __name__ == "__main__":
    main()
