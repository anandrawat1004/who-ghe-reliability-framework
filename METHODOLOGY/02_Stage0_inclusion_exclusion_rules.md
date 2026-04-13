# Stage 0 — Audit Universe: Inclusion and Exclusion Rules

**Purpose:** Formal definition of the audit universe for the forensic analysis of WHO mortality estimates. This text is written for direct reuse in the **Methods** section of the white paper and in reproducibility documentation.

---

## 1. Publication-ready Methods text (verbatim)

**Suggested heading in the report:** *Definition of the audit universe*

We defined the audit universe as follows. **Countries:** all countries and territories for which the WHO Mortality Database contained at least one year of cause-of-death data coded under ICD-10 (List 101) within the period 2000–2021. We identified available country-years from the official WHO Mortality Database availability file (February 2025 release). **Time window:** 2000–2021, to align with the latest WHO Global Health Estimates (GHE) country-level cause-of-death series and to span the pre-SDG baseline, major NCD transition period, and the COVID-19 pandemic. **Cause coding:** we restricted the analysis to mortality data coded under ICD-10 (List 101) only; earlier ICD revisions (ICD-7, ICD-8, ICD-9) were excluded to ensure comparability with WHO GHE and to avoid artefacts from historical changes in cause-of-death classification.

A country-year was **included** in the main audit if (i) ICD-10 cause-of-death data were present in the WHO Mortality Database for that country and year, and (ii) reference population data were available for the same country-year in the WHO Mortality Database population file, so that completeness and rate checks could be performed. Country-years with mortality data but without corresponding population data were retained in the availability matrix but excluded from rate-based and completeness-dependent diagnostics; they were not used in reported-vs-estimated divergence calculations that require denominators. A country-year was **excluded** if it was not present in the availability file as having ICD-10 mortality data, so that missingness was treated explicitly as non-reporting rather than as zero deaths.

For robustness and interpretability, we also produced a **high-quality subset**: country-years with at least three consecutive years of ICD-10 data within 2000–2021. Analyses were run on both the full audit universe and, where noted, on this subset to assess the sensitivity of smoothness and volatility indicators to sparse reporting.

---

## 2. Rule specification (for implementation)

### 2.1 Data sources

| Item | Source |
|------|--------|
| Country-year availability (mortality) | WHO Mortality Database — Availability file (e.g. `AVAILABILITY_list_ctry_years_feb2025.xlsx` or equivalent). |
| Country-year availability (population) | Same availability file (population sheet/columns) or Population and live births package. |
| Cause coding | List = 101 (ICD-10) only. |

### 2.2 Inclusion criteria (main audit)

| Criterion | Rule |
|----------|------|
| **Geography** | Any country or territory appearing in the WHO Mortality Database with at least one year of ICD-10 data in 2000–2021. |
| **Time** | Year ∈ [2000, 2021]. |
| **Mortality data** | At least one record (any cause, any sex) for that country-year in the concatenated ICD-10 parts 1–6. |
| **Population data** | Reference population available for the same country-year (for inclusion in rate and completeness-dependent steps). |

### 2.3 Exclusion criteria

| Criterion | Rule |
|-----------|------|
| **Non-reported country-years** | Country-year not listed as having ICD-10 mortality data in the availability file → excluded; never treat as zero deaths. |
| **Other ICD lists** | Records with List ≠ 101 dropped before aggregation. |
| **Pre-2000 / post-2021** | Years outside 2000–2021 excluded from the audit window. |

### 2.4 High-quality subset (optional, for sensitivity)

| Criterion | Rule |
|-----------|------|
| **Consecutive years** | Country has ≥ 3 consecutive years of ICD-10 mortality data within 2000–2021. |

Use this subset when reporting “robust” smoothness or volatility results that should not be driven by single-year or sparse reporting.

---

## 3. Output of Stage 0

Stage 0 must produce:

1. **Audit universe table**  
   Columns: `country` (or `country_code`), `year`, `mortality_available`, `population_available`, `included` (logical), optionally `n_consecutive_years`, `in_high_quality_subset`.

2. **Country-level summary**  
   For each country: first year, last year, total years with data, whether in high-quality subset.

3. **Manifest (versioned)**  
   A small file (e.g. YAML or JSON) recording: data source versions (e.g. “WHO MDB Availability Feb 2025”), audit window (2000–2021), and inclusion rule labels (“main”, “high_quality_subset”).

This table and manifest should be used by all downstream stages so that exclusions are consistent and traceable.

---

## 4. Rationale for reviewers

- **ICD-10 only:** Avoids mixing classification systems and aligns with GHE, which is based on ICD-10 cause groups.  
- **Explicit missingness:** Using the availability file ensures we do not interpret “no row” as “zero deaths,” protecting volatility and smoothness metrics from artefact.  
- **Population requirement:** Ensures that any rate-based or completeness-based metric is interpretable and avoids silent errors in joins.  
- **High-quality subset:** Gives a conservative benchmark for “what holds when data are less sparse,” which is useful for policy-facing conclusions.

---

*To be cited in the report as the formal definition of the audit universe. Align with 01_ICD10_cause_groupings.md and 03_join_schema_reported_vs_estimated.md.*
