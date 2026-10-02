# Shared regional mappings

`tiam_country_countrycode_region.csv` is the country-to-TIAM map supplied for the additional aluminium, cement, and steel outputs. It retains the supplied columns and all 202 country rows. The mapping has 16 regions, unique country codes, and no blank country codes or region assignments. Aggregation uses the `Code` and `Region` columns; the descriptive and auxiliary columns do not control allocation.

The following five geographic corrections were approved and applied to the supplied map:

| Country | Code | Supplied region | Corrected region |
| --- | --- | --- | --- |
| Tanzania | TZA | ODA | AFR |
| Mauritius | MUS | CSA | AFR |
| Fiji | FJI | CSA | ODA |
| Samoa | WSM | AFR | ODA |
| Brunei Darussalam | BRN | MEA | ODA |

`tiam_country_region_supplements.csv` covers the 30 additional country or territory codes present in current aluminium and cement sources but omitted from the supplied map. Each row records its assignment and rationale. These supplements add coverage without replacing supplied assignments. In particular, Saint Pierre and Miquelon (`SPM`) uses the geographical Americas convention and is assigned to `CSA`; Greenland (`GRL`) uses the Danish-territory convention and is assigned to `WEU`. These are documented allocation conventions rather than rows supplied in the original map.

Together, the corrected supplied map and supplements cover every country code in the current aluminium and cement country CSVs. Country names may differ between sources, so joins use codes. `ANT` is retained as the supplied legacy Netherlands Antilles code; the supplements separately cover its successor country or territory codes `CUW`, `BES`, and `SXM`.

The same mapping also covers all 176 countries in the steel workbook and all
countries in the reviewed World Steel source maps. No further steel-specific
geography overrides are needed. The TIAM steel workflow regroups country
volumes before calculating regional production growth or World Steel indices.

`OMNIA_region_mapping_241120.csv` remains the separate mapping for OMNIA outputs. It contains repeated entries for `GUY` and `LIE`; these are not duplicate entries in the TIAM mapping. TIAM outputs must be aggregated from country data because several OMNIA regions span multiple TIAM regions.

The aluminium country outputs also contain the resulting repeated `GUY` and
`LIE` rows. TIAM generation consolidates these known aliases only when every
2019-2050 value is zero and their OMNIA assignments agree. Unexpected duplicate
codes or nonzero duplicate rows stop generation for review. This consolidation
preserves all annual volumes and does not change the source country files.

Cement history contains blank production values for Macao (`MAC`, 2019-2024)
and Sudan (`SDN`, 2020-2024). The existing OMNIA aggregation excludes these
missing observations from regional sums. TIAM generation follows that same
policy by using zero contributions for these specific blanks during
aggregation; it does not estimate the missing production or edit country
history. Unexpected missing observations stop generation for review.
