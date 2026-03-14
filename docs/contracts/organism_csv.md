# Organism CSV Contract

## Purpose

Import taxon records into `Organism`.

This contract is intended for create-only imports.

## Required columns

- `ncbi_taxonomy_id`
- `scientific_name`
- `taxonomic_rank`

## Optional columns

- `parent_ncbi_taxonomy_id`
- `genus`
- `species`
- `notes`

## CSV shape

```csv
ncbi_taxonomy_id,scientific_name,taxonomic_rank,parent_ncbi_taxonomy_id,genus,species,notes
853,Faecalibacterium prausnitzii,species,816,Faecalibacterium,prausnitzii,Important commensal
816,Faecalibacterium,genus,186803,Faecalibacterium,,Genus node
```

## Column rules

- `ncbi_taxonomy_id`
  - required
  - integer
  - unique across `Organism`
- `scientific_name`
  - required
  - non-empty string
- `taxonomic_rank`
  - required
  - non-empty string
- `parent_ncbi_taxonomy_id`
  - optional integer
  - when present, should resolve to an existing or same-file organism
- `genus`
  - optional text
- `species`
  - optional text
- `notes`
  - optional text

## Duplicate rules

- duplicate `ncbi_taxonomy_id` values already present in the database should be reported as duplicates and skipped
- duplicate `ncbi_taxonomy_id` values inside the uploaded file should be reported as duplicates and skipped

## Validation rules

- required columns must exist in the header
- `ncbi_taxonomy_id` must parse as an integer
- `scientific_name` and `taxonomic_rank` must be present
- `parent_ncbi_taxonomy_id`, when present, must parse as an integer

## Import behavior

- create-only
- no updates to existing `Organism` rows
- parent references may be resolved after row creation if same-file parents are supported

## Notes

- `ncbi_taxonomy_id` is the preferred external lookup key for downstream imports
