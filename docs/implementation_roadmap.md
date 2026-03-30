# Implementation Roadmap

This document translates the planned work in `docs/roadmap.md` into a practical implementation sequence for the current codebase.

It assumes the current architecture remains unchanged:

- Django-first
- server-rendered templates
- graph payloads built at request time
- no new primary graph tables
- no SPA rewrite

## Current baseline

Already implemented:

- `Disease Network` at `/graph/disease/`
- `Co-abundance Taxon Network` at `/graph/co-abundance/`
- Cytoscape and ECharts graph renderers
- graph filtering by study, disease query, taxon query, branch, and grouping rank
- co-abundance filters for pattern and minimum support
- browser deep links from the disease graph into supporting comparison and finding views
- multi-select focus behavior with consistent neighborhood fading in Cytoscape and ECharts
- co-abundance edge right-click actions with a dedicated evidence page at `/graph/co-abundance/edge-detail/`

Main planned changes from `docs/roadmap.md`:

1. export the current graph selection
2. open graph-highlighted taxa in the browser via filters
3. replace large graph payload tables with paged supporting-result views

## Guiding principles

- prefer the smallest correct change
- keep the graph pages server-rendered
- reuse current browser list views instead of building parallel data UIs
- keep graph-derived evidence read-only and traceable back to `QualitativeFinding`
- avoid schema changes unless a later phase proves they are required

## Recommended implementation order

### Phase 1: ECharts focus parity

Status:

- implemented, with cumulative multi-select behavior retained across both graph pages

Goal:

- make ECharts graph interaction feel closer to Cytoscape when a user clicks a node

Why first:

- lowest product risk
- isolated mostly to frontend graph rendering
- improves both graph pages without changing data contracts

Scope:

- clicking a node in ECharts should clearly highlight the node and its immediate neighborhood
- non-neighbor nodes and edges should fade consistently
- repeated click should clear focus
- preserve current zoom-based label behavior

Likely files:

- `templates/core/graph.html`
- `templates/core/directional_taxon_network.html`
- optionally `static/css/site.css` if focus styling is easier to centralize

Implementation notes:

- keep the current `focusedNodeId` mechanism
- extend ECharts node and edge styling so the focused state visually matches the Cytoscape faded/context/focused behavior more closely
- keep this entirely client-side

Validation:

- click node in disease graph with `engine=echarts`
- click node in co-abundance graph with `engine=echarts`
- confirm focus and clear-focus button still work
- confirm context menus still work after focus changes

### Phase 2: Co-abundance edge detail on right click

Status:

- implemented with a dedicated evidence route and paginated supporting comparison and finding sections

Goal:

- add edge right-click actions for co-abundance edges that open a dedicated evidence page

Why second:

- directly addresses the highest-value co-abundance UX request
- depends on edge interaction being stable first

Scope:

- right click on a co-abundance edge opens the same style of action panel already used for graph interactions
- the edge action panel should stay small and navigational
- the panel should include a link to a dedicated server-rendered evidence page for that edge
- the dedicated evidence page should generate the supporting information on request
- do not try to render all supporting edge values inside the context menu itself
- assume some edges may eventually have very large support sets, including thousands of contributing rows or derived items

Likely files:

- `core/views.py`
- `core/urls.py`
- `core/graph_payloads.py`
- `templates/core/directional_taxon_network.html`
- possibly a new template such as `templates/core/co_abundance_edge_detail.html`

Implementation notes:

- the current co-abundance graph already has edge payload identity in memory, but it does not yet expose edge actions
- the graph payload needs a stable edge-detail query contract so the frontend can build a URL from the selected edge
- the edge panel should expose one or two actions only, for example:
  - `Open edge evidence`
  - optionally `Open matching taxa`
- the evidence page should be server-rendered and paginated where needed
- avoid embedding large comparison lists or calculation dumps into the context menu
- keep the menu as an action launcher, not a data container

Recommended URL contract:

- create a new route under `core`, for example `/graph/co-abundance/edge-detail/`
- pass the current graph state through GET params:
  - `study`
  - `disease`
  - `taxon`
  - `branch`
  - `group_rank`
  - `pattern`
  - `min_support`
- pass the selected edge identity through GET params, for example:
  - `source_taxon`
  - `target_taxon`

