"""Cross-classifier comparison helpers, extracted from
notebooks/07_compare_classifiers.ipynb.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def is_label_softmax(df: pd.DataFrame, cols: list[str]) -> bool:
    """True if every scored row sums to ~1 — i.e. scores compete across labels."""
    scored_rows = df.loc[df[cols].max(axis=1) > 0, cols]
    return bool(np.isclose(scored_rows.sum(axis=1), 1.0, atol=0.02).all())


def regional_z(
    df: pd.DataFrame,
    cols: list[str],
    labels: list[str],
    titles: pd.DataFrame,
    ref_region: str = "Global",
) -> pd.DataFrame:
    """Mean score per region, z-scored per label against a market-only baseline.

    `titles` must have `spotify_uri` and `region` columns (the 00_titles.csv
    frame in the notebook). `ref_region` is excluded from the mean/std (it's a
    worldwide chart, not a market) and then scored against that baseline,
    matching 06.1/06.2 § 4.
    """
    m = titles.merge(df[["spotify_uri"] + cols], on="spotify_uri", how="inner")
    means = m.groupby("region")[cols].mean()
    baseline = means.drop(index=ref_region) if ref_region in means.index else means
    z = (means - baseline.mean()) / baseline.std(ddof=0)
    z.columns = labels
    return z
