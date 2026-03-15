import csv
from dataclasses import asdict, dataclass
from io import StringIO

from django.db import transaction

from database.models import (
    AlphaMetric,
    BetaMetric,
    Comparison,
    Group,
    ImportBatch,
    MetadataValue,
    MetadataVariable,
    Organism,
    QualitativeFinding,
    QuantitativeFinding,
    Study,
)


@dataclass
class ImportPreview:
    batch_name: str
    import_type: str
    required_columns: list[str]
    file_name: str
    total_rows: int
    valid_rows: list[dict]
    errors: list[dict]
    duplicates: list[dict]

    def to_dict(self):
        return asdict(self)


SUPPORTED_IMPORT_TYPES = (
    'organism',
    'study',
    'group',
    'comparison',
    'metadata_variable',
    'metadata_value',
    'qualitative_finding',
    'quantitative_finding',
    'alpha_metric',
    'beta_metric',
)

BOOLEAN_TRUE_VALUES = {'1', 'true', 'yes', 'on'}
BOOLEAN_FALSE_VALUES = {'0', 'false', 'no', 'off'}


def build_preview(*, file_name, content, import_type, batch_name):
    if import_type not in SUPPORTED_IMPORT_TYPES:
        raise ValueError(f'Unsupported import type: {import_type}')

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
    import_type = preview_data['import_type']
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


def _missing_columns_preview(*, batch_name, import_type, file_name, required_columns, missing_columns):
    return ImportPreview(
        batch_name=batch_name,
        import_type=import_type,
        required_columns=list(required_columns),
        file_name=file_name,
        total_rows=0,
        valid_rows=[],
        errors=[
            {
                'row_number': None,
                'message': f'Missing required columns: {", ".join(missing_columns)}',
            }
        ],
        duplicates=[],
    )


