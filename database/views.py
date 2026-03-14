from django.db.models import Q
from django.views.generic import DetailView, ListView, TemplateView

from .models import Organism, RelativeAssociation, Sample, Study


class BrowserListView(ListView):
    paginate_by = 20
    ordering_map = {}
    default_ordering = None
    search_fields = ()

    def get_search_query(self):
        return self.request.GET.get('q', '').strip()

    def get_ordering(self):
        requested_ordering = self.request.GET.get('order_by', '').strip()
        if requested_ordering in self.ordering_map:
            return self.ordering_map[requested_ordering]
        return self.default_ordering

    def apply_search(self, queryset):
        query = self.get_search_query()
        if not query or not self.search_fields:
            return queryset

        search_filter = Q()
        for field_name in self.search_fields:
            search_filter |= Q(**{f'{field_name}__icontains': query})
        return queryset.filter(search_filter)

    def apply_filters(self, queryset):
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self.apply_search(queryset)
        queryset = self.apply_filters(queryset)
        ordering = self.get_ordering()
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_query'] = self.get_search_query()
        context['current_order_by'] = self.request.GET.get('order_by', '').strip()
        context['ordering_options'] = self.ordering_map.items()
        return context


class BrowserHomeView(TemplateView):
    template_name = 'database/browser_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cards'] = [
            {
                'title': 'Studies',
                'count': Study.objects.count(),
                'description': 'Browse curated studies and their sampling context.',
                'url_name': 'database:study-list',
            },
            {
                'title': 'Samples',
                'count': Sample.objects.count(),
                'description': 'Inspect cohorts, methods, and attached metadata.',
                'url_name': 'database:sample-list',
            },
            {
                'title': 'Organisms',
                'count': Organism.objects.count(),
                'description': 'Search taxa by name, rank, or taxonomy identifier.',
                'url_name': 'database:organism-list',
            },
            {
                'title': 'Relative Associations',
                'count': RelativeAssociation.objects.count(),
                'description': 'Explore pairwise organism associations across samples.',
                'url_name': 'database:relativeassociation-list',
            },
        ]
        return context


class StudyListView(BrowserListView):
    model = Study
    template_name = 'database/study_list.html'
    context_object_name = 'studies'
    search_fields = ('title', 'source_doi', 'country', 'journal')
    ordering_map = {
        'title': ('title',),
        '-title': ('-title',),
        'publication_year': ('publication_year', 'title'),
        '-publication_year': ('-publication_year', 'title'),
        'created_at': ('created_at',),
        '-created_at': ('-created_at',),
    }
    default_ordering = ('title',)

    def apply_filters(self, queryset):
        country = self.request.GET.get('country', '').strip()
        publication_year = self.request.GET.get('publication_year', '').strip()
        if country:
            queryset = queryset.filter(country__icontains=country)
        if publication_year:
            queryset = queryset.filter(publication_year=publication_year)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_country'] = self.request.GET.get('country', '').strip()
        context['current_publication_year'] = self.request.GET.get('publication_year', '').strip()
        context['publication_years'] = [
            value
            for value in Study.objects.order_by('-publication_year')
            .values_list('publication_year', flat=True)
            .distinct()
            if value is not None
        ]
        return context


class StudyDetailView(DetailView):
    model = Study
    template_name = 'database/study_detail.html'
    context_object_name = 'study'

    def get_queryset(self):
        return Study.objects.prefetch_related('samples')


class SampleListView(BrowserListView):
    model = Sample
    template_name = 'database/sample_list.html'
    context_object_name = 'samples'
    search_fields = ('label', 'site', 'method', 'cohort', 'study__title')
    ordering_map = {
        'label': ('label',),
        '-label': ('-label',),
        'study': ('study__title', 'label'),
        '-study': ('-study__title', 'label'),
        'sample_size': ('sample_size', 'label'),
        '-sample_size': ('-sample_size', 'label'),
        'created_at': ('created_at',),
        '-created_at': ('-created_at',),
    }
    default_ordering = ('study__title', 'label')

    def get_queryset(self):
        return super().get_queryset().select_related('study')

    def apply_filters(self, queryset):
        study_id = self.request.GET.get('study', '').strip()
        site = self.request.GET.get('site', '').strip()
        if study_id:
            queryset = queryset.filter(study_id=study_id)
        if site:
            queryset = queryset.filter(site__icontains=site)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_study'] = self.request.GET.get('study', '').strip()
        context['current_site'] = self.request.GET.get('site', '').strip()
        context['studies'] = Study.objects.order_by('title')
        return context


