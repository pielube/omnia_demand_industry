# CHN and SKT projection comparisons

`chn_skt_old_vs_new.pdf` contains six pages, one per metric, with CHN and SKT
side by side. Individual figures are also available as PNGs. Each panel shows
only the old and new annual series in Mt, covering 2019-2050.

- Old: each sector's `ARCHIVED_outputs_skt_taiwan/` archive (Taiwan in SKT).
- New: each sector's `outputs/` directory (Taiwan in CHN).
- Aluminium: baseline primary, secondary, and scrap projections.
- Cement: production, which equals demand in this workflow.
- Steel production: `steel_production_omnia_2019_anchored_worldsteel_indexed.csv`
  from each directory. Both curves use the OMNIA-2019-anchored World Steel
  index method: old includes Taiwan in SKT, and new includes Taiwan in CHN.
  Both retain exactly the same original OMNIA 2019 regional anchors. The new
  WSA membership applies to the 2019 denominator and the 2020-2025 observations;
  subsequent production follows the updated workbook's OMNIA growth from the
  new 2025 level. The archived curve retains the old workbook's growth path.
  Production is total crude steel; the repository does not provide a separate
  primary-only projection.
- Steel scrap: `steel_scrap_omnia.csv` from each directory. The new series is
  extracted from the updated workbook and transfers Taiwan's scrap from SKT
  to CHN in every year, including 2019.

Recreate all figures from the repository root:

```text
python plot_chn_skt_comparison.py
```

Identical curves overlap; old is dashed and new is solid so both remain visible.
