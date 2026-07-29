from pathlib import Path

from plot_primary_bgs_alignment_top9 import make_figure


BASE_DIR = Path(__file__).resolve().parent
FIGURES_DIR = BASE_DIR / "outputs" / "figures"

OUTPUT_PNG = FIGURES_DIR / "aluminium_primary_bgs_alignment_top27_2024_9x3.png"
OUTPUT_PDF = FIGURES_DIR / "aluminium_primary_bgs_alignment_top27_2024_9x3.pdf"


if __name__ == "__main__":
    countries = make_figure(
        country_count=27,
        nrows=9,
        ncols=3,
        figsize=(7.2, 18.0),
        output_png=OUTPUT_PNG,
        output_pdf=OUTPUT_PDF,
        top=0.945,
        bottom=0.03,
        hspace=0.30,
        legend_y=0.968,
        title_y=0.995,
    )
    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_PDF}")
    print("Countries included:")
    for row in countries.itertuples(index=False):
        print(f"  {row.Country} ({row.ISO3})")
