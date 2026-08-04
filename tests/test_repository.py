from __future__ import annotations

from scripts.validate_repository import validate


def test_repository_is_release_ready_without_large_local_artifacts():
    result = validate()
    assert result["status"] == "pass"
    assert result["candidate_file_count"] > 0
    assert result["errors"] == []
