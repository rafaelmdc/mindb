# Disease Graph

## Purpose

The disease graph at `/graph/disease/` is the main qualitative network view for comparison-centered exploration.

It is built from curated `QualitativeFinding` rows and answers questions like:

- which taxa are repeatedly reported as enriched for a disease-like target group
- which taxa are repeatedly reported as depleted
- how those findings change when rolled up from leaf taxa to a higher rank
- how the pattern changes inside one selected taxonomic branch

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

## Filters and controls

The page supports:

- `study`
- `direction`
- `disease`
- `taxon`
- `branch`
- `group_rank`
- `engine`

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

Each renderer exposes its own layout controls. Cytoscape uses repulsion, edge-length scale, and gravity values tuned for its force layout. ECharts exposes repulsion, edge length, and gravity values for its own force graph implementation.

Filter semantics:

- `taxon` is a free-text filter on the finding taxon label and rank
- `branch` is the lineage-aware exact taxon-scope filter backed by `TaxonClosure`

The disease graph taxon-detail launch uses `branch`, not `taxon`, so the graph opens with an exact lineage scope instead of relying on text matching.

## Node semantics

The graph uses two node types:

- disease nodes
- taxon nodes

Disease label derivation:

- use `Comparison.group_a.condition` when present
- otherwise fall back to `Comparison.group_a.name`

Taxon role split:

- enriched and increased findings are mapped to the `enriched` column
- depleted and decreased findings are mapped to the `depleted` column

This means the same grouped taxon can appear twice when evidence exists on both sides of the graph.

## Edge semantics

Each edge represents one or more qualitative findings connecting one taxon-role node to one disease node.

Edge payload includes:

- grouped taxon label
- disease label
- direction summary column
- finding count
- study count
- source count
- contributing comparison labels
- contributing leaf taxon count

Edges are aggregated after rank rollup. The stored database rows remain leaf-level findings.

## Layout behavior

The page is intentionally columnar before the renderer relaxes the layout:

- enriched taxa start on the left
- disease nodes start in the center
- depleted taxa start on the right

This preserves the qualitative meaning even when the chosen renderer moves nodes to reduce overlap.

## Browser integrations

The disease graph includes context-menu shortcuts into the browser:

- taxon node -> taxon detail page
- disease node -> matching group list filtered by condition
- edge -> supporting comparison list filtered by disease, branch, and direction grouping
- edge -> supporting qualitative finding list filtered by disease, branch, and direction grouping

These shortcuts are the intended path from a summary edge back to row-level evidence.

The main graph page now keeps a paginated supporting-evidence table instead of a full inline payload dump. Rows are sorted by stronger edges first and link directly to paginated supporting comparisons and qualitative findings.

When JavaScript is available, evidence-table pagination happens in place from the already-loaded graph JSON, so browsing evidence pages does not rerender the graph canvas. The current table page is still reflected in the `edge_page` query param, and direct full-page loads still have a server-rendered fallback.

The taxon browser also includes an `Open in disease graph` action. That launch uses:

- `branch=<taxon_id>`
- `group_rank=leaf` for leaf taxa
- `group_rank=<taxon.rank>` for supported ancestor ranks such as `genus` or `family`

This keeps the launch exact and bookmarkable while preserving a sensible default rollup for the selected taxon page.

## Summary cards

The page reports:

- disease count
- enriched grouped-taxon count
- depleted grouped-taxon count
- finding count

When rollup omits findings because no ancestor exists at the selected rank, the page also shows a skipped-findings alert.

## Caveats

- This is an exploratory view over curated qualitative findings.
- It is not a causal graph.
- Direction comes from the qualitative finding relative to the comparison context, not from temporal sequencing.
- `QuantitativeFinding` is not currently used as the primary edge source for this graph.
