"""Train and evaluate the ML AQI forecast, write a results report and save the best model per horizon.

Usage (from the repo root):
    pip install -r requirements-ml.txt
    python src/fetch_weather.py          # optional: adds weather features (data/weather.csv)
    python src/train_forecast.py         # evaluate, write docs/ML_RESULTS.md + docs/ml_forecast.png, save models
    python src/train_forecast.py --predict   # print the latest saved-model forecasts only

Nothing here touches data/aqi.db (it is read, never written).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analysis, config, db, forecast, ml_forecast as ml
from src.fetch_weather import load_weather

DOCS_DIR = config.ROOT_DIR / "docs"
MODELS_DIR = config.DATA_DIR / "models"
ML_NAMES = ("ridge", "random_forest", "hist_gb")


def load_city_series() -> pd.Series:
    return forecast.city_hourly(analysis.prepare(db.load_readings()), fill_limit=0)


def run_evaluation(s: pd.Series, weather: pd.DataFrame | None, folds: int, fold_days: int) -> pd.DataFrame:
    preds = ml.evaluate(s, weather=None, n_folds=folds, fold_days=fold_days)
    if weather is not None and not weather.empty:
        with_wx = ml.evaluate(s, weather=weather, n_folds=folds, fold_days=fold_days, include_baselines=False)
        keep = ["horizon", "fold", "origin"] + [c for c in with_wx.columns if c.endswith("+weather")]
        preds = preds.merge(with_wx[keep], on=["horizon", "fold", "origin"], how="inner")
    return preds


def best_ml_method(summary: pd.DataFrame, horizon: int) -> str:
    rows = summary[(summary["horizon"] == horizon) & summary["method"].str.replace("+weather", "", regex=False).isin(ML_NAMES)]
    return rows.sort_values("mae").iloc[0]["method"]


def backtest_phrase(folds: int, fold_days: int) -> str:
    """The qualifier that goes next to every accuracy number (README, ML_RESULTS.md, the dashboard)."""
    return f"on a {folds * fold_days}-day back-test ({folds} rolling {fold_days}-day windows)"


def mae_table_markdown(summary: pd.DataFrame) -> list[str]:
    """MAE per method and horizon as a markdown table (methods with '+weather' are the weather versions)."""
    horizons = sorted(summary["horizon"].unique())
    pivot = summary.pivot(index="method", columns="horizon", values="mae")
    order = sorted(pivot.index, key=lambda m: (m not in ("persistence", "project_baseline", "same_hour_yesterday"), m.endswith("+weather"), m))
    lines = ["| method | " + " | ".join(f"{h} h MAE" for h in horizons) + " |", "|---" * (len(horizons) + 1) + "|"]
    for m in order:
        lines.append(f"| {m} | " + " | ".join(f"{pivot.loc[m, h]:.1f}" for h in horizons) + " |")
    return lines


def weather_effect(summary: pd.DataFrame) -> pd.DataFrame:
    """Per horizon: best MAE among the models without weather vs the best among those with weather.

    Empty when the evaluation had no weather. `change_pct` is negative when weather lowered the error.
    """
    rows = []
    for h in sorted(summary["horizon"].unique()):
        block = summary[summary["horizon"] == h]
        base = block[block["method"].isin(ML_NAMES)]
        wx = block[block["method"].str.endswith("+weather")]
        if base.empty or wx.empty:
            continue
        b, w = base.sort_values("mae").iloc[0], wx.sort_values("mae").iloc[0]
        rows.append({"horizon": h, "best_without": b["method"], "mae_without": b["mae"],
                     "best_with": w["method"], "mae_with": w["mae"], "change_pct": 100 * (w["mae"] / b["mae"] - 1)})
    return pd.DataFrame(rows, columns=["horizon", "best_without", "mae_without", "best_with", "mae_with", "change_pct"])


def render_markdown(preds: pd.DataFrame, summary: pd.DataFrame, s: pd.Series, folds: int, fold_days: int) -> str:
    first, last = preds["origin"].min(), preds["origin"].max()
    uses_weather = any(c.endswith("+weather") for c in preds.columns)
    phrase = backtest_phrase(folds, fold_days)
    lines = [
        "# ML forecast results",
        "",
        f"Generated {datetime.now(config.IST):%d %b %Y %H:%M} IST from {len(s)} hourly city-mean AQI values "
        f"({s.index.min():%d %b} to {s.index.max():%d %b %Y}).",
        "",
        f"**How it was tested.** Rolling-origin evaluation: {folds} consecutive test windows of {fold_days} days "
        f"({first:%d %b} to {last:%d %b}). For each window the models are trained only on the past (with a gap of "
        "one horizon, so no target overlaps the test period) and scored on the window. Errors are in AQI points; "
        "lower is better. Weather features: " + ("included." if uses_weather else "not included (no data/weather.csv).") + "",
        "",
    ]
    for h in sorted(summary["horizon"].unique()):
        block = summary[summary["horizon"] == h].sort_values("mae")
        lines += [f"## {h}-hour-ahead forecast", "", f"Scored {phrase}.", "",
                  "| method | MAE | RMSE | vs 'same as now' |", "|---|---|---|---|"]
        for _, r in block.iterrows():
            skill = "baseline" if r["method"] == "persistence" else f"{r['skill_vs_persistence']:+.0%}"
            lines.append(f"| {r['method']} | {r['mae']:.1f} | {r['rmse']:.1f} | {skill} |")
        best = best_ml_method(summary, h)
        fw = ml.folds_won(preds, best).query("horizon == @h").iloc[0]
        lines += ["", f"Best model: **{best}**, lower MAE than 'same as now' in {fw['folds_won']} of {fw['folds']} test windows.", ""]
    lines += ["## MAE by method and horizon", "", f"Mean absolute error in AQI points, {phrase}. Methods ending in +weather use weather features.", ""]
    lines += mae_table_markdown(summary) + [""]
    effect = weather_effect(summary)
    if not effect.empty:
        lines += ["## Effect of weather features", "", f"Best model without weather vs best model with weather, {phrase}:", ""]
        for _, r in effect.iterrows():
            verb = "lowered" if r["change_pct"] < 0 else "raised" if r["change_pct"] > 0 else "did not change"
            lines.append(f"- {int(r['horizon'])} h: {r['best_without']} {r['mae_without']:.1f} -> {r['best_with']} {r['mae_with']:.1f}; "
                         f"weather {verb} the MAE" + ("" if r["change_pct"] == 0 else f" by {abs(r['change_pct']):.1f}%") + ".")
        lines.append("")
    lines += [
        "## How to read this",
        "",
        "- **'same as now' (persistence)** predicts that AQI stays where it is. It is hard to beat at short horizons.",
        "- **project_baseline** is the statistical forecast in `src/forecast.py`, evaluated exactly as it would have been issued at each hour.",
        "- **same_hour_yesterday** repeats the AQI from 24 hours before the target hour.",
        f"- The test period is only {folds * fold_days} days and the windows are correlated, so small differences between models are within noise.",
        "- The test period covers the autumn rise in pollution; a model trained mostly on cleaner months faces a shifted distribution, which is why the models predict the change from the current AQI rather than the level.",
        "- Weather features use the weather at the target hour, which assumes a weather forecast is available when the prediction is made.",
        "",
        "![MAE by method and horizon](ml_forecast.png)",
    ]
    return "\n".join(lines) + "\n"


def plot(preds: pd.DataFrame, summary: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    horizons = sorted(summary["horizon"].unique())
    methods = list(summary.sort_values("mae")["method"].unique())
    order = [m for m in ("persistence", "same_hour_yesterday", "project_baseline") if m in methods] + [
        m for m in methods if m not in ("persistence", "same_hour_yesterday", "project_baseline")
    ]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.2, 1]})
    width = 0.8 / len(order)
    for i, m in enumerate(order):
        vals = [summary[(summary["horizon"] == h) & (summary["method"] == m)]["mae"].iloc[0] for h in horizons]
        ax1.bar([x + i * width for x in range(len(horizons))], vals, width, label=m)
    ax1.set_xticks([x + 0.4 - width / 2 for x in range(len(horizons))], [f"{h} h ahead" for h in horizons])
    ax1.set_ylabel("MAE (AQI points, lower is better)")
    ax1.set_title("Forecast error by method")
    ax1.legend(fontsize=7, ncol=2)

    h = max(horizons)
    best = best_ml_method(summary, h)
    last_fold = preds[(preds["horizon"] == h) & (preds["fold"] == preds["fold"].max())].sort_values("origin")
    target_time = last_fold["origin"] + pd.Timedelta(hours=h)
    ax2.plot(target_time, last_fold["actual"], color="black", label="actual")
    ax2.plot(target_time, last_fold["persistence"], color="grey", linestyle="--", label="same as now")
    ax2.plot(target_time, last_fold[best], color="tab:red", label=best)
    ax2.set_title(f"{h}-hour-ahead forecast, last test week")
    ax2.set_ylabel("city AQI")
    ax2.legend(fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def save_models(s: pd.Series, weather: pd.DataFrame | None, summary: pd.DataFrame) -> None:
    import joblib

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    info: dict[int, dict] = {}
    for h in sorted(summary["horizon"].unique()):
        method = best_ml_method(summary, h)
        use_wx = method.endswith("+weather")
        model = ml.fit_final(s, h, method, weather if use_wx else None)
        row = summary[(summary["horizon"] == h) & (summary["method"] == method)].iloc[0]
        base = summary[(summary["horizon"] == h) & (summary["method"] == "persistence")].iloc[0]
        joblib.dump(
            {"model": model, "horizon": h, "method": method, "uses_weather": use_wx,
             "cv_mae": float(row["mae"]), "persistence_mae": float(base["mae"]),
             "trained_through": str(s.dropna().index.max())},
            MODELS_DIR / f"forecast_h{h}.joblib",
        )
        info[int(h)] = {"method": method, "rows_used": int(model.n_rows_), "feature_names": list(model.feature_names_)}
        print(f"saved {MODELS_DIR / f'forecast_h{h}.joblib'}  ({method})")
    meta = ml.write_meta(MODELS_DIR, info)
    print(f"saved {MODELS_DIR / ml.META_NAME}  (scikit-learn {meta['sklearn_version']}, numpy {meta['numpy_version']})")


def print_latest(s: pd.Series, weather: pd.DataFrame | None) -> None:
    import joblib

    files = sorted(MODELS_DIR.glob("forecast_h*.joblib"), key=lambda p: int(p.stem.split("h")[-1]))
    if not files:
        sys.exit("No saved models. Run: python src/train_forecast.py")
    try:
        ml.check_models_usable(MODELS_DIR)
    except ml.ModelVersionError as exc:
        sys.exit(str(exc))
    now = s.dropna()
    print(f"Latest city AQI: {now.iloc[-1]:.0f} at {now.index[-1]:%d %b %H:%M} IST")
    for f in files:
        bundle = joblib.load(f)
        pred = ml.predict_latest(bundle["model"], s, bundle["horizon"], weather if bundle["uses_weather"] else None)
        text = "not available (recent data has gaps)" if pred is None else f"{pred:.0f}"
        print(f"  +{bundle['horizon']:>2} h: {text:>6}   [{bundle['method']}, back-test MAE {bundle['cv_mae']:.0f} vs {bundle['persistence_mae']:.0f} for 'same as now']")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folds", type=int, default=4, help="number of test windows (default 4)")
    ap.add_argument("--fold-days", type=int, default=7, help="length of each test window in days (default 7)")
    ap.add_argument("--no-save", action="store_true", help="do not write the report, chart or models")
    ap.add_argument("--predict", action="store_true", help="only print forecasts from the saved models")
    args = ap.parse_args()

    s = load_city_series()
    if s.empty:
        sys.exit("No data in the database. Run python src/backfill.py first.")
    weather = load_weather()
    if args.predict:
        print_latest(s, weather)
        return

    print(f"{len(s)} hourly values; weather features: {'yes' if weather is not None else 'no (run src/fetch_weather.py)'}")
    preds = run_evaluation(s, weather, args.folds, args.fold_days)
    summary = ml.summarize(preds)
    print(summary.round(2).to_string(index=False))
    print("\n" + "\n".join(mae_table_markdown(summary)))
    effect = weather_effect(summary)
    if not effect.empty:
        print("\n" + effect.round(2).to_string(index=False))
    if args.no_save:
        return
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "ML_RESULTS.md").write_text(render_markdown(preds, summary, s, args.folds, args.fold_days), encoding="utf-8")
    plot(preds, summary, DOCS_DIR / "ml_forecast.png")
    save_models(s, weather, summary)
    print("Wrote docs/ML_RESULTS.md and docs/ml_forecast.png")


if __name__ == "__main__":
    main()
