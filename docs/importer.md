# Importer Notes

The importer is intentionally simple:

- upload CSV
- build a preview
- report validation errors and duplicates
- confirm import
- record the batch in `ImportBatch`

Each import type has its own parser in [imports/services.py](/home/rafael/Documents/GitHub/innovhealth_microbiome/imports/services.py), and each parser validates directly against the new `Study` / `Group` / `Comparison` / `Finding` schema.
