"""Focused numerical tests for the steel workbook methodology."""

import unittest

import numpy as np
import pandas as pd

from steel.tiam_steel_projection_utils import YEARS, calculate_regional_model


def fixture_inputs():
    countries = {}
    for metric, bases in {"demand": [100.0, 100.0, 800.0], "population": [100.0] * 3, "scrap": [20.0, 20.0, 80.0]}.items():
        frame = pd.DataFrame({"ISO3": ["AAA", "BBB", "CHN"]})
        for year in YEARS:
            scale = 1.0 + (int(year) - 2019) / 31.0 if metric != "population" else 1.0
            frame[year] = np.array(bases) * scale
        countries[metric] = frame
    mapping = pd.DataFrame({"ISO3": ["AAA", "BBB", "CHN"], "TIAMRegion": ["OTH", "OTH", "CHI"]})
    calibration = pd.DataFrame({"TIAMRegion": ["OTH", "CHI"], "Calibration2019_kt": [400.0, 1600.0]})
    adjustments = pd.DataFrame({"TIAMRegion": ["OTH", "CHI"], "AdjustmentFactor": [1.1, 1.0]})
    return countries, mapping, calibration, adjustments


class SteelWorkbookMethodTests(unittest.TestCase):
    def test_calibration_normalization_constant_adjusted_growth_and_china_residual(self):
        countries, mapping, calibration, adjustments = fixture_inputs()
        result = calculate_regional_model(countries, mapping, calibration, adjustments)
        production = result["production"].set_index("TIAMRegion")
        parameters = result["parameters"].set_index("TIAMRegion")
        # Raw 400 kt is a 20% share, normalized to 1000 kt global 2019 demand.
        self.assertEqual(production.at["OTH", "2019"], 200.0)
        self.assertEqual(production.at["CHI", "2019"], 800.0)
        self.assertEqual(result["per_capita"].set_index("TIAMRegion").at["OTH", "2019"], 1000.0)
        expected_growth = (2.0 ** (1.0 / 31.0) - 1.0) * 1.1
        self.assertAlmostEqual(parameters.at["OTH", "AppliedProductionCAGR"], expected_growth)
        for year in YEARS[1:]:
            self.assertAlmostEqual(production.at["OTH", year] / production.at["OTH", str(int(year) - 1)], 1.0 + expected_growth)
        # China balances demand every year, instead of using its own CAGR.
        demand = result["demand"].set_index("TIAMRegion")
        np.testing.assert_allclose(production.sum(), demand.sum(), rtol=1e-13)
        self.assertNotAlmostEqual(production.at["CHI", "2050"] / production.at["CHI", "2019"], 2.0)
        np.testing.assert_allclose(result["scrap"][YEARS].sum(), countries["scrap"][YEARS].sum())

    def test_unmapped_duplicate_and_missing_country_series_rejected(self):
        countries, mapping, calibration, adjustments = fixture_inputs()
        with self.assertRaisesRegex(ValueError, "Unmapped"):
            calculate_regional_model(countries, mapping.iloc[:-1], calibration, adjustments)
        with self.assertRaisesRegex(ValueError, "duplicate ISO3"):
            calculate_regional_model(countries, pd.concat([mapping, mapping.iloc[:1]]), calibration, adjustments)
        countries["demand"].loc[0, "2032"] = np.nan
        with self.assertRaisesRegex(ValueError, "missing or nonfinite"):
            calculate_regional_model(countries, mapping, calibration, adjustments)

    def test_population_gaps_and_negative_residual_rejected(self):
        countries, mapping, calibration, adjustments = fixture_inputs()
        countries["population"].loc[2, "2040"] = 0.0
        with self.assertRaisesRegex(ValueError, "positive annual population"):
            calculate_regional_model(countries, mapping, calibration, adjustments)
        countries, mapping, calibration, adjustments = fixture_inputs()
        adjustments.loc[0, "AdjustmentFactor"] = 50.0
        with self.assertRaisesRegex(ValueError, "negative values"):
            calculate_regional_model(countries, mapping, calibration, adjustments)

    def test_cagr_endpoint_and_adjustment_coverage_required(self):
        countries, mapping, calibration, adjustments = fixture_inputs()
        with self.assertRaisesRegex(ValueError, "2050 CAGR endpoint"):
            calculate_regional_model(countries, mapping, calibration, adjustments, end_year=2049)
        with self.assertRaisesRegex(ValueError, "Adjustment regions differ"):
            calculate_regional_model(countries, mapping, calibration, adjustments.iloc[:1])


if __name__ == "__main__":
    unittest.main()
