"""Plot current versus archived CHN/SKT projections, 2019-2050."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "comparison_figures"
YEARS = list(range(2019, 2051))
YEAR_COLUMNS = [str(year) for year in YEARS]
SERIES = [
    ("aluminium_primary", "Primary aluminium production", "aluminium", "baseline/aluminium_primary_omnia.csv"),
    ("aluminium_secondary", "Secondary aluminium production", "aluminium", "baseline/aluminium_secondary_omnia.csv"),
    ("aluminium_scrap", "Aluminium scrap", "aluminium", "baseline/aluminium_scrap_omnia.csv"),
    ("cement", "Cement production / demand", "cement", "cement_omnia.csv"),
    ("steel_production", "Steel production — OMNIA-2019-anchored WSA index", "steel", "steel_production_omnia_2019_anchored_worldsteel_indexed.csv"),
    ("steel_scrap", "Steel scrap", "steel", "steel_scrap_omnia.csv"),
]


def read_projection(path):
    data = pd.read_csv(path).set_index("OMNIARegion")
    if not data.index.is_unique:
        raise ValueError(f"Duplicate OMNIA regions: {path}")
    values = data.loc[["CHN", "SKT"], YEAR_COLUMNS].astype(float) / 1000.0
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(f"Non-finite projection values: {path}")
    return values


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    pdf_path = OUTPUT_DIR / "chn_skt_old_vs_new.pdf"
    with PdfPages(pdf_path) as pdf:
        for name, title, sector, filename in SERIES:
            old = read_projection(ROOT / sector / "outputs_skt_taiwan" / filename)
            new = read_projection(ROOT / sector / "outputs" / filename)
            fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
            fig.suptitle(title, fontsize=14)
            for ax, region in zip(axes, ["CHN", "SKT"]):
                # Draw the dashed archive last so coincident series remain visible.
                new_line, = ax.plot(YEARS, new.loc[region], color="#0072B2", linewidth=2.2, label="New")
                old_line, = ax.plot(YEARS, old.loc[region], color="#D55E00", linewidth=1.8, linestyle="--", label="Old")
                ax.set_title(region, fontsize=12)
                ax.set_xlabel("Year")
                ax.set_ylabel("Mt / year")
                ax.set_xlim(2019, 2050)
                ax.set_xticks([2019, 2025, 2030, 2040, 2050])
                ax.yaxis.set_major_locator(MaxNLocator(5))
                ax.yaxis.set_major_formatter(
                    FuncFormatter(lambda value, _: f"{value:,.3f}".rstrip("0").rstrip("."))
                )
                if (old.loc[region].eq(0) & new.loc[region].eq(0)).all():
                    ax.set_ylim(-0.01, 0.01)
                    ax.set_yticks([0])
                ax.spines[["top", "right"]].set_visible(False)
                ax.grid(axis="y", color="#e6e6e6", linewidth=0.6)
                ax.legend(handles=[old_line, new_line], frameon=False)
            png_path = OUTPUT_DIR / f"{name}_chn_skt_old_vs_new.png"
            fig.savefig(png_path, dpi=180)
            pdf.savefig(fig)
            plt.close(fig)
            print(f"Saved: {png_path}")
    print(f"Saved: {pdf_path}")


if __name__ == "__main__":
    main()
