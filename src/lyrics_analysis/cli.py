from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .pipeline import lyric_topic_emotion_pipeline


def _safe_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return name or "dataset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BERTopic + emotion analysis on song lyrics")
    parser.add_argument("--input", required=True, help="Path to CSV with columns: song,region,lyrics")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated result CSV files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_root = Path(args.output_dir)
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{_safe_name(input_path.stem)}_{run_stamp}"
    output_dir = output_root / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    result = lyric_topic_emotion_pipeline(df)

    result["assignments_per_song"].to_csv(output_dir / "topic_assignments_per_song.csv", index=False)
    result["topic_keywords"].to_csv(output_dir / "topic_keywords.csv", index=False)
    result["topic_distribution_by_region"].to_csv(output_dir / "topic_distribution_by_region.csv", index=False)
    result["emotion_by_region"].to_csv(output_dir / "emotion_by_region.csv", index=False)
    result["emotion_by_topic"].to_csv(output_dir / "emotion_by_topic.csv", index=False)

    print("Saved outputs to:")
    print(f"- {output_dir / 'topic_assignments_per_song.csv'}")
    print(f"- {output_dir / 'topic_keywords.csv'}")
    print(f"- {output_dir / 'topic_distribution_by_region.csv'}")
    print(f"- {output_dir / 'emotion_by_region.csv'}")
    print(f"- {output_dir / 'emotion_by_topic.csv'}")


if __name__ == "__main__":
    main()
