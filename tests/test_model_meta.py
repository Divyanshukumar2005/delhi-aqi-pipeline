"""meta.json (library versions next to the saved models), the guard that uses it, and the report helpers
in train_forecast.py. Needs scikit-learn; skipped without it."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
import sklearn  # noqa: E402

from src import ml_forecast as ml, train_forecast as tf  # noqa: E402
from tests.test_ml_forecast import synthetic_series  # noqa: E402


def write_meta(path, version: str | None = None):
    meta = ml.write_meta(path, {6: {"method": "ridge", "rows_used": 10, "feature_names": ["aqi_now"]}})
    if version is not None:
        meta["sklearn_version"] = version
        (path / ml.META_NAME).write_text(json.dumps(meta), encoding="utf-8")


# ------------------------------------------------------------------ meta.json and the guard
def test_write_meta_records_versions_date_rows_and_features(tmp_path):
    meta = ml.write_meta(tmp_path, {12: {"method": "ridge", "rows_used": 99, "feature_names": ["a", "b"]}})
    on_disk = json.loads((tmp_path / "meta.json").read_text())
    assert on_disk == meta
    assert on_disk["sklearn_version"] == sklearn.__version__ and on_disk["numpy_version"] == np.__version__
    assert pd.Timestamp(on_disk["training_date"]).year >= 2026
    assert on_disk["models"]["12"] == {"method": "ridge", "rows_used": 99, "feature_names": ["a", "b"]}


def test_guard_accepts_models_trained_with_the_installed_version(tmp_path):
    write_meta(tmp_path)
    ml.check_models_usable(tmp_path)          # does not raise


def test_guard_rejects_another_version_with_the_retrain_message(tmp_path):
    write_meta(tmp_path, version="0.0.1")
    with pytest.raises(ml.ModelVersionError) as exc:
        ml.check_models_usable(tmp_path)
    assert str(exc.value) == "Models were trained with scikit-learn 0.0.1; run python src/train_forecast.py to retrain."


@pytest.mark.parametrize("content", [None, "not json", "{}", "[]"])
def test_guard_rejects_a_missing_or_unreadable_meta_json(tmp_path, content):
    if content is not None:
        (tmp_path / "meta.json").write_text(content, encoding="utf-8")
    with pytest.raises(ml.ModelVersionError, match="train_forecast.py"):
        ml.check_models_usable(tmp_path)


def summary_frame(with_weather: bool) -> pd.DataFrame:
    rows = [(6, "persistence", 15.0), (6, "ridge", 10.0), (6, "random_forest", 12.0), (6, "hist_gb", 12.5)]
    if with_weather:
        rows += [(6, "ridge+weather", 8.0), (6, "random_forest+weather", 13.0), (6, "hist_gb+weather", 12.0)]
    df = pd.DataFrame(rows, columns=["horizon", "method", "mae"])
    df["rmse"] = df["mae"] * 1.3
    df["n"] = 100
    df["skill_vs_persistence"] = 1 - df["mae"] / 15.0
    return df


def test_save_models_writes_meta_with_rows_and_feature_names(tmp_path, monkeypatch):
    monkeypatch.setattr(tf, "MODELS_DIR", tmp_path)
    s = synthetic_series()
    tf.save_models(s, None, summary_frame(False))
    meta = json.loads((tmp_path / "meta.json").read_text())
    X, _ = ml.build_dataset(s, 6)
    assert meta["sklearn_version"] == sklearn.__version__
    assert meta["models"]["6"]["rows_used"] == len(X)
    assert meta["models"]["6"]["feature_names"] == list(X.columns)
    ml.check_models_usable(tmp_path)


def test_print_latest_refuses_models_from_another_version(tmp_path, monkeypatch):
    monkeypatch.setattr(tf, "MODELS_DIR", tmp_path)
    s = synthetic_series()
    tf.save_models(s, None, summary_frame(False))
    write_meta(tmp_path, version="0.0.1")
    with pytest.raises(SystemExit) as exc:
        tf.print_latest(s, None)
    assert "scikit-learn 0.0.1" in str(exc.value)


# --------------------------------------------------------- report wording and the weather comparison
def test_every_results_section_carries_the_backtest_qualifier():
    s = synthetic_series()
    preds = ml.evaluate(s, horizons=(6,), n_folds=2, fold_days=3)
    text = tf.render_markdown(preds, ml.summarize(preds), s, 2, 3)
    assert "on a 6-day back-test (2 rolling 3-day windows)" in text
    # the table is introduced by the qualifier, never left on its own
    assert text.index("Scored on a 6-day back-test") < text.index("| method | MAE | RMSE")


def test_backtest_phrase_matches_the_wording_used_in_the_readme():
    assert tf.backtest_phrase(4, 7) == "on a 28-day back-test (4 rolling 7-day windows)"


def test_mae_table_lists_both_versions_for_every_horizon():
    lines = tf.mae_table_markdown(summary_frame(True))
    assert lines[0] == "| method | 6 h MAE |"
    assert "| ridge | 10.0 |" in lines and "| ridge+weather | 8.0 |" in lines


def test_weather_effect_compares_the_best_model_with_and_without_weather():
    eff = tf.weather_effect(summary_frame(True)).iloc[0]
    assert (eff["best_without"], eff["best_with"]) == ("ridge", "ridge+weather")
    assert eff["change_pct"] == pytest.approx(-20.0)            # 10.0 -> 8.0
    assert tf.weather_effect(summary_frame(False)).empty


def test_results_report_says_when_weather_did_not_help():
    s = synthetic_series()
    preds = ml.evaluate(s, horizons=(6,), n_folds=2, fold_days=3)
    summary = summary_frame(True)
    summary.loc[summary["method"] == "ridge+weather", "mae"] = 11.0
    summary.loc[summary["method"] == "hist_gb+weather", "mae"] = 12.5
    text = tf.render_markdown(preds, summary, s, 2, 3)
    assert "weather raised the MAE by 10.0%" in text
