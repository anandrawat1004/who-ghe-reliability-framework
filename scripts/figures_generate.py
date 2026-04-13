#!/usr/bin/env python3
"""
Publication figures (300 DPI) for the white paper and Zenodo.
Outputs (FIGURES/):
  fig01_pipeline.png
  fig02_country_comparison.png
  fig03_volatility_matrix.png
  fig04_tiers.png
"""
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
FEATURES = _REPO / "FEATURES"
ARTIFACTS = _REPO / "ARTIFACTS"
FIGURES = _REPO / "FIGURES"
DPI = 300


def fig01_pipeline():
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3)
    ax.axis("off")

    stages = [
        (1.2, "Stage 0\nAudit universe", "Inclusion rules\n(ICD-10, 2000-2021)"),
        (3.2, "Stages 1-3\nCRVS layer", "Reported deaths\n(WHO MDB)"),
        (5.2, "Stage 4\nGHE layer", "Modelled deaths\n(GHE)"),
        (7.0, "Stage 5\nJoin", "Matched panel\n(all-cause)"),
        (8.8, "Stage 6\nMetrics", "Bias, ASI,\nvolatility matrix"),
        (10.8, "Stage 7\nReliability lens", "Tiers A-D,\ncountry cards"),
    ]
    for i, (x, title, sub) in enumerate(stages):
        box = mpatches.FancyBboxPatch(
            (x, 1), 1.85, 1.2, boxstyle="round,pad=0.02",
            facecolor="steelblue", edgecolor="white", alpha=0.85,
        )
        ax.add_patch(box)
        ax.text(x + 0.925, 1.75, title, ha="center", va="center", fontsize=8, fontweight="bold", color="white")
        ax.text(x + 0.925, 1.35, sub, ha="center", va="center", fontsize=6, color="white")
        if i < len(stages) - 1:
            ax.annotate(
                "", xy=(x + 1.9, 1.6), xytext=(x + 1.85, 1.6),
                arrowprops=dict(arrowstyle="->", color="gray", lw=1.5),
            )

    ax.text(0.5, 0.4, "Inputs:\nWHO MDB, GHE", fontsize=7, ha="center", color="gray")
    ax.text(12.5, 0.4, "Outputs:\nFEATURES, ARTIFACTS", fontsize=7, ha="center", color="gray")
    fig.suptitle("End-to-end audit pipeline (reproducible stages)", fontsize=11, y=1.05)
    plt.tight_layout()
    out = FIGURES / "fig01_pipeline.png"
    plt.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close()
    print("Wrote", out)


def fig02_country_comparison(panel_path, lens_path):
    import pandas as pd
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(panel_path)
    lens = pd.read_csv(lens_path)

    both = panel[panel["has_both"]].copy()
    nat = both.groupby(["country_code", "year"]).agg(
        deaths_reported=("deaths_reported", "sum"),
        deaths_estimated=("deaths_estimated", "sum"),
    ).reset_index()

    tier_a = lens[lens["tier"] == "A"]["country_code"].iloc[0]
    tier_d = lens[lens["tier"] == "D"]["country_code"].iloc[0]
    asi_a = lens[lens["country_code"] == tier_a]["asi"].iloc[0]
    asi_d = lens[lens["country_code"] == tier_d]["asi"].iloc[0]

    def plot_country(ax, country_code, asi_val):
        df = nat[nat["country_code"] == country_code].sort_values("year")
        ax.plot(df["year"], df["deaths_reported"], "o-", label="Reported (CRVS)", color="C0", lw=2, markersize=4)
        ax.plot(df["year"], df["deaths_estimated"], "s--", label="Estimated (GHE)", color="C1", lw=2, markersize=4)
        ax.set_title(f"{country_code} (ASI = {asi_val:.2f})")
        ax.set_ylabel("Deaths (national total)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    plot_country(ax1, tier_a, asi_a)
    plot_country(ax2, tier_d, asi_d)
    ax1.set_xlabel("Year")
    ax2.set_xlabel("Year")
    fig.suptitle(
        "Structural smoothness contrast: Tier A vs Tier D (reported vs GHE all-cause deaths)",
        fontsize=10,
        y=1.02,
    )
    plt.tight_layout()
    out = FIGURES / "fig02_country_comparison.png"
    plt.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close()
    print("Wrote", out)


def fig03_volatility_matrix(vol_path):
    import pandas as pd
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    vol = pd.read_parquet(vol_path)
    med_v = vol["volatility_reported"].median()
    med_d = vol["divergence_magnitude"].median()

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    ax.axvline(med_v, color="gray", linestyle="--", alpha=0.7, label="Median split")
    ax.axhline(med_d, color="gray", linestyle="--", alpha=0.7)

    colors = {"Q1": "C3", "Q2": "C2", "Q3": "C0", "Q4": "C1"}
    for q in ("Q1", "Q2", "Q3", "Q4"):
        sub = vol[vol["quadrant"] == q]
        if len(sub) == 0:
            continue
        ax.scatter(
            sub["volatility_reported"],
            sub["divergence_magnitude"],
            label=q,
            color=colors.get(q, "gray"),
            s=90,
            zorder=5,
            edgecolors="white",
            linewidths=0.5,
        )
        for _, r in sub.iterrows():
            ax.annotate(
                r["country_code"],
                (r["volatility_reported"], r["divergence_magnitude"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
            )

    ax.set_xlabel("Reported series volatility (std of first diff of log deaths)")
    ax.set_ylabel("Divergence magnitude (median |log ratio|)")
    ax.legend(loc="upper right", title="Quadrant")
    ax.set_title("Where countries sit: volatility vs alignment (pilot sample)")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = FIGURES / "fig03_volatility_matrix.png"
    plt.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close()
    print("Wrote", out)


def fig04_tiers(lens_path):
    import pandas as pd
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    lens = pd.read_csv(lens_path)
    counts = lens["tier"].value_counts().reindex(["A", "B", "C", "D"], fill_value=0)

    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    colors = {"A": "#2e7d32", "B": "#f9a825", "C": "#ef6c00", "D": "#c62828"}
    bars = ax.bar(
        counts.index,
        counts.values,
        color=[colors.get(t, "gray") for t in counts.index],
        edgecolor="white",
    )
    for b in bars:
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.05,
            str(int(b.get_height())),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )
    ax.set_ylabel("Number of countries")
    ax.set_xlabel("Reliability tier (v1 rules)")
    ax.set_title("Pilot reliability lens: how many countries per tier (T>=5)")
    ax.set_ylim(0, max(counts.values) * 1.25 if counts.values.max() > 0 else 4)
    ax.set_yticks(range(int(ax.get_ylim()[1]) + 1))
    plt.tight_layout()
    out = FIGURES / "fig04_tiers.png"
    plt.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close()
    print("Wrote", out)


def main():
    panel_path = FEATURES / "panel_allcause_matched.parquet"
    vol_path = FEATURES / "volatility_matrix_labels.parquet"
    lens_path = ARTIFACTS / "reliability_lens.csv"

    fig01_pipeline()
    if vol_path.exists():
        fig03_volatility_matrix(vol_path)
    else:
        print("Skip fig03: missing", vol_path)
    if lens_path.exists():
        fig04_tiers(lens_path)
    else:
        print("Skip fig04: missing", lens_path)
    if panel_path.exists() and lens_path.exists():
        fig02_country_comparison(panel_path, lens_path)
    else:
        print("Skip fig02: missing panel or lens")

    print("Done. Figures in", FIGURES)


if __name__ == "__main__":
    main()