Recommended backend behavior:

- rebuild the filtered co-abundance context on the server using the same inputs as the graph page
- isolate the selected grouped-taxon pair
- show the aggregate counts for that edge
- show supporting comparisons and findings in paginated sections or linked paginated browser views
- keep the computation request-scoped so there is no new persisted edge model

Possible small payload additions:

- raw `source_taxon_pk`
- raw `target_taxon_pk`
- a canonical edge-detail URL generated from current filters
- structured labels if the template needs to render richer action text

Validation:

- right click same-direction edge and confirm action panel opens
- right click opposite-direction edge and confirm action panel opens
- right click mixed edge and confirm action panel opens
- open the edge evidence page and confirm it reflects the same filtered graph context
- confirm the evidence page remains usable with paginated large result sets

### Phase 3: Open highlighted taxa in the browser

Status:

- implemented for disease-graph launches from the taxon detail page
- co-abundance launch deferred because it needs a different relation-aware filter contract

Goal:

- let users open a selected taxon from the taxon browser directly into a graph view filtered to that taxon

Why third:

- builds on the existing taxon browser as the main entry point
- gives users a direct “show me this taxon’s network relations” workflow
- avoids introducing extra graph-side selection state

Scope:

- from the taxon page, add actions that open the desired graph with filters that preserve the intended taxonomic scope
- the graph should load already narrowed to the selected taxon page context
- current implementation covers the disease graph only

Recommended first implementation:

- add graph launch buttons on:
  - taxon detail page
  - optionally taxon list rows later
- the launch should point to graph routes with GET params such as:
  - disease graph:
    `/graph/disease/?branch=<taxon_id>&group_rank=<taxon_rank_or_leaf>`
- use the exact `branch` filter for disease-graph launches so ancestor taxa open as lineage scopes instead of text matches
- for leaf taxa, set `group_rank=leaf`
- for supported ancestor ranks such as `genus` or `family`, set `group_rank` to the viewed taxon rank

Recommended UX:

- on a taxon detail page, show actions such as:
  - `Open in disease graph`
- when the disease graph loads, the branch filter should already reflect the selected taxon and the grouping rank should match the viewed taxon context
- the resulting graph should show the selected lineage scope without depending on free-text taxon matching
- do not expose a co-abundance launch until its taxon-filter contract is intentionally designed

Likely files:

- `templates/database/organism_detail.html`
- optionally `templates/database/organism_list.html`
- possibly `database/views.py` only if extra context helpers are needed

Implementation notes:

- do not add backend session state for this
- use simple GET links so the graph URL is bookmarkable and shareable
- prefer exact taxon identity for browser launches when the graph already supports an exact branch filter
- keep the disease graph `taxon` text input as a separate free-text filter rather than overloading it with branch semantics

Validation:

- open a taxon detail page
- launch disease graph from a leaf taxon and confirm `branch` and `group_rank=leaf` are present
- launch disease graph from an ancestor taxon and confirm `branch` and the matching ancestor `group_rank` are present
- confirm the resulting graph is narrowed to the selected lineage scope

### Phase 4: Replace large graph payload tables with paged supporting views

Status:

- implemented with paginated supporting-evidence tables on both graph pages
- disease graph preview rows link into paginated comparison and qualitative-finding browser views
- co-abundance preview rows link into the paginated edge evidence page
- evidence-table page changes happen client-side from the loaded graph JSON, keep `edge_page` in the URL, and do not rebuild the graph canvas on normal pagination clicks

Goal:

- stop using large inline tables as the primary way to inspect graph evidence

Why fourth:

- current browser list views already paginate
- this reduces duplication and keeps graph pages lighter

Scope:

- reduce the large `Current graph payload` tables on both graph pages
- keep compact summary text on the graph pages
- add clear actions into supporting browser views instead

Recommended disease-graph behavior:

- keep summary cards
- keep compact graph explanation
- route users to paginated `ComparisonListView` and `QualitativeFindingListView` via current context actions
- paginate the graph-page evidence table in place when JavaScript is available, with a normal server-rendered fallback for direct loads

Recommended co-abundance behavior:

- add paged supporting result views instead of a full inline all-edges table
- paginate the graph-page evidence table in place when JavaScript is available
- keep dedicated edge evidence pages as the deeper paginated inspection path

