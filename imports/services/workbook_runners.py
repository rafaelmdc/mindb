"""Workbook import execution runners."""

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

from .helpers import resolve_comparison, resolve_group, resolve_organism, resolve_study


@transaction.atomic
def run_workbook_import(preview_data, workbook_import_runners):
    """Persist a confirmed workbook preview by replaying each validated section runner."""
    batch = ImportBatch.objects.create(
        name=preview_data['batch_name'],
        import_type='excel_workbook',
        status=ImportBatch.Status.VALIDATED,
        source_file=preview_data.get('file_name', ''),
    )

    created_count = 0
    section_counts = {}
    for section in preview_data.get('sections', []):
        import_type = section['import_type']
        runner = workbook_import_runners.get(import_type)
        if not runner:
            continue
        section_created_count = runner(section.get('valid_rows', []), batch)
        section_counts[import_type] = section_created_count
        created_count += section_created_count

    duplicate_count = len(preview_data.get('duplicates', []))
    error_count = len(preview_data.get('errors', []))
    skipped_count = len(preview_data.get('skipped_rows', []))
    batch.success_count = created_count
    batch.error_count = duplicate_count + error_count
    batch.status = ImportBatch.Status.COMPLETED if error_count == 0 else ImportBatch.Status.FAILED
    section_summary = ', '.join(
        f'{import_type}: {count}'
        for import_type, count in section_counts.items()
        if count
    )
    batch.notes = (
        f'Imported {created_count} rows from Excel workbook. '
        f'Skipped {duplicate_count} duplicates. '
        f'Skipped {skipped_count} incomplete-paper rows. '
        f'Validation errors: {error_count}.'
    )
    if section_summary:
        batch.notes = f'{batch.notes} Created by section: {section_summary}.'
    batch.save(update_fields=['success_count', 'error_count', 'status', 'notes'])
    return batch


def run_workbook_study_import(valid_rows, batch):
    """Create missing studies from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        study = resolve_study(row.get('doi') or '', row['title'])
        if study:
            continue
        Study.objects.create(
            doi=row['doi'],
            title=row['title'],
            country=row['country'],
            journal=row['journal'],
            year=row['year'],
            notes=row['notes'],
        )
        created_count += 1
    return created_count


def run_workbook_group_import(valid_rows, batch):
    """Create missing groups from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        study = resolve_study(row.get('study_doi', ''), row.get('study_title', ''))
        if not study:
            continue
        group = Group.objects.filter(study=study, name=row['name']).first()
        if group:
            continue
        Group.objects.create(
            study=study,
            name=row['name'],
            condition=row['condition'],
            sample_size=row['sample_size'],
            cohort=row['cohort'],
            site=row['site'],
            notes=row['notes'],
        )
        created_count += 1
    return created_count


def run_workbook_comparison_import(valid_rows, batch):
    """Create missing comparisons from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        study = resolve_study(row.get('study_doi', ''), row.get('study_title', ''))
        group_a = resolve_group(row.get('study_doi', ''), row.get('study_title', ''), row['group_a_name'])
        group_b = resolve_group(row.get('study_doi', ''), row.get('study_title', ''), row['group_b_name'])
        if not study or not group_a or not group_b:
            continue
        comparison = Comparison.objects.filter(
            study=study,
            group_a=group_a,
            group_b=group_b,
            label=row['label'],
        ).first()
        if comparison:
            continue
        Comparison.objects.create(
            study=study,
            group_a=group_a,
            group_b=group_b,
            label=row['label'],
            notes=row['notes'],
        )
        created_count += 1
    return created_count


def run_workbook_organism_import(valid_rows, batch):
    """Create missing organisms from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        organism = resolve_organism(row['scientific_name'], row['ncbi_taxonomy_id'])
        if organism:
            continue
        Organism.objects.create(
            ncbi_taxonomy_id=row['ncbi_taxonomy_id'],
            scientific_name=row['scientific_name'],
            rank=row['rank'],
            notes=row['notes'],
        )
        created_count += 1
    return created_count


