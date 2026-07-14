"""Plot cement projections for the nine largest OMNIA regions in 2019."""

from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

INPUT_CSV = OUTPUTS_DIR / "cement_omnia_region_projection_2019_2050.csv"
OUTPUT_PNG = FIGURES_DIR / "cement_omnia_regions_top9_2019_3x3.png"
OUTPUT_PDF = FIGURES_DIR / "cement_omnia_regions_top9_2019_3x3.pdf"

RANK_YEAR = 2019
START_YEAR = 2019
END_YEAR = 2050
REGION_COUNT = 9


def read_projection() -> pd.DataFrame:
    projection = pd.read_csv(INPUT_CSV)
    projection.columns = [
        int(column) if str(column).isdigit() else column
        for column in projection.columns
    ]

    required_columns = {"OMNIARegion", *range(START_YEAR, END_YEAR + 1)}
    missing = required_columns - set(projection.columns)
    if missing:
        raise ValueError(
            f"{INPUT_CSV.name} is missing columns: {sorted(missing, key=str)}"
        )
    if projection["OMNIARegion"].duplicated().any():
        duplicates = projection.loc[
            projection["OMNIARegion"].duplicated(keep=False), "OMNIARegion"
        ].tolist()
        raise ValueError(f"Duplicate OMNIA regions: {duplicates}")
    return projection


def set_plot_theme() -> None:
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
            "figure.dpi": 300,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )


def make_figure() -> list[str]:
    projection = read_projection()
    years = list(range(START_YEAR, END_YEAR + 1))
    selected = (
        projection.sort_values(RANK_YEAR, ascending=False)
        .head(REGION_COUNT)[["OMNIARegion", RANK_YEAR]]
        .reset_index(drop=True)
    )
    selected_regions = selected["OMNIARegion"].tolist()

    plot_data = projection[
        projection["OMNIARegion"].isin(selected_regions)
    ].copy()
    plot_data = plot_data.melt(
        id_vars="OMNIARegion",
        value_vars=years,
        var_name="Year",
        value_name="Production_kt",
    )
    plot_data["Production_Mt"] = plot_data["Production_kt"] / 1000

    set_plot_theme()
    fig, axes = plt.subplots(
        3,
        3,
        figsize=(7.2, 6.7),
        sharex=True,
        constrained_layout=True,
    )
    axes = axes.ravel()

    for ax, region in zip(axes, selected_regions):
        region_data = plot_data[plot_data["OMNIARegion"].eq(region)]
        sns.lineplot(
            data=region_data,
            x="Year",
            y="Production_Mt",
            color="#0072B2",
            linewidth=1.55,
            estimator=None,
            errorbar=None,
            ax=ax,
        )
        ax.set_title(region, loc="left", pad=3)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.grid(axis="y", color="0.88", linewidth=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=2.5, width=0.55, color="0.2", pad=2)
        ax.set_xlim(START_YEAR, END_YEAR)
        ax.set_xticks([2019, 2024, 2035, 2050])
        ax.margins(x=0)

    fig.supxlabel("Year", fontsize=8)
    fig.supylabel("Cement production (Mt)", fontsize=8)
    fig.suptitle(
        "Cement projections for the nine largest-producing OMNIA regions in 2019",
        x=0.01,
        y=1.02,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)
    return selected_regions


def main() -> None:
    selected_regions = make_figure()
    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_PDF}")
    print(f"OMNIA regions included: {', '.join(selected_regions)}")


if __name__ == "__main__":
    main()
