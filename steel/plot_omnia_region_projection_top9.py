"""Plot steel production and scrap for the nine largest 2019 OMNIA regions."""

from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

RANK_YEAR = 2019
START_YEAR = 2019
END_YEAR = 2050
REGION_COUNT = 9

PLOTS = [
    {
        "name": "production",
        "input": OUTPUTS_DIR
        / "steel_production_omnia_region_projection_2019_2050.csv",
        "png": FIGURES_DIR / "steel_production_omnia_regions_top9_2019_3x3.png",
        "pdf": FIGURES_DIR / "steel_production_omnia_regions_top9_2019_3x3.pdf",
        "ylabel": "Steel production (Mt)",
        "title": (
            "Steel production projections for the nine largest-producing "
            "OMNIA regions in 2019"
        ),
        "color": "#0072B2",
    },
    {
        "name": "scrap",
        "input": OUTPUTS_DIR / "steel_scrap_omnia_region_projection_2019_2050.csv",
        "png": FIGURES_DIR / "steel_scrap_omnia_regions_top9_2019_3x3.png",
        "pdf": FIGURES_DIR / "steel_scrap_omnia_regions_top9_2019_3x3.pdf",
        "ylabel": "Steel scrap (Mt)",
        "title": "Steel scrap projections for the nine largest OMNIA regions in 2019",
        "color": "#009E73",
    },
]


def read_projection(path: Path) -> pd.DataFrame:
    projection = pd.read_csv(path)
    projection.columns = [
        int(column) if str(column).isdigit() else column
        for column in projection.columns
    ]
    required = {"OMNIARegion", *range(START_YEAR, END_YEAR + 1)}
    missing = required - set(projection.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing, key=str)}")
    if projection["OMNIARegion"].duplicated().any():
        raise ValueError(f"{path.name} has duplicate OMNIA regions")
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


def make_figure(config: dict) -> list[str]:
    projection = read_projection(config["input"])
    years = list(range(START_YEAR, END_YEAR + 1))
    selected_regions = (
        projection.sort_values(RANK_YEAR, ascending=False)
        .head(REGION_COUNT)["OMNIARegion"]
        .tolist()
    )
    plot_data = projection[
        projection["OMNIARegion"].isin(selected_regions)
    ].melt(
        id_vars="OMNIARegion",
        value_vars=years,
        var_name="Year",
        value_name="Value_kt",
    )
    plot_data["Value_Mt"] = plot_data["Value_kt"] / 1000

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
            y="Value_Mt",
            color=config["color"],
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
    fig.supylabel(config["ylabel"], fontsize=8)
    fig.suptitle(
        config["title"],
        x=0.01,
        y=1.02,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config["png"], bbox_inches="tight")
    fig.savefig(config["pdf"], bbox_inches="tight")
    plt.close(fig)
    return selected_regions


def main() -> None:
    for config in PLOTS:
        selected_regions = make_figure(config)
        print(f"Saved: {config['png']}")
        print(f"Saved: {config['pdf']}")
        print(
            f"OMNIA regions included ({config['name']}): "
            f"{', '.join(selected_regions)}"
        )


if __name__ == "__main__":
    main()