class SampleDetailView(DetailView):
    model = Sample
    template_name = 'database/sample_detail.html'
    context_object_name = 'sample'

    def get_queryset(self):
        return (
            Sample.objects.select_related('study', 'core_metadata')
            .prefetch_related('metadata_values__variable', 'relative_associations__organism_1', 'relative_associations__organism_2')
        )


class OrganismListView(BrowserListView):
    model = Organism
    template_name = 'database/organism_list.html'
    context_object_name = 'organisms'
    search_fields = ('scientific_name', 'genus', 'species', 'ncbi_taxonomy_id')
    ordering_map = {
        'scientific_name': ('scientific_name',),
        '-scientific_name': ('-scientific_name',),
        'ncbi_taxonomy_id': ('ncbi_taxonomy_id',),
        '-ncbi_taxonomy_id': ('-ncbi_taxonomy_id',),
        'taxonomic_rank': ('taxonomic_rank', 'scientific_name'),
        '-taxonomic_rank': ('-taxonomic_rank', 'scientific_name'),
    }
    default_ordering = ('scientific_name',)

    def apply_filters(self, queryset):
        taxonomic_rank = self.request.GET.get('taxonomic_rank', '').strip()
        if taxonomic_rank:
            queryset = queryset.filter(taxonomic_rank=taxonomic_rank)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_taxonomic_rank'] = self.request.GET.get('taxonomic_rank', '').strip()
        context['taxonomic_ranks'] = (
            Organism.objects.order_by('taxonomic_rank')
            .values_list('taxonomic_rank', flat=True)
            .distinct()
        )
        return context


class OrganismDetailView(DetailView):
    model = Organism
    template_name = 'database/organism_detail.html'
    context_object_name = 'organism'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organism = self.object
        context['association_count'] = (
            RelativeAssociation.objects.filter(Q(organism_1=organism) | Q(organism_2=organism)).count()
        )
        context['child_organisms'] = organism.children.order_by('scientific_name')
        return context


class RelativeAssociationListView(BrowserListView):
    model = RelativeAssociation
    template_name = 'database/relativeassociation_list.html'
    context_object_name = 'associations'
    search_fields = (
        'association_type',
        'method',
        'sample__label',
        'sample__study__title',
        'organism_1__scientific_name',
        'organism_2__scientific_name',
    )
    ordering_map = {
        'sample': ('sample__study__title', 'sample__label'),
        '-sample': ('-sample__study__title', 'sample__label'),
        'value': ('value', 'sample__label'),
        '-value': ('-value', 'sample__label'),
        'p_value': ('p_value', 'sample__label'),
        '-p_value': ('-p_value', 'sample__label'),
        'confidence': ('confidence', 'sample__label'),
        '-confidence': ('-confidence', 'sample__label'),
        'created_at': ('created_at',),
        '-created_at': ('-created_at',),
    }
    default_ordering = ('sample__study__title', 'sample__label', 'organism_1__scientific_name')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'sample',
            'sample__study',
            'organism_1',
            'organism_2',
        )

    def apply_filters(self, queryset):
        study_id = self.request.GET.get('study', '').strip()
        sign = self.request.GET.get('sign', '').strip()
        association_type = self.request.GET.get('association_type', '').strip()
        if study_id:
            queryset = queryset.filter(sample__study_id=study_id)
        if sign:
            queryset = queryset.filter(sign=sign)
        if association_type:
            queryset = queryset.filter(association_type__icontains=association_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_study'] = self.request.GET.get('study', '').strip()
        context['current_sign'] = self.request.GET.get('sign', '').strip()
        context['current_association_type'] = self.request.GET.get('association_type', '').strip()
        context['studies'] = Study.objects.order_by('title')
        context['sign_choices'] = RelativeAssociation.Sign.choices
        return context


class RelativeAssociationDetailView(DetailView):
    model = RelativeAssociation
    template_name = 'database/relativeassociation_detail.html'
    context_object_name = 'association'

    def get_queryset(self):
        return RelativeAssociation.objects.select_related(
            'sample',
            'sample__study',
            'organism_1',
            'organism_2',
            'import_batch',
        )
