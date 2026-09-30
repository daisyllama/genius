"""Tests for lyrics_analysis.pipeline.discovery."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import requests

from lyrics_analysis.pipeline.discovery import (
    DiscoveredChartFile,
    discover_new_files,
    download_csv,
    extract_chart_metadata,
)


class TestExtractChartMetadata:
    def test_valid_url(self):
        region, week = extract_chart_metadata(
            "https://example.com/regional-ar-weekly-2026-03-05.csv"
        )
        assert region == "ar"
        assert week == date(2026, 3, 5)

    def test_uppercase_name(self):
        region, _ = extract_chart_metadata(
            "https://example.com/REGIONAL-GLOBAL-WEEKLY-2026-03-05.csv"
        )
        assert region == "global"

    def test_unsupported_name_raises(self):
        with pytest.raises(ValueError):
            extract_chart_metadata("https://example.com/not-a-chart-file.csv")


class FakeResponse:
    def __init__(self, content: bytes, status: int = 200):
        self.content = content
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise requests.HTTPError(f"status {self._status}")


class TestDownloadCsv:
    def test_writes_file_to_target_dir(self, tmp_path: Path, monkeypatch):
        target_dir = tmp_path / "nested" / "downloads"

        def fake_get(url, timeout):
            return FakeResponse(b"rank,uri\n1,x\n")

        monkeypatch.setattr(requests, "get", fake_get)
        result = download_csv("https://example.com/regional-ar-weekly-2026-03-05.csv", target_dir)

        assert result == target_dir / "regional-ar-weekly-2026-03-05.csv"
        assert result.read_bytes() == b"rank,uri\n1,x\n"
        assert target_dir.exists()

    def test_http_error_propagates(self, tmp_path: Path, monkeypatch):
        def fake_get(url, timeout):
            return FakeResponse(b"", status=404)

        monkeypatch.setattr(requests, "get", fake_get)
        with pytest.raises(requests.HTTPError):
            download_csv("https://example.com/regional-ar-weekly-2026-03-05.csv", tmp_path)


class TestDiscoverNewFiles:
    def test_discovers_multiple_urls(self, tmp_path: Path, monkeypatch):
        def fake_get(url, timeout):
            return FakeResponse(b"data")

        monkeypatch.setattr(requests, "get", fake_get)

        urls = [
            "https://example.com/regional-ar-weekly-2026-03-05.csv",
            "https://example.com/regional-jp-weekly-2026-03-05.csv",
        ]
        result = discover_new_files(urls, tmp_path)

        assert len(result) == 2
        assert all(isinstance(r, DiscoveredChartFile) for r in result)
        assert result[0].region_code == "ar"
        assert result[1].region_code == "jp"
        assert result[0].chart_week == date(2026, 3, 5)
        assert result[0].source_url == urls[0]
        assert result[0].local_path.exists()
