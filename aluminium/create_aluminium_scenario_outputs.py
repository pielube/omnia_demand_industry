from pathlib import Path

from create_primary_country_projection_bgs_aligned import (
    run_workflow as run_primary_workflow,
)
from create_secondary_scrap_2025_aligned_projections import (
    run_workflow as run_secondary_scrap_workflow,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"

SCENARIOS = {
    "recycling rate scenario": "recycling_rate_scenario",
    "lifetime scenario": "lifetime_scenario",
}


def main():
    for scenario_sheet, directory_name in SCENARIOS.items():
        output_dir = OUTPUTS_DIR / directory_name
        print(f"\nBuilding aluminium scenario: {scenario_sheet}")
        run_primary_workflow(
            scenario_sheet=scenario_sheet,
            output_dir=output_dir,
        )
        run_secondary_scrap_workflow(
            scenario_sheet=scenario_sheet,
            output_dir=output_dir,
        )


if __name__ == "__main__":
    main()
