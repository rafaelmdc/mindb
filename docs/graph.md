# Graph Overview

This project currently exposes two server-rendered graph views built from curated `QualitativeFinding` data:

- `Disease Network` at `/graph/disease/`
- `Co-abundance Taxon Network` at `/graph/co-abundance/`

`QuantitativeFinding` remains supporting evidence for the browser and future analysis work. It is not the primary edge source for either current graph.

## Shared architecture

Both graph pages follow the same high-level flow:

1. `core.views` loads filtered `QualitativeFinding` rows with the required `Comparison`, `Group`, `Study`, and `Taxon` joins.
2. `core.graph_payloads` converts those rows into JSON-ready node and edge payloads.
3. The payload is embedded in the template with `json_script`.
4. The page renders the graph with either Cytoscape or ECharts, selected by the user.

The graph layer is intentionally derived at request time. There are no stored graph tables or background graph materialization jobs in the current implementation.

## Shared controls

Both graph pages support:

- study filter
- disease text query
- taxon text query
- taxonomic branch filter
- grouping rank selector:
  - `leaf`
  - `species`
  - `genus`
  - `family`
  - `order`
  - `class`
  - `phylum`
- renderer selector:
  - `cytoscape`
  - `echarts`

Both pages also expose per-engine layout controls. Cytoscape and ECharts use different parameter sets and defaults, so the visible sliders change when the engine changes.

Shared filter names do not always have identical semantics across both graphs. In particular, the disease graph taxon-detail launch uses the exact lineage-aware `branch` filter plus an explicit `group_rank`, while the disease graph `taxon` field remains a free-text finding-level filter.

## Shared interactions

Both graph pages now support the same core interaction model in Cytoscape and ECharts:

- click one or more nodes to build a cumulative selection
- selected nodes stay highlighted until clicked again or cleared
- immediate neighbors are shown as context
- non-neighbor nodes and edges fade
- `Clear focus` resets the full current selection
- right click opens a small action menu for the selected graph element where actions are available

The current implementation keeps this state entirely client-side. No graph selection is stored in the database or session.

The supporting-evidence tables on both graph pages also paginate client-side from the already-loaded graph JSON. Normal page-number clicks update only the evidence table and URL state instead of rebuilding the graph, while direct full-page loads still have a server-rendered fallback.

## Disease graph

The disease graph is a comparison-centered qualitative network.

- diseases are derived from `Comparison.group_a.condition`, falling back to `Comparison.group_a.name`
- enriched taxa are rendered as one taxon role column
- depleted taxa are rendered as a separate taxon role column
- edges aggregate leaf-level findings into the selected grouping rank
- taxon-detail deep links into this graph use `branch=<taxon_id>` with a matching `group_rank`, rather than relying on the free-text `taxon` query

Canonical documentation:

- [Disease Graph](disease_graph.md)

## Co-abundance graph

The co-abundance graph is a derived taxon-pair pattern view.

- pairs are generated from findings that appear in the same `Comparison`
- qualitative directions are normalized into positive vs negative buckets
- pair support is tracked as `same_direction`, `opposite_direction`, or `mixed`
- edges are aggregated across comparisons and optionally filtered by minimum support

### Co-abundance edge evidence

Co-abundance edges now expose a dedicated evidence page at `/graph/co-abundance/edge-detail/`.

The edge-detail route:

- receives the current graph filters through GET params
- receives the selected grouped taxon pair through `source_taxon` and `target_taxon`
- rebuilds the filtered co-abundance context at request time
- isolates the selected grouped-taxon edge
- shows aggregate same-vs-opposite support counts
- paginates supporting comparisons
- paginates the exact `QualitativeFinding` rows that rolled up into the selected edge

This keeps the graph page lightweight while still giving users a traceable path back to row-level evidence.

Canonical documentation:

- [Co-abundance Graph](co_abundance_graph.md)

## Shared caveats

- Both views are exploratory and should not be presented as causal or mechanistic evidence.
- Rank rollup can omit findings when no ancestor exists at the selected rank. The UI reports those skipped counts.
- The browser remains the source of truth for row-level inspection. The graph pages are derived summaries with context-menu shortcuts into the underlying browser views.
