import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


def normalize_row(row, global_max=None):
    non_zero = row[row != 0]
    if len(non_zero) == 0:
        return row.apply(lambda x: np.nan)
    min_r = 1.0
    max_r = global_max if global_max is not None else non_zero.max()
    if max_r == min_r:
        return row.apply(lambda x: 0.0 if x != 0 else np.nan)
    return row.apply(lambda x: (x - min_r) / (max_r - min_r) if x != 0 else np.nan)


def pack_row(row):
    vals = row.dropna().sort_values().to_list()
    padded = vals + [np.nan] * (len(row) - len(vals))
    return pd.Series(padded, index=row.index)


STRATEGIES = {
    "mean_std": (["optionalCorrectedMean", "optionalCorrectedStd"], [True, False]),
    "median":   (["optionalCorrectedMedian"],                       [True]),
    "ranksum":  (["optionalCorrectedRankSum"],                      [True]),
}

TRACK_COLORS = {
    "AI_track": "steelblue",
    "CS_track": "coral",
}

TRACK_LABELS = {
    "AI_track": "AI Track",
    "CS_track": "CS Track",
}


def create_split_heatmaps(
    df_matrix: pd.DataFrame,
    student_metrics: pd.DataFrame,
    preferences: pd.DataFrame,
    output_prefix: str = "split_heatmap",
    exclude_mandatory: bool = False,
    courses: pd.DataFrame = None,
):
    tracks = student_metrics["track"].unique()

    global_max = preferences.loc[:, preferences.columns.str.startswith("Rg")].max().max()

    for strategy_name, (sort_cols, ascending) in STRATEGIES.items():

        fig = plt.figure(figsize=(20, 10))
        suffix = " (optional courses only)" if exclude_mandatory else ""
        fig.suptitle(
            f"Student Satisfaction Heatmap by Track  |  sorted by {' + '.join(sort_cols)}{suffix}",
            fontsize=14, fontweight="bold", y=1.01,
        )

        norm = Normalize(vmin=0, vmax=1)
        cmap = "RdYlGn_r"

        axes = []
        track_list = sorted(tracks)

        for ax_idx, track in enumerate(track_list):

            ax = fig.add_subplot(1, len(track_list), ax_idx + 1)
            axes.append(ax)

            mask = student_metrics["track"] == track

            sorted_ids = (
                student_metrics.loc[mask]
                .sort_values(by=sort_cols, ascending=ascending)
                .index
            )

            sub_matrix = df_matrix.loc[sorted_ids]
            cols_used = sub_matrix.columns[(sub_matrix != 0).any(axis=0)]
            sub_matrix = sub_matrix[cols_used]

            if exclude_mandatory and courses is not None:
                mandatory_ids = courses.loc[courses[track], "courseID"].tolist()
                mandatory_cols = [f"c{cid}" for cid in mandatory_ids]
                cols_to_drop = [c for c in mandatory_cols if c in sub_matrix.columns]
                sub_matrix = sub_matrix.drop(columns=cols_to_drop)

            df_norm = sub_matrix.apply(lambda row: normalize_row(row, global_max), axis=1)

            df_packed = df_norm.apply(pack_row, axis=1)
            df_packed.columns = [f"rank {i+1}" for i in range(df_packed.shape[1])]

            color = TRACK_COLORS.get(track, "gray")
            label = TRACK_LABELS.get(track, track)

            sns.heatmap(
                df_packed,
                ax=ax,
                cmap=cmap,
                norm=norm,
                cbar=False,
                linewidths=0.4,
                linecolor="grey",
                mask=df_packed.isna(),
            )

            ax.set_title(label, fontsize=12, fontweight="bold", color=color, pad=8)
            ax.set_xlabel("Assigned courses (best to worst rank)", fontsize=9)
            ax.set_ylabel(
                "Students (most satisfied to least satisfied)" if ax_idx == 0 else "",
                fontsize=9,
            )
            ax.tick_params(axis="y", labelsize=7)
            ax.tick_params(axis="x", labelsize=8)

            ax.text(
                0.99, 0.01,
                f"n = {len(sorted_ids)}",
                transform=ax.transAxes,
                ha="right", va="bottom",
                fontsize=8, color="white",
                bbox=dict(boxstyle="round,pad=0.2", fc=color, alpha=0.7),
            )

        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=axes, fraction=0.02, pad=0.02)
        cbar.set_label("Normalized rank (0 = best, 1 = worst)", fontsize=9)

        plt.tight_layout()

        filename = f"{output_prefix}_{strategy_name}.png"
        plt.savefig(filename, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved: {filename}")


