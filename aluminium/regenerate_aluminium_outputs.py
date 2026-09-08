"""Rebuild allocation maps, all aluminium scenarios, and comparison figures."""

from pathlib import Path

from create_aluminium_scenario_outputs import SCENARIOS
from create_primary_country_projection_bgs_aligned import run_workflow as run_primary
from create_primary_producer_zijie_map import main as rebuild_primary_map
from create_secondary_producer_zijie_map import main as rebuild_secondary_map
from create_secondary_scrap_2025_aligned_projections import run_workflow as run_secondary_scrap
from plot_omnia_old_vs_new import METRICS, plot_metric


BASE_DIR = Path(__file__).resolve().parent


def main():
    rebuild_primary_map()
    rebuild_secondary_map()
    for sheet, directory in {"baseline": "baseline", **SCENARIOS}.items():
        output_dir = BASE_DIR / "outputs" / directory
        # Build totals only once both component files use the current mapping.
        run_primary(sheet, output_dir, write_totals=False)
        run_secondary_scrap(sheet, output_dir)

    for metric, title in METRICS.items():
        print(f"Saved: {plot_metric(metric, title)}")

    region_archive = BASE_DIR / "ARCHIVED_outputs_skt_taiwan" / "baseline"
    if region_archive.is_dir():
        for metric, title in {
            **METRICS,
            "total": "Total aluminium production",
        }.items():
            output_path = plot_metric(
                metric,
                title,
                old_baseline_dir=region_archive,
                comparison_name="skt_taiwan_vs_corrected",
                old_label="Taiwan in SKT",
                new_label="Taiwan in CHN",
            )
            print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
