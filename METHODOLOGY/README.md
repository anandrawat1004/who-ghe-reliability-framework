# Methodology — Audit pipeline definitions

This folder contains the locked definitions for the forensic audit of WHO mortality estimates (Rawat 2026).

## Documents (use in this order)

1. **01_ICD10_cause_groupings.md** — Cause-of-death groupings: all-cause (Tier 1), top causes (Tier 2), contentious causes (Tier 3). Aligned with WHO Mortality Database List 101 and WHO GHE.
2. **02_Stage0_inclusion_exclusion_rules.md** — Audit universe: countries, time window (2000–2021), inclusion/exclusion rules. Includes **publication-ready Methods text** for the report.
3. **03_join_schema_reported_vs_estimated.md** — Table layouts and join strategy for WHO Mortality Database (reported) and WHO Global Health Estimates (estimated). Keys, cause mapping, and data flow.

## Quick reference

- **Cause coding:** ICD-10 only, List = 101. All-cause = List 101 total-cause code (confirm from Documentation Annex; commonly 1000).
- **Audit window:** 2000–2021.
- **Join key:** country_code (ISO3) + year + cause_group + sex.
- **Contentious causes:** Malaria, Self-harm (suicide), Maternal, COVID-19, Ill-defined diseases/injuries.

## Data sources

- WHO Mortality Database: https://www.who.int/data/data-collection-tools/who-mortality-database  
- List of causes (ICD-10): https://platform.who.int/mortality/about/list-of-causes-and-corresponding-icd-10-codes  
- WHO Global Health Estimates: https://www.who.int/data/global-health-estimates  
- GHE methods (2000–2021): WHO/DDI/DNA/GHE/2024.2 (cite in report).
