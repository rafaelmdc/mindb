# Agent Task: Refactor Codebase to the New Microbiome Data Model

## Goal

Refactor the existing Django/PostgreSQL codebase away from the old pairwise `RelativeAssociation`-centered design and toward a simpler, scalable model that matches the real extraction units used in the microbiome literature.

The new design must support:

* study-level paper records
* study groups / cohorts / arms
* explicit comparisons between groups
* qualitative taxon findings such as enriched / depleted
* quantitative taxon values such as relative abundance
* optional alpha and beta diversity tables
* light metadata via a slim EAV system
* import provenance and tracking

This is a practical refactor for a presentation-stage but scalable system. Keep the implementation compact and clean. Do not overengineer.

---

## Core modeling change

### Old assumption

The previous schema treated the main biological unit as a pairwise organism-organism relationship:

* `RelativeAssociation(sample, organism_1, organism_2, value, sign, ...)`

This is wrong for the current literature extraction workflow.

### New assumption

The real extraction units are usually:

1. **qualitative directional findings in a comparison**

   * Example: in Parkinson's disease vs control, *Bacteroides* is enriched

2. **quantitative values for one taxon in one group**

   * Example: in controls, *Bacteroides dorei* has relative abundance 3.15

So the new model centers on:

* `Study`
* `Group`
* `Comparison`
* `Organism`
* `QualitativeFinding`
* `QuantitativeFinding`

Optional:

* `AlphaMetric`
* `BetaMetric`

---

## New schema to implement

## 1. Study

Represents one publication / paper.

Fields:

* `id`
* `doi` nullable, unique when present
* `title`
* `journal` nullable
* `year` nullable
* `country` nullable
* `created_at`
* `updated_at`
* `notes` nullable

Notes:

* Keep this compact.
* Timestamps are required.
* Add indexes where appropriate.

---

## 2. Group

Represents a study arm / cohort / subgroup.

Examples:

* disease
* control
* severe disease
* mild disease
* discovery cohort
* validation cohort

Fields:

* `id`
* `study_id` FK to `Study`
* `name`
* `condition` nullable
* `sample_size` nullable
* `cohort` nullable
* `site` nullable
* `created_at`
* `updated_at`
* `notes` nullable

Constraints:

* unique `(study_id, name)`

Notes:

* This replaces the old `Sample` semantics.
* If the existing code uses `Sample`, rename carefully or replace with a migration path.

---

## 3. Comparison

Represents a directional comparison between two groups.

Example:

* PD vs healthy controls

Fields:

* `id`
* `study_id` FK to `Study`
* `group_a_id` FK to `Group`
* `group_b_id` FK to `Group`
* `label`
* `created_at`
* `updated_at`
* `notes` nullable

Constraints:

* `group_a_id != group_b_id`
* recommended unique constraint on `(study_id, group_a_id, group_b_id, label)`

Notes:

* `group_a` is the directional reference for qualitative findings.
* Keep this simple. No need for a complex comparison ontology right now.

---

## 4. Organism

Represents a microbial taxon.

Fields:

* `id`
* `scientific_name`
* `rank`
* `ncbi_taxonomy_id` nullable
* `created_at`
* `updated_at`
* `notes` nullable

Constraints:

* `ncbi_taxonomy_id` unique when present
* consider unique or indexed `scientific_name`

Notes:

* Keep taxonomy normalization simple for now.
* Rank examples: phylum, class, order, family, genus, species.

---

## 5. QualitativeFinding

Represents a directional taxon finding inside a comparison.

Use for findings like:

* enriched
* depleted
* increased
* decreased

Fields:

* `id`
* `comparison_id` FK to `Comparison`
* `organism_id` FK to `Organism`
* `direction`
* `source`
* `import_batch_id` nullable FK to `ImportBatch`
* `created_at`
* `updated_at`
* `notes` nullable

Recommended values for `direction`:

* `enriched`
* `depleted`

Constraints:

* recommended unique constraint on `(comparison_id, organism_id, direction, source)`

Notes:

* Keep `source` as a single short provenance string.
* Examples of `source`:

  * `Results section 3.2`
  * `Table 2`
  * `Supplementary Table S4`
* Do not add p-values, q-values, methods, or many provenance columns unless already truly needed.

---

## 6. QuantitativeFinding

Represents one exact numeric taxon value in one group.

Use for values like:

* relative abundance
* later maybe absolute abundance

Fields:

* `id`
* `group_id` FK to `Group`
* `organism_id` FK to `Organism`
* `value_type`
* `value`
* `unit` nullable
* `source`
* `import_batch_id` nullable FK to `ImportBatch`
* `created_at`
* `updated_at`
* `notes` nullable

Recommended values for `value_type`:

* `relative_abundance`

Constraints:

* recommended unique constraint on `(group_id, organism_id, value_type, source)`

Notes:

* This fixes the old design error.
* Quantitative values belong to one organism in one group, not organism A relative to organism B.
* Keep `value` numeric.

---

## 7. AlphaMetric (optional)

Keep as an optional extension.

Fields:

* `id`
* `group_id` FK to `Group`
* `metric`
* `value`
* `source`
* `import_batch_id` nullable FK to `ImportBatch`
* `created_at`
* `updated_at`
* `notes` nullable

Examples:

* Shannon
* Simpson
* Chao1

Notes:

* Optional model. Implement cleanly but do not make the rest of the system depend on it.

---

## 8. BetaMetric (optional)

Keep as an optional extension.

Fields:

* `id`
* `comparison_id` FK to `Comparison`
* `metric`
* `value`
* `source`
* `import_batch_id` nullable FK to `ImportBatch`
* `created_at`
* `updated_at`
* `notes` nullable

Examples:

* Bray-Curtis
* Jaccard
* weighted UniFrac
* unweighted UniFrac

