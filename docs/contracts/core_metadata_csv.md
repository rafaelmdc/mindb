# CoreMetadata CSV Contract

## Purpose

Import frequently queried structured sample-level metadata into `CoreMetadata`.

This contract depends on `Sample` records already existing.

## Required columns

- `study_source_doi`
- `sample_label`

## Optional columns

- `condition`
- `male_percent`
- `age_mean`
- `age_sd`
- `bmi_mean`
- `bmi_sd`
- `notes`

## CSV shape

```csv
study_source_doi,sample_label,condition,male_percent,age_mean,age_sd,bmi_mean,bmi_sd,notes
10.1000/example,Cohort A,Healthy,48.0,42.1,8.4,24.6,3.1,Structured metadata
```

## Lookup rules

- resolve the target sample using `(study_source_doi, sample_label)`
- internal database IDs should not be used in CSV input

## Column rules

- `study_source_doi`
  - required
  - must resolve to an existing `Study.source_doi`
- `sample_label`
  - required
  - must resolve to an existing `Sample` within that study
- `condition`
  - optional text
- `male_percent`
  - optional float
- `age_mean`
  - optional float
- `age_sd`
  - optional float
- `bmi_mean`
  - optional float
- `bmi_sd`
  - optional float
- `notes`
  - optional text

## Duplicate rules

- if `CoreMetadata` already exists for the resolved sample, that row should be reported as a duplicate and skipped
- duplicate `(study_source_doi, sample_label)` rows within the uploaded file should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- target sample must resolve successfully
- numeric fields, when present, must parse as floats

## Import behavior

- create-only
- no updates to existing `CoreMetadata` rows
- valid rows create `CoreMetadata` records and are attributed to the generated `ImportBatch`

## Notes

- `CoreMetadata` should remain minimal and not be expanded into a catch-all metadata import
