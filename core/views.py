from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.views.generic import TemplateView

from database.models import Organism, RelativeAssociation, Sample, Study

from .graph import build_association_graph


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
                'label': 'Samples',
                'count': Sample.objects.count(),
                'url_name': 'database:sample-list',
            },
            {
                'label': 'Organisms',
                'count': Organism.objects.count(),
                'url_name': 'database:organism-list',
            },
            {
                'label': 'Associations',
                'count': RelativeAssociation.objects.count(),
                'url_name': 'database:relativeassociation-list',
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


class GraphView(TemplateView):
    template_name = 'core/graph.html'

    def get_queryset(self):
        queryset = RelativeAssociation.objects.select_related(
            'sample',
            'sample__study',
            'organism_1',
            'organism_2',
        )

        study_id = self.request.GET.get('study', '').strip()
        sign = self.request.GET.get('sign', '').strip()
        association_type = self.request.GET.get('association_type', '').strip()
        organism_query = self.request.GET.get('organism', '').strip()

        if study_id:
            queryset = queryset.filter(sample__study_id=study_id)
        if sign:
            queryset = queryset.filter(sign=sign)
        if association_type:
            queryset = queryset.filter(association_type__icontains=association_type)
        if organism_query:
            queryset = queryset.filter(
                Q(organism_1__scientific_name__icontains=organism_query)
                | Q(organism_2__scientific_name__icontains=organism_query)
                | Q(organism_1__genus__icontains=organism_query)
                | Q(organism_2__genus__icontains=organism_query)
                | Q(organism_1__species__icontains=organism_query)
                | Q(organism_2__species__icontains=organism_query)
            )

        return queryset.order_by('organism_1__scientific_name', 'organism_2__scientific_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        graph_data = build_association_graph(self.get_queryset())
        context['graph_data'] = graph_data
        context['studies'] = Study.objects.order_by('title')
        context['sign_choices'] = RelativeAssociation.Sign.choices
        context['current_study'] = self.request.GET.get('study', '').strip()
        context['current_sign'] = self.request.GET.get('sign', '').strip()
        context['current_association_type'] = self.request.GET.get('association_type', '').strip()
        context['current_organism'] = self.request.GET.get('organism', '').strip()
        return context
