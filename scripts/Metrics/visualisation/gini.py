import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TRACK_COLORS = {
    "AI_track": "steelblue",
    "CS_track": "coral",
}

TRACK_LABELS = {
    "AI_track": "AI Track",
    "CS_track": "CS Track",
}


def gini(values):
    values = np.sort(np.array(values, dtype=float))
    n = len(values)
    mean = values.mean()
    if mean == 0:
        return 0.0
    diff_sum = np.sum(np.abs(values[:, None] - values[None, :]))
    return diff_sum / (2 * n ** 2 * mean)


def lorenz(values):
    values = np.sort(np.array(values, dtype=float))
    cumsum = np.cumsum(values)
    cumsum = np.insert(cumsum, 0, 0)
    x = np.linspace(0, 1, len(cumsum))
    y = cumsum / cumsum[-1]
    return x, y


def create_gini_plot(
    student_metrics: pd.DataFrame,
    metric: str = "optionalCorrectedRankSum",
    output_path: str = "gini_plot.png",
):
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1, label="Perfect equality")

    tracks = sorted(student_metrics["track"].unique())

    for track in tracks:
        values = student_metrics.loc[student_metrics["track"] == track, metric].dropna().values
        x, y = lorenz(values)
        g = gini(values)
        color = TRACK_COLORS.get(track, "gray")
        label = TRACK_LABELS.get(track, track)
        ax.plot(x, y, color=color, linewidth=2, label=f"{label}  (Gini = {g:.3f})")
        ax.fill_between(x, x, y, alpha=0.08, color=color)

    ax.set_title(f"Lorenz Curve  |  metric: {metric}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Cumulative share of students (sorted by rank sum)", fontsize=10)
    ax.set_ylabel("Cumulative share of rank sum", fontsize=10)
    ax.legend(fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")
