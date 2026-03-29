# MINdb — State-Node Directional Graph Concept

## Goal

Add a second derived graph view that represents directional qualitative pattern relationships between taxon states rather than plain taxon nodes.

This view is intended to support statements like:

- when taxon A is reported increased, taxon B is often also reported increased
- when taxon A is reported increased, taxon B is often reported decreased
- when taxon A is reported decreased, taxon B is often reported increased
- when taxon A is reported decreased, taxon B is often also reported decreased

The graph is meant to express repeated literature patterns, not causation.

---

## Why this is a different view

The current directional taxon network is fundamentally a signed undirected co-pattern graph:

- taxon A and taxon B move in the same direction
- taxon A and taxon B move in opposite directions

That is useful, but it does not support directional statements cleanly.

If we want a view that reads more like:

- `A up -> B down`
- `A down -> B up`

then the nodes cannot just be taxa.

They need to be **taxon-state nodes**.

---

## Core idea

Each node represents one taxon in one directional state.

Examples:

- `Blautia ↑`
- `Blautia ↓`
- `Bacteroides ↑`
- `Bacteroides ↓`

Each edge represents repeated co-occurrence of one state with another state within the same comparison context.

Examples:

- `Blautia ↑ -> Roseburia ↑`
- `Blautia ↑ -> Bacteroides ↓`
- `Blautia ↓ -> Prevotella ↑`

This makes the arrow notation descriptive rather than fake-causal.

---

## Important framing

This graph should be described as:

- directional in representation
- comparison-derived
- pattern-based
- exploratory

This graph should **not** be described as:

- causal
- mechanistic
- temporal
- intervention-based

Suggested wording:

> A directional state graph connecting taxon-direction states that are repeatedly reported together within shared comparison contexts.

---

## What the arrow means

The arrow should not mean:

- A biologically causes B to change
- A temporally precedes B

The arrow should mean:

- the graph is expressing an ordered relation between two reported taxon states
- one state is being used as the source anchor for a repeated co-pattern involving another state

In practice:

- `A ↑ -> B ↓` means comparisons repeatedly contain both “A increased” and “B decreased”
- `A ↓ -> B ↑` means comparisons repeatedly contain both “A decreased” and “B increased”

This is directional notation for a state relationship, not causal inference.

---

## Node semantics

Each node is:

- one canonical `Taxon`
- at one selected grouping rank
- in one normalized state

Recommended state buckets:

- `up`
  - derived from `enriched`
  - derived from `increased`
- `down`
  - derived from `depleted`
  - derived from `decreased`

Examples:

- `Faecalibacterium ↑`
- `Faecalibacterium ↓`
- `Bacteroides ↑`
- `Bacteroides ↓`

This immediately makes opposite-state patterns legible.

---

## Edge semantics

An edge connects one state-node to another state-node when both states appear in the same comparison context.

Examples:

- `A ↑ -> B ↑`
- `A ↑ -> B ↓`
- `A ↓ -> B ↑`
- `A ↓ -> B ↓`

Edges should aggregate across many comparisons and expose:

- number of supporting comparisons
- number of supporting studies
- number of sources
- disease or condition labels
- comparison labels

---

## Symmetry and duplication

This view raises an important modeling choice.

If one comparison contains:

- `A ↑`
- `B ↓`

then mathematically both of these are true:

- `A ↑ -> B ↓`
- `B ↓ -> A ↑`

So a naive implementation would create mirrored edges.

That is usually too noisy.

### Recommended approach

Choose one canonical ordering rule for display, while keeping the directional state notation.

Examples of possible canonical rules:

- alphabetical by node label
- taxon id order
- stable sort by `(taxon_id, state)`

This means the arrow is used to present a state-pair relationship in a readable form, not to claim asymmetric biology.

Alternative later option:

- allow mirrored edges in a matrix or adjacency-table view rather than in the main network graph

For the graph itself, canonical single-edge display is cleaner.

---

## What “mixed” means here

There are two kinds of mixedness to distinguish.

### Edge-level mixed support

For one taxon pair, the literature may support more than one state relation:

- `A ↑ -> B ↓`
- `A ↑ -> B ↑`
- `A ↓ -> B ↑`
- `A ↓ -> B ↓`

If the selected view aggregates too broadly, these patterns can mix.

### Recommended solution

Do **not** collapse all taxon-pair behavior into one edge too early.

Instead:

- treat each state-pair as its own edge type
- only label an edge `mixed` if the UI deliberately rolls multiple state-pair patterns together for summary

That keeps the graph cleaner and more honest.

---

## Best first scope

The first version should stay narrow.

### Included

- build from `QualitativeFinding`
- create state-nodes at one grouping rank
- support disease or condition filtering
- support study filtering
- support branch filtering
- support minimum-support thresholds
- show edges like:
  - `up -> up`
  - `up -> down`
  - `down -> up`
  - `down -> down`

### Excluded for V1

- causal claims
- effect-size weighting
- quantitative values
- temporal ordering
- explicit intervention evidence
- stored graph cache tables

---

## Why this is useful

This view is useful because it says more than “same” or “opposite”.

It can distinguish:

- co-enrichment
- co-depletion
- enriched-vs-depleted patterning
- depleted-vs-enriched patterning

That gives users a more expressive graph without pretending the data is causal.

---

## Product wording

Recommended short description:

> An exploratory state-node graph that connects taxon-direction states repeatedly reported together within shared comparison contexts.

Recommended caveat:

> This view summarizes repeated qualitative state patterns from curated findings. Arrow direction is representational and does not imply causation, mechanism, or temporal order.

---

## Suggested node labels

Recommended label format:

- `Taxon ↑`
- `Taxon ↓`

Alternative if arrows render poorly:

- `Taxon (up)`
- `Taxon (down)`

The arrow form is clearer if the frontend renders it cleanly.

---

## Suggested color semantics

Recommended node colors:

- `up` nodes in a green or teal family
- `down` nodes in a red or orange family

Recommended edge colors:

- neutral edge color by default
- optional edge coloring based on target state:
  - toward `up` target nodes
  - toward `down` target nodes

The node state should carry most of the semantic load.

---

## Relationship to the current graph suite

This state-node graph would become a third graph lens in MINdb:

1. current disease-centered graph
   - disease to taxon findings
2. current directional taxon network
   - taxon to taxon same/opposite pattern graph
3. future state-node graph
   - taxon-state to taxon-state directional pattern graph

Together these would cover:

- disease-oriented evidence
- pairwise same/opposite pattern structure
- explicit state-pair pattern structure

---

## Recommended implementation stance

When this is implemented later, it should:

- remain derived from the current qualitative data model
- avoid adding a new primary schema model
- avoid causal language
- prefer explicit state-node semantics over ambiguous taxon-only arrows

If later performance requires caching, the cache should be for derived view output only, not for new scientific source-of-truth records.
