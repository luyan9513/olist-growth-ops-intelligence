PYTHON := .venv/bin/python
DBT := .venv/bin/dbt

.PHONY: check-env manifest dbt-parse dbt-build test train analysis dashboard portfolio-build portfolio-check repo-check ci verify

check-env:
	$(PYTHON) scripts/check_environment.py

manifest:
	$(PYTHON) -m src.ingest --raw-dir data/raw --manifest data/processed/raw_manifest.json

dbt-parse:
	$(DBT) --no-version-check parse --project-dir dbt --profiles-dir dbt

dbt-build:
	$(DBT) --no-version-check build --project-dir dbt --profiles-dir dbt

test:
	$(PYTHON) -m pytest

train:
	$(PYTHON) -m src.train all

analysis:
	$(PYTHON) scripts/export_analysis_snapshot.py

dashboard:
	.venv/bin/streamlit run streamlit_app.py

portfolio-build:
	$(PYTHON) -m scripts.build_portfolio_evidence

portfolio-check: portfolio-build
	$(PYTHON) -m scripts.validate_portfolio
	$(PYTHON) -m pytest tests/test_portfolio.py tests/test_streamlit_pages.py -q

repo-check:
	$(PYTHON) -m scripts.validate_repository

ci: repo-check dbt-parse test

verify: check-env manifest dbt-build train analysis test
