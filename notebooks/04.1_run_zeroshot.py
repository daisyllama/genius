# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Zero-Shot Runner
# MAGIC %md
# MAGIC # Zero-Shot NLI Classifier Runner
# MAGIC
# MAGIC Executes only the zero-shot classifier using functions from `04_classification`.

# COMMAND ----------

# DBTITLE 1,Import functions
# MAGIC %run ./04_classification

# COMMAND ----------

# DBTITLE 1,Config
RUN = ["zeroshot"]

# Load data
analysis_df = pd.read_csv(PROCESSED / "03_lyrics_trans.csv")
if "lyrics_in_en" not in analysis_df.columns:
    raise KeyError("Expected 'lyrics_in_en' column in 03_lyrics_trans.csv")
print(f"Loaded {len(analysis_df)} songs for zero-shot classification")

# COMMAND ----------

# DBTITLE 1,Run zero-shot classification
if "zeroshot" not in RUN:
    print("Skipped (not in RUN).")
else:
    df_zs = load_checkpoint(zeroshot_checkpoint_path, zeroshot_emotion_cols)
    if df_zs is None:
        df_zs = analysis_df.copy()
        for col in zeroshot_emotion_cols:
            if col not in df_zs.columns:
                df_zs[col] = pd.NA

    if "lyrics_prepared" not in df_zs.columns:
        df_zs["lyrics_prepared"] = df_zs.apply(
            lambda r: prepare_lyrics(r.get("lyrics_in_en", ""), artist=r.get("artist", "")),
            axis=1,
        )

    todo = df_zs[df_zs[zeroshot_emotion_cols].isna().any(axis=1)].index.tolist()
    print(f"Songs pending classification: {len(todo)} / {len(df_zs)}")

    if todo:
        zeroshot_classifier = load_zeroshot_classifier()
        n_saved = 0
        for i, idx in enumerate(tqdm(todo, desc="zeroshot", unit="song")):
            scores = classify_song_zeroshot(df_zs.at[idx, "lyrics_prepared"], zeroshot_classifier)
            for emotion, score in scores.items():
                df_zs.at[idx, f"emotion_{emotion}"] = score

            n_saved += 1
            if n_saved % CHECKPOINT_EVERY == 0:
                save_checkpoint(df_zs, zeroshot_checkpoint_path)
                tqdm.write(f"  ✓ Checkpoint saved ({n_saved} songs this run)")

        save_checkpoint(df_zs, zeroshot_checkpoint_path)
        print(f"Done. Checkpoint saved to {zeroshot_checkpoint_path}")
    else:
        print("No unclassified rows. Using existing scores.")

    df_zs = derive_contract_columns(df_zs, zeroshot_emotion_cols)
    df_zs = df_zs.drop(columns=["lyrics_prepared"])
    df_zs.to_csv(zeroshot_output_path, index=False)
    print(f"Saved to {zeroshot_output_path}")
    display(df_zs.head(3))

    # part one 1h 34mins zeroshot:  27%|██▋       | 299/1105 [1:34:24<4:14:28, 18.94s/song]
    # part two 4h 07mins zeroshot: 100%|██████████| 815/815 [4:07:23<00:00, 18.21s/song]
    # total 5h 41mins

# COMMAND ----------

# DBTITLE 1,Regional summary
titles_df = pd.read_csv(PROCESSED / "00_titles.csv")[["spotify_uri", "region"]]

merged = titles_df.merge(df_zs[["spotify_uri"] + zeroshot_emotion_cols],
                          on="spotify_uri", how="inner")
zeroshot_regional_summary = merged.groupby("region")[zeroshot_emotion_cols].mean().round(3)
zeroshot_regional_summary.columns = [c.replace("emotion_", "") for c in zeroshot_regional_summary.columns]
display(zeroshot_regional_summary)
out_path = PROCESSED / "04.1_regional_summary_zeroshot.csv"
zeroshot_regional_summary.to_csv(out_path, index=False)
print(f"Saved to {out_path}")