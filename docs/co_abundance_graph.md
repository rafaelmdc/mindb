# Co-abundance Graph

## Purpose

The co-abundance graph at `/graph/co-abundance/` is a derived taxon-pair pattern view built from shared qualitative comparison context.

It helps users explore questions like:

- which taxa are repeatedly reported in the same direction within the same comparison
- which taxa are repeatedly reported in opposite directions
- which taxon pairs have mixed literature support
- how pair patterns change after lineage rollup or branch filtering

This page is exploratory. It summarizes repeated co-patterns in the curated literature and should not be interpreted as proof of direct biological interaction.

## Data source

Primary source:

- `QualitativeFinding`

Required joins:

- `QualitativeFinding.comparison`
- `Comparison.study`
- `Comparison.group_a`
- `Comparison.group_b`
- `QualitativeFinding.taxon`

Taxonomic rollup support:

- `TaxonClosure`

## Pair generation logic

The current implementation derives edges at request time.

1. Load filtered qualitative findings.
2. Roll each finding up to the selected grouping rank when requested.
3. Normalize directions into two buckets:
   - positive:
     `enriched`, `increased`
   - negative:
     `depleted`, `decreased`
4. Within each `Comparison`, deduplicate local items by grouped taxon plus normalized direction.
5. Generate unordered grouped-taxon pairs inside that comparison.
6. Classify each local pair as:
   - `same_direction`
   - `opposite_direction`
7. Count leaf-level support for each grouped pair from the underlying leaf taxa that sit under each grouped taxon inside that comparison.
8. Aggregate those leaf-level pair counts across comparisons and studies, while also retaining separate comparison breadth counts.

The payload stores a stable `source` and `target` order for rendering and table output, but the graph meaning is a taxon-pair relationship, not a causal directional statement.

## Filters and controls

The page supports:

- `study`
- `disease`
- `taxon`
- `branch`
- `group_rank`
- `pattern`
- `support_mode`
- `min_support`
- `engine`

Pattern choices:

- `all`
- `same_direction`
- `opposite_direction`
- `mixed`

Supported grouping ranks:

- `leaf`
- `species`
- `genus`
- `family`
- `order`
- `class`
- `phylum`

Supported renderers:

- `cytoscape`
- `echarts`

As with the disease graph, the visible layout sliders are renderer-specific.

Support modes:

- `leaf`
  Counts support from underlying leaf-level taxon pairs after rollup. This is the higher-resolution mode.
- `rolled_up`
  Counts support the old way, where each grouped pair can contribute at most one same-direction and one opposite-direction support event per comparison after rollup.

Co-abundance taxon filtering is applied after pair generation, not when loading the raw findings queryset. This preserves the full within-comparison taxon context needed to build edges, then keeps only edges involving the queried taxon or its lineage descendants or ancestors that remain visible at the selected grouping rank.

## Node semantics

Each node represents one grouped taxon at the selected rank.

Node payload includes:

- taxon label
- taxon primary key
- rank
- taxonomy id
- grouping rank
- degree
- study count
- contributing leaf taxon count

## Edge semantics

Each edge represents repeated pair support between two grouped taxa across filtered comparisons.

Edge payload includes:

- `dominant_pattern`
- `same_direction_count`
- `opposite_direction_count`
- `total_support`
- `same_direction_comparison_count`
- `opposite_direction_comparison_count`
- `comparison_count`
- `study_count`
- `source_count`
- contributing comparison labels
- contributing disease labels
- contributing leaf taxon count

Dominant pattern rules:

- `same_direction` when same-direction leaf support is greater
- `opposite_direction` when opposite-direction leaf support is greater
- `mixed` when both leaf-support types exist and are tied

The `min_support` filter is applied to leaf-level total support after aggregation.

## Summary cards

The page reports:

- taxon count
- edge count
- total leaf-level supports
- study count
- same-direction edge count
- opposite-direction edge count
- mixed edge count

As in the disease graph, skipped rollups are surfaced when selected taxa do not have an ancestor at the chosen rank.

## Browser integrations

The current co-abundance graph context menu exposes:

- taxon node -> taxon detail page

The browser remains the intended place for detailed row-level inspection once a taxon pair of interest has been identified.

The main graph page now uses a paginated supporting-evidence table instead of a full inline all-edges dump. Rows are sorted by stronger edges first and link to the dedicated paginated edge evidence page for that pair.

When JavaScript is available, evidence-table pagination happens in place from the already-loaded graph JSON, so paging through edge rows does not rerender the graph canvas. The current table page is still reflected in the `edge_page` query param, and direct full-page loads still have a server-rendered fallback.

The interactive graph header also exposes `Download PNG` and `Download SVG` actions. These exports are generated client-side from the current rendered graph state, so focused taxa and faded context are preserved in the downloaded network image.

## Caveats

- This graph is derived from shared comparison context, not from abundance correlation matrices.
- It is not causal, mechanistic, or temporal.
- It is not currently built from `QuantitativeFinding`.
- Edge classification is comparison-aware, but the main strength metric is leaf-level pair support after rollup rather than one boolean event per grouped pair per comparison.
