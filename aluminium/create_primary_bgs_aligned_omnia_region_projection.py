from pathlib import Path

from create_primary_omnia_region_projection import generate_outputs


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"

INPUT_CSV = (
    OUTPUTS_DIR / "aluminium_primary_country_projection_bgs_aligned_2019_2050.csv"
)
TOTALS_CSV = (
    OUTPUTS_DIR
    / "aluminium_primary_bgs_aligned_omnia_region_projection_2019_2050.csv"
)
GROWTH_CSV = (
    OUTPUTS_DIR / "aluminium_primary_bgs_aligned_omnia_region_growth_2019_2050.csv"
)


def main():
    generate_outputs(INPUT_CSV, TOTALS_CSV, GROWTH_CSV)


if __name__ == "__main__":
    main()