def run_workbook_metadata_variable_import(valid_rows, batch):
    """Create missing metadata variables from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        variable = MetadataVariable.objects.filter(name=row['name']).first()
        if variable:
            continue
        MetadataVariable.objects.create(
            name=row['name'],
            display_name=row['display_name'],
            value_type=row['value_type'],
            is_filterable=row['is_filterable'],
        )
        created_count += 1
    return created_count


def run_workbook_metadata_value_import(valid_rows, batch):
    """Create missing metadata values from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        group = resolve_group(row.get('study_doi', ''), row.get('study_title', ''), row['group_name'])
        variable = MetadataVariable.objects.filter(name=row['variable_name']).first()
        if not group or not variable:
            continue
        value = MetadataValue.objects.filter(group=group, variable=variable).first()
        if value:
            continue
        MetadataValue.objects.create(
            group=group,
            variable=variable,
            value_float=row.get('value_float'),
            value_int=row.get('value_int'),
            value_text=row.get('value_text'),
            value_bool=row.get('value_bool'),
        )
        created_count += 1
    return created_count


def run_workbook_qualitative_finding_import(valid_rows, batch):
    """Create qualitative findings from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        comparison = resolve_comparison(
            row.get('study_doi', ''),
            row.get('study_title', ''),
            row['group_a_name'],
            row['group_b_name'],
            row['comparison_label'],
        )
        organism = resolve_organism(
            row['organism_scientific_name'],
            row.get('organism_ncbi_taxonomy_id'),
        )
        if not comparison or not organism:
            continue
        finding = QualitativeFinding.objects.filter(
            comparison=comparison,
            organism=organism,
            direction=row['direction'],
            source=row['source'],
        ).first()
        if finding:
            continue
        QualitativeFinding.objects.create(
            comparison=comparison,
            organism=organism,
            direction=row['direction'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
        created_count += 1
    return created_count


def run_workbook_quantitative_finding_import(valid_rows, batch):
    """Create quantitative findings from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        group = resolve_group(row.get('study_doi', ''), row.get('study_title', ''), row['group_name'])
        organism = resolve_organism(
            row['organism_scientific_name'],
            row.get('organism_ncbi_taxonomy_id'),
        )
        if not group or not organism:
            continue
        finding = QuantitativeFinding.objects.filter(
            group=group,
            organism=organism,
            value_type=row['value_type'],
            source=row['source'],
        ).first()
        if finding:
            continue
        QuantitativeFinding.objects.create(
            group=group,
            organism=organism,
            value_type=row['value_type'],
            value=row['value'],
            unit=row['unit'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
        created_count += 1
    return created_count


def run_workbook_alpha_metric_import(valid_rows, batch):
    """Create alpha metrics from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        group = resolve_group(row.get('study_doi', ''), row.get('study_title', ''), row['group_name'])
        if not group:
            continue
        metric = AlphaMetric.objects.filter(group=group, metric=row['metric'], source=row['source']).first()
        if metric:
            continue
        AlphaMetric.objects.create(
            group=group,
            metric=row['metric'],
            value=row['value'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
        created_count += 1
    return created_count


def run_workbook_beta_metric_import(valid_rows, batch):
    """Create beta metrics from workbook preview rows."""
    created_count = 0
    for row in valid_rows:
        comparison = resolve_comparison(
            row.get('study_doi', ''),
            row.get('study_title', ''),
            row['group_a_name'],
            row['group_b_name'],
            row['comparison_label'],
        )
        if not comparison:
            continue
        metric = BetaMetric.objects.filter(
            comparison=comparison,
            metric=row['metric'],
            source=row['source'],
        ).first()
        if metric:
            continue
        BetaMetric.objects.create(
            comparison=comparison,
            metric=row['metric'],
            value=row['value'],
            source=row['source'],
            notes=row['notes'],
            import_batch=batch,
        )
        created_count += 1
    return created_count


WORKBOOK_IMPORT_RUNNERS = {
    'study': run_workbook_study_import,
    'group': run_workbook_group_import,
    'comparison': run_workbook_comparison_import,
    'organism': run_workbook_organism_import,
    'metadata_variable': run_workbook_metadata_variable_import,
    'metadata_value': run_workbook_metadata_value_import,
    'qualitative_finding': run_workbook_qualitative_finding_import,
    'quantitative_finding': run_workbook_quantitative_finding_import,
    'alpha_metric': run_workbook_alpha_metric_import,
    'beta_metric': run_workbook_beta_metric_import,
}
