# Reported vs Estimated Join Schema — WHO Mortality Database and WHO GHE

**Purpose:** Define the table layouts and join strategy so that WHO Mortality Database (reported CRVS) and WHO Global Health Estimates (modelled) can be compared in a single panel for bias, smoothness, and reliability analysis.

---

## 1. Standardised identifiers (use everywhere)

| Identifier | Definition | Source |
|------------|------------|--------|
| **country_code** | ISO 3166-1 alpha-3 (ISO3) where possible. | Map WHO MDB Country (numeric) and GHE country labels via a single lookup (e.g. from WHO country_codes + manual alignment to ISO3). |
| **year** | Calendar year (integer). | Both. |
| **cause_group** | Common cause label used for joining (see §3). | Your aggregation; must be consistent across reported and estimated tables. |
| **sex** | 1 = Male, 2 = Female, 0 or 9 = Both/unspecified (align to GHE convention). | Both; standardise to same encoding. |

Use **country_code + year + cause_group (+ sex if applicable)** as the composite key for joining.

---

## 2. Reported layer — WHO Mortality Database

### 2.1 Raw MDB schema (from your ICD-10 parts)

From your Mortality Database files (e.g. `Morticd10_part1` … `Morticd10_part6`):

- **Country** — WHO numeric country code  
- **Admin1, SubDiv** — optional (often blank)  
- **Year** — calendar year  
- **List** — tabulation list (use **101** only)  
- **Cause** — numeric cause code (List 101)  
- **Sex** — 1 = Male, 2 = Female  
- **Frmat, IM_Frmat** — age format codes (see Documentation)  
- **Deaths1 … Deaths26** — death counts by age band (format depends on Frmat)  
- **IM_Deaths1 …** — infant mortality age bands  

### 2.2 Target: reported panel (tidy, one row per unit)

Produce a **reported** table with one row per (country_code, year, cause_group, sex) or (country_code, year, cause_group) if you aggregate over sex.

| Column | Type | Description |
|--------|------|-------------|
| **country_code** | string (ISO3) | From Country via country_codes lookup. |
| **year** | integer | 2000–2021. |
| **cause_group** | string | Your common cause label (see §3). |
| **sex** | string or int | e.g. "Both", "Male", "Female" or 0,1,2. |
| **reported_deaths** | numeric | Sum of deaths for that unit (after mapping Cause → cause_group and summing age bands). |
| **source_list** | int | Always 101. |
| **source_part** | string | e.g. "icd10_part3" for traceability. |

- **Aggregation:** For each (Country, Year, List, Cause, Sex), sum Deaths1…Deaths26 (and infant bands if used) into a single **reported_deaths** count. Map **Cause** (List 101) to **cause_group** using the cause groupings document (01_ICD10_cause_groupings.md).  
- **Filter:** List = 101 only; Year in 2000–2021; only country-years in the Stage 0 inclusion table.

---

## 3. Estimated layer — WHO Global Health Estimates

### 3.1 GHE data (typical download)

GHE cause-of-death downloads usually provide:

- Country (name or code)  
- Year (often 2000, 2010, 2015, 2019, 2020, 2021 or full 2000–2021)  
- Cause (name or code)  
- Sex  
- Age (or age group)  
- **Deaths** (point estimate)  
- **Lower** / **Upper** (uncertainty bounds, if published)

### 3.2 Target: estimated panel (tidy)

| Column | Type | Description |
|--------|------|-------------|
| **country_code** | string (ISO3) | From GHE country label via your lookup. |
| **year** | integer | 2000–2021. |
| **cause_group** | string | Same set of labels as in reported table. |
| **sex** | string or int | Same encoding as reported. |
| **estimated_deaths** | numeric | GHE point estimate. |
| **lower_ui** | numeric | Lower uncertainty bound (if available). |
| **upper_ui** | numeric | Upper uncertainty bound (if available). |

- **cause_group:** Use the same **cause_group** values as in the reported table. Map GHE cause names (e.g. “Malaria”, “Maternal disorders”, “Self-harm”) to this set; some GHE groups may combine several MDB causes — then reported_deaths for that cause_group is the sum of the corresponding MDB Cause codes.

---

## 4. Cause-group mapping (reported ↔ estimated)

Create one **cause mapping** table used by both layers:

| Column | Description |
|--------|-------------|
| **cause_group** | Your single label (e.g. "All cause", "Malaria", "Maternal", "Self-harm", "COVID-19", "Ill-defined diseases"). |
| **mdb_cause_codes** | List of Cause codes (List 101) that map to this group (e.g. [1000] for all-cause; one or more for others). |
| **ghe_cause_name** | Exact string or code from GHE download (for matching). |
| **icd10_range** | Optional; ICD-10 range for documentation. |

