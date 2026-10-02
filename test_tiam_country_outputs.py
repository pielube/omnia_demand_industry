"""Safety checks for country aggregation and recomputed TIAM growth indices."""

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from create_tiam_country_outputs import build_outputs, read_country_projection
from tiam_projection_utils import (
    TIAM_REGIONS,
    YEARS,
    aggregate_country_projection,
    calculate_growth_rates,
    read_tiam_mapping,
    validate_global_totals,
    validate_mapping,
)


def country_rows(codes, base_values, future_values=None):
    future_values = base_values if future_values is None else future_values
    result = pd.DataFrame({"ISO3": codes})
    for year in YEARS:
        result[year] = base_values if year == "2019" else future_values
    return result


def mapping_rows(codes, regions):
    return pd.DataFrame({"ISO3": codes, "TIAMRegion": regions, "Country": codes})


class TiamProjectionTests(unittest.TestCase):
    def test_map_normalization_and_duplicate_conflicts(self):
        mapping = mapping_rows([" gbr "], [" uk "])
        normalized = validate_mapping(mapping)
        self.assertEqual(normalized.iloc[0]["ISO3"], "GBR")
        self.assertEqual(normalized.iloc[0]["TIAMRegion"], "UK")
        for regions in (["UK", "UK"], ["UK", "WEU"]):
            with self.subTest(regions=regions), self.assertRaisesRegex(ValueError, "duplicate or conflicting"):
                validate_mapping(mapping_rows(["GBR", "GBR"], regions))

    def test_map_invalid_blank_codes_and_unknown_regions(self):
        for codes, regions in [([""], ["UK"]), (["GB"], ["UK"]), (["GBR"], ["XXX"])]:
            with self.subTest(codes=codes, regions=regions), self.assertRaises(ValueError):
                validate_mapping(mapping_rows(codes, regions))

    def test_supplements_cannot_override_supplied_assignments(self):
        base = pd.DataFrame({"Country": ["United Kingdom"], "Code": ["GBR"], "Region": ["UK"]})
        supplement = pd.DataFrame({"Country": ["United Kingdom"], "Code": ["GBR"], "Region": ["WEU"], "Reason": ["Example"]})
        with patch("tiam_projection_utils.pd.read_csv", side_effect=[base, supplement]), patch.object(Path, "exists", return_value=True):
            with self.assertRaisesRegex(ValueError, "duplicate or conflicting"):
                read_tiam_mapping(Path("base.csv"), Path("extra.csv"))

    def test_aggregation_rejects_country_gaps_and_duplicates(self):
        mapping = mapping_rows(["GBR"], ["UK"])
        with self.assertRaisesRegex(ValueError, "missing from TIAM mapping.*FRA"):
            aggregate_country_projection(country_rows(["GBR", "FRA"], [10, 20]), mapping)
        with self.assertRaisesRegex(ValueError, "duplicate ISO3"):
            aggregate_country_projection(country_rows(["GBR", "GBR"], [10, 20]), mapping)

    def test_aggregation_rejects_nonfinite_and_negative_values(self):
        mapping = mapping_rows(["GBR"], ["UK"])
        for invalid in (np.nan, np.inf, -1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                aggregate_country_projection(country_rows(["GBR"], [invalid]), mapping)

    def test_global_volumes_and_weighted_growth_are_preserved(self):
        # Two countries growing by 10x and 2x combine to 2.8x, not their 6x mean.
        source = country_rows(["GBR", "FRA"], [10.0, 90.0], [100.0, 180.0])
        totals = aggregate_country_projection(source, mapping_rows(["GBR", "FRA"], ["WEU", "WEU"]))
        self.assertEqual(totals["TIAMRegion"].tolist(), list(TIAM_REGIONS))
        np.testing.assert_allclose(totals[YEARS].sum(), source[YEARS].sum())
        growth = calculate_growth_rates(totals).set_index("Year")
        self.assertEqual(growth.loc[2019, "WEU"], 1.0)
        self.assertAlmostEqual(growth.loc[2050, "WEU"], 2.8)
        self.assertAlmostEqual(growth.loc[2100, "WEU"], 2.8)
        self.assertTrue(growth["UK"].eq(1.0).all())
        with self.assertRaisesRegex(ValueError, "preserve global totals"):
            validate_global_totals(totals, source.assign(**{"2031": [1.0, 1.0]}))

    def test_zero_base_with_nonzero_intermediate_future_rejected(self):
        source = country_rows(["GBR"], [0.0]).rename(columns={"ISO3": "TIAMRegion"})
        source["TIAMRegion"] = "UK"
        source["2020"] = 1.0
        with self.assertRaisesRegex(ValueError, "zero-base"):
            calculate_growth_rates(source)

    def test_cement_population_excluded_before_aggregation(self):
        source = country_rows(["GBR", "GBR", "MAC"], [10.0, 999.0, 0.0])
        source["Metric"] = ["Cement production", "Population", "Cement production"]
        source["Unit"] = ["kt cement", "thousand persons", "kt cement"]
        source.loc[2, "2019"] = np.nan
        with patch("create_tiam_country_outputs.pd.read_csv", return_value=source.copy()):
            volumes = read_country_projection(Path("cement_country.csv"), "cement")
            totals = aggregate_country_projection(volumes, mapping_rows(["GBR", "MAC"], ["UK", "CHI"]))
            self.assertEqual(volumes.loc[volumes.ISO3.eq("MAC"), "2019"].iloc[0], 0.0)
        source.loc[2, "2030"] = np.nan
        with patch("create_tiam_country_outputs.pd.read_csv", return_value=source.copy()):
            with self.assertRaisesRegex(ValueError, "missing or nonfinite"):
                aggregate_country_projection(
                    read_country_projection(Path("cement_country.csv"), "cement"),
                    mapping_rows(["GBR", "MAC"], ["UK", "CHI"]),
                )
        self.assertEqual(totals["2019"].sum(), 10.0)

    def test_documented_zero_volume_aluminium_aliases_only(self):
        source = country_rows(["GUY", "GUY", "LIE", "LIE"], [0.0] * 4)
        source["OMNIARegion"] = ["LAM", "LAM", "ENW", "ENW"]
        with patch("create_tiam_country_outputs.pd.read_csv", return_value=source.copy()):
            consolidated = read_country_projection(Path("aluminium_country.csv"), "aluminium")
            self.assertEqual(consolidated["ISO3"].tolist(), ["GUY", "LIE"])
        source.loc[0, "2041"] = 1.0
        with patch("create_tiam_country_outputs.pd.read_csv", return_value=source.copy()):
            with self.assertRaisesRegex(ValueError, "zero annual volumes"):
                read_country_projection(Path("aluminium_country.csv"), "aluminium")
        source["2041"] = 0.0
        source["ISO3"] = "GBR"
        with patch("create_tiam_country_outputs.pd.read_csv", return_value=source.copy()):
            with self.assertRaisesRegex(ValueError, "Unexpected duplicate"):
                read_country_projection(Path("aluminium_country.csv"), "aluminium")

    def test_current_repository_has_exactly_26_complete_counterparts(self):
        # Build in memory: validates every country and annual source/global total.
        outputs = build_outputs(read_tiam_mapping())
        self.assertEqual(len(outputs), 26)
        for path, frame in outputs.items():
            with self.subTest(path=path):
                self.assertIn("tiam", path.name)
                self.assertEqual(len(frame), 13 if "growth_rates" in path.name else 16)


if __name__ == "__main__":
    unittest.main()
