# services.py Documentation

## Purpose

This file implements the CSV import service layer for the admin-only importer.

Its responsibilities are:

- parse uploaded CSV content
- validate rows against a model-specific contract
- produce a preview payload with valid rows, errors, and duplicates
- execute confirmed imports inside a transaction
- create and update `ImportBatch` records for provenance and summary reporting

## Where it fits

This module sits behind the `imports` views:

- [imports/views.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/imports/views.py)

It depends on the core schema models in:

- [database/models.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/database/models.py)

The CSV contracts it implements are documented in:

- [docs/contracts/README.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/README.md)
- [docs/contracts/organism_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/organism_csv.md)
- [docs/contracts/study_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/study_csv.md)
- [docs/contracts/sample_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/sample_csv.md)
- [docs/contracts/core_metadata_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/core_metadata_csv.md)
- [docs/contracts/metadata_variable_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/metadata_variable_csv.md)
- [docs/contracts/metadata_value_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/metadata_value_csv.md)
- [docs/contracts/relative_association_csv.md](/home/rafael/Documents/GitHub/innovhealth_microbiome/docs/contracts/relative_association_csv.md)

## Main components

### `ImportPreview`

A small dataclass used as the preview payload returned from validation. It contains:

- batch metadata
- required columns
- valid rows
- validation errors
- duplicate reports

The preview is converted to a plain dict with `to_dict()` so it can be stored in the session.

### Public entry points

#### `build_preview(...)`

Selects the correct preview builder for an `import_type`, parses the CSV with `csv.DictReader`, and returns an `ImportPreview`.

#### `run_import(preview_data)`

Creates the `ImportBatch`, dispatches to the correct import runner, updates the batch summary fields, and returns the saved batch.

### Shared helpers

The file includes reusable helpers for:

- missing-column previews
- generic preview response assembly
- row cleaning
- integer / float / boolean parsing
- sample resolution from `(study_source_doi, sample_label)`

### Per-contract preview builders

Each supported import type has its own `_build_*_preview(...)` function. These functions:

- check required headers
- resolve related records where needed
- validate data types and required values
- detect duplicates in the uploaded file
- detect duplicates already in the database
- normalize row data into a consistent structure for preview and later import

Implemented builders:

- `_build_organism_preview`
- `_build_study_preview`
- `_build_sample_preview`
- `_build_core_metadata_preview`
- `_build_metadata_variable_preview`
- `_build_metadata_value_preview`
- `_build_relative_association_preview`

### Per-contract import runners

Each supported import type also has a `_run_*_import(...)` function that writes the validated rows.

Implemented runners:

- `_run_organism_import`
- `_run_study_import`
- `_run_sample_import`
- `_run_core_metadata_import`
- `_run_metadata_variable_import`
- `_run_metadata_value_import`
- `_run_relative_association_import`

### Dispatch registries

Two dicts at the bottom of the file tie everything together:

- `PREVIEW_BUILDERS`
- `IMPORT_RUNNERS`

Any new import type should be added to both.

## Control flow

Typical flow for one upload:

1. A view reads the uploaded CSV and calls `build_preview(...)`.
2. `build_preview(...)` checks `import_type` and dispatches to a contract-specific preview builder.
3. The preview builder parses each row and returns:
   - `valid_rows`
   - `errors`
   - `duplicates`
4. The view stores that preview in the session and renders the preview page.
5. After confirmation, the view passes the preview dict to `run_import(...)`.
6. `run_import(...)` creates an `ImportBatch`, dispatches to the correct runner, and updates the final batch counts/status.

## Important assumptions

- Imports are create-only. Existing rows are reported as duplicates and skipped instead of being updated.
- CSVs use contract-level natural keys instead of internal database IDs where possible.
- `Sample` resolution depends on `Study.source_doi`, so studies without DOI values are harder to reference from downstream imports.
- `MetadataValue` rows must populate exactly one typed value field, and that field must match the variable's `value_type`.
- `RelativeAssociation` rows are normalized to canonical organism ordering before duplicate checks so reverse pairs do not create separate records.
- Only `MetadataValue` and `RelativeAssociation` currently store the created `ImportBatch` directly because those models include that foreign key in the implemented schema.

## Notable edge cases

- Missing required columns short-circuit into a preview with one top-level error and no row-level parsing.
- Boolean parsing accepts a small set of string forms: `1/0`, `true/false`, `yes/no`, `on/off`.
- `Organism` parent references are resolved in a second pass after row creation so same-file parent taxa can be linked.
- `RelativeAssociation` duplicate checks use the canonicalized organism pair, not the uploaded order.
- `MetadataVariable.allowed_values` must parse as a JSON array, not just any JSON value.

## How to modify safely

- When adding a new import type, update all of these together:
  - `SUPPORTED_IMPORT_TYPES`
  - one `_build_*_preview(...)`
  - one `_run_*_import(...)`
  - `PREVIEW_BUILDERS`
  - `IMPORT_RUNNERS`
  - the upload form choices in [imports/forms.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/imports/forms.py)
  - the preview column config in [imports/views.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/imports/views.py)
  - tests in [imports/tests.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/imports/tests.py)
- Keep preview normalization and import writes aligned. If a preview builder changes the shape of `valid_rows`, the corresponding runner usually needs to change too.
- Be careful with duplicate keys for pairwise or EAV-style data; they should stay aligned with the model constraints in [database/models.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/database/models.py).

## Suggested follow-up

- The file is doing a lot of contract-specific work in one module. If import complexity grows further, the next safe cleanup would be splitting each import type into its own smaller service module while preserving the current dispatch pattern.
- If study records without DOI need to be import targets downstream, the project will need an alternative stable lookup key in the contracts.
