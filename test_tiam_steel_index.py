"""Verify World Steel country regrouping and TIAM indexing math."""

import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from steel.rebase_steel_production_tiam_2019_worldsteel_indexed import (
    apply_tiam_index,
    build_outputs,
    make_tiam_observations,
    remap_country_regions,
)
from tiam_projection_utils import TIAM_REGIONS, YEARS


def synthetic_observations():
    mapping = pd.DataFrame({"ISO3": ["GBR", "FRA"], "Country": ["UK", "France"], "TIAMRegion": ["WEU", "WEU"]})
    source_map = pd.DataFrame({"ISO3": ["GBR", "FRA"], "SourceCountry": ["UK", "France"], "OMNIARegion": ["UKM", "FRN"]})
    historical = pd.DataFrame({
        "SourceCountry": ["UK", "France"], "Production2019_kt": [10.0, 90.0],
        "Production2020_kt": [100.0, 180.0], "Availability2019": ["reported"] * 2,
        "Availability2020": ["reported"] * 2,
    })
    recent = pd.DataFrame({"Country": ["UK", "France"], **{year: [100.0, 180.0] for year in range(2021, 2026)}})
    panel = source_map.merge(historical, on="SourceCountry").rename(columns={"SourceCountry": "SourceCountry2019_2020"})
    for flag in ("CountrySeriesEstimated", "ValueEstimated2019", "ValueEstimated2020"):
        panel[flag] = "no"
    for year in range(2021, 2026):
        panel[year] = [100.0, 180.0]
    return make_tiam_observations(panel, mapping, historical, recent, source_map, source_map)


class TiamSteelIndexTests(unittest.TestCase):
    def test_countries_regroup_before_ratios_are_calculated(self):
        observation = synthetic_observations().iloc[0]
        self.assertEqual(observation["TIAMRegion"], "WEU")
        self.assertEqual(observation["BasketCountryCount"], 2)
        self.assertEqual(observation["WSA2019_kt"], 100.0)
        self.assertEqual(observation["WSA2025_kt"], 280.0)
        # 10x and 2x country indices combine to 2.8x by base-year volume.
        self.assertAlmostEqual(observation["WSAIndex2025"], 2.8)
        self.assertNotEqual(observation["WSAIndex2025"], 6.0)

    def test_2019_fixed_and_future_handoff_retains_original_growth(self):
        original = pd.DataFrame({"TIAMRegion": ["WEU"], **{year: [100.0] for year in YEARS}})
        for year in range(2025, 2051):
            original[str(year)] = 200.0 * 1.1 ** (year - 2025)
        rebased, audit = apply_tiam_index(original, synthetic_observations())
        np.testing.assert_array_equal(rebased["2019"], original["2019"])
        self.assertAlmostEqual(rebased.loc[0, "2025"], 280.0)
        self.assertAlmostEqual(rebased.loc[0, "2026"], 308.0)
        future_years = [str(year) for year in range(2026, 2051)]
        np.testing.assert_allclose(rebased[future_years] / rebased.loc[0, "2025"], original[future_years] / original.loc[0, "2025"])
        self.assertAlmostEqual(audit.loc[0, "HandoffGrowthDifference_pp"], 0.0)
        self.assertIn("TIAM2019", audit.loc[0, "HistoricalFormula"])
        self.assertIn("DerivedTIAM2025_kt", audit.columns)
        self.assertNotIn("OMNIARegion", audit.columns)

    def test_country_mapping_gap_is_rejected_before_aggregation(self):
        source = pd.DataFrame({"ISO3": ["GBR", "FRA"], "OMNIARegion": ["UKM", "FRN"]})
        mapping = pd.DataFrame({"ISO3": ["GBR"], "TIAMRegion": ["UK"]})
        with self.assertRaisesRegex(ValueError, "missing from TIAM mapping.*FRA"):
            remap_country_regions(source, mapping)

    def test_supplied_projection_is_hashed_without_an_existing_baseline(self):
        original = pd.DataFrame({"TIAMRegion": TIAM_REGIONS, **{year: [100.0] * 16 for year in YEARS}})
        expected_hash = hashlib.sha256(original.to_csv(index=False, float_format="%.17g").encode("utf-8")).hexdigest()
        with patch("steel.rebase_steel_production_tiam_2019_worldsteel_indexed.INPUT_PROJECTION_CSV", Path("nonexistent_tiam_baseline.csv")):
            outputs = build_outputs(original=original)
        audit = next(frame for path, frame in outputs.items() if "audit" in path.name)
        self.assertTrue(audit["OriginalProjectionCSV_SHA256"].eq(expected_hash).all())
        self.assertEqual(len(audit), 16)


if __name__ == "__main__":
    unittest.main()
