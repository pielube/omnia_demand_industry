from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"

INPUT_PATH = INPUTS_DIR / "10 regions Al data.xlsx"
OUTPUT_DIR = OUTPUTS_DIR / "figures"
OUTPUT_PNG = OUTPUT_DIR / "zijie_primary_regions_top9_3x3.png"
OUTPUT_PDF = OUTPUT_DIR / "zijie_primary_regions_top9_3x3.pdf"

SCENARIO_SHEET = "baseline"
SCENARIO_LABEL = "Primary Al ingot (kt)"
RANK_YEAR = 2024
START_YEAR = 2024
END_YEAR = 2050
REGION_COUNT = 9


def read_zijie_primary():
    raw = pd.read_excel(INPUT_PATH, sheet_name=SCENARIO_SHEET, header=None)
    matches = raw.iloc[0].eq(SCENARIO_LABEL)
    if matches.sum() != 1:
        raise ValueError(f"Could not find one block labelled {SCENARIO_LABEL!r}.")

    start_col = int(matches[matches].index[0])
    regions = raw.iloc[0, start_col + 1:start_col + 11].tolist()
    data = raw.iloc[1:, start_col:start_col + 11].copy()
    data.columns = ["Year"] + regions
    data = data[data["Year"].between(START_YEAR, END_YEAR)].copy()
    data["Year"] = data["Year"].astype(int)
    return data, regions


def make_figure():
    data, regions = read_zijie_primary()
    top_regions = (
        data.loc[data["Year"].eq(RANK_YEAR), regions]
        .iloc[0]
        .rename("Value_kt")
        .reset_index()
        .rename(columns={"index": "Region"})
        .sort_values("Value_kt", ascending=False)
        .head(REGION_COUNT)["Region"]
        .tolist()
    )

    plot_data = data.melt(
        id_vars="Year",
        value_vars=top_regions,
        var_name="Region",
        value_name="PrimaryProduction_kt",
    )
    plot_data["PrimaryProduction_Mt"] = plot_data["PrimaryProduction_kt"] / 1000

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

    fig, axes = plt.subplots(
        3,
        3,
        figsize=(7.2, 6.7),
        sharex=True,
        constrained_layout=True,
    )
    axes = axes.ravel()

    for ax, region in zip(axes, top_regions):
        region_data = plot_data[plot_data["Region"].eq(region)]
        sns.lineplot(
            data=region_data,
            x="Year",
            y="PrimaryProduction_Mt",
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
        ax.set_xticks([2024, 2030, 2040, 2050])
        ax.margins(x=0)

    fig.supxlabel("Year", fontsize=8)
    fig.supylabel("Primary aluminium ingot production (Mt)", fontsize=8)
    fig.suptitle(
        "Zijie baseline primary aluminium projections by region",
        x=0.01,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)

    return top_regions


if __name__ == "__main__":
    regions = make_figure()
    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_PDF}")
    print("Regions included:")
    for region in regions:
        print(f"  {region}")
