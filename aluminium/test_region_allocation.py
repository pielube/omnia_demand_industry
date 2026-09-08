"""Check that region corrections preserve the INF country allocations."""

import unittest
from unittest.mock import patch

import pandas as pd

import create_secondary_producer_zijie_map as secondary


class RegionAllocationTests(unittest.TestCase):
    def test_taiwan_is_transferred_after_source_totals_are_allocated(self):
        mapping = pd.DataFrame(
            [
                ["China", "CHN", "CN", "CHN", "China"],
                ["Taiwan, Province of China", "CHN", "TW", "TWN", "Other Asia"],
                ["Republic of Korea", "SKT", "KR", "KOR", "Other Asia"],
            ],
            columns=["country_OMNIA", "region", "ISO2", "ISO3", "ZijieRegion"],
        )
        source_records = pd.DataFrame(
            [
                ["China", "China", "CHN", 10610.0, "test observation"],
                ["Taiwan", "Taiwan, Province of China", "SKT", 300.0, "test observation"],
                ["South Korea", "Republic of Korea", "SKT", 1700.0, "test observation"],
            ],
            columns=[
                "Country_INF_Data", "CountryForMatch", "OMNIARegion_INF_Data",
                "SecondaryAllocationWeight", "SourceDetail",
            ],
        )
        source_totals = pd.DataFrame(
            [["CHN", 10610.0], ["SKT", 2000.0]],
            columns=["OMNIARegion", "OMNIARegionTotal2019_kt"],
        )
        empty_primary = pd.DataFrame(columns=["ISO3", "OMNIARegion"])
        with (
            patch.object(secondary, "read_omnia_region_totals", return_value=source_totals),
            patch.object(secondary, "read_secondary_records", return_value=source_records),
            patch.object(secondary, "make_primary_fallback_weights", return_value=empty_primary),
        ):
            corrected = secondary.build_producer_map(None, mapping).set_index("ISO3")

        self.assertEqual(corrected.loc["TWN", "SecondaryProduction2019_kt"], 300.0)
        self.assertEqual(corrected.loc["KOR", "SecondaryProduction2019_kt"], 1700.0)
        self.assertEqual(corrected.loc["CHN", "SecondaryProduction2019_kt"], 10610.0)
        self.assertEqual(corrected.loc["TWN", "SourceOMNIARegion"], "SKT")
        self.assertEqual(corrected.loc["TWN", "OMNIARegion"], "CHN")
        self.assertEqual(corrected.loc["TWN", "OMNIARegionTotal2019_kt"], 10910.0)
        self.assertEqual(corrected.loc["KOR", "OMNIARegionTotal2019_kt"], 1700.0)
        self.assertEqual(corrected["SecondaryProduction2019_kt"].sum(), 12610.0)
        self.assertEqual(mapping.set_index("ISO3").at["TWN", "region"], "CHN")
        self.assertAlmostEqual(
            corrected.loc["TWN", "OMNIARegionShare"], 300.0 / 10910.0
        )


if __name__ == "__main__":
    unittest.main()
