# Migration Note - 2026-03-15

This refactor is a clean schema break.

## What changed

- `Sample` was replaced by `Group`
- `CoreMetadata` was removed
- `RelativeAssociation` was removed from the main data path
- `Comparison` was added
- `QualitativeFinding` and `QuantitativeFinding` replaced the old association-centered finding model
- `AlphaMetric` now points to `Group`
- `BetaMetric` now points to `Comparison`
- `MetadataValue` now points to `Group`
- `Study.source_doi` became `Study.doi`
- `Study.publication_year` became `Study.year`
- `Organism.taxonomic_rank` became `Organism.rank`

## Migration strategy

- the `database` app migrations were reset to a new `0001_initial.py`
- old migration files were removed
- existing databases using the old schema must be dropped and recreated
- automatic conversion of legacy `RelativeAssociation` rows is not provided because the old data model does not map cleanly to the new extraction units

## Legacy data note

Legacy data can only be migrated safely when it can be re-expressed as:

- one organism in one group with a numeric value
- one organism in one comparison with a qualitative direction
