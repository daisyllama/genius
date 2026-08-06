# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,GoEmotions Runner
# MAGIC %md
# MAGIC # GoEmotions Classifier Runner
# MAGIC
# MAGIC Executes only the GoEmotions classifier using functions from `04_classification`.
# MAGIC
# MAGIC Run this notebook and `04_run_zeroshot` simultaneously to classify with both models in parallel.

# COMMAND ----------

# DBTITLE 1,Import functions
# MAGIC %run ./04_classification

# COMMAND ----------

# DBTITLE 1,Config
RUN = ["goemotions"]

# Load data
analysis_df = pd.read_csv(PROCESSED / "03_lyrics_trans.csv")
if "lyrics_in_en" not in analysis_df.columns:
    raise KeyError("Expected 'lyrics_in_en' column in 03_lyrics_trans.csv")
print(f"Loaded {len(analysis_df)} songs for GoEmotions classification")

# COMMAND ----------

# DBTITLE 1,Run GoEmotions classification
if "goemotions" not in RUN:
    print("Skipped (not in RUN).")
else:
    df_ge = load_checkpoint(goemotions_checkpoint_path, goemotions_emotion_cols)
    if df_ge is None:
        df_ge = analysis_df.copy()
        for col in goemotions_emotion_cols:
            if col not in df_ge.columns:
                df_ge[col] = pd.NA

    if "lyrics_prepared" not in df_ge.columns:
        df_ge["lyrics_prepared"] = df_ge.apply(
            lambda r: prepare_lyrics(r.get("lyrics_in_en", ""), artist=r.get("artist", "")),
            axis=1,
        )

    todo = df_ge[df_ge[goemotions_emotion_cols].isna().any(axis=1)].index.tolist()
    print(f"Songs pending classification: {len(todo)} / {len(df_ge)}")

    if todo:
        goemotions_classifier = load_goemotions_classifier()
        n_saved = 0
        for i, idx in enumerate(tqdm(todo, desc="goemotions", unit="song")):
            scores = classify_song_goemotions(df_ge.at[idx, "lyrics_prepared"], goemotions_classifier)
            for emotion, score in scores.items():
                df_ge.at[idx, f"emotion_{emotion}"] = score

            n_saved += 1
            if n_saved % CHECKPOINT_EVERY == 0:
                save_checkpoint(df_ge, goemotions_checkpoint_path)
                tqdm.write(f"  ✓ Checkpoint saved ({n_saved} songs this run)")

        save_checkpoint(df_ge, goemotions_checkpoint_path)
        print(f"Done. Checkpoint saved to {goemotions_checkpoint_path}")
    else:
        print("No unclassified rows. Using existing scores.")

    df_ge = derive_contract_columns(df_ge, goemotions_emotion_cols)
    df_ge = df_ge.drop(columns=["lyrics_prepared"])
    df_ge.to_csv(goemotions_output_path, index=False)
    print(f"Saved to {goemotions_output_path}")
    display(df_ge.head(3))

# ~29m runtime for a full GoEmotions pass on Databricks Serverless.

# COMMAND ----------

# DBTITLE 1,Regional summary
titles_df = pd.read_csv(PROCESSED / "00_titles.csv")[["spotify_uri", "region"]]

merged = titles_df.merge(df_ge[["spotify_uri"] + goemotions_emotion_cols],
                          on="spotify_uri", how="inner")
goemotions_regional_summary = merged.groupby("region")[goemotions_emotion_cols].mean().round(3)
goemotions_regional_summary.columns = [c.replace("emotion_", "") for c in goemotions_regional_summary.columns]
display(goemotions_regional_summary)
out_path = PROCESSED / "04.2_regional_summary_goemotions.csv"
goemotions_regional_summary.to_csv(out_path, index=False)
print(f"Saved to {out_path}")