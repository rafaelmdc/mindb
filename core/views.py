from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import TemplateView

from database.models import Comparison, Group, QualitativeFinding, QuantitativeFinding, Study, Taxon

from .graph_payloads import (
    GRAPH_GROUPING_CHOICES,
    build_disease_graph,
    build_directional_taxon_network,
    get_directional_edge_evidence,
)
from .graph_renderers import (
    DISEASE_LAYOUT_CONTROL_SPECS,
    DIRECTIONAL_LAYOUT_CONTROL_SPECS,
    GRAPH_ENGINE_CHOICES,
    build_disease_layout_settings,
    build_directional_layout_settings,
    normalize_graph_engine,
)
from .model_diagram import MODEL_DIAGRAM_CONTENT_TYPES, render_model_diagram, render_model_diagram_svg


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = [
            {
                'label': 'Studies',
                'count': Study.objects.count(),
                'url_name': 'database:study-list',
            },
            {
                'label': 'Groups',
                'count': Group.objects.count(),
                'url_name': 'database:group-list',
            },
            {
                'label': 'Comparisons',
                'count': Comparison.objects.count(),
                'url_name': 'database:comparison-list',
            },
            {
                'label': 'Taxa',
                'count': Taxon.objects.count(),
                'url_name': 'database:taxon-list',
            },
            {
                'label': 'Qualitative',
                'count': QualitativeFinding.objects.count(),
                'url_name': 'database:qualitativefinding-list',
            },
            {
                'label': 'Quantitative',
                'count': QuantitativeFinding.objects.count(),
                'url_name': 'database:quantitativefinding-list',
            },
        ]
        return context


class StaffHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'core/staff_home.html'
    login_url = '/admin/login/'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.user.is_authenticated and not request.user.is_staff:
            raise Http404()
        return response


class ModelDiagramView(LoginRequiredMixin, TemplateView):
    template_name = 'core/model_diagram.html'
    login_url = '/admin/login/'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.user.is_authenticated and not request.user.is_staff:
            raise Http404()
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['diagram_svg'] = mark_safe(render_model_diagram_svg())
            context['diagram_error'] = ''
        except Exception as exc:
            context['diagram_svg'] = ''
            context['diagram_error'] = str(exc)
        return context


class ModelDiagramDownloadView(LoginRequiredMixin, View):
    login_url = '/admin/login/'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.user.is_authenticated and not request.user.is_staff:
            raise Http404()
        return response

    def get(self, request, *args, **kwargs):
        output_format = kwargs['output_format']
        if output_format not in MODEL_DIAGRAM_CONTENT_TYPES:
            raise Http404()

        diagram = render_model_diagram(output_format)
        response = HttpResponse(diagram, content_type=MODEL_DIAGRAM_CONTENT_TYPES[output_format])
        response['Content-Disposition'] = f'attachment; filename="mindb-schema.{output_format}"'
        return response


