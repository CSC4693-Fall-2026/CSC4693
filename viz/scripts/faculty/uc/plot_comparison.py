import matplotlib.pyplot as plt
import polars as pl
from pathlib import Path

# Plots uc_comparison.parquet as a dot per campus, grouped by department bucket

HERE = Path(__file__).parent
DATA = HERE / "uc_comparison.parquet"
OUT = HERE / "uc_comparison.png"

TITLE = "UC graduate earnings relative to faculty pay, by field"
SUBTITLE = "Ladder faculty, 2023. Campuses with at least 10 on both sides."

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
DOT = "#2a78d6"


def main():
    # Lecturers are often part-time, so their pay is not a full-time salary
    df = (
        pl.read_parquet(DATA)
        .filter((pl.col("series") == "ladder") & pl.col("meets_min_n"))
        .select("campus", "department", "ratio_5yr")
    )

    order = (
        df.group_by("department")
        .agg(pl.col("ratio_5yr").median().alias("mid"), pl.len().alias("n"))
        .sort("mid")
    )

    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    for y, (dept, mid, n) in enumerate(order.iter_rows()):
        vals = df.filter(pl.col("department") == dept)
        ax.plot([vals["ratio_5yr"].min(), vals["ratio_5yr"].max()], [y, y],
                color=GRID, linewidth=2, zorder=1, solid_capstyle="round")
        for campus, _, ratio in vals.iter_rows():
            ax.scatter(ratio, y, s=90, zorder=3, color=DOT,
                       edgecolors=SURFACE, linewidths=2)
            # Label the only point above parity so it can be identified
            if ratio > 1:
                ax.annotate(f"{campus.title()}  {ratio:.2f}", (ratio, y),
                            textcoords="offset points", xytext=(12, 0),
                            va="center", fontsize=9, color=INK)
        ax.scatter(mid, y, marker="|", s=320, color=INK, linewidths=2, zorder=4)
        # n varies a lot by field, Agriculture is only 2 campuses
        ax.annotate(f"n={n}", (0.018, y), va="center", fontsize=8.5, color=MUTED)

    ax.axvline(1, color=SECONDARY, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
    ax.annotate("parity (1.0)", (1, len(order) - 0.42),
                textcoords="offset points", xytext=(7, 0),
                fontsize=8.5, color=SECONDARY, va="center")

    ax.set_yticks(range(order.height), order["department"].to_list(), fontsize=10, color=INK)
    ax.set_xlim(0, 1.32)
    ax.set_ylim(-0.7, order.height - 0.3)
    ax.set_xlabel("Graduate earnings 5 years out, as a share of faculty pay",
                  fontsize=10, color=SECONDARY, labelpad=10)

    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0)
    for side, spine in ax.spines.items():
        spine.set_visible(side == "bottom")
        spine.set_color(AXIS)

    ax.scatter([], [], s=90, color=DOT, edgecolors=SURFACE, linewidths=2, label="one campus")
    ax.scatter([], [], marker="|", s=320, color=INK, linewidths=2, label="field median")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2, frameon=False,
              fontsize=9, labelcolor=SECONDARY, handletextpad=0.4,
              columnspacing=1.6, borderpad=0)

    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.text(0.015, 0.955, TITLE, fontsize=13.5, color=INK, va="center")
    fig.text(0.015, 0.915, SUBTITLE, fontsize=9.5, color=SECONDARY, va="center")
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)

    print(f"Wrote {OUT.name} ({df.height} campus x field points, ladder faculty only).")


if __name__ == "__main__":
    main()
