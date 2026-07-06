from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"

INPUT_PATH = OUTPUTS_DIR / "aluminium_scrap_country_projection_2019_2050.csv"
OUTPUT_DIR = OUTPUTS_DIR / "figures"
OUTPUT_PNG = OUTPUT_DIR / "aluminium_scrap_top9_2019_3x3.png"
OUTPUT_PDF = OUTPUT_DIR / "aluminium_scrap_top9_2019_3x3.pdf"

RANK_YEAR = 2019
START_YEAR = 2019
END_YEAR = 2050
COUNTRY_COUNT = 9


def read_projection():
    output = pd.read_csv(INPUT_PATH)
    output.columns = [int(col) if str(col).isdigit() else col for col in output.columns]
    return output


def make_figure():
    output = read_projection()
    years = [col for col in output.columns if isinstance(col, int) and START_YEAR <= col <= END_YEAR]
    selected = (
        output
        .sort_values(RANK_YEAR, ascending=False)
        .head(COUNTRY_COUNT)
        [["Country", "ISO3", "ZijieRegion"]]
        .reset_index(drop=True)
    )
    selected_iso3 = selected["ISO3"].tolist()

    plot_data = output[output["ISO3"].isin(selected_iso3)].copy()
    plot_data = plot_data.melt(
        id_vars=["Country", "ISO3", "ZijieRegion"],
        value_vars=years,
        var_name="Year",
        value_name="Scrap_kt",
    )
    plot_data["Scrap_Mt"] = plot_data["Scrap_kt"] / 1000

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

    for ax, row in zip(axes, selected.itertuples(index=False)):
        country_data = plot_data[plot_data["ISO3"].eq(row.ISO3)]
        sns.lineplot(
            data=country_data,
            x="Year",
            y="Scrap_Mt",
            color="#009E73",
            linewidth=1.55,
            estimator=None,
            errorbar=None,
            ax=ax,
        )
        ax.set_title(f"{row.Country} ({row.ISO3})", loc="left", pad=3)
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
    fig.supylabel("Aluminium scrap (Mt)", fontsize=8)
    fig.suptitle(
        "Aluminium scrap projections for the nine largest 2019 countries",
        x=0.01,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)

    return selected


if __name__ == "__main__":
    countries = make_figure()
    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_PDF}")
    print("Countries included:")
    for row in countries.itertuples(index=False):
        print(f"  {row.Country} ({row.ISO3})")