class GraphView(TemplateView):
    template_name = 'core/graph.html'

    def get_grouping_rank(self):
        grouping_rank = self.request.GET.get('group_rank', '').strip() or 'family'
        valid_ranks = {value for value, _label in GRAPH_GROUPING_CHOICES}
        return grouping_rank if grouping_rank in valid_ranks else 'family'

    def get_queryset(self):
        queryset = QualitativeFinding.objects.select_related(
            'comparison',
            'comparison__study',
            'comparison__group_a',
            'comparison__group_b',
            'taxon',
        )

        study_id = self.request.GET.get('study', '').strip()
        direction = self.request.GET.get('direction', '').strip()
        disease_query = self.request.GET.get('disease', '').strip() or self.request.GET.get('comparison', '').strip()
        taxon_query = self.request.GET.get('taxon', '').strip()
        branch_id = self.request.GET.get('branch', '').strip()

        if study_id:
            queryset = queryset.filter(comparison__study_id=study_id)
        if direction:
            queryset = queryset.filter(direction=direction)
        if disease_query:
            queryset = queryset.filter(
                Q(comparison__group_a__condition__icontains=disease_query)
                | Q(comparison__group_a__name__icontains=disease_query)
                | Q(comparison__label__icontains=disease_query)
            )
        if taxon_query:
            queryset = queryset.filter(
                Q(taxon__scientific_name__icontains=taxon_query)
                | Q(taxon__rank__icontains=taxon_query)
            )
        if branch_id:
            queryset = queryset.filter(taxon__closure_ancestors__ancestor_id=branch_id).distinct()

        return queryset.order_by('comparison__label', 'taxon__scientific_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grouping_rank = self.get_grouping_rank()
        current_engine = normalize_graph_engine(self.request.GET.get('engine', '').strip() or 'cytoscape')
        layout_settings = build_disease_layout_settings(self.request.GET)
        graph_data = build_disease_graph(self.get_queryset(), grouping_rank=grouping_rank)
        branch_id = self.request.GET.get('branch', '').strip()
        context['graph_data'] = graph_data
        context['studies'] = Study.objects.order_by('title')
        context['direction_choices'] = QualitativeFinding.Direction.choices
        context['grouping_rank_choices'] = GRAPH_GROUPING_CHOICES
        context['engine_choices'] = GRAPH_ENGINE_CHOICES
        context['active_layout_controls'] = [
            {
                **spec,
                'value': layout_settings[spec['name']],
            }
            for spec in DISEASE_LAYOUT_CONTROL_SPECS[current_engine]
        ]
        context['layout_settings'] = layout_settings
        context['branch_taxa'] = Taxon.objects.order_by('scientific_name')[:200]
        context['current_engine'] = current_engine
        context['current_study'] = self.request.GET.get('study', '').strip()
        context['current_direction'] = self.request.GET.get('direction', '').strip()
        context['current_disease'] = self.request.GET.get('disease', '').strip() or self.request.GET.get('comparison', '').strip()
        context['current_taxon'] = self.request.GET.get('taxon', '').strip()
        context['current_branch'] = branch_id
        context['current_group_rank'] = grouping_rank
        context['current_branch_taxon'] = Taxon.objects.filter(pk=branch_id).first() if branch_id else None
        return context


class DirectionalTaxonGraphMixin:
    def get_grouping_rank(self):
        grouping_rank = self.request.GET.get('group_rank', '').strip() or 'family'
        valid_ranks = {value for value, _label in GRAPH_GROUPING_CHOICES}
        return grouping_rank if grouping_rank in valid_ranks else 'family'

    def get_minimum_support(self):
        minimum_support = self.request.GET.get('min_support', '').strip() or '1'
        try:
            return max(int(minimum_support), 1)
        except ValueError:
            return 1

    def get_pattern_filter(self):
        pattern_filter = self.request.GET.get('pattern', '').strip() or 'all'
        return pattern_filter if pattern_filter in {'all', 'same_direction', 'opposite_direction', 'mixed'} else 'all'

    def get_study_id(self):
        return self.request.GET.get('study', '').strip()

    def get_disease_query(self):
        return self.request.GET.get('disease', '').strip() or self.request.GET.get('comparison', '').strip()

    def get_taxon_query(self):
        return self.request.GET.get('taxon', '').strip()

    def get_branch_id(self):
        return self.request.GET.get('branch', '').strip()

    def get_graph_filter_query_params(self):
        params = {
            'group_rank': self.get_grouping_rank(),
            'pattern': self.get_pattern_filter(),
            'min_support': self.get_minimum_support(),
        }
        if self.get_study_id():
            params['study'] = self.get_study_id()
        if self.get_disease_query():
            params['disease'] = self.get_disease_query()
        if self.get_taxon_query():
            params['taxon'] = self.get_taxon_query()
        if self.get_branch_id():
            params['branch'] = self.get_branch_id()
        return params

    def get_queryset(self):
        queryset = QualitativeFinding.objects.select_related(
            'comparison',
            'comparison__study',
            'comparison__group_a',
            'comparison__group_b',
            'taxon',
        )

        study_id = self.get_study_id()
        disease_query = self.get_disease_query()
        branch_id = self.get_branch_id()

        if study_id:
            queryset = queryset.filter(comparison__study_id=study_id)
        if disease_query:
            queryset = queryset.filter(
                Q(comparison__group_a__condition__icontains=disease_query)
                | Q(comparison__group_a__name__icontains=disease_query)
                | Q(comparison__label__icontains=disease_query)
            )
        if branch_id:
            queryset = queryset.filter(taxon__closure_ancestors__ancestor_id=branch_id).distinct()

        return queryset.order_by('comparison__label', 'taxon__scientific_name')


class DirectionalTaxonNetworkView(DirectionalTaxonGraphMixin, TemplateView):
    template_name = 'core/directional_taxon_network.html'

    def _build_edge_detail_url(self, edge_data):
        query = {
            **self.get_graph_filter_query_params(),
            'source_taxon': edge_data['source_taxon_pk'],
            'target_taxon': edge_data['target_taxon_pk'],
        }
        return f"{reverse('core:co-abundance-edge-detail')}?{urlencode(query)}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grouping_rank = self.get_grouping_rank()
        branch_id = self.get_branch_id()
        minimum_support = self.get_minimum_support()
        pattern_filter = self.get_pattern_filter()
        current_engine = normalize_graph_engine(self.request.GET.get('engine', '').strip() or 'cytoscape')
        layout_settings = build_directional_layout_settings(self.request.GET)
        graph_data = build_directional_taxon_network(
            self.get_queryset(),
            grouping_rank=grouping_rank,
            minimum_support=minimum_support,
            pattern_filter=pattern_filter,
            taxon_query=self.get_taxon_query(),
        )
        for edge in graph_data['edges']:
            edge['data']['edge_detail_url'] = self._build_edge_detail_url(edge['data'])
        context['graph_data'] = graph_data
        context['studies'] = Study.objects.order_by('title')
        context['grouping_rank_choices'] = GRAPH_GROUPING_CHOICES
        context['engine_choices'] = GRAPH_ENGINE_CHOICES
        context['active_layout_controls'] = [
            {
                **spec,
                'value': layout_settings[spec['name']],
            }
            for spec in DIRECTIONAL_LAYOUT_CONTROL_SPECS[current_engine]
        ]
        context['layout_settings'] = layout_settings
        context['branch_taxa'] = Taxon.objects.order_by('scientific_name')[:200]
        context['pattern_choices'] = (
            ('all', 'All patterns'),
            ('same_direction', 'Same direction'),
            ('opposite_direction', 'Opposite direction'),
            ('mixed', 'Mixed'),
        )
        context['current_engine'] = current_engine
        context['current_study'] = self.get_study_id()
        context['current_disease'] = self.get_disease_query()
        context['current_taxon'] = self.get_taxon_query()
        context['current_branch'] = branch_id
        context['current_group_rank'] = grouping_rank
        context['current_min_support'] = minimum_support
        context['current_pattern'] = pattern_filter
        context['current_branch_taxon'] = Taxon.objects.filter(pk=branch_id).first() if branch_id else None
        return context


class DirectionalTaxonEdgeDetailView(DirectionalTaxonGraphMixin, TemplateView):
    template_name = 'core/co_abundance_edge_detail.html'
    comparison_paginate_by = 20
    finding_paginate_by = 30

    def _paginate(self, items, *, page_param, per_page):
        paginator = Paginator(items, per_page)
        return paginator.get_page(self.request.GET.get(page_param, '1'))

    def _build_graph_url(self):
        return f"{reverse('core:co-abundance-network')}?{urlencode(self.get_graph_filter_query_params())}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        source_taxon_id = self.request.GET.get('source_taxon', '').strip()
        target_taxon_id = self.request.GET.get('target_taxon', '').strip()
        if not source_taxon_id or not target_taxon_id:
            raise Http404('Both source_taxon and target_taxon are required.')

        grouping_rank = self.get_grouping_rank()
        minimum_support = self.get_minimum_support()
        pattern_filter = self.get_pattern_filter()
        edge_evidence = get_directional_edge_evidence(
            self.get_queryset(),
            source_taxon_id=source_taxon_id,
            target_taxon_id=target_taxon_id,
            grouping_rank=grouping_rank,
            minimum_support=minimum_support,
            pattern_filter=pattern_filter,
            taxon_query=self.get_taxon_query(),
        )
        if edge_evidence is None:
            raise Http404('No co-abundance edge matched the current filters.')

        branch_id = self.get_branch_id()
        context['edge_evidence'] = edge_evidence
        context['comparison_page_obj'] = self._paginate(
            edge_evidence['comparisons'],
            page_param='comparison_page',
            per_page=self.comparison_paginate_by,
        )
        context['finding_page_obj'] = self._paginate(
            edge_evidence['findings'],
            page_param='finding_page',
            per_page=self.finding_paginate_by,
        )
        context['current_study'] = self.get_study_id()
        context['current_disease'] = self.get_disease_query()
        context['current_taxon'] = self.get_taxon_query()
        context['current_branch'] = branch_id
        context['current_group_rank'] = grouping_rank
        context['current_min_support'] = minimum_support
        context['current_pattern'] = pattern_filter
        context['current_study_obj'] = Study.objects.filter(pk=context['current_study']).first() if context['current_study'] else None
        context['current_branch_taxon'] = Taxon.objects.filter(pk=branch_id).first() if branch_id else None
        context['graph_url'] = self._build_graph_url()
        return context
