"""Select simple regional trend models and extrapolate WCA consumption to 2100."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib import pyplot as plt

from wca_regional_consumption import read_wca_regional_consumption


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "inputs" / "wca_regional_cement_consumption.csv"
OUTPUT_CSV = BASE_DIR / "outputs" / "wca_regional_cement_consumption_to_2100.csv"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"
FIGURE_STEM = FIGURE_DIR / "wca_market_type_trajectories_to_2100_2x2"

OBSERVED_YEARS = np.array([2020, 2024, 2035, 2050], dtype=float)
OUTPUT_YEARS = np.arange(2020, 2101)
MARKET_ORDER = (
    "Decline then stable",
    "Already stable",
    "Slow growth",
    "Fast growth",
)


@dataclass(frozen=True)
class FittedModel:
    name: str
    parameters: tuple[float, ...]
    predict: Callable[[np.ndarray], np.ndarray]

    @property
    def equation(self) -> str:
        if self.name == "constant":
            return f"y = {self.parameters[0]:.6g}"
        intercept, slope = self.parameters
        if self.name == "linear":
            return f"y = {intercept:.6g} + ({slope:.6g})*t"
        if self.name == "exponential":
            return f"y = {intercept:.6g}*exp(({slope:.6g})*t)"
        if self.name == "logarithmic":
            return f"y = {intercept:.6g} + ({slope:.6g})*ln(1+t)"
        raise ValueError(f"Unknown model: {self.name}")


def fit_model(name: str, years: np.ndarray, values: np.ndarray) -> FittedModel:
    """Fit a candidate model, using t = year - 2020 for readable equations."""
    t = np.asarray(years, dtype=float) - 2020.0
    values = np.asarray(values, dtype=float)

    if name == "constant":
        mean = float(values.mean())
        return FittedModel(
            name,
            (mean,),
            lambda year: np.full(np.asarray(year).shape, mean, dtype=float),
        )

    if name == "linear":
        slope, intercept = np.polyfit(t, values, 1)
        return FittedModel(
            name,
            (float(intercept), float(slope)),
            lambda year: intercept + slope * (np.asarray(year, dtype=float) - 2020.0),
        )

    if name == "exponential":
        if np.any(values <= 0):
            raise ValueError("Exponential fitting requires positive observations")
        growth, log_scale = np.polyfit(t, np.log(values), 1)
        scale = float(np.exp(log_scale))
        return FittedModel(
            name,
            (scale, float(growth)),
            lambda year: scale
            * np.exp(growth * (np.asarray(year, dtype=float) - 2020.0)),
        )

    if name == "logarithmic":
        slope, intercept = np.polyfit(np.log1p(t), values, 1)
        return FittedModel(
            name,
            (float(intercept), float(slope)),
            lambda year: intercept
            + slope * np.log1p(np.asarray(year, dtype=float) - 2020.0),
        )

    raise ValueError(f"Unknown model: {name}")


def leave_one_out_rmse(name: str, years: np.ndarray, values: np.ndarray) -> float:
    """Measure out-of-sample error across the four source observations."""
    squared_errors = []
    for held_out in range(len(years)):
        keep = np.arange(len(years)) != held_out
        model = fit_model(name, years[keep], values[keep])
        prediction = float(model.predict(np.array([years[held_out]]))[0])
        squared_errors.append((prediction - values[held_out]) ** 2)
    return float(np.sqrt(np.mean(squared_errors)))


def select_model(years: np.ndarray, values: np.ndarray) -> tuple[FittedModel, float]:
    """Select the candidate with the lowest leave-one-out RMSE."""
    candidates = ("constant", "linear", "exponential", "logarithmic")
    scores = {
        name: leave_one_out_rmse(name, years, values) for name in candidates
    }
    selected_name = min(scores, key=scores.get)
    return fit_model(selected_name, years, values), scores[selected_name]


def build_extrapolations(
    source_rows: list[dict[str, str | float]],
) -> list[dict[str, object]]:
    results = []
    for row in source_rows:
        observed = np.array(
            [row[f"Consumption {int(year)} (Mtpa)"] for year in OBSERVED_YEARS],
            dtype=float,
        )
        model, score = select_model(OBSERVED_YEARS, observed)
        fitted = np.maximum(model.predict(OUTPUT_YEARS), 0.0)

        result: dict[str, object] = {
            "Market type": row["Market type"],
            "Region": row["Region"],
            "Fit function": model.name,
            "Fit equation (t = year - 2020)": model.equation,
            "LOOCV RMSE (Mtpa)": round(score, 6),
        }
        result.update(
            {
                f"Observed consumption {int(year)} (Mtpa)": value
                for year, value in zip(OBSERVED_YEARS, observed)
            }
        )
        result.update(
            {
                f"Fitted consumption {year} (Mtpa)": round(float(value), 6)
                for year, value in zip(OUTPUT_YEARS, fitted)
            }
        )
        results.append(result)
    return results


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Market type",
        "Region",
        "Fit function",
        "Fit equation (t = year - 2020)",
        "LOOCV RMSE (Mtpa)",
        *(f"Observed consumption {int(year)} (Mtpa)" for year in OBSERVED_YEARS),
        *(f"Fitted consumption {year} (Mtpa)" for year in OUTPUT_YEARS),
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_extrapolations(path: Path) -> list[dict[str, str]]:
    """Read the generated CSV so the figure is explicitly based on that output."""
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def plot_extrapolations(rows: list[dict[str, str]]) -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.4), sharex=True, constrained_layout=True)
    colors = plt.get_cmap("tab10").colors

    for ax, market_type in zip(axes.flat, MARKET_ORDER):
        market_rows = [row for row in rows if row["Market type"] == market_type]
        for color, row in zip(colors, market_rows):
            values = np.array(
                [row[f"Fitted consumption {year} (Mtpa)"] for year in OUTPUT_YEARS],
                dtype=float,
            )
            ax.plot(
                OUTPUT_YEARS,
                values,
                color=color,
                linewidth=1.8,
                label=f"{row['Region']} ({row['Fit function']})",
            )
            anchor_values = np.array(
                [row[f"Observed consumption {int(year)} (Mtpa)"] for year in OBSERVED_YEARS],
                dtype=float,
            )
            ax.scatter(
                OBSERVED_YEARS,
                anchor_values,
                color=color,
                edgecolor="white",
                linewidth=0.35,
                s=18,
                zorder=3,
            )

        ax.set_title(market_type, loc="left", fontweight="bold")
        ax.set_xlim(2020, 2100)
        ax.set_xticks([2020, 2040, 2060, 2080, 2100])
        ax.grid(axis="y", color="0.88", linewidth=0.7)
        ax.margins(y=0.1)
        ax.legend(frameon=False, loc="best")

    fig.supxlabel("Year")
    fig.supylabel("Fitted cement consumption (Mtpa)")
    fig.suptitle(
        "Regional cement consumption extrapolations to 2100",
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.002,
        "Lines: fitted models; markers: source observations. Selected by lowest leave-one-out RMSE; t = year - 2020.",
        ha="center",
        fontsize=7.5,
        color="0.35",
    )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_STEM.with_suffix(".png"), bbox_inches="tight")
    fig.savefig(FIGURE_STEM.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    source_rows = read_wca_regional_consumption(INPUT_CSV)
    extrapolations = build_extrapolations(source_rows)
    write_csv(extrapolations, OUTPUT_CSV)
    plot_extrapolations(read_extrapolations(OUTPUT_CSV))

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Saved: {FIGURE_STEM.with_suffix('.png')}")
    print(f"Saved: {FIGURE_STEM.with_suffix('.pdf')}")
    print("Selected functions:")
    for row in extrapolations:
        print(f"  {row['Region']}: {row['Fit function']}")


if __name__ == "__main__":
    main()
