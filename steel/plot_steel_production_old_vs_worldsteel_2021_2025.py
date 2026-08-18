"""Plot original and 2021-2025 World Steel-rebased steel projections."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import StrMethodFormatter
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

ORIGINAL_CSV = OUTPUTS_DIR / "steel_production_omnia.csv"
REBASED_CSV = (
    OUTPUTS_DIR / "steel_production_omnia_worldsteel_2021_2025_rebased.csv"
)
AUDIT_CSV = (
    OUTPUTS_DIR / "steel_production_worldsteel_2021_2025_rebase_audit.csv"
)
OUTPUT_STEM = (
    FIGURES_DIR
    / "steel_production_omnia_old_vs_worldsteel_2021_2025_rebased_2019_2050"
)

FIRST_YEAR = 2019
LAST_YEAR = 2050
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
YEAR_COLUMNS = [str(year) for year in YEARS]
OBSERVED_YEARS = list(range(2021, 2026))
KT_PER_MT = 1000.0

REGION_LABELS = {
    "AFN": "Northern Africa",
    "ANZ": "Australia and New Zealand",
    "BRA": "Brazil",
    "CAN": "Canada",
    "CHL": "Chile",
    "CHN": "China Mainland",
    "EUE": "Eastern EU",
    "IDN": "Indonesia, Philippines, Viet Nam",
    "IND": "India",
    "JPN": "Japan",
    "MEA": "Middle East",
    "MEX": "Mexico",
    "NIG": "Nigeria",
    "RUS": "Russia",
    "SKT": "South Korea and Taiwan",
    "USA": "United States",
}

ORIGINAL_COLOR = "#6B7280"
REBASED_COLOR = "#0072B2"
OBSERVATION_COLOR = "#D55E00"
INTERPOLATION_COLOR = "#7B2CBF"
OBSERVATION_SPAN_COLOR = "#FDE68A"


def read_projection(path: Path) -> pd.DataFrame:
    """Read and validate one OMNIA production projection."""
    projection = pd.read_csv(path)
    required_columns = ["OMNIARegion", *YEAR_COLUMNS]
    if projection.columns.tolist() != required_columns:
        raise ValueError(
            f"Unexpected columns in {path.name}: {projection.columns.tolist()}"
        )
    if projection["OMNIARegion"].duplicated().any():
        duplicates = projection.loc[
            projection["OMNIARegion"].duplicated(keep=False), "OMNIARegion"
        ].tolist()
        raise ValueError(f"Duplicate regions in {path.name}: {duplicates}")

    projection[YEAR_COLUMNS] = projection[YEAR_COLUMNS].apply(
        pd.to_numeric, errors="raise"
    )
    values = projection[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"Invalid production values in {path.name}")
    return projection.set_index("OMNIARegion")


def read_audit() -> pd.DataFrame:
    """Read the audit table that identifies the rebased regions."""
    audit = pd.read_csv(AUDIT_CSV, keep_default_na=False)
    required = {
        "OMNIARegion",
        "Interpolated2020_kt",
        *{f"Observed{year}_kt" for year in OBSERVED_YEARS},
    }
    missing = required - set(audit.columns)
    if missing:
        raise ValueError(f"Audit file is missing columns: {sorted(missing)}")
    if audit["OMNIARegion"].duplicated().any():
        raise ValueError("Duplicate OMNIA regions in rebase audit")
    return audit.set_index("OMNIARegion")


def validate_inputs(
    original: pd.DataFrame,
    rebased: pd.DataFrame,
    audit: pd.DataFrame,
) -> list[str]:
    """Validate matching projections and return rebased regions by scale."""
    if original.index.tolist() != rebased.index.tolist():
        raise ValueError("Original and rebased OMNIA regions do not match")

    missing_regions = sorted(set(audit.index) - set(original.index))
    if missing_regions:
        raise ValueError(f"Audited regions missing from projections: {missing_regions}")
    if set(audit.index) != set(REGION_LABELS):
        raise ValueError(
            "Plot labels do not match audited regions: "
            f"{sorted(REGION_LABELS)} vs {sorted(audit.index)}"
        )

    numerically_equal = np.isclose(
        original[YEAR_COLUMNS].to_numpy(dtype=float),
        rebased[YEAR_COLUMNS].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-9,
    )
    changed_regions = set(original.index[~numerically_equal.all(axis=1)])
    if changed_regions != set(audit.index):
        raise ValueError(
            "Changed projection regions do not match the rebase audit: "
            f"{sorted(changed_regions)} vs {sorted(audit.index)}"
        )

    return (
        rebased.loc[list(audit.index), "2025"]
        .sort_values(ascending=False)
        .index.tolist()
    )


def plot_comparison(
    original: pd.DataFrame,
    rebased: pd.DataFrame,
    audit: pd.DataFrame,
    regions: list[str],
) -> plt.Figure:
    """Build a four-column comparison for all Excel-rebased regions."""
    columns = 4
    rows = int(np.ceil(len(regions) / columns))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(22, 16),
        sharex=True,
        constrained_layout=False,
    )
    axes = np.atleast_1d(axes).ravel()

    for axis, region in zip(axes, regions):
        original_values = original.loc[region, YEAR_COLUMNS].to_numpy(float) / KT_PER_MT
        rebased_values = rebased.loc[region, YEAR_COLUMNS].to_numpy(float) / KT_PER_MT

        axis.axvspan(
            2021,
            2025,
            color=OBSERVATION_SPAN_COLOR,
            alpha=0.25,
            linewidth=0,
            zorder=0,
        )
        axis.plot(
            YEARS,
            original_values,
            color=ORIGINAL_COLOR,
            linestyle="--",
            linewidth=1.9,
            zorder=2,
        )
        axis.plot(
            YEARS,
            rebased_values,
            color=REBASED_COLOR,
            linewidth=2.2,
            zorder=3,
        )
        axis.scatter(
            OBSERVED_YEARS,
            [rebased_values[year - FIRST_YEAR] for year in OBSERVED_YEARS],
            color=OBSERVATION_COLOR,
            edgecolor="white",
            linewidth=0.6,
            s=27,
            zorder=4,
        )
        axis.scatter(
            [2020],
            [rebased_values[2020 - FIRST_YEAR]],
            marker="D",
            color=INTERPOLATION_COLOR,
            edgecolor="white",
            linewidth=0.6,
            s=35,
            zorder=5,
        )

        axis.set_title(
            f"{region} — {REGION_LABELS[region]}",
            loc="left",
            fontsize=10.5,
            pad=6,
        )
        axis.set_xlim(FIRST_YEAR, LAST_YEAR)
        axis.set_xticks([2019, 2025, 2030, 2040, 2050])
        axis.tick_params(axis="x", labelbottom=True, labelsize=8.5)
        axis.tick_params(axis="y", labelsize=8.5)
        axis.grid(axis="both", color="#D1D5DB", linewidth=0.65, alpha=0.65)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

        low = min(original_values.min(), rebased_values.min())
        high = max(original_values.max(), rebased_values.max())
        padding = max((high - low) * 0.10, high * 0.015, 0.2)
        axis.set_ylim(max(0.0, low - padding), high + padding)
        y_format = "{x:,.1f}" if high < 10 else "{x:,.0f}"
        axis.yaxis.set_major_formatter(StrMethodFormatter(y_format))

    for axis in axes[len(regions) :]:
        axis.set_visible(False)

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=ORIGINAL_COLOR,
            linestyle="--",
            linewidth=1.9,
            label="Original OMNIA projection",
        ),
        Line2D(
            [0],
            [0],
            color=REBASED_COLOR,
            linewidth=2.2,
            label="World Steel-rebased projection",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor=INTERPOLATION_COLOR,
            markeredgecolor="white",
            markersize=6,
            label="Interpolated 2020",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=OBSERVATION_COLOR,
            markeredgecolor="white",
            markersize=6,
            label="Observed 2021–2025",
        ),
    ]

    figure.suptitle(
        "Steel production: original vs 2021–2025 World Steel rebase",
        fontsize=19,
        fontweight="bold",
        y=0.985,
    )
    figure.text(
        0.5,
        0.958,
        "2020 is linearly interpolated; post-2025 projection shapes are preserved",
        ha="center",
        fontsize=11,
        color="#374151",
    )
    figure.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.937),
        ncol=4,
        frameon=False,
        fontsize=10,
    )
    figure.supylabel("Crude steel production (Mt)", x=0.012, fontsize=12)
    figure.supxlabel("Year", y=0.026, fontsize=12)
    figure.text(
        0.5,
        0.009,
        "Source for 2021–2025 observations: World Steel Association export, "
        "last updated 28 July 2026.",
        ha="center",
        fontsize=9,
        color="#4B5563",
    )
    figure.tight_layout(rect=(0.025, 0.045, 0.995, 0.905), h_pad=2.0, w_pad=1.25)
    return figure


def main() -> None:
    original = read_projection(ORIGINAL_CSV)
    rebased = read_projection(REBASED_CSV)
    audit = read_audit()
    regions = validate_inputs(original, rebased, audit)

    figure = plot_comparison(original, rebased, audit, regions)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_STEM.with_suffix(".pdf")
    png_path = OUTPUT_STEM.with_suffix(".png")
    figure.savefig(pdf_path, bbox_inches="tight")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")
    print(f"Regions plotted: {', '.join(regions)}")


if __name__ == "__main__":
    main()
