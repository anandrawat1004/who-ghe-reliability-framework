# ICD-10 Cause Groupings for the Audit Pipeline

**Purpose:** Define the cause-of-death groupings used in Stage 0 and subsequent stages of the forensic audit. Aligned with WHO Mortality Database (List 101, ICD-10) and WHO Global Health Estimates (GHE) cause categories.

**Authoritative reference:**  
[List of causes and corresponding ICD-10 codes](https://platform.who.int/mortality/about/list-of-causes-and-corresponding-icd-10-codes) (WHO Mortality Platform).

---

## 1. Cause coding in the WHO Mortality Database

- **List:** Use only **List = 101** (ICD-10 tabulation list).
- **Cause:** Numeric code. The Documentation.zip Annex maps these to cause names; the order matches the official cause list (first row = 1000, second = 1001, etc.).
- **All-cause** in the raw data is the List 101 total-cause code (commonly **1000**; confirm from Documentation Annex). ICD-10 range A00–Y89.

Always join or aggregate using **List = 101** so that cause codes are comparable across country-years.

---

## 2. Tier 1 — All-cause mortality

Use for baseline reliability, volatility realism, and collapse detection.

| Group label   | WHO MDB (List 101) | ICD-10 range | Notes |
|---------------|--------------------|-------------|--------|
| **All causes** | List 101 all-cause code (confirm from Annex; commonly 1000) | A00–Y89     | Single cause in raw data; no aggregation. |

**Inclusion:** All country-years with at least one record for the all-cause code, List = 101.

---

## 3. Tier 2 — Top causes (global and region-specific)

These align with WHO GHE “leading causes” and support bias signals and smoothness checks. Use the **same** cause list (List 101) and the numeric Cause codes that correspond to the rows in the official cause list.

### 3.1 Broad categories (for first-pass analysis)

| Category | ICD-10 range (from WHO cause list) | Use in audit |
|----------|------------------------------------|--------------|
| **Communicable, maternal, perinatal and nutritional** | A00–B99, D50–D53, D64.9, E00–E02, E40–E46, E50–E64, G00–G04, G14, H65–H66, J00–J22, N70–N73, O00–O99, P00–P96, U04, U07.1, U07.2, U09.9, U10.9 | Aggregate from List 101 sub-causes. |
| **Noncommunicable diseases** | C00–C97, D00–D48, D55–D64 (minus D64.9), D65–D89, E03–E07, E10–E34, E65–E88, F01–F99, G06–G98 (minus G14), H00–H61, H68–H93, I00–I99, J30–J98, K00–K92, L00–L98, M00–M99, N00–N64, N75–N98, Q00–Q99, R95, U07.0, X41, X42, X44, X45 | As above. |
| **Injuries** | V01–Y89 (minus X41–X42, X44–X45), U12.9 | As above. |

### 3.2 Specific top causes (for cause-level audit)

Obtain the exact **Cause** code for each from the Documentation PDF (Annex table) or by matching the cause name to the official list order. Representative cause names and ICD-10 ranges:

| Cause name | ICD-10 range | Typical GHE alignment |
|------------|--------------|------------------------|
| Ischaemic heart disease | I20–I25 | Yes |
| Stroke (cerebrovascular disease) | I60–I69 | Yes |
| Chronic obstructive pulmonary disease | J40–J44 | Yes |
| Lower respiratory infections | J09–J22, P23, U04 | Yes |
| Trachea, bronchus, lung cancers | C33–C34 | Yes |
| Diabetes mellitus | E10–E14 | Yes |
| Malignant neoplasms (all) | C00–C97 | Yes |
| Alzheimer and other dementias | F01, F03, G30–G31 | Yes |
| Diarrhoeal diseases | A00, A01, A03, A04, A06–A09 | Yes |
| Tuberculosis | A15–A19, B90 | Yes |

**Implementation:** Build a lookup table **cause_code → cause_name → ICD-10 range** from the Documentation.zip cause list. For “top causes,” subset to the causes that appear in GHE leading-cause downloads for your audit window (2000–2021).

---

## 4. Tier 3 — Contentious / high-bias causes (stress-test set)

These are known to be sensitive to under-reporting, reclassification, or modelling and are used for the forensic “stress test” (malaria, suicide, maternal, COVID-era).

| Cause label | ICD-10 range (WHO cause list) | Rationale for inclusion |
|-------------|------------------------------|--------------------------|
| **Malaria** | B50–B54, P37.3, P37.4 | High imputation in many LMICs; reporting vs estimated divergence. |
| **Self-inflicted injuries (suicide)** | X60–X84, Y870 | Stigma; under-reporting and “ill-defined” dumping. |
| **Maternal conditions** | O00–O99 | Attribution and completeness vary widely. |
| **COVID-19** | U07.1, U07.2, U09.9, U10.9 | 2020–2021 only; excess mortality vs reported. |
| **Ill-defined diseases** | R00–R94, R96–R99 | Garbage-code proxy; high share → low reliability. |
| **Ill-defined injuries/accidents** | Y10–Y34, Y872 | Undetermined intent; overlaps with suicide. |

**Implementation:** Map the cause names above to the corresponding **Cause** codes in List 101 using the Documentation annex. Filter raw data to these Cause codes when building the “contentious causes” subset.

---

## 5. GHE alignment (reported vs estimated join)

WHO GHE cause categories are built from the same ICD-10 framework. When building the join:

1. **WHO Mortality Database:** Keep **List = 101**, **Cause** (numeric), and optionally **cause name** from your lookup.
2. **WHO GHE:** Use the cause names or cause codes provided in the GHE download (e.g. “Malaria,” “Maternal disorders,” “Self-harm”). GHE technical report: *WHO methods and data sources for country-level causes of death 2000–2021* (WHO/DDI/DNA/GHE/2024.2).
3. **Join key:** Use a **cause_group** or **cause_name** that you define so that:
   - MDB: aggregate reported deaths to that cause_group (summing over the relevant Cause codes if one GHE group maps to several MDB causes).
   - GHE: use the same cause_group label or official GHE cause name.

A separate document (**03_join_schema_reported_vs_estimated.md**) defines the exact table layout and keys.

---

## 6. Garbage-code and ill-defined causes

For bias signals (e.g. “garbage-code share”):

- **Ill-defined diseases:** R00–R94, R96–R99 (single cause in List 101).
- **Ill-defined injuries/accidents:** Y10–Y34, Y872 (single cause in List 101).

Compute, by country-year (and optionally cause):

- *Ill-defined share = (deaths from ill-defined causes) / (all-cause deaths)*  
using reported deaths from the Mortality Database.

---

## 7. Checklist before Stage 1

- [ ] Restrict to **List = 101** only.
- [ ] Build **cause_code → cause_name → ICD-10** lookup from Documentation.
- [ ] Define Tier 1: all-cause (List 101 all-cause code; confirm from Documentation Annex, commonly 1000).
- [ ] Define Tier 2: set of “top cause” Cause codes matching GHE leading causes.
- [ ] Define Tier 3: Cause codes for malaria, self-inflicted injuries, maternal, COVID-19, ill-defined diseases, ill-defined injuries.
- [ ] Document any cause aggregation (e.g. “Communicable” = sum of specific Cause codes) for reproducibility.

---

*Source: WHO Mortality Database Documentation; platform.who.int/mortality/about/list-of-causes-and-corresponding-icd-10-codes. Last aligned with audit pipeline: 2025.*
