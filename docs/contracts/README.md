# CSV Import Contracts

This directory defines the expected CSV structure for admin-only import workflows.

These contracts are intentionally model-specific:

- one CSV shape per import type
- explicit required and optional columns
- explicit lookup fields for related records
- duplicate and validation rules defined per model

Documented contracts in this directory:

- `Organism`
- `Study`
- `Sample`
- `CoreMetadata`
- `MetadataVariable`
- `MetadataValue`
- `RelativeAssociation`
- `AlphaMetric`
- `BetaMetric`

Design rules:

- prefer stable lookup fields over internal database IDs
- preserve schema constraints from `docs/schema.md`
- keep imports create-only unless update behavior is explicitly added later
- validate and preview before writing any records

Implementation status:

- `Organism` import is implemented in code
- the remaining contracts are documented but not yet implemented

Related docs:

- `docs/schema.md`
- `docs/roadmap.md`