Possible second-step option:

- create a dedicated paginated co-abundance evidence list view if the existing browser views are not sufficient

For co-abundance work, this likely becomes necessary as part of Phase 2 rather than a later enhancement.

Likely files:

- `templates/core/graph.html`
- `templates/core/directional_taxon_network.html`
- `database/views.py`
- `templates/database/comparison_list.html`
- `templates/database/qualitativefinding_list.html`

Implementation notes:

- prefer reusing existing pagination behavior in `BrowserListView`
- only add a new view if the current comparison/finding lists cannot express the needed evidence clearly
- do not introduce a separate graph-results app

Validation:

- confirm graph pages remain readable with larger payloads
- confirm supporting browser links open paginated results
- confirm no evidence path is lost when the large inline tables are reduced

### Phase 5: Graph export support

Status:

- implemented on both graph pages with direct `Download PNG` and `Download SVG` actions
- exports are generated client-side from the live renderer state
- no separate print route or print-mode page was added

Goal:

- let users export the current graph selection in a usable form

Why fifth:

- useful, but lower leverage than interaction and evidence navigation
- easier to do once the selection model and summary UI are settled

Recommended first implementation:

- add direct graph export buttons on the interactive page
- support:
  - `PNG`
  - `SVG`
- export the live graph state rather than a separate report page

Recommended technical approach:

- keep this client-side
- use the renderer's own export path where possible
- avoid adding a separate server-side print route for V1

Likely files:

- `templates/core/graph.html`
- `templates/core/directional_taxon_network.html`

Implementation notes:

- use the current graph state so focused nodes and faded context carry into the export
- keep export actions close to the graph canvas controls

Validation:

- download disease graph as PNG and SVG
- download co-abundance graph as PNG and SVG
- confirm focused nodes and faded context are preserved in the export

## Cross-cutting backend refinements

These are not standalone phases, but they likely come up while doing the work above.

### Payload structure cleanup

For both graph builders, consider adding small structured fields where the templates currently depend on comma-joined strings.

Likely file:

- `core/graph_payloads.py`

Useful additions:

- arrays for comparison labels and disease labels
- a compact calculation summary string for tooltips or export metadata if needed
- selected-node adjacency summaries if a future export mode needs them

### Browser filter polish

The browser already supports graph-driven filtering in some places.

Likely follow-up work:

- add clearer graph-launch actions from taxon pages
- add clearer banners describing graph-derived taxon filters
- keep all graph-to-browser links GET-based and bookmarkable

Likely files:

- `database/views.py`
- `templates/database/*.html`

## Testing strategy

Prefer narrow tests after each phase.

### Server-side tests

Likely file:

- `core/tests.py`

Add tests for:

- new graph query params if introduced
- any payload additions needed by templates
- browser highlight/filter query parsing
- export control markup

### Manual UI checks

For each graph page and both engines:

- load with default filters
- load with study, branch, and grouping-rank filters
- focus and clear focus
- right click node
- right click edge where supported
- follow browser deep links

## Risks and tradeoffs

### Risk: too much custom JS in templates

Mitigation:

- keep interactions incremental
- reuse existing focus/context-menu logic
- move only repeated helpers, not the whole graph system

### Risk: graph pages become overloaded with auxiliary data

Mitigation:

- keep the graph page as summary plus navigation
- push long evidence inspection back into paginated browser views

### Risk: co-abundance evidence needs more than the existing browser views can show

Mitigation:

- first try filtered `Comparison` and `QualitativeFinding` pages
- only add a dedicated evidence list if those views cannot express the relationship clearly

## Suggested milestone breakdown

Milestone 1:

- ECharts focus parity on both graph pages

Milestone 2:

- richer co-abundance edge detail on right click

Milestone 3:

- open focused taxa in browser with highlighting

Milestone 4:

- reduce large inline graph tables in favor of paginated supporting views

Milestone 5:

- export current graph selection

## Definition of done

This roadmap is complete when:

- both graph pages have consistent interaction quality across Cytoscape and ECharts
- graph selections can be sent into the browser cleanly
- large evidence inspection happens in paginated views instead of oversized inline tables
- co-abundance edge detail is understandable without reading raw payload fields
- graph export is useful for a filtered or focused graph state
