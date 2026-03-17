# Graph Design

## Purpose

The graph view represents qualitative microbiome findings derived from curated `QualitativeFinding` records.

Its purpose is to let users visually explore:

- which organisms are reported as enriched for a disease
- which organisms are reported as depleted for a disease
- how many supporting findings exist for each disease-taxon connection

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

- one node type represents a disease-like target condition derived from `Comparison.group_a`
- organism nodes are split by directional role:
  - enriched organisms appear in the left column
  - depleted organisms appear in the right column
  - the same organism label may appear on both sides when evidence exists in both directions

### Edge meaning

An edge represents one or more qualitative findings linking an organism role node to a disease node.

### Edge attributes

- dominant direction
- number of supporting findings
- number of unique sources
- contributing comparison labels

## Notes

- `QuantitativeFinding` is supporting evidence, not the primary graph edge type.
- The old organism-organism `RelativeAssociation` graph has been removed.
- The current web layout is intentionally columnar:
  - left: enriched organisms
  - center: diseases
  - right: depleted organisms
