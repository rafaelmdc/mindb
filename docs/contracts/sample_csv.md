# Sample CSV Contract

## Purpose

Import analyzable study units into `Sample`.

This contract depends on `Study` records already existing.

## Required columns

- `study_source_doi`
- `label`

## Optional columns

- `site`
- `method`
- `cohort`
- `sample_size`
- `notes`

## CSV shape

```csv
study_source_doi,label,site,method,cohort,sample_size,notes
10.1000/example,Cohort A,Gut,16S,Control,120,Baseline cohort
10.1000/example,Cohort B,Gut,16S,Case,98,Case subgroup
```

## Column rules

- `study_source_doi`
  - required
  - must resolve to an existing `Study.source_doi`
- `label`
  - required
  - non-empty string
- `site`
  - optional text
- `method`
  - optional text
- `cohort`
  - optional text
- `sample_size`
  - optional integer
- `notes`
  - optional text

## Lookup rules

- the target study is resolved by `Study.source_doi = study_source_doi`
- internal database IDs should not be used in CSV input

## Duplicate rules

- duplicate `(study_source_doi, label)` pairs already present in the database should be reported as duplicates and skipped
- duplicate `(study_source_doi, label)` pairs within the uploaded file should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- `study_source_doi` must resolve to an existing `Study`
- `label` must be present
- `sample_size`, when present, must parse as an integer

## Import behavior

- create-only
- no updates to existing `Sample` rows
- valid rows create `Sample` records and are attributed to the generated `ImportBatch`

## Notes

- this contract preserves the uniqueness rule on `Sample(study_id, label)`
- downstream imports should reference samples by `(study_source_doi, sample_label)`
