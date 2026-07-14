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
        "name": "primary",
        "input": OUTPUTS_DIR / "aluminium_primary_omnia_region_projection_2019_2050.csv",
        "png": FIGURES_DIR / "aluminium_primary_omnia_regions_top9_2019_3x3.png",
        "pdf": FIGURES_DIR / "aluminium_primary_omnia_regions_top9_2019_3x3.pdf",
        "value_column": "PrimaryProduction_Mt",
        "ylabel": "Primary aluminium ingot production (Mt)",
        "title": (
            "Primary aluminium projections for the nine largest-producing "
            "OMNIA regions in 2019"
        ),
        "color": "#0072B2",
    },
    {
        "name": "secondary",
        "input": OUTPUTS_DIR / "aluminium_secondary_omnia_region_projection_2019_2050.csv",
        "png": FIGURES_DIR / "aluminium_secondary_omnia_regions_top9_2019_3x3.png",
        "pdf": FIGURES_DIR / "aluminium_secondary_omnia_regions_top9_2019_3x3.pdf",
        "value_column": "SecondaryProduction_Mt",
        "ylabel": "Secondary aluminium ingot production (Mt)",
        "title": (
            "Secondary aluminium projections for the nine largest-producing "
            "OMNIA regions in 2019"
        ),
        "color": "#D55E00",
    },
    {
        "name": "scrap",
        "input": OUTPUTS_DIR / "aluminium_scrap_omnia_region_projection_2019_2050.csv",
        "png": FIGURES_DIR / "aluminium_scrap_omnia_regions_top9_2019_3x3.png",
        "pdf": FIGURES_DIR / "aluminium_scrap_omnia_regions_top9_2019_3x3.pdf",
        "value_column": "Scrap_Mt",
        "ylabel": "Aluminium scrap (Mt)",
        "title": "Aluminium scrap projections for the nine largest OMNIA regions in 2019",
        "color": "#009E73",
    },
]


def read_projection(input_path):
    output = pd.read_csv(input_path)
    output.columns = [int(col) if str(col).isdigit() else col for col in output.columns]

    required_columns = {"OMNIARegion", *range(START_YEAR, END_YEAR + 1)}
    missing = required_columns - set(output.columns)
    if missing:
        raise ValueError(f"{input_path.name} is missing columns: {sorted(missing, key=str)}")

    if output["OMNIARegion"].duplicated().any():
        duplicates = output.loc[
            output["OMNIARegion"].duplicated(keep=False), "OMNIARegion"
        ].tolist()
        raise ValueError(f"Duplicate OMNIA regions in {input_path.name}: {duplicates}")

    return output


def set_plot_theme():
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


def make_figure(config):
    output = read_projection(config["input"])
    years = list(range(START_YEAR, END_YEAR + 1))
    selected = (
        output.sort_values(RANK_YEAR, ascending=False)
        .head(REGION_COUNT)[["OMNIARegion", RANK_YEAR]]
        .reset_index(drop=True)
    )
    selected_regions = selected["OMNIARegion"].tolist()

    plot_data = output[output["OMNIARegion"].isin(selected_regions)].copy()
    plot_data = plot_data.melt(
        id_vars="OMNIARegion",
        value_vars=years,
        var_name="Year",
        value_name="Value_kt",
    )
    plot_data[config["value_column"]] = plot_data["Value_kt"] / 1000

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
            y=config["value_column"],
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


def main():
    for config in PLOTS:
        selected_regions = make_figure(config)
        print(f"Saved: {config['png']}")
        print(f"Saved: {config['pdf']}")
        print(f"OMNIA regions included ({config['name']}): {', '.join(selected_regions)}")


if __name__ == "__main__":
    main()
