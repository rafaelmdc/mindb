# RelativeAssociation CSV Contract

## Purpose

Import pairwise organism-organism associations into `RelativeAssociation`.

This contract depends on:

- `Study`
- `Sample`
- `Organism`

## Required columns

- `study_source_doi`
- `sample_label`
- `organism_1_taxonomy_id`
- `organism_2_taxonomy_id`
- `association_type`

## Optional columns

- `value`
- `sign`
- `p_value`
- `q_value`
- `method`
- `confidence`
- `notes`

## CSV shape

```csv
study_source_doi,sample_label,organism_1_taxonomy_id,organism_2_taxonomy_id,association_type,value,sign,p_value,q_value,method,confidence,notes
10.1000/example,Cohort A,853,816,correlation,0.42,positive,0.01,0.03,spearman,0.90,Reported in supplement
10.1000/example,Cohort A,1000,1100,cooccurrence,,,,,network_inference,,Derived edge
```

## Column rules

- `study_source_doi`
  - required
  - must resolve to an existing `Study.source_doi`
- `sample_label`
  - required
  - must resolve, together with `study_source_doi`, to an existing `Sample`
- `organism_1_taxonomy_id`
  - required
  - must resolve to an existing `Organism.ncbi_taxonomy_id`
- `organism_2_taxonomy_id`
  - required
  - must resolve to an existing `Organism.ncbi_taxonomy_id`
- `association_type`
  - required
  - non-empty string
- `value`
  - optional float
- `sign`
  - optional
  - expected values: `positive`, `negative`, `neutral`
- `p_value`
  - optional float
- `q_value`
  - optional float
- `method`
  - optional text
- `confidence`
  - optional float
- `notes`
  - optional text

## Lookup rules

- resolve the sample using `(study_source_doi, sample_label)`
- resolve organisms using `Organism.ncbi_taxonomy_id`
- internal foreign key IDs should not be used in CSV input

## Pairwise rules

- self-pairs are invalid: `organism_1_taxonomy_id` must not equal `organism_2_taxonomy_id`
- canonical ordering should be enforced during validation/import so the lower resolved organism ID becomes `organism_1`
- reverse duplicates should not create separate rows

## Duplicate rules

- duplicates should be checked against the canonical pair key:
  - `(study_source_doi, sample_label, canonical_taxonomy_pair, association_type)`
- rows matching an existing `RelativeAssociation` by that key should be reported as duplicates and skipped
- duplicate rows inside the uploaded file by that same canonical key should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- study, sample, and both organisms must resolve successfully
- taxonomy IDs must parse as integers
- optional numeric fields, when present, must parse as floats
- `sign`, when present, must be one of the allowed values

## Import behavior

- create-only
- no updates to existing `RelativeAssociation` rows
- valid rows create `RelativeAssociation` records and are attributed to the generated `ImportBatch`

## Notes

- this contract preserves the uniqueness rule on `(sample_id, organism_1_id, organism_2_id, association_type)`
- duplicate detection must use canonical ordering so reverse pairs are not imported twice
