import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
NEW_BASELINE_DIR = BASE_DIR / "outputs" / "baseline"
OLD_BASELINE_DIR = BASE_DIR / "ARCHIVED_outputs_old" / "baseline"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"

FIRST_YEAR = 2019
LAST_YEAR = 2050
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
YEAR_COLUMNS = [str(year) for year in YEARS]
NROWS = 7
NCOLS = 4

METRICS = {
    "primary": "Primary aluminium production",
    "secondary": "Secondary aluminium production",
    "scrap": "Aluminium scrap",
}


def read_omnia_projection(path):
    projection = pd.read_csv(path)
    required = {"OMNIARegion", *YEAR_COLUMNS}
    missing = required - set(projection.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    if projection["OMNIARegion"].duplicated().any():
        duplicates = projection.loc[
            projection["OMNIARegion"].duplicated(keep=False),
            "OMNIARegion",
        ].tolist()
        raise ValueError(f"{path} contains duplicate regions: {duplicates}")

    projection[YEAR_COLUMNS] = projection[YEAR_COLUMNS].apply(
        pd.to_numeric,
        errors="raise",
    )
    if not np.isfinite(projection[YEAR_COLUMNS].to_numpy()).all():
        raise ValueError(f"{path} contains non-finite projection values.")
    return projection.set_index("OMNIARegion")


def validate_pair(old, new, metric):
    old_regions = old.index.tolist()
    new_regions = new.index.tolist()
    if set(old_regions) != set(new_regions):
        raise ValueError(
            f"{metric}: old and new files contain different OMNIA regions."
        )
    if len(new_regions) != NROWS * NCOLS:
        raise ValueError(
            f"{metric}: expected {NROWS * NCOLS} OMNIA regions, "
            f"found {len(new_regions)}."
        )
    return new_regions


def plot_metric(
    metric,
    title,
    output_dir=FIGURES_DIR,
    output_format="pdf",
    old_baseline_dir=OLD_BASELINE_DIR,
    new_baseline_dir=NEW_BASELINE_DIR,
    comparison_name="old_vs_new",
    old_label="Old baseline",
    new_label="New baseline",
):
    if output_format not in {"pdf", "png"}:
        raise ValueError(f"Unsupported output format: {output_format}")
    filename = f"aluminium_{metric}_omnia.csv"
    old = read_omnia_projection(Path(old_baseline_dir) / filename)
    new = read_omnia_projection(Path(new_baseline_dir) / filename)
    regions = validate_pair(old, new, metric)

    figure, axes = plt.subplots(
        NROWS,
        NCOLS,
        figsize=(16, 21),
        sharex=True,
        constrained_layout=False,
    )

    new_line = None
    old_line = None
    for axis, region in zip(axes.flat, regions):
        new_values = new.loc[region, YEAR_COLUMNS].to_numpy(dtype=float)
        old_values = old.loc[region, YEAR_COLUMNS].to_numpy(dtype=float)

        new_line, = axis.plot(
            YEARS,
            new_values,
            color="#0072B2",
            linewidth=2.0,
            label=new_label,
            zorder=2,
        )
        old_line, = axis.plot(
            YEARS,
            old_values,
            color="#D55E00",
            linewidth=1.8,
            linestyle="--",
            label=old_label,
            zorder=3,
        )

        axis.set_title(region, fontsize=11, fontweight="bold")
        axis.set_xlim(FIRST_YEAR, LAST_YEAR)
        axis.set_xticks([2019, 2030, 2040, 2050])
        if np.allclose(new_values, 0) and np.allclose(old_values, 0):
            axis.set_ylim(-0.05, 0.05)
            axis.set_yticks([0])
        else:
            axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        axis.grid(color="#d9d9d9", linewidth=0.6, alpha=0.8)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.tick_params(labelsize=8)

    figure.suptitle(
        f"{title}: {new_label} versus {old_label} by OMNIA region",
        fontsize=17,
        fontweight="bold",
        y=0.995,
    )
    figure.legend(
        handles=[new_line, old_line],
        labels=[new_label, old_label],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.958),
        ncol=2,
        frameon=False,
        fontsize=11,
    )
    figure.supxlabel("Year", fontsize=12, y=0.012)
    figure.supylabel("Production (kt)", fontsize=12, x=0.008)
    figure.subplots_adjust(
        left=0.06,
        right=0.985,
        bottom=0.045,
        top=0.895,
        hspace=0.48,
        wspace=0.25,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir
        / (
            f"aluminium_{metric}_omnia_{comparison_name}_2019_2050_7x4."
            f"{output_format}"
        )
    )
    figure.savefig(output_path, bbox_inches="tight", dpi=160)
    plt.close(figure)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Compare aluminium OMNIA baselines.")
    parser.add_argument("--old-baseline-dir", type=Path, default=OLD_BASELINE_DIR)
    parser.add_argument("--new-baseline-dir", type=Path, default=NEW_BASELINE_DIR)
    parser.add_argument("--output-dir", type=Path, default=FIGURES_DIR)
    parser.add_argument("--comparison-name", default="old_vs_new")
    parser.add_argument("--old-label", default="Old baseline")
    parser.add_argument("--new-label", default="New baseline")
    parser.add_argument("--include-total", action="store_true")
    args = parser.parse_args()
    metrics = dict(METRICS)
    if args.include_total:
        metrics["total"] = "Total aluminium production"
    for metric, title in metrics.items():
        output_path = plot_metric(
            metric,
            title,
            output_dir=args.output_dir,
            old_baseline_dir=args.old_baseline_dir,
            new_baseline_dir=args.new_baseline_dir,
            comparison_name=args.comparison_name,
            old_label=args.old_label,
            new_label=args.new_label,
        )
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
