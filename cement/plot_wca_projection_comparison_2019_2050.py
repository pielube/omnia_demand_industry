"""Plot 2019-2050 WCA cement demand for the nine largest producers."""

from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"

DYNAMIC_SHARE_PATH = OUTPUTS_DIR / "cement_demand_with_population_wca_regions.csv"
FIXED_SHARE_PATH = OUTPUTS_DIR / "cement_demand_with_population_wca_fixed_shares.csv"

OUTPUT_DIR = OUTPUTS_DIR / "figures"
OUTPUT_PDF = OUTPUT_DIR / "wca_projection_comparison_top9_2019_2050_3x3.pdf"

RANK_YEAR = 2024
START_YEAR = 2019
END_YEAR = 2050
COUNTRY_COUNT = 9


def read_cement_projection(path, approach):
    df = pd.read_csv(path)
    df.columns = [int(col) if str(col).isdigit() else col for col in df.columns]
    cement = df[df["Metric"].eq("Cement production")].copy()
    year_columns = [
        col
        for col in cement.columns
        if isinstance(col, int) and START_YEAR <= col <= END_YEAR
    ]

    long = cement.melt(
        id_vars=["Country", "ISO3"],
        value_vars=year_columns,
        var_name="Year",
        value_name="Demand_kt",
    )
    long["Approach"] = approach
    long["Demand_Mt"] = long["Demand_kt"] / 1000
    return long


def make_figure():
    dynamic = read_cement_projection(DYNAMIC_SHARE_PATH, "Dynamic shares")
    fixed = read_cement_projection(FIXED_SHARE_PATH, "Fixed shares")

    first_countries = (
        pd.read_csv(DYNAMIC_SHARE_PATH)
        .rename(columns=lambda col: int(col) if str(col).isdigit() else col)
        .query("Metric == 'Cement production'")
        .sort_values(RANK_YEAR, ascending=False)
        [["Country", "ISO3", RANK_YEAR]]
        .drop_duplicates()
        .head(COUNTRY_COUNT)
        .reset_index(drop=True)
    )
    first_iso3 = first_countries["ISO3"].tolist()

    plot_data = pd.concat([dynamic, fixed], ignore_index=True)
    plot_data = plot_data[plot_data["ISO3"].isin(first_iso3)].copy()

    sns.set_theme(
        context="paper",
        style="white",
        font="Arial",
        rc={
            "axes.linewidth": 0.6,
            "axes.edgecolor": "0.15",
            "axes.labelcolor": "0.1",
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "figure.dpi": 300,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )

    approach_palette = {
        "Dynamic shares": "#0072B2",
        "Fixed shares": "#D55E00",
    }

    fig, axes = plt.subplots(
        3,
        3,
        figsize=(7.2, 6.7),
        sharex=True,
        constrained_layout=True,
    )
    axes = axes.ravel()

    for ax, iso3 in zip(axes, first_iso3):
        country_data = plot_data[plot_data["ISO3"].eq(iso3)]
        country_name = country_data["Country"].iloc[0]

        sns.lineplot(
            data=country_data,
            x="Year",
            y="Demand_Mt",
            hue="Approach",
            palette=approach_palette,
            linewidth=1.45,
            estimator=None,
            errorbar=None,
            ax=ax,
            legend=False,
        )

        ax.axvline(RANK_YEAR, color="0.65", linewidth=0.6, linestyle="--", zorder=0)
        ax.set_title(f"{country_name} ({iso3})", loc="left", pad=3)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.grid(axis="y", color="0.88", linewidth=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=2.5, width=0.55, color="0.2", pad=2)
        ax.set_xlim(START_YEAR, END_YEAR)
        ax.margins(x=0)

    for ax in axes:
        ax.set_xticks([2020, 2030, 2040, 2050])

    axes[7].set_xlabel("Year", fontsize=8)
    fig.supylabel("Cement demand (Mt)", fontsize=8)
    fig.suptitle(
        "WCA cement demand: nine largest producers, 2019-2050",
        x=0.01,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    approach_handles = [
        Line2D(
            [0],
            [0],
            color=approach_palette["Dynamic shares"],
            lw=1.6,
            label="Dynamic shares",
        ),
        Line2D(
            [0],
            [0],
            color=approach_palette["Fixed shares"],
            lw=1.6,
            label="Fixed shares",
        ),
    ]

    fig.legend(
        handles=approach_handles,
        loc="outside lower center",
        frameon=False,
        ncol=2,
        handlelength=2.4,
        columnspacing=1.0,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)

    return first_countries


if __name__ == "__main__":
    countries = make_figure()
    print(f"Saved: {OUTPUT_PDF}")
    print("Countries included:")
    for row in countries.itertuples(index=False):
        print(f"  {row.Country} ({row.ISO3})")