- **All-cause:** cause_group = "All cause"; MDB Cause = 1000; GHE = “Total” or equivalent.  
- **Contentious:** cause_group = "Malaria" ↔ MDB cause code for Malaria (List 101) ↔ GHE “Malaria”; similarly for Maternal, Self-harm, COVID-19, Ill-defined.  
- **Top causes:** Add one row per GHE leading cause you use, with the corresponding MDB Cause code(s).

This table is the single source of truth for “reported vs estimated” cause alignment.

---

## 5. Joined panel (audit-ready)

After building **reported** and **estimated** panels with the same **country_code**, **year**, **cause_group**, **sex**:

**Join:** Full outer join on (country_code, year, cause_group, sex) so that:

- Rows with both reported and estimated data have both counts.  
- Rows with only reported (no GHE for that unit) have estimated_deaths = NA.  
- Rows with only estimated (e.g. country without CRVS) have reported_deaths = NA.

**Output table (example):**

| Column | Type | Description |
|--------|------|-------------|
| country_code | string | ISO3. |
| year | integer | 2000–2021. |
| cause_group | string | Common cause label. |
| sex | string/int | Standardised. |
| reported_deaths | numeric | From MDB (NA if no data). |
| estimated_deaths | numeric | From GHE (NA if no data). |
| lower_ui | numeric | GHE lower bound (optional). |
| upper_ui | numeric | GHE upper bound (optional). |
| in_audit_universe | logical | From Stage 0 (population available, etc.). |

**Derived (in pipeline):**

- **divergence** = reported_deaths − estimated_deaths (or ratio), only where both non-NA.  
- **reported_share** = reported_deaths / sum(reported_deaths) by (country, year) for all-cause.  
- Use **in_audit_universe** to restrict which rows enter bias and reliability metrics.

---

## 6. Country code alignment

- **WHO Mortality Database:** Uses numeric **Country** (e.g. 1400). Your `country_codes` file maps to names. Add a column **iso3** (or **country_code**) via a small table: WHO_numeric → ISO3 (and name).  
- **WHO GHE:** Downloads may use country names or ISO3. Build a table: GHE_country_label → **country_code** (ISO3).  
- Use **country_code** (ISO3) as the single key in both reported and estimated panels and in Stage 0.

If a country appears in one source but not the other, the outer join still retains it with NA on the other side; document such cases in the availability matrix.

---

## 7. Data flow summary

```
WHO MDB raw (ICD-10 parts 1–6)     WHO GHE downloads
         │                                    │
         ▼                                    ▼
  Filter List=101                      Map cause names
  Map Country → country_code           Map country → country_code
  Map Cause → cause_group             Map cause → cause_group
  Sum deaths by (country_code,        Keep estimated_deaths,
   year, cause_group, sex)             lower_ui, upper_ui
         │                                    │
         ▼                                    ▼
  reported panel                      estimated panel
  (country_code, year, cause_group,   (country_code, year, cause_group,
   sex, reported_deaths)               sex, estimated_deaths, lower_ui, upper_ui)
         │                                    │
         └──────────────┬─────────────────────┘
                        │
                        ▼
              Full outer join on
              (country_code, year, cause_group, sex)
                        │
                        ▼
              Joined panel + Stage 0 in_audit_universe
                        │
                        ▼
              Bias signals, smoothness, reliability lens
```

---

## 8. Checklist before first join

- [ ] **Stage 0** table and manifest produced; **in_audit_universe** defined.  
- [ ] **Cause mapping** table built: cause_group ↔ MDB Cause codes ↔ GHE cause names.  
- [ ] **Country lookups:** MDB Country → country_code; GHE country → country_code.  
- [ ] **Reported panel:** List=101, 2000–2021, one row per (country_code, year, cause_group, sex), reported_deaths = sum of deaths.  
- [ ] **Estimated panel:** same keys, estimated_deaths (and UIs if available).  
- [ ] **Join:** outer join on (country_code, year, cause_group, sex); then merge Stage 0 so **in_audit_universe** is on the joined table.

---

*Companion to 01_ICD10_cause_groupings.md and 02_Stage0_inclusion_exclusion_rules.md. Use with WHO GHE methods document: WHO methods and data sources for country-level causes of death 2000–2021 (WHO/DDI/DNA/GHE/2024.2).*