Notes:

* Optional model.
* Keep simple.

---

## 9. ImportBatch

Tracks import provenance and status.

Fields:

* `id`
* `name`
* `source_file`
* `import_type`
* `status`
* `created_at`
* `notes` nullable

Optional useful fields:

* `success_count`
* `error_count`

Notes:

* Keep lightweight but useful for admin and debugging.

---

## 10. MetadataVariable

Slim EAV descriptor table.

Fields:

* `id`
* `name`
* `value_type`
* `display_name` nullable
* `is_filterable` default false
* `created_at`
* `updated_at`

Notes:

* Keep very small.
* Do not add heavy ontology logic yet.

---

## 11. MetadataValue

Slim EAV value table linked to `Group`.

Fields:

* `id`
* `group_id` FK to `Group`
* `variable_id` FK to `MetadataVariable`
* `value_text` nullable
* `value_float` nullable
* `value_int` nullable
* `value_bool` nullable
* `created_at`
* `updated_at`

Constraints:

* unique `(group_id, variable_id)`
* only one typed value field should be filled

Notes:

* Keep EAV as a light extension, not as the center of the system.
* Use it for metadata like age mean, BMI mean, sequencing platform, antibiotic exclusion, etc.

---

## Remove or demote from the old design

## Remove as central logic

The following should no longer be the core of the codebase:

* `RelativeAssociation`
* `CoreMetadata`
* organism-organism abundance logic
* canonical organism ordering logic tied to abundance records

## Demote or postpone

If a true taxon-taxon association model is needed later, reintroduce it separately as an optional model such as:

* `TaxonPairAssociation`

But do not keep it as the main data path.

---

## Keep the EAV?

Yes, but only as a **slim extension layer**.

Decision:

* **keep** `MetadataVariable` + `MetadataValue`
* **do not keep** `CoreMetadata`
* store a few common fields directly on `Study` and `Group`
* store sparse/heterogeneous metadata in EAV

Direct columns should cover:

* `Study.country`
* `Group.condition`
* `Group.sample_size`
* `Group.cohort`
* `Group.site`

Use EAV for less common metadata.

---

## Required codebase changes

Implement the refactor across the whole codebase, not just the models.

### 1. Models

* Replace the old schema with the new models above.
* Keep model definitions compact.
* Add timestamps and sensible constraints.
* Use Django `TextChoices` or enums where helpful for:

  * `direction`
  * `value_type`
  * `ImportBatch.status`

### 2. Migrations

* Create proper Django migrations.
* Prefer a clean break over fragile migration complexity if the project is still early-stage.
* If legacy data exists, provide a short migration note explaining what can and cannot be migrated automatically.

### 3. Admin

Update Django admin to match the new logic.

Minimum admin requirements:

* searchable `Study`
* inline or easy navigation from `Study` to `Group`
* easy browsing of `Comparison`
* filterable `QualitativeFinding`
* filterable `QuantitativeFinding`
* usable `ImportBatch` admin
* simple `MetadataVariable` / `MetadataValue` admin

Make the admin practical for curation.

### 4. Import pipeline

Refactor import code to target the new schema.

The import system should support:

* qualitative imports into `QualitativeFinding`
* quantitative imports into `QuantitativeFinding`
* optional alpha imports into `AlphaMetric`
* optional beta imports into `BetaMetric`
* metadata imports into `MetadataValue`
* provenance tracking through `ImportBatch`

Do not assume all input files have every field.
Keep parsers tolerant but validated.

### 5. Validation

Add validation for:

* unique constraints
* comparison groups cannot be identical
* only one typed EAV value field may be set
* quantitative values must be numeric
* required foreign keys must exist

### 6. API / serializers / views

Refactor any serializers, REST endpoints, service functions, or views that still assume pairwise organism-organism abundance logic.

Expected new core query patterns:

* all qualitative findings for a disease/control comparison
* all quantitative values for a given group
* all taxa linked to a study
* all studies mentioning a given taxon
* metadata filters by group

### 7. Frontend / graph layer

If the codebase already has graph generation, update it to use the new data model.

The primary graph should now be based on:

* disease/group comparisons
* taxa
* qualitative enriched/depleted edges

Do not use the old pairwise organism-organism logic for abundance findings.

---

## Target graph semantics after refactor

### Preferred first graph

A bipartite comparison/taxon or disease/taxon network built from `QualitativeFinding`.

Possible edge meaning:

* enriched
* depleted

Possible edge weight:

* count of supporting findings or studies

### Quantitative support

Use `QuantitativeFinding` as an evidence layer, not the main graph edge type.

---

## Implementation strategy

Use this order:

1. replace models
2. generate migrations
3. update admin
4. update import pipeline
5. update serializers / views / services
6. update graph logic
7. delete obsolete code paths
8. test imports and queries

Keep the refactor incremental but decisive.

---

## Non-goals

Do **not** add any of the following unless strictly required by the existing codebase:

* complex ontology systems
* deep taxonomic normalization workflows
* multiple provenance fields per finding
* p/q-value-heavy qualitative tables
* method tracking on every row
* advanced review workflows
* overbuilt metadata frameworks

This refactor should stay compact and presentation-ready.

---

## Deliverables expected from the agent

1. Updated Django models
2. New migrations
3. Updated admin registrations
4. Refactored import logic
5. Updated serializers / views / query services
6. Removal or deprecation of obsolete `RelativeAssociation`-based paths
7. Short README or migration note summarizing the new model and the breaking changes

---

## Final guidance

When in doubt, prefer:

* fewer fields
* clearer logic
* easier imports
* explicit group/comparison modeling
* direct support for qualitative enriched/depleted findings
* direct support for quantitative organism values

The system should be easy to explain in a presentation and still clean enough to scale later.
