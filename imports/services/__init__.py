"""Service entry points for admin-driven import preview and execution.

This package exposes two public functions:

- `build_preview()`
  Parse an uploaded file, validate it against the supported import contract,
  and return a session-safe preview payload that the admin flow can inspect
  before any database write occurs.
- `run_import()`
  Persist a previously confirmed preview payload, create the corresponding
  `ImportBatch`, and return the completed batch record.

Callers should import only from `imports.services`. The rest of the package is
internal structure for keeping the importer maintainable as the workbook flow
has grown larger than the original CSV-only implementation.

Package layout
--------------

Shared modules:

- `constants.py`
  Central registry for supported import types, workbook sheet names, controlled
  vocabularies, and other importer constants that need to stay aligned across
  preview and write paths.
- `helpers.py`
  Low-level parsing and normalization helpers shared by both CSV and workbook
  imports. This includes workbook loading, scalar coercion, note merging, and
  ORM resolution helpers used during preview validation.
- `types.py`
  Lightweight dataclasses that represent preview sections, row summaries, and
  issue collections before they are serialized into the session.

CSV import path:

- `csv_preview.py`
  Preview builders for the single-file CSV contracts. These functions validate
  headers and rows, resolve foreign keys where needed, and produce the same
  preview contract consumed by the admin confirmation UI.
- `runners.py`
  Create-only write runners for CSV previews after confirmation. Each runner is
  intentionally narrow and assumes preview validation has already happened.

Workbook import path:

- `workbook.py`
  Thin facade for workbook-specific entry points. This is the only workbook
  module that `__init__` imports directly so the public API stays stable even
  if the internal workbook modules are rearranged later.
- `workbook_common.py`
  Shared workbook state containers and helper functions used while building a
  multi-sheet preview. This keeps row-level preview bookkeeping out of the
  section-specific builders.
- `workbook_sections.py`
  Preview builders for the core workbook sheets:
  `paper`, `groups`, `comparissons`, `organisms`, `qualitative_findings`,
  `quantitative_findings`, and `diversity_metrics`. These functions validate
  cross-sheet IDs and translate workbook-specific values into the current
  schema-oriented import representation.
- `workbook_metadata.py`
  Logic for staging freeform workbook metadata into the slim EAV layer. This
  module extracts metadata-like columns from workbook rows, creates the preview
  records needed for `MetadataVariable` and `MetadataValue`, and keeps that
  behavior separate from the core sheet parsing code.
- `workbook_runners.py`
  Confirmed-write execution for workbook previews. This module creates the
  final `Study`, `Group`, `Comparison`, finding, diversity, and metadata rows
  in the required order after preview validation has already established a
  coherent workbook state.

Flow overview
-------------

1. `build_preview()` routes by `import_type`.
2. CSV files are handled by `csv_preview.py`.
3. Excel workbooks are handled by `workbook.py`, which delegates to the
   workbook-specific modules above.
4. `run_import()` routes the confirmed preview to either `runners.py` or
   `workbook_runners.py`.

Design constraints
------------------

- The admin UI expects a single preview/result contract regardless of source
  format, so CSV and workbook paths intentionally converge on the same payload
  shape.
- Imports remain create-only. Validation and duplicate detection happen during
  preview, and the write phase assumes that preview data is authoritative.
- The package is split by importer responsibility rather than by Django model
  so that preview logic, write logic, and workbook-specific transformations are
  easier to trace and test independently.
"""

import csv
from io import StringIO

from django.db import transaction

from database.models import ImportBatch

from .constants import SUPPORTED_IMPORT_TYPES
from .csv_preview import PREVIEW_BUILDERS
from .runners import IMPORT_RUNNERS
from .workbook import build_workbook_preview, run_workbook_import


def build_preview(*, file_name, content, import_type, batch_name):
    """Build a preview payload for either a CSV contract file or the curator workbook."""
    if import_type not in SUPPORTED_IMPORT_TYPES:
        raise ValueError(f'Unsupported import type: {import_type}')

    if import_type == 'excel_workbook':
        return build_workbook_preview(
            file_name=file_name,
            content=content,
            batch_name=batch_name,
        )

    reader = csv.DictReader(StringIO(content))
    fieldnames = reader.fieldnames or []
    rows = list(reader)
    preview_builder = PREVIEW_BUILDERS[import_type]
    return preview_builder(
        file_name=file_name,
        fieldnames=fieldnames,
        rows=rows,
        batch_name=batch_name,
        import_type=import_type,
    )


@transaction.atomic
def run_import(preview_data):
    """Persist a previously confirmed preview payload and record the result in `ImportBatch`."""
    import_type = preview_data['import_type']
    if import_type == 'excel_workbook':
        return run_workbook_import(preview_data)

    if import_type not in IMPORT_RUNNERS:
        raise ValueError(f'Unsupported import type: {import_type}')

    batch = ImportBatch.objects.create(
        name=preview_data['batch_name'],
        import_type=f'{import_type}_csv',
        status=ImportBatch.Status.VALIDATED,
        source_file=preview_data.get('file_name', ''),
    )

    created_count = IMPORT_RUNNERS[import_type](preview_data['valid_rows'], batch)
    duplicate_count = len(preview_data.get('duplicates', []))
    error_count = len(preview_data.get('errors', []))
    batch.success_count = created_count
    batch.error_count = duplicate_count + error_count
    batch.status = ImportBatch.Status.COMPLETED if error_count == 0 else ImportBatch.Status.FAILED
    batch.notes = (
        f'Imported {created_count} {import_type} rows from CSV. '
        f'Skipped {duplicate_count} duplicates. '
        f'Validation errors: {error_count}.'
    )
    batch.save(update_fields=['success_count', 'error_count', 'status', 'notes'])
    return batch
