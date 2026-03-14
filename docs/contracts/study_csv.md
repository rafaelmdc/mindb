# Study CSV Contract

## Purpose

Import publication-level study records into `Study`.

This contract is intended for create-only imports.

## Required columns

- `title`

## Optional columns

- `source_doi`
- `country`
- `journal`
- `publication_year`
- `notes`

## CSV shape

```csv
source_doi,title,country,journal,publication_year,notes
10.1000/example,Example Study,Portugal,Microbiome Journal,2024,Curated from paper
,Untitled Internal Study,Spain,,2023,
```

## Column rules

- `title`
  - required
  - non-empty string
- `source_doi`
  - optional
  - when present, must be unique across `Study`
- `country`
  - optional text
- `journal`
  - optional text
- `publication_year`
  - optional integer
- `notes`
  - optional text

## Duplicate rules

- rows with the same non-empty `source_doi` as an existing `Study` should be reported as duplicates and skipped
- rows with duplicate non-empty `source_doi` values inside the uploaded file should be reported as duplicates and skipped
- rows without `source_doi` are allowed, but they should not be auto-deduplicated by title alone

## Validation rules

- required columns must exist in the header
- `title` must be present
- `publication_year`, when present, must parse as an integer

## Import behavior

- create-only
- no updates to existing `Study` rows
- valid rows create `Study` records and are attributed to the generated `ImportBatch`

## Notes

- `source_doi` is the preferred external lookup key for downstream imports
- follow-up import contracts should reference studies by `study_source_doi`