def _build_preview_response(*, batch_name, import_type, file_name, required_columns, valid_rows, errors, duplicates):
    return ImportPreview(
        batch_name=batch_name,
        import_type=import_type,
        required_columns=list(required_columns),
        file_name=file_name,
        total_rows=len(valid_rows) + len(errors) + len(duplicates),
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _cleaned_row(raw_row):
    return {key: (value or '').strip() for key, value in raw_row.items()}


def _parse_int(value, field_name):
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, f'{field_name} must be an integer.'


def _parse_float(value, field_name):
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, f'{field_name} must be a float.'


def _parse_optional_int(value, field_name):
    if value == '':
        return None, None
    return _parse_int(value, field_name)


def _parse_optional_float(value, field_name):
    if value == '':
        return None, None
    return _parse_float(value, field_name)


def _parse_optional_bool(value, field_name):
    if value == '':
        return None, None
    normalized = value.lower()
    if normalized in BOOLEAN_TRUE_VALUES:
        return True, None
    if normalized in BOOLEAN_FALSE_VALUES:
        return False, None
    return None, f'{field_name} must be a boolean.'


def _resolve_study(study_doi, study_title):
    if study_doi:
        return Study.objects.filter(doi=study_doi).first()
    if study_title:
        return Study.objects.filter(title=study_title).first()
    return None


def _resolve_group(study_doi, study_title, group_name):
    if not group_name:
        return None
    study = _resolve_study(study_doi, study_title)
    if not study:
        return None
    return Group.objects.filter(study=study, name=group_name).select_related('study').first()


def _resolve_comparison(study_doi, study_title, group_a_name, group_b_name, label):
    study = _resolve_study(study_doi, study_title)
    if not study:
        return None
    return (
        Comparison.objects.filter(
            study=study,
            group_a__name=group_a_name,
            group_b__name=group_b_name,
            label=label,
        )
        .select_related('study', 'group_a', 'group_b')
        .first()
    )


def _resolve_organism(scientific_name, ncbi_taxonomy_id):
    if ncbi_taxonomy_id is not None:
        organism = Organism.objects.filter(ncbi_taxonomy_id=ncbi_taxonomy_id).first()
        if organism:
            return organism
    if scientific_name:
        return Organism.objects.filter(scientific_name__iexact=scientific_name).first()
    return None


def _row_requires_study_reference(row, errors, row_number):
    if row.get('study_doi') or row.get('study_title'):
        return True
    errors.append(
        {
            'row_number': row_number,
            'message': 'At least one of study_doi or study_title is required.',
        }
    )
    return False


def _build_organism_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('scientific_name', 'rank')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_taxonomy_ids = set(
        Organism.objects.exclude(ncbi_taxonomy_id__isnull=True).values_list('ncbi_taxonomy_id', flat=True)
    )
    existing_names = {name.lower() for name in Organism.objects.values_list('scientific_name', flat=True)}
    seen_taxonomy_ids = set()
    seen_names = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not row['scientific_name'] or not row['rank']:
            errors.append({'row_number': row_number, 'message': 'scientific_name and rank are required.'})
            continue

        taxonomy_id, taxonomy_error = _parse_optional_int(row.get('ncbi_taxonomy_id', ''), 'ncbi_taxonomy_id')
        if taxonomy_error:
            errors.append({'row_number': row_number, 'message': taxonomy_error})
            continue

        duplicate_name_key = row['scientific_name'].lower()
        if taxonomy_id is not None:
            if taxonomy_id in seen_taxonomy_ids:
                duplicates.append({'row_number': row_number, 'message': 'Duplicate ncbi_taxonomy_id in uploaded file.'})
                continue
            if taxonomy_id in existing_taxonomy_ids:
                duplicates.append({'row_number': row_number, 'message': 'Organism with this ncbi_taxonomy_id already exists.'})
                continue
        elif duplicate_name_key in seen_names or duplicate_name_key in existing_names:
            duplicates.append({'row_number': row_number, 'message': 'Organism with this scientific_name already exists.'})
            continue

        if taxonomy_id is not None:
            seen_taxonomy_ids.add(taxonomy_id)
        seen_names.add(duplicate_name_key)
        valid_rows.append(
            {
                'row_number': row_number,
                'ncbi_taxonomy_id': taxonomy_id,
                'scientific_name': row['scientific_name'],
                'rank': row['rank'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_study_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('title',)
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_dois = set(Study.objects.exclude(doi__isnull=True).exclude(doi='').values_list('doi', flat=True))
    existing_titles = {title.lower() for title in Study.objects.values_list('title', flat=True)}
    seen_dois = set()
    seen_titles = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not row['title']:
            errors.append({'row_number': row_number, 'message': 'title is required.'})
            continue

        year, year_error = _parse_optional_int(row.get('year', ''), 'year')
        if year_error:
            errors.append({'row_number': row_number, 'message': year_error})
            continue

        doi = row.get('doi', '')
        title_key = row['title'].lower()
        if doi:
            if doi in seen_dois:
                duplicates.append({'row_number': row_number, 'message': 'Duplicate doi in uploaded file.'})
                continue
            if doi in existing_dois:
                duplicates.append({'row_number': row_number, 'message': 'Study with this doi already exists.'})
                continue
            seen_dois.add(doi)
        elif title_key in seen_titles or title_key in existing_titles:
            duplicates.append({'row_number': row_number, 'message': 'Study with this title already exists.'})
            continue

        seen_titles.add(title_key)
        valid_rows.append(
            {
                'row_number': row_number,
                'doi': doi or None,
                'title': row['title'],
                'country': row.get('country', ''),
                'journal': row.get('journal', ''),
                'year': year,
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_group_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('study_doi', 'study_title', 'name')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(Group.objects.values_list('study_id', 'name'))
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['name']:
            errors.append({'row_number': row_number, 'message': 'name is required.'})
            continue

        study = _resolve_study(row['study_doi'], row['study_title'])
        if not study:
            errors.append({'row_number': row_number, 'message': 'Study reference does not resolve to an existing Study.'})
            continue

        sample_size, sample_size_error = _parse_optional_int(row.get('sample_size', ''), 'sample_size')
        if sample_size_error:
            errors.append({'row_number': row_number, 'message': sample_size_error})
            continue

        duplicate_key = (study.pk, row['name'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate study/group pair in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'Group with this study and name already exists.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'study_id': study.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'name': row['name'],
                'condition': row.get('condition', ''),
                'sample_size': sample_size,
                'cohort': row.get('cohort', ''),
                'site': row.get('site', ''),
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_comparison_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('study_doi', 'study_title', 'group_a_name', 'group_b_name', 'label')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(Comparison.objects.values_list('study_id', 'group_a_id', 'group_b_id', 'label'))
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_a_name'] or not row['group_b_name'] or not row['label']:
            errors.append({'row_number': row_number, 'message': 'group_a_name, group_b_name, and label are required.'})
            continue

        group_a = _resolve_group(row['study_doi'], row['study_title'], row['group_a_name'])
        group_b = _resolve_group(row['study_doi'], row['study_title'], row['group_b_name'])
        if not group_a or not group_b:
            errors.append({'row_number': row_number, 'message': 'Both groups must resolve to existing Group rows.'})
            continue
        if group_a.pk == group_b.pk:
            errors.append({'row_number': row_number, 'message': 'Comparison groups must be different.'})
            continue

        duplicate_key = (group_a.study_id, group_a.pk, group_b.pk, row['label'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate comparison row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'Comparison already exists for this study, groups, and label.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'study_id': group_a.study_id,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_a_id': group_a.pk,
                'group_b_id': group_b.pk,
                'group_a_name': group_a.name,
                'group_b_name': group_b.name,
                'label': row['label'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_metadata_variable_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('name', 'value_type')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_names = set(MetadataVariable.objects.values_list('name', flat=True))
    seen_names = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not row['name'] or not row['value_type']:
            errors.append({'row_number': row_number, 'message': 'name and value_type are required.'})
            continue
        if row['value_type'] not in MetadataVariable.ValueType.values:
            errors.append({'row_number': row_number, 'message': 'value_type must be one of: float, int, text, bool.'})
            continue

        is_filterable, bool_error = _parse_optional_bool(row.get('is_filterable', ''), 'is_filterable')
        if bool_error:
            errors.append({'row_number': row_number, 'message': bool_error})
            continue

        if row['name'] in seen_names:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate variable name in uploaded file.'})
            continue
        if row['name'] in existing_names:
            duplicates.append({'row_number': row_number, 'message': 'MetadataVariable with this name already exists.'})
            continue
        seen_names.add(row['name'])

        valid_rows.append(
            {
                'row_number': row_number,
                'name': row['name'],
                'display_name': row.get('display_name', ''),
                'value_type': row['value_type'],
                'is_filterable': False if is_filterable is None else is_filterable,
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_metadata_value_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('study_doi', 'study_title', 'group_name', 'variable_name')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(MetadataValue.objects.values_list('group_id', 'variable_id'))
    variables = {variable.name: variable for variable in MetadataVariable.objects.all()}
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_name'] or not row['variable_name']:
            errors.append({'row_number': row_number, 'message': 'group_name and variable_name are required.'})
            continue

        group = _resolve_group(row['study_doi'], row['study_title'], row['group_name'])
        if not group:
            errors.append({'row_number': row_number, 'message': 'Group reference does not resolve to an existing Group.'})
            continue

        variable = variables.get(row['variable_name'])
        if not variable:
            errors.append({'row_number': row_number, 'message': 'variable_name does not resolve to an existing MetadataVariable.'})
            continue

        typed_fields = {}
        typed_count = 0

        value_float, float_error = _parse_optional_float(row.get('value_float', ''), 'value_float')
        if float_error:
            errors.append({'row_number': row_number, 'message': float_error})
            continue
        typed_fields['value_float'] = value_float
        typed_count += value_float is not None

        value_int, int_error = _parse_optional_int(row.get('value_int', ''), 'value_int')
        if int_error:
            errors.append({'row_number': row_number, 'message': int_error})
            continue
        typed_fields['value_int'] = value_int
        typed_count += value_int is not None

        value_text = row.get('value_text', '')
        typed_fields['value_text'] = value_text or None
        typed_count += bool(value_text)

        value_bool, bool_error = _parse_optional_bool(row.get('value_bool', ''), 'value_bool')
        if bool_error:
            errors.append({'row_number': row_number, 'message': bool_error})
            continue
        typed_fields['value_bool'] = value_bool
        typed_count += value_bool is not None

        if typed_count != 1:
            errors.append({'row_number': row_number, 'message': 'Exactly one typed value field must be populated.'})
            continue

        expected_field = {
            MetadataVariable.ValueType.FLOAT: 'value_float',
            MetadataVariable.ValueType.INTEGER: 'value_int',
            MetadataVariable.ValueType.TEXT: 'value_text',
            MetadataVariable.ValueType.BOOLEAN: 'value_bool',
        }[variable.value_type]
        populated_field = next(field_name for field_name, value in typed_fields.items() if value is not None)
        if expected_field != populated_field:
            errors.append({'row_number': row_number, 'message': f'Variable "{variable.name}" requires {expected_field}.'})
            continue

        duplicate_key = (group.pk, variable.pk)
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate group/variable row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'MetadataValue already exists for this group and variable.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'group_id': group.pk,
                'variable_id': variable.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_name': row['group_name'],
                'variable_name': variable.name,
                **typed_fields,
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_qualitative_finding_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = (
        'study_doi',
        'study_title',
        'group_a_name',
        'group_b_name',
        'comparison_label',
        'organism_scientific_name',
        'direction',
        'source',
    )
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(
        QualitativeFinding.objects.values_list('comparison_id', 'organism_id', 'direction', 'source')
    )
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_a_name'] or not row['group_b_name'] or not row['comparison_label']:
            errors.append({'row_number': row_number, 'message': 'Comparison reference fields are required.'})
            continue
        if not row['organism_scientific_name'] or not row['direction'] or not row['source']:
            errors.append({'row_number': row_number, 'message': 'organism_scientific_name, direction, and source are required.'})
            continue

        comparison = _resolve_comparison(
            row['study_doi'],
            row['study_title'],
            row['group_a_name'],
            row['group_b_name'],
            row['comparison_label'],
        )
        if not comparison:
            errors.append({'row_number': row_number, 'message': 'Comparison reference does not resolve to an existing Comparison.'})
            continue

        taxonomy_id, taxonomy_error = _parse_optional_int(row.get('organism_ncbi_taxonomy_id', ''), 'organism_ncbi_taxonomy_id')
        if taxonomy_error:
            errors.append({'row_number': row_number, 'message': taxonomy_error})
            continue
        organism = _resolve_organism(row['organism_scientific_name'], taxonomy_id)
        if not organism:
            errors.append({'row_number': row_number, 'message': 'Organism reference does not resolve to an existing Organism.'})
            continue

        if row['direction'] not in QualitativeFinding.Direction.values:
            errors.append({'row_number': row_number, 'message': 'direction must be one of: enriched, depleted, increased, decreased.'})
            continue

        duplicate_key = (comparison.pk, organism.pk, row['direction'], row['source'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate qualitative finding row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'QualitativeFinding already exists for this comparison, organism, direction, and source.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'comparison_id': comparison.pk,
                'organism_id': organism.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_a_name': row['group_a_name'],
                'group_b_name': row['group_b_name'],
                'comparison_label': row['comparison_label'],
                'organism_scientific_name': organism.scientific_name,
                'direction': row['direction'],
                'source': row['source'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_quantitative_finding_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = (
        'study_doi',
        'study_title',
        'group_name',
        'organism_scientific_name',
        'value_type',
        'value',
        'source',
    )
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(
        QuantitativeFinding.objects.values_list('group_id', 'organism_id', 'value_type', 'source')
    )
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_name'] or not row['organism_scientific_name'] or not row['value_type'] or not row['source']:
            errors.append({'row_number': row_number, 'message': 'group_name, organism_scientific_name, value_type, and source are required.'})
            continue

        group = _resolve_group(row['study_doi'], row['study_title'], row['group_name'])
        if not group:
            errors.append({'row_number': row_number, 'message': 'Group reference does not resolve to an existing Group.'})
            continue

        taxonomy_id, taxonomy_error = _parse_optional_int(row.get('organism_ncbi_taxonomy_id', ''), 'organism_ncbi_taxonomy_id')
        if taxonomy_error:
            errors.append({'row_number': row_number, 'message': taxonomy_error})
            continue
        organism = _resolve_organism(row['organism_scientific_name'], taxonomy_id)
        if not organism:
            errors.append({'row_number': row_number, 'message': 'Organism reference does not resolve to an existing Organism.'})
            continue

        if row['value_type'] not in QuantitativeFinding.ValueType.values:
            errors.append({'row_number': row_number, 'message': 'value_type must be one of: relative_abundance.'})
            continue

        value, value_error = _parse_float(row.get('value', ''), 'value')
        if value_error:
            errors.append({'row_number': row_number, 'message': value_error})
            continue

        duplicate_key = (group.pk, organism.pk, row['value_type'], row['source'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate quantitative finding row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'QuantitativeFinding already exists for this group, organism, value_type, and source.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'group_id': group.pk,
                'organism_id': organism.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_name': row['group_name'],
                'organism_scientific_name': organism.scientific_name,
                'value_type': row['value_type'],
                'value': value,
                'unit': row.get('unit', ''),
                'source': row['source'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_alpha_metric_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = ('study_doi', 'study_title', 'group_name', 'metric', 'value', 'source')
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(AlphaMetric.objects.values_list('group_id', 'metric', 'source'))
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_name'] or not row['metric'] or not row['source']:
            errors.append({'row_number': row_number, 'message': 'group_name, metric, and source are required.'})
            continue

        group = _resolve_group(row['study_doi'], row['study_title'], row['group_name'])
        if not group:
            errors.append({'row_number': row_number, 'message': 'Group reference does not resolve to an existing Group.'})
            continue

        value, value_error = _parse_float(row.get('value', ''), 'value')
        if value_error:
            errors.append({'row_number': row_number, 'message': value_error})
            continue

        duplicate_key = (group.pk, row['metric'], row['source'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate alpha metric row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'AlphaMetric already exists for this group, metric, and source.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'group_id': group.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_name': row['group_name'],
                'metric': row['metric'],
                'value': value,
                'source': row['source'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _build_beta_metric_preview(*, file_name, fieldnames, rows, batch_name, import_type):
    required_columns = (
        'study_doi',
        'study_title',
        'group_a_name',
        'group_b_name',
        'comparison_label',
        'metric',
        'value',
        'source',
    )
    missing_columns = [column for column in required_columns if column not in fieldnames]
    if missing_columns:
        return _missing_columns_preview(
            batch_name=batch_name,
            import_type=import_type,
            file_name=file_name,
            required_columns=required_columns,
            missing_columns=missing_columns,
        )

    existing_keys = set(BetaMetric.objects.values_list('comparison_id', 'metric', 'source'))
    seen_keys = set()
    valid_rows = []
    errors = []
    duplicates = []

    for row_number, raw_row in enumerate(rows, start=2):
        row = _cleaned_row(raw_row)
        if not _row_requires_study_reference(row, errors, row_number):
            continue
        if not row['group_a_name'] or not row['group_b_name'] or not row['comparison_label'] or not row['metric'] or not row['source']:
            errors.append({'row_number': row_number, 'message': 'Comparison reference, metric, and source are required.'})
            continue

        comparison = _resolve_comparison(
            row['study_doi'],
            row['study_title'],
            row['group_a_name'],
            row['group_b_name'],
            row['comparison_label'],
        )
        if not comparison:
            errors.append({'row_number': row_number, 'message': 'Comparison reference does not resolve to an existing Comparison.'})
            continue

        value, value_error = _parse_float(row.get('value', ''), 'value')
        if value_error:
            errors.append({'row_number': row_number, 'message': value_error})
            continue

        duplicate_key = (comparison.pk, row['metric'], row['source'])
        if duplicate_key in seen_keys:
            duplicates.append({'row_number': row_number, 'message': 'Duplicate beta metric row in uploaded file.'})
            continue
        if duplicate_key in existing_keys:
            duplicates.append({'row_number': row_number, 'message': 'BetaMetric already exists for this comparison, metric, and source.'})
            continue
        seen_keys.add(duplicate_key)

        valid_rows.append(
            {
                'row_number': row_number,
                'comparison_id': comparison.pk,
                'study_doi': row['study_doi'],
                'study_title': row['study_title'],
                'group_a_name': row['group_a_name'],
                'group_b_name': row['group_b_name'],
                'comparison_label': row['comparison_label'],
                'metric': row['metric'],
                'value': value,
                'source': row['source'],
                'notes': row.get('notes', ''),
            }
        )

    return _build_preview_response(
        batch_name=batch_name,
        import_type=import_type,
        file_name=file_name,
        required_columns=required_columns,
        valid_rows=valid_rows,
        errors=errors,
        duplicates=duplicates,
    )


def _run_organism_import(valid_rows, batch):
    for row in valid_rows:
        Organism.objects.create(
            ncbi_taxonomy_id=row['ncbi_taxonomy_id'],
            scientific_name=row['scientific_name'],
            rank=row['rank'],
            notes=row['notes'],
        )
    return len(valid_rows)


def _run_study_import(valid_rows, batch):
    for row in valid_rows:
        Study.objects.create(
            doi=row['doi'],
            title=row['title'],
            country=row['country'],
            journal=row['journal'],
            year=row['year'],
            notes=row['notes'],
        )
    return len(valid_rows)


def _run_group_import(valid_rows, batch):
    for row in valid_rows:
        Group.objects.create(
            study_id=row['study_id'],
            name=row['name'],
            condition=row['condition'],
            sample_size=row['sample_size'],
            cohort=row['cohort'],
            site=row['site'],
            notes=row['notes'],
        )
    return len(valid_rows)


def _run_comparison_import(valid_rows, batch):
    for row in valid_rows:
        Comparison.objects.create(
            study_id=row['study_id'],
            group_a_id=row['group_a_id'],
            group_b_id=row['group_b_id'],
            label=row['label'],
            notes=row['notes'],
        )
    return len(valid_rows)


def _run_metadata_variable_import(valid_rows, batch):
    for row in valid_rows:
        MetadataVariable.objects.create(
            name=row['name'],
            display_name=row['display_name'],
            value_type=row['value_type'],
            is_filterable=row['is_filterable'],
        )
    return len(valid_rows)


def _run_metadata_value_import(valid_rows, batch):
    for row in valid_rows:
        MetadataValue.objects.create(
            group_id=row['group_id'],
            variable_id=row['variable_id'],
            value_float=row['value_float'],
            value_int=row['value_int'],
            value_text=row['value_text'],
            value_bool=row['value_bool'],
        )
    return len(valid_rows)


def _run_qualitative_finding_import(valid_rows, batch):
    for row in valid_rows:
        QualitativeFinding.objects.create(
            comparison_id=row['comparison_id'],
            organism_id=row['organism_id'],
            direction=row['direction'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
    return len(valid_rows)


def _run_quantitative_finding_import(valid_rows, batch):
    for row in valid_rows:
        QuantitativeFinding.objects.create(
            group_id=row['group_id'],
            organism_id=row['organism_id'],
            value_type=row['value_type'],
            value=row['value'],
            unit=row['unit'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
    return len(valid_rows)


def _run_alpha_metric_import(valid_rows, batch):
    for row in valid_rows:
        AlphaMetric.objects.create(
            group_id=row['group_id'],
            metric=row['metric'],
            value=row['value'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
    return len(valid_rows)


def _run_beta_metric_import(valid_rows, batch):
    for row in valid_rows:
        BetaMetric.objects.create(
            comparison_id=row['comparison_id'],
            metric=row['metric'],
            value=row['value'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
    return len(valid_rows)


PREVIEW_BUILDERS = {
    'organism': _build_organism_preview,
    'study': _build_study_preview,
    'group': _build_group_preview,
    'comparison': _build_comparison_preview,
    'metadata_variable': _build_metadata_variable_preview,
    'metadata_value': _build_metadata_value_preview,
    'qualitative_finding': _build_qualitative_finding_preview,
    'quantitative_finding': _build_quantitative_finding_preview,
    'alpha_metric': _build_alpha_metric_preview,
    'beta_metric': _build_beta_metric_preview,
}

IMPORT_RUNNERS = {
    'organism': _run_organism_import,
    'study': _run_study_import,
    'group': _run_group_import,
    'comparison': _run_comparison_import,
    'metadata_variable': _run_metadata_variable_import,
    'metadata_value': _run_metadata_value_import,
    'qualitative_finding': _run_qualitative_finding_import,
    'quantitative_finding': _run_quantitative_finding_import,
    'alpha_metric': _run_alpha_metric_import,
    'beta_metric': _run_beta_metric_import,
}
