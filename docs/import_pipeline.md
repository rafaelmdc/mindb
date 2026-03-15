# Import Pipeline

The current import pipeline is a create-only CSV workflow with preview and validation before any database write.

## Supported import types

- `organism`
- `study`
- `group`
- `comparison`
- `metadata_variable`
- `metadata_value`
- `qualitative_finding`
- `quantitative_finding`
- `alpha_metric`
- `beta_metric`

## Resolution rules

- studies resolve by `study_doi` first, then `study_title`
- groups resolve by study reference plus `group_name`
- comparisons resolve by study reference plus `group_a_name`, `group_b_name`, and `comparison_label`
- organisms resolve by `organism_ncbi_taxonomy_id` when present, otherwise `organism_scientific_name`

## Validation rules

- required columns are checked per import type
- duplicate rows are detected before write
- metadata values must populate exactly one typed field
- quantitative values must be numeric
- comparison groups must resolve to existing distinct groups
