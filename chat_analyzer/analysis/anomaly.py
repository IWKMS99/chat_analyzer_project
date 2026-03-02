# === Standard library ===
import logging
from typing import Dict, Optional

# === Data handling & Stats ===
import numpy as np
import pandas as pd
from scipy.stats import zscore

# === Visualization ===
import matplotlib.pyplot as plt

from chat_analyzer.utils import finalize_plot, require_non_empty_df

logger = logging.getLogger(__name__)


def _zscore_spikes(daily_counts: pd.Series, threshold: float) -> pd.Series:
    if len(daily_counts) < 5:
        logger.warning("Слишком мало дней для надежного анализа аномалий (zscore).")
        return pd.Series(dtype=float)
    if daily_counts.std() == 0:
        logger.warning("Стандартное отклонение дневной активности равно 0. Z-score аномалии не определяются.")
        return pd.Series(dtype=float)
    zs = pd.Series(zscore(daily_counts.fillna(0)), index=daily_counts.index)
    return daily_counts[zs > threshold]


def _robust_spikes(daily_counts: pd.Series, threshold: float) -> pd.DataFrame:
    if len(daily_counts) < 7:
        logger.warning("Слишком мало дней для robust-анализа аномалий.")
        return pd.DataFrame(columns=["msg_count", "weekday_median", "weekday_mad", "robust_score"])

    df_daily = pd.DataFrame({"msg_count": daily_counts})
    dt_index = pd.to_datetime(df_daily.index)
    df_daily["weekday"] = dt_index.dayofweek

    grouped = df_daily.groupby("weekday")["msg_count"]
    weekday_median = grouped.transform("median")

    def mad(series: pd.Series) -> float:
        return float(np.median(np.abs(series - np.median(series))))

    weekday_mad = grouped.transform(mad)
    weekday_mad = weekday_mad.replace(0, np.nan)

    robust_score = (df_daily["msg_count"] - weekday_median) / (1.4826 * weekday_mad)
    robust_score = robust_score.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    out = pd.DataFrame(
        {
            "msg_count": df_daily["msg_count"],
            "weekday_median": weekday_median,
            "weekday_mad": weekday_mad.fillna(0.0),
            "robust_score": robust_score,
        },
        index=df_daily.index,
    )
    return out[out["robust_score"] > threshold]


def analyze_anomalous_days(
    df: pd.DataFrame,
    threshold: float = 2.0,
    save_path: Optional[str] = None,
    mode: str = "robust",
) -> Dict[str, object]:
    """Находит и визуализирует дни с аномально высокой активностью."""
    if not require_non_empty_df(df, logger, "analyze_anomalous_days", ["date_only", "from", "text"]):
        return {"metrics": {}, "artifacts": {}, "warnings": ["empty_input"]}

    mode = (mode or "robust").lower()
    if mode not in {"robust", "zscore", "both"}:
        logger.warning("Неизвестный режим аномалий '%s', используется robust.", mode)
        mode = "robust"

    warnings = []

    try:
        daily_counts = df.groupby("date_only").size().rename("msg_count")
        if daily_counts.empty:
            logger.warning("Нет данных по дням для расчета аномалий.")
            return {"metrics": {}, "artifacts": {}, "warnings": ["empty_daily_counts"]}

        robust_spikes = pd.DataFrame()
        zscore_spikes = pd.Series(dtype=float)

        if mode in {"robust", "both"}:
            robust_spikes = _robust_spikes(daily_counts, threshold=threshold)
        if mode in {"zscore", "both"}:
            zscore_spikes = _zscore_spikes(daily_counts, threshold=threshold)

        logger.info("\n--- Анализ аномальных дней ---")
        logger.info("Режим: %s; Порог: %.2f", mode, threshold)
        if mode in {"robust", "both"}:
            if robust_spikes.empty:
                logger.info("Robust: аномальных дней не найдено.")
            else:
                logger.info("Robust аномалии:\n%s", robust_spikes[["msg_count", "robust_score"]])
        if mode in {"zscore", "both"}:
            if zscore_spikes.empty:
                logger.info("Z-score: аномальных дней не найдено.")
            else:
                logger.info("Z-score аномалии:\n%s", zscore_spikes)

        plt.figure(figsize=(14, 7))
        daily_counts_plot = daily_counts.copy()
        daily_counts_plot.index = pd.to_datetime(daily_counts_plot.index)
        plt.plot(daily_counts_plot.index, daily_counts_plot, label="Сообщения по дням", color="steelblue", alpha=0.7)

        if mode in {"robust", "both"} and not robust_spikes.empty:
            robust_plot = robust_spikes.copy()
            robust_plot.index = pd.to_datetime(robust_plot.index)
            plt.scatter(
                robust_plot.index,
                robust_plot["msg_count"],
                color="crimson",
                label=f"Robust аномалии (>{threshold})",
                zorder=5,
                s=50,
            )

        if mode in {"zscore", "both"} and not zscore_spikes.empty:
            z_plot = zscore_spikes.copy()
            z_plot.index = pd.to_datetime(z_plot.index)
            plt.scatter(
                z_plot.index,
                z_plot,
                color="darkorange",
                marker="x",
                label=f"Z-score аномалии (>{threshold})",
                zorder=5,
                s=55,
            )

        plt.title("Ежедневная активность и аномальные дни", fontsize=16)
        plt.xlabel("Дата", fontsize=12)
        plt.ylabel("Количество сообщений", fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        finalize_plot(logger, save_path, "график аномальных дней")

        robust_dates = set(pd.to_datetime(robust_spikes.index).date) if not robust_spikes.empty else set()
        zscore_dates = set(pd.to_datetime(zscore_spikes.index).date) if not zscore_spikes.empty else set()
        unified_dates = sorted(robust_dates | zscore_dates)

        if unified_dates:
            logger.info("Примеры сообщений в аномальные дни (макс. 5 на день):")
        for date_only in unified_dates:
            logger.info("Дата: %s", date_only)
            sample_msgs = df.loc[df["date_only"] == date_only, ["from", "text"]].head(5)
            if sample_msgs.empty:
                logger.info("  (Нет примеров сообщений)")
                continue
            for row in sample_msgs.itertuples(index=False):
                text_preview = str(row.text)[:100]
                if len(str(row.text)) > 100:
                    text_preview += "..."
                logger.info("  %s: %s", row[0], text_preview)

        metrics = {
            "mode": mode,
            "threshold": threshold,
            "daily_days": int(len(daily_counts)),
            "robust_count": int(len(robust_spikes)),
            "zscore_count": int(len(zscore_spikes)),
        }
        artifacts = {
            "robust_spikes": robust_spikes,
            "zscore_spikes": zscore_spikes,
        }
        logger.info("%s", "-" * 20)
        return {"metrics": metrics, "artifacts": artifacts, "warnings": warnings}

    except Exception as exc:
        logger.error("Ошибка при анализе аномальных дней: %s", exc, exc_info=logger.isEnabledFor(logging.DEBUG))
        plt.close()
        return {"metrics": {}, "artifacts": {}, "warnings": ["anomaly_exception"]}
