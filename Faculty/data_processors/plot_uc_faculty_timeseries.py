import sys
import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

SURF, INK, INK2, GRID, CTX, HUE = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#d6d5d0", "#2a78d6"
src, out = sys.argv[1], sys.argv[2]
l = pl.read_parquet(src).filter(pl.col("series") == "ladder")
order = (l.filter(pl.col("year") == 2024).sort("median_gross", descending=True)["bucket"].to_list())
years = sorted(l["year"].unique().to_list())
series = {b: l.filter(pl.col("bucket") == b).sort("year")["median_gross"].to_list() for b in order}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
fig, axes = plt.subplots(2, 5, figsize=(15, 6.4), sharex=True, sharey=True, facecolor=SURF)
for ax, b in zip(axes.flat, order):
    ax.set_facecolor(SURF)
    for other, v in series.items():
        if other != b:
            ax.plot(years, v, color=CTX, lw=1, zorder=1)
    v = series[b]
    ax.plot(years, v, color=HUE, lw=2, zorder=3)
    ax.scatter([years[0], years[-1]], [v[0], v[-1]], s=22, color=HUE, edgecolor=SURF, linewidth=1.5, zorder=4)
    ax.annotate(f"${v[-1]/1000:.0f}k", (years[-1], v[-1]), xytext=(0, 7), textcoords="offset points",
                ha="right", va="bottom", color=INK, fontsize=9, fontweight="bold")
    ax.annotate(f"${v[0]/1000:.0f}k", (years[0], v[0]), xytext=(0, -12), textcoords="offset points",
                ha="left", va="top", color=INK2, fontsize=8.5)
    n = l.filter((pl.col("bucket") == b) & (pl.col("year") == 2024))["n"].item()
    ax.set_title(b.replace("Architecture & Environmental Design", "Architecture & Env. Design").replace("Education & Public Administration", "Education & Public Admin."), loc="left", fontsize=9.5, color=INK, fontweight="bold", pad=16)
    ax.text(0, 1.015, f"+{v[-1]/v[0]-1:.0%} since 2013 · n={n:,} in 2024", transform=ax.transAxes, fontsize=8, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.set_xticks([2013, 2018, 2024])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    ax.set_ylim(60000, 340000)
fig.suptitle("UC ladder faculty: median gross pay by department bucket, 2013 to 2024", x=0.06, ha="left",
             fontsize=13, color=INK, fontweight="bold", y=0.995)
fig.text(0.06, 0.935, "Assistant, associate, and full professors plus lecturers with security of employment, all UC campuses. "
         "Nominal dollars. Gray lines are the other nine buckets.", fontsize=9, color=INK2)
fig.text(0.06, 0.012, "Source: UC CPRA pay records via Faculty/data/cleaned_salaries.parquet; ladder titles matched by job title.",
         fontsize=8, color=INK2)
fig.tight_layout(rect=(0.04, 0.03, 1, 0.92), h_pad=2.6, w_pad=1.2)
fig.savefig(out, dpi=170, facecolor=SURF)
