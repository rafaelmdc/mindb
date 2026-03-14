# MetadataValue CSV Contract

## Purpose

Import flexible sample-level metadata into `MetadataValue`.

This contract depends on:

- `Study`
- `Sample`
- `MetadataVariable`

## Required columns

- `study_source_doi`
- `sample_label`
- `variable_name`

## Optional columns

- `value_float`
- `value_int`
- `value_text`
- `value_bool`
- `unit`
- `raw_value`
- `variation`
- `notes`

## CSV shape

```csv
study_source_doi,sample_label,variable_name,value_float,value_int,value_text,value_bool,unit,raw_value,variation,notes
10.1000/example,Cohort A,age_mean,42.1,,,,years,42.1,,From table 1
10.1000/example,Cohort A,smoking_status,,,never,,,never,,From table 2
10.1000/example,Cohort A,is_case,,,,true,,true,,Derived flag
```

## Lookup rules

- resolve the sample using `(study_source_doi, sample_label)`
- resolve the variable using `MetadataVariable.name = variable_name`
- internal foreign key IDs should not be used in CSV input

## Typed value rules

- exactly one of `value_float`, `value_int`, `value_text`, or `value_bool` must be populated
- the populated typed value field must match `MetadataVariable.value_type`

## Column rules

- `study_source_doi`
  - required
  - must resolve to an existing `Study.source_doi`
- `sample_label`
  - required
  - must resolve to an existing `Sample` within that study
- `variable_name`
  - required
  - must resolve to an existing `MetadataVariable.name`
- `unit`
  - optional text
- `raw_value`
  - optional text
- `variation`
  - optional text
- `notes`
  - optional text

## Duplicate rules

- duplicate `(study_source_doi, sample_label, variable_name)` rows already present in the database should be reported as duplicates and skipped
- duplicate `(study_source_doi, sample_label, variable_name)` rows within the uploaded file should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- study, sample, and variable must resolve successfully
- exactly one typed value field must be populated
- typed value must match the target variable's declared `value_type`
- numeric fields, when present, must parse correctly
- boolean values, when present, must parse correctly

## Import behavior

- create-only
- no updates to existing `MetadataValue` rows
- valid rows create `MetadataValue` records and are attributed to the generated `ImportBatch`

## Notes

- this contract preserves the uniqueness rule on `(sample_id, variable_id)`
- `raw_value` is intended to preserve the source text when useful, even when a typed value is also stored
