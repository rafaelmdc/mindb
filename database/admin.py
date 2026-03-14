from django.contrib import admin

from .models import (
    CoreMetadata,
    ImportBatch,
    MetadataValue,
    MetadataVariable,
    Organism,
    RelativeAssociation,
    Sample,
    Study,
)


class CoreMetadataInline(admin.StackedInline):
    model = CoreMetadata
    extra = 0


class SampleInline(admin.TabularInline):
    model = Sample
    extra = 0
    fields = ('label', 'cohort', 'site', 'method', 'sample_size')
    show_change_link = True


class MetadataValueInline(admin.TabularInline):
    model = MetadataValue
    extra = 0
    autocomplete_fields = ('variable', 'import_batch')
    fields = ('variable', 'value_float', 'value_int', 'value_text', 'value_bool', 'unit', 'import_batch')


class RelativeAssociationInline(admin.TabularInline):
    model = RelativeAssociation
    extra = 0
    autocomplete_fields = ('organism_1', 'organism_2', 'import_batch')
    fields = (
        'organism_1',
        'organism_2',
        'association_type',
        'sign',
        'value',
        'method',
        'import_batch',
    )


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_year', 'journal', 'country', 'source_doi')
    list_filter = ('publication_year', 'country', 'journal')
    search_fields = ('title', 'source_doi', 'journal', 'country')
    inlines = (SampleInline,)


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('label', 'study', 'cohort', 'site', 'method', 'sample_size')
    list_filter = ('study', 'site', 'method', 'cohort')
    search_fields = ('label', 'study__title', 'cohort', 'site', 'method')
    autocomplete_fields = ('study',)
    list_select_related = ('study',)
    inlines = (CoreMetadataInline, MetadataValueInline, RelativeAssociationInline)


@admin.register(Organism)
class OrganismAdmin(admin.ModelAdmin):
    list_display = ('scientific_name', 'ncbi_taxonomy_id', 'taxonomic_rank', 'genus', 'species')
    list_filter = ('taxonomic_rank', 'genus')
    search_fields = ('scientific_name', 'ncbi_taxonomy_id', 'genus', 'species')
    autocomplete_fields = ('parent_taxonomy',)


@admin.register(RelativeAssociation)
class RelativeAssociationAdmin(admin.ModelAdmin):
    list_display = (
        'sample',
        'organism_1',
        'organism_2',
        'association_type',
        'sign',
        'value',
        'method',
        'import_batch',
    )
    list_filter = ('association_type', 'sign', 'method', 'sample__study', 'import_batch')
    search_fields = (
        'sample__label',
        'sample__study__title',
        'organism_1__scientific_name',
        'organism_2__scientific_name',
        'association_type',
        'method',
    )
    list_select_related = ('sample__study', 'organism_1', 'organism_2', 'import_batch')
    autocomplete_fields = ('sample', 'organism_1', 'organism_2', 'import_batch')


@admin.register(MetadataVariable)
class MetadataVariableAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'domain', 'value_type', 'is_filterable')
    list_filter = ('domain', 'value_type', 'is_filterable')
    search_fields = ('display_name', 'name', 'domain', 'description')


@admin.register(MetadataValue)
class MetadataValueAdmin(admin.ModelAdmin):
    list_display = ('sample', 'variable', 'unit', 'raw_value', 'import_batch')
    list_filter = ('variable__domain', 'variable__value_type', 'import_batch')
    search_fields = (
        'sample__label',
        'sample__study__title',
        'variable__display_name',
        'variable__name',
        'raw_value',
    )
    list_select_related = ('sample__study', 'variable', 'import_batch')
    autocomplete_fields = ('sample', 'variable', 'import_batch')


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'import_type', 'status', 'uploaded_at', 'success_count', 'error_count')
    list_filter = ('status', 'import_type', 'uploaded_at')
    search_fields = ('name', 'source_file', 'notes')
    change_list_template = 'admin/database/importbatch/change_list.html'


@admin.register(CoreMetadata)
class CoreMetadataAdmin(admin.ModelAdmin):
    list_display = ('sample', 'condition', 'male_percent', 'age_mean', 'bmi_mean')
    list_filter = ('condition',)
    search_fields = ('sample__label', 'sample__study__title', 'condition', 'notes')
    autocomplete_fields = ('sample',)
