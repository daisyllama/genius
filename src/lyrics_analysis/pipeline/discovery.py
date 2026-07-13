"""Discovery and download helpers for regional chart CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Iterable

import pandas as pd
import requests

REGION_PATTERN = re.compile(r"regional-(?P<region>[a-z]+)-weekly-(?P<week>\d{4}-\d{2}-\d{2})\.csv", re.I)


@dataclass(frozen=True)
class DiscoveredChartFile:
    region_code: str
    chart_week: date
    source_url: str
    local_path: Path


def extract_chart_metadata(url: str) -> tuple[str, date]:
    match = REGION_PATTERN.search(url)
    if match is None:
        raise ValueError(f"Unsupported chart file name: {url}")
    return match.group("region").lower(), pd.to_datetime(match.group("week")).date()


def download_csv(url: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", 1)[-1]
    target_path = target_dir / filename
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    target_path.write_bytes(response.content)
    return target_path


def discover_new_files(source_urls: Iterable[str], target_dir: Path) -> list[DiscoveredChartFile]:
    discovered: list[DiscoveredChartFile] = []
    for url in source_urls:
        region_code, chart_week = extract_chart_metadata(url)
        local_path = download_csv(url, target_dir)
        discovered.append(
            DiscoveredChartFile(
                region_code=region_code,
                chart_week=chart_week,
                source_url=url,
                local_path=local_path,
            )
        )
    return discovered
