# Graph Design

## Purpose

The graph view represents qualitative microbiome findings derived from curated `QualitativeFinding` records.

Its purpose is to let users visually explore:

- which organisms are reported in which comparisons
- whether those findings are enriched or depleted
- how many supporting findings exist for each comparison-taxon connection

## Source data

Primary source model:

- `QualitativeFinding`

Supporting models:

- `Comparison`
- `Group`
- `Study`
- `Organism`

## Graph semantics

### Node meaning

- one node type represents a `Comparison`
- one node type represents an `Organism`

### Edge meaning

An edge represents one or more qualitative findings linking an organism to a comparison.

### Edge attributes

- dominant direction
- counts by direction
- number of supporting findings
- number of unique sources

## Notes

- `QuantitativeFinding` is supporting evidence, not the primary graph edge type.
- The old organism-organism `RelativeAssociation` graph has been removed.
