from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from database.models import ImportBatch

from .forms import CsvImportUploadForm
from .services import build_preview, run_import

PREVIEW_SESSION_KEY = 'imports_preview'
IMPORT_TYPE_LABELS = dict(CsvImportUploadForm.IMPORT_TYPE_CHOICES)
PREVIEW_COLUMNS = {
    'organism': [
        ('row_number', 'Row'),
        ('ncbi_taxonomy_id', 'NCBI Taxonomy ID'),
        ('scientific_name', 'Scientific Name'),
        ('rank', 'Rank'),
    ],
    'study': [
        ('row_number', 'Row'),
        ('doi', 'DOI'),
        ('title', 'Title'),
        ('country', 'Country'),
        ('journal', 'Journal'),
        ('year', 'Year'),
    ],
    'group': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('name', 'Group Name'),
        ('condition', 'Condition'),
        ('cohort', 'Cohort'),
        ('site', 'Site'),
        ('sample_size', 'Sample Size'),
    ],
    'comparison': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_a_name', 'Group A'),
        ('group_b_name', 'Group B'),
        ('label', 'Label'),
    ],
    'metadata_variable': [
        ('row_number', 'Row'),
        ('name', 'Name'),
        ('display_name', 'Display Name'),
        ('value_type', 'Value Type'),
        ('is_filterable', 'Filterable'),
    ],
    'metadata_value': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_name', 'Group'),
        ('variable_name', 'Variable'),
        ('value_float', 'Float'),
        ('value_int', 'Integer'),
        ('value_text', 'Text'),
        ('value_bool', 'Boolean'),
    ],
    'qualitative_finding': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_a_name', 'Group A'),
        ('group_b_name', 'Group B'),
        ('comparison_label', 'Comparison'),
        ('organism_scientific_name', 'Organism'),
        ('direction', 'Direction'),
        ('source', 'Source'),
    ],
    'quantitative_finding': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_name', 'Group'),
        ('organism_scientific_name', 'Organism'),
        ('value_type', 'Value Type'),
        ('value', 'Value'),
        ('unit', 'Unit'),
        ('source', 'Source'),
    ],
    'alpha_metric': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_name', 'Group'),
        ('metric', 'Metric'),
        ('value', 'Value'),
        ('source', 'Source'),
    ],
    'beta_metric': [
        ('row_number', 'Row'),
        ('study_doi', 'Study DOI'),
        ('study_title', 'Study Title'),
        ('group_a_name', 'Group A'),
        ('group_b_name', 'Group B'),
        ('comparison_label', 'Comparison'),
        ('metric', 'Metric'),
        ('value', 'Value'),
        ('source', 'Source'),
    ],
}


@staff_member_required
@require_http_methods(['GET', 'POST'])
def upload_csv(request):
    if request.method == 'POST':
        form = CsvImportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            preview = build_preview(
                file_name=csv_file.name,
                content=csv_file.read().decode('utf-8-sig'),
                import_type=form.cleaned_data['import_type'],
                batch_name=form.cleaned_data['name'],
            )
            request.session[PREVIEW_SESSION_KEY] = preview.to_dict()
            return redirect('imports:preview')
    else:
        form = CsvImportUploadForm()

    return render(
        request,
        'imports/upload.html',
        {
            'form': form,
            'import_choices': CsvImportUploadForm.IMPORT_TYPE_CHOICES,
        },
    )


@staff_member_required
def preview_csv(request):
    preview = request.session.get(PREVIEW_SESSION_KEY)
    if not preview:
        return redirect('imports:upload')

    import_type = preview['import_type']
    preview_columns = PREVIEW_COLUMNS.get(
        import_type,
        [(key, key.replace('_', ' ').title()) for key in preview['valid_rows'][0].keys()] if preview['valid_rows'] else [],
    )
    return render(
        request,
        'imports/preview.html',
        {
            'preview': preview,
            'import_label': IMPORT_TYPE_LABELS.get(import_type, import_type.replace('_', ' ').title()),
            'preview_columns': preview_columns,
        },
    )


@staff_member_required
@require_http_methods(['POST'])
def confirm_csv(request):
    preview = request.session.get(PREVIEW_SESSION_KEY)
    if not preview:
        return redirect('imports:upload')

    batch = run_import(preview)
    request.session.pop(PREVIEW_SESSION_KEY, None)
    return redirect('imports:result', batch_id=batch.pk)


@staff_member_required
def import_result(request, batch_id):
    batch = get_object_or_404(ImportBatch, pk=batch_id)
    import_key = batch.import_type.removesuffix('_csv')
    return render(
        request,
        'imports/result.html',
        {
            'batch': batch,
            'import_label': IMPORT_TYPE_LABELS.get(import_key, import_key.replace('_', ' ').title()),
        },
    )
