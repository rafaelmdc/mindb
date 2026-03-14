# MetadataVariable CSV Contract

## Purpose

Import controlled EAV variable definitions into `MetadataVariable`.

This contract is intended for create-only imports.

## Required columns

- `name`
- `display_name`
- `value_type`

## Optional columns

- `domain`
- `default_unit`
- `description`
- `is_filterable`
- `allowed_values`

## CSV shape

```csv
name,display_name,domain,value_type,default_unit,description,is_filterable,allowed_values
smoking_status,Smoking Status,clinical,text,,Smoking status,true,"[""never"",""former"",""current""]"
age_mean,Age Mean,demographic,float,years,Average age,true,
```

## Column rules

- `name`
  - required
  - unique across `MetadataVariable`
  - stable identifier used by downstream imports
- `display_name`
  - required
  - non-empty string
- `value_type`
  - required
  - allowed values: `float`, `int`, `text`, `bool`
- `domain`
  - optional text
- `default_unit`
  - optional text
- `description`
  - optional text
- `is_filterable`
  - optional boolean
  - accepted values should include `true`/`false`, `1`/`0`, `yes`/`no`
- `allowed_values`
  - optional JSON array string

## Duplicate rules

- duplicate `name` values already present in the database should be reported as duplicates and skipped
- duplicate `name` values inside the uploaded file should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- `value_type` must be one of the allowed values
- `is_filterable`, when present, must parse as a boolean
- `allowed_values`, when present, must parse as a JSON array

## Import behavior

- create-only
- no updates to existing `MetadataVariable` rows
- valid rows create `MetadataVariable` records and are attributed to the generated `ImportBatch`

## Notes

- downstream `MetadataValue` imports should reference variables by `name`
