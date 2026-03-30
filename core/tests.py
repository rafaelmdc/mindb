from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from core.graph import build_directional_taxon_network
from core.model_diagram import render_model_diagram_svg

from database.models import Comparison, Group, QualitativeFinding, QuantitativeFinding, Study, Taxon, TaxonClosure


class HomeViewTests(TestCase):
    def setUp(self):
        study = Study.objects.create(title='Study A')
        group_a = Group.objects.create(study=study, name='Case')
        group_b = Group.objects.create(study=study, name='Control')
        taxon = Taxon.objects.create(
            ncbi_taxonomy_id=101,
            scientific_name='Taxon A',
            rank='species',
        )
        comparison = Comparison.objects.create(
            study=study,
            group_a=group_a,
            group_b=group_b,
            label='Case vs control',
        )
        QualitativeFinding.objects.create(
            comparison=comparison,
            taxon=taxon,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Results 3.2',
        )
        QuantitativeFinding.objects.create(
            group=group_a,
            taxon=taxon,
            value_type=QuantitativeFinding.ValueType.RELATIVE_ABUNDANCE,
            value=1.5,
            source='Table 2',
        )

    def test_home_page_renders_counts_and_navigation(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Microbiome Interaction Network Database')
        self.assertContains(response, 'Groups')
        self.assertContains(response, 'Comparisons')
        self.assertContains(response, 'Qualitative')
        self.assertContains(response, reverse('database:browser-home'))
        self.assertContains(response, reverse('core:disease-network'))
        self.assertContains(response, reverse('core:staff-home'))


class GraphViewTests(TestCase):
    def setUp(self):
        self.study_a = Study.objects.create(title='Study A')
        self.study_b = Study.objects.create(title='Study B')
        self.group_a = Group.objects.create(study=self.study_a, name='Case')
        self.group_b = Group.objects.create(study=self.study_a, name='Control')
        self.group_c = Group.objects.create(study=self.study_b, name='Validation')
        self.group_d = Group.objects.create(study=self.study_b, name='Reference')
        self.comparison_a = Comparison.objects.create(
            study=self.study_a,
            group_a=self.group_a,
            group_b=self.group_b,
            label='Case vs control',
        )
        self.comparison_b = Comparison.objects.create(
            study=self.study_b,
            group_a=self.group_c,
            group_b=self.group_d,
            label='Validation vs reference',
        )
        self.organism_a = Taxon.objects.create(
            ncbi_taxonomy_id=101,
            scientific_name='Faecalibacterium prausnitzii',
            rank='species',
        )
        self.organism_a_genus = Taxon.objects.create(
            ncbi_taxonomy_id=100,
            scientific_name='Faecalibacterium',
            rank='genus',
        )
        self.organism_a.parent = self.organism_a_genus
        self.organism_a.save(update_fields=['parent'])
        self.organism_b = Taxon.objects.create(
            ncbi_taxonomy_id=202,
            scientific_name='Bacteroides fragilis',
            rank='species',
        )
        self.organism_b_genus = Taxon.objects.create(
            ncbi_taxonomy_id=200,
            scientific_name='Bacteroides',
            rank='genus',
        )
        self.organism_b.parent = self.organism_b_genus
        self.organism_b.save(update_fields=['parent'])
        self.organism_c = Taxon.objects.create(
            ncbi_taxonomy_id=303,
            scientific_name='Roseburia intestinalis',
            rank='species',
        )
        self.organism_c_genus = Taxon.objects.create(
            ncbi_taxonomy_id=300,
            scientific_name='Roseburia',
            rank='genus',
        )
        self.organism_c.parent = self.organism_c_genus
        self.organism_c.save(update_fields=['parent'])
        self.family = Taxon.objects.create(
            ncbi_taxonomy_id=999,
            scientific_name='Ruminococcaceae',
            rank='family',
        )
        self.organism_a_genus.parent = self.family
        self.organism_a_genus.save(update_fields=['parent'])
        self.organism_c_genus.parent = self.family
        self.organism_c_genus.save(update_fields=['parent'])
        self._attach_lineage(self.family, self.organism_a_genus, self.organism_a)
        self._attach_lineage(self.family, self.organism_c_genus, self.organism_c)
        self._attach_lineage(self.organism_b_genus, self.organism_b)
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=self.organism_a,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=self.organism_b,
            direction=QualitativeFinding.Direction.DEPLETED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_b,
            taxon=self.organism_c,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 4',
        )

    def _attach_lineage(self, *taxa):
        for depth, ancestor in enumerate(reversed(taxa)):
            TaxonClosure.objects.get_or_create(
                ancestor=ancestor,
                descendant=taxa[-1],
                defaults={'depth': len(taxa) - depth - 1},
            )
        for taxon in taxa:
            TaxonClosure.objects.get_or_create(
                ancestor=taxon,
                descendant=taxon,
                defaults={'depth': 0},
            )
        for descendant_index, descendant in enumerate(taxa[1:], start=1):
            for ancestor_index, ancestor in enumerate(taxa[:descendant_index]):
                TaxonClosure.objects.get_or_create(
                    ancestor=ancestor,
                    descendant=descendant,
                    defaults={'depth': descendant_index - ancestor_index},
                )

    def test_graph_page_renders_summary(self):
        response = self.client.get(reverse('core:disease-network'), {'group_rank': 'leaf'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Disease Network')
        self.assertEqual(response.context['graph_data']['summary']['disease_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['taxon_count'], 3)
        self.assertEqual(response.context['graph_data']['summary']['enriched_taxon_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['depleted_taxon_count'], 1)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 3)

    def test_graph_page_filters_by_direction(self):
        response = self.client.get(
            reverse('core:disease-network'),
            {
                'direction': QualitativeFinding.Direction.ENRICHED,
                'group_rank': 'leaf',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['finding_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['enriched_taxon_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['depleted_taxon_count'], 0)

    def test_graph_page_groups_findings_by_rank(self):
        response = self.client.get(reverse('core:disease-network'), {'group_rank': 'genus'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['grouping_rank'], 'genus')
        self.assertEqual(response.context['graph_data']['summary']['taxon_count'], 3)
        node_labels = {node['data']['label'] for node in response.context['graph_data']['nodes'] if node['data']['node_type'] == 'taxon'}
        self.assertIn('Faecalibacterium', node_labels)
        self.assertIn('Bacteroides', node_labels)
        self.assertIn('Roseburia', node_labels)
        self.assertNotIn('Faecalibacterium prausnitzii', node_labels)

    def test_graph_page_filters_by_taxonomic_branch(self):
        response = self.client.get(reverse('core:disease-network'), {'branch': self.family.pk, 'group_rank': 'genus'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 2)
        node_labels = {node['data']['label'] for node in response.context['graph_data']['nodes'] if node['data']['node_type'] == 'taxon'}
        self.assertIn('Faecalibacterium', node_labels)
        self.assertIn('Roseburia', node_labels)
        self.assertNotIn('Bacteroides', node_labels)

    def test_graph_page_reports_skipped_rollups_when_rank_is_missing(self):
        response = self.client.get(reverse('core:disease-network'), {'group_rank': 'phylum'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['skipped_rollup_count'], 3)
        self.assertContains(response, '3 findings omitted because no ancestor exists at the selected rank.')

    def test_graph_page_accepts_explicit_engine_selection(self):
        response = self.client.get(reverse('core:disease-network'), {'engine': 'echarts'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_engine'], 'echarts')
        self.assertContains(response, 'echarts.min.js')
        self.assertContains(response, "renderer: 'svg'")
        self.assertContains(response, 'name="echarts_repulsion"')
        self.assertContains(response, 'name="echarts_edge_length"')
        self.assertContains(response, 'name="echarts_gravity"')
        self.assertNotContains(response, 'name="cytoscape_repulsion_scale"')

    def test_graph_page_shows_cytoscape_layout_controls_by_default(self):
        response = self.client.get(reverse('core:disease-network'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_group_rank'], 'family')
        self.assertContains(response, '<option value="species"', html=False)
        self.assertContains(response, 'name="cytoscape_repulsion_scale"')
        self.assertContains(response, 'name="cytoscape_edge_length_scale"')
        self.assertContains(response, 'name="cytoscape_gravity"')
        self.assertNotContains(response, 'name="echarts_repulsion"')

    def test_graph_page_preserves_custom_layout_values(self):
        response = self.client.get(
            reverse('core:disease-network'),
            {
                'engine': 'echarts',
                'echarts_repulsion': '1350',
                'echarts_edge_length': '280',
                'echarts_gravity': '0.06',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['layout_settings']['echarts_repulsion'], 1350.0)
        self.assertEqual(response.context['layout_settings']['echarts_edge_length'], 280.0)
        self.assertEqual(response.context['layout_settings']['echarts_gravity'], 0.06)
        self.assertContains(response, 'value="1350.0"')
        self.assertContains(response, 'value="280.0"')
        self.assertContains(response, 'value="0.06"')

    def test_graph_page_uses_compact_supporting_evidence_preview(self):
        response = self.client.get(reverse('core:disease-network'), {'group_rank': 'leaf'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supporting Evidence')
        self.assertNotContains(response, 'Current graph payload')
        self.assertContains(response, 'Comparisons')
        self.assertContains(response, 'Findings')
        self.assertContains(response, 'Download PNG')
        self.assertContains(response, 'Download SVG')
        self.assertContains(response, '@tone-row/cytoscape-svg@1.0.2/cytoscape-svg.js')
        self.assertContains(response, 'node[node_type = "taxon"].zoom-labeled')
        self.assertContains(response, "cy.on('zoom', updateZoomLabels);")
        self.assertContains(response, 'id="supporting-evidence"', html=False)
        self.assertEqual(len(response.context['edge_preview']), 3)
        self.assertEqual(response.context['edge_page_obj'].paginator.count, 3)
        first_preview_edge = response.context['edge_preview'][0]['data']
        self.assertIn(reverse('database:comparison-list'), first_preview_edge['comparison_url'])
        self.assertIn(reverse('database:qualitativefinding-list'), first_preview_edge['finding_url'])

    @patch('core.views.build_disease_graph')
    def test_graph_page_supporting_evidence_preview_is_paginated(self, mock_build_disease_graph):
        mock_build_disease_graph.return_value = {
            'nodes': [],
            'edges': [
                {
                    'data': {
                        'id': f'edge-{index}',
                        'source': f'taxon-{index}',
                        'target': f'disease-{index}',
                        'source_taxon_pk': index,
                        'source_label': f'Taxon {index:02d}',
                        'target_label': f'Disease {index:02d}',
                        'column': 'enriched',
                        'finding_count': 1,
                        'study_count': 1,
                    }
                }
                for index in range(1, 10)
            ],
            'summary': {
                'edge_count': 9,
                'disease_count': 0,
                'taxon_count': 0,
                'enriched_taxon_count': 0,
                'depleted_taxon_count': 0,
                'finding_count': 0,
                'grouping_rank': 'leaf',
                'skipped_rollup_count': 0,
            },
        }

        response = self.client.get(reverse('core:disease-network'), {'edge_page': '2'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['edge_page_obj'].number, 2)
        self.assertEqual(response.context['edge_page_obj'].paginator.count, 9)
        self.assertEqual(len(response.context['edge_preview']), 1)
        self.assertContains(response, 'edge_page=1')
        self.assertNotContains(response, '#supporting-evidence')
        self.assertContains(response, 'Showing 9-9 of 9 graph edges.')


class DirectionalTaxonNetworkTests(TestCase):
    def setUp(self):
        self.study = Study.objects.create(title='Study A')
        self.case_group = Group.objects.create(study=self.study, name='Case', condition='IBD')
        self.control_group = Group.objects.create(study=self.study, name='Control', condition='Healthy')
        self.validation_group = Group.objects.create(study=self.study, name='Validation', condition='IBD')
        self.reference_group = Group.objects.create(study=self.study, name='Reference', condition='Healthy')
        self.comparison_a = Comparison.objects.create(
            study=self.study,
            group_a=self.case_group,
            group_b=self.control_group,
            label='IBD vs healthy discovery',
        )
        self.comparison_b = Comparison.objects.create(
            study=self.study,
            group_a=self.validation_group,
            group_b=self.reference_group,
            label='IBD vs healthy validation',
        )
        self.taxon_a = Taxon.objects.create(ncbi_taxonomy_id=101, scientific_name='Blautia wexlerae', rank='species')
        self.taxon_a_genus = Taxon.objects.create(ncbi_taxonomy_id=100, scientific_name='Blautia', rank='genus')
        self.taxon_a.parent = self.taxon_a_genus
        self.taxon_a.save(update_fields=['parent'])
        self.taxon_b = Taxon.objects.create(ncbi_taxonomy_id=201, scientific_name='Roseburia intestinalis', rank='species')
        self.taxon_b_genus = Taxon.objects.create(ncbi_taxonomy_id=200, scientific_name='Roseburia', rank='genus')
        self.taxon_b.parent = self.taxon_b_genus
        self.taxon_b.save(update_fields=['parent'])
        self.taxon_c = Taxon.objects.create(ncbi_taxonomy_id=301, scientific_name='Bacteroides fragilis', rank='species')
        self.taxon_c_genus = Taxon.objects.create(ncbi_taxonomy_id=300, scientific_name='Bacteroides', rank='genus')
        self.taxon_c.parent = self.taxon_c_genus
        self.taxon_c.save(update_fields=['parent'])
        self.family = Taxon.objects.create(ncbi_taxonomy_id=999, scientific_name='Lachnospiraceae', rank='family')
        self.taxon_a_genus.parent = self.family
        self.taxon_a_genus.save(update_fields=['parent'])
        self.taxon_b_genus.parent = self.family
        self.taxon_b_genus.save(update_fields=['parent'])
        self._attach_lineage(self.family, self.taxon_a_genus, self.taxon_a)
        self._attach_lineage(self.family, self.taxon_b_genus, self.taxon_b)
        self._attach_lineage(self.taxon_c_genus, self.taxon_c)

        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=self.taxon_a,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=self.taxon_b,
            direction=QualitativeFinding.Direction.INCREASED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=self.taxon_c,
            direction=QualitativeFinding.Direction.DEPLETED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_b,
            taxon=self.taxon_a,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 4',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_b,
            taxon=self.taxon_b,
            direction=QualitativeFinding.Direction.DECREASED,
            source='Table 4',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_b,
            taxon=self.taxon_c,
            direction=QualitativeFinding.Direction.DEPLETED,
            source='Table 4',
        )

    def _attach_lineage(self, *taxa):
        for depth, ancestor in enumerate(reversed(taxa)):
            TaxonClosure.objects.get_or_create(
                ancestor=ancestor,
                descendant=taxa[-1],
                defaults={'depth': len(taxa) - depth - 1},
            )
        for taxon in taxa:
            TaxonClosure.objects.get_or_create(
                ancestor=taxon,
                descendant=taxon,
                defaults={'depth': 0},
            )
        for descendant_index, descendant in enumerate(taxa[1:], start=1):
            for ancestor_index, ancestor in enumerate(taxa[:descendant_index]):
                TaxonClosure.objects.get_or_create(
                    ancestor=ancestor,
                    descendant=descendant,
                    defaults={'depth': descendant_index - ancestor_index},
                )

    def test_directional_taxon_network_builder_aggregates_pair_patterns(self):
        graph_data = build_directional_taxon_network(
            QualitativeFinding.objects.select_related('comparison', 'comparison__group_a', 'comparison__group_b', 'comparison__study', 'taxon'),
        )

        self.assertEqual(graph_data['summary']['edge_count'], 3)
        edge_payloads = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']}): edge['data']
            for edge in graph_data['edges']
        }
        self.assertEqual(
            edge_payloads[frozenset({'Blautia wexlerae', 'Roseburia intestinalis'})]['dominant_pattern'],
            'mixed',
        )
        self.assertEqual(
            edge_payloads[frozenset({'Blautia wexlerae', 'Bacteroides fragilis'})]['dominant_pattern'],
            'opposite_direction',
        )
        self.assertEqual(
            edge_payloads[frozenset({'Roseburia intestinalis', 'Bacteroides fragilis'})]['dominant_pattern'],
            'mixed',
        )

    def test_directional_taxon_network_builder_counts_leaf_support_after_rollup(self):
        extra_taxon = Taxon.objects.create(
            ncbi_taxonomy_id=102,
            scientific_name='Blautia obeum',
            rank='species',
            parent=self.taxon_a_genus,
        )
        self._attach_lineage(self.family, self.taxon_a_genus, extra_taxon)
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=extra_taxon,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 2',
        )
        QualitativeFinding.objects.create(
            comparison=self.comparison_b,
            taxon=extra_taxon,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 4',
        )

        graph_data = build_directional_taxon_network(
            QualitativeFinding.objects.select_related(
                'comparison',
                'comparison__group_a',
                'comparison__group_b',
                'comparison__study',
                'taxon',
            ),
            grouping_rank='genus',
        )

        edge_payloads = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']}): edge['data']
            for edge in graph_data['edges']
        }
        blautia_bacteroides = edge_payloads[frozenset({'Blautia', 'Bacteroides'})]
        self.assertEqual(blautia_bacteroides['dominant_pattern'], 'opposite_direction')
        self.assertEqual(blautia_bacteroides['total_support'], 4)
        self.assertEqual(blautia_bacteroides['same_direction_count'], 0)
        self.assertEqual(blautia_bacteroides['opposite_direction_count'], 4)
        self.assertEqual(blautia_bacteroides['comparison_count'], 2)
        self.assertEqual(blautia_bacteroides['same_direction_comparison_count'], 0)
        self.assertEqual(blautia_bacteroides['opposite_direction_comparison_count'], 2)

        rolled_up_graph_data = build_directional_taxon_network(
            QualitativeFinding.objects.select_related(
                'comparison',
                'comparison__group_a',
                'comparison__group_b',
                'comparison__study',
                'taxon',
            ),
            grouping_rank='genus',
            support_mode='rolled_up',
        )
        rolled_up_edge_payloads = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']}): edge['data']
            for edge in rolled_up_graph_data['edges']
        }
        rolled_up_blautia_bacteroides = rolled_up_edge_payloads[frozenset({'Blautia', 'Bacteroides'})]
        self.assertEqual(rolled_up_blautia_bacteroides['dominant_pattern'], 'opposite_direction')
        self.assertEqual(rolled_up_blautia_bacteroides['total_support'], 2)
        self.assertEqual(rolled_up_blautia_bacteroides['same_direction_count'], 0)
        self.assertEqual(rolled_up_blautia_bacteroides['opposite_direction_count'], 2)
        self.assertEqual(rolled_up_blautia_bacteroides['support_mode'], 'rolled_up')

    def test_directional_taxon_network_builder_applies_user_mixed_threshold(self):
        extra_taxon = Taxon.objects.create(
            ncbi_taxonomy_id=102,
            scientific_name='Blautia obeum',
            rank='species',
            parent=self.taxon_a_genus,
        )
        self._attach_lineage(self.family, self.taxon_a_genus, extra_taxon)
        QualitativeFinding.objects.create(
            comparison=self.comparison_a,
            taxon=extra_taxon,
            direction=QualitativeFinding.Direction.ENRICHED,
            source='Table 2',
        )

        default_graph_data = build_directional_taxon_network(
            QualitativeFinding.objects.select_related(
                'comparison',
                'comparison__group_a',
                'comparison__group_b',
                'comparison__study',
                'taxon',
            ),
            grouping_rank='genus',
            support_mode='leaf',
            mixed_threshold=0,
        )
        default_edge_payloads = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']}): edge['data']
            for edge in default_graph_data['edges']
        }
        self.assertEqual(
            default_edge_payloads[frozenset({'Blautia', 'Roseburia'})]['dominant_pattern'],
            'same_direction',
        )

        relaxed_graph_data = build_directional_taxon_network(
            QualitativeFinding.objects.select_related(
                'comparison',
                'comparison__group_a',
                'comparison__group_b',
                'comparison__study',
                'taxon',
            ),
            grouping_rank='genus',
            support_mode='leaf',
            mixed_threshold=20,
        )
        relaxed_edge_payloads = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']}): edge['data']
            for edge in relaxed_graph_data['edges']
        }
        blautia_roseburia = relaxed_edge_payloads[frozenset({'Blautia', 'Roseburia'})]
        self.assertEqual(blautia_roseburia['same_direction_count'], 2)
        self.assertEqual(blautia_roseburia['opposite_direction_count'], 1)
        self.assertEqual(blautia_roseburia['dominant_pattern'], 'mixed')

    def test_directional_taxon_network_page_filters_by_pattern(self):
        response = self.client.get(
            reverse('core:co-abundance-network'),
            {
                'pattern': 'opposite_direction',
                'group_rank': 'leaf',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Co-abundance Taxon Network')
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 1)
        self.assertEqual(response.context['graph_data']['summary']['opposite_direction_edge_count'], 1)
        self.assertEqual(response.context['graph_data']['summary']['mixed_edge_count'], 0)

    def test_directional_taxon_network_page_filters_edges_by_taxon_after_pair_generation(self):
        response = self.client.get(
            reverse('core:co-abundance-network'),
            {
                'group_rank': 'leaf',
                'taxon': 'Blautia wexlerae',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 2)
        edge_pairs = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']})
            for edge in response.context['graph_data']['edges']
        }
        self.assertEqual(
            edge_pairs,
            {
                frozenset({'Blautia wexlerae', 'Roseburia intestinalis'}),
                frozenset({'Blautia wexlerae', 'Bacteroides fragilis'}),
            },
        )

    def test_directional_taxon_network_page_matches_family_query_to_descendant_leaf_edges(self):
        response = self.client.get(
            reverse('core:co-abundance-network'),
            {
                'group_rank': 'leaf',
                'taxon': 'Lachnospiraceae',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 3)
        edge_pairs = {
            frozenset({edge['data']['source_label'], edge['data']['target_label']})
            for edge in response.context['graph_data']['edges']
        }
        self.assertEqual(
            edge_pairs,
            {
                frozenset({'Blautia wexlerae', 'Roseburia intestinalis'}),
                frozenset({'Blautia wexlerae', 'Bacteroides fragilis'}),
                frozenset({'Roseburia intestinalis', 'Bacteroides fragilis'}),
            },
        )

    def test_directional_taxon_network_page_groups_by_rank(self):
        response = self.client.get(reverse('core:co-abundance-network'), {'group_rank': 'genus'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['grouping_rank'], 'genus')
        labels = {node['data']['label'] for node in response.context['graph_data']['nodes']}
        self.assertIn('Blautia', labels)
        self.assertIn('Roseburia', labels)
        self.assertIn('Bacteroides', labels)

    def test_directional_taxon_network_page_accepts_explicit_engine_selection(self):
        response = self.client.get(reverse('core:co-abundance-network'), {'engine': 'echarts'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_engine'], 'echarts')
        self.assertContains(response, 'echarts.min.js')
        self.assertContains(response, "renderer: 'svg'")
        self.assertContains(response, 'name="echarts_repulsion"')
        self.assertContains(response, 'name="echarts_edge_length"')
        self.assertContains(response, 'name="echarts_gravity"')
        self.assertNotContains(response, 'name="cytoscape_repulsion_scale"')

    def test_directional_taxon_network_page_shows_cytoscape_layout_controls_by_default(self):
        response = self.client.get(reverse('core:co-abundance-network'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_group_rank'], 'family')
        self.assertEqual(response.context['current_mixed_threshold'], 20)
        self.assertContains(response, '<option value="species"', html=False)
        self.assertContains(response, 'value="20"')
        self.assertContains(response, 'name="cytoscape_repulsion_scale"')
        self.assertContains(response, 'name="cytoscape_edge_length_scale"')
        self.assertContains(response, 'name="cytoscape_gravity"')
        self.assertNotContains(response, 'name="echarts_repulsion"')

    def test_directional_taxon_network_page_preserves_custom_layout_values(self):
        response = self.client.get(
            reverse('core:co-abundance-network'),
            {
                'engine': 'echarts',
                'echarts_repulsion': '1450',
                'echarts_edge_length': '300',
                'echarts_gravity': '0.04',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['layout_settings']['echarts_repulsion'], 1450.0)
        self.assertEqual(response.context['layout_settings']['echarts_edge_length'], 300.0)
        self.assertEqual(response.context['layout_settings']['echarts_gravity'], 0.04)
        self.assertContains(response, 'value="1450.0"')
        self.assertContains(response, 'value="300.0"')
        self.assertContains(response, 'value="0.04"')

    def test_directional_taxon_network_page_includes_edge_detail_urls(self):
        response = self.client.get(
            reverse('core:co-abundance-network'),
            {
                'group_rank': 'leaf',
                'support_mode': 'rolled_up',
            },
        )

        self.assertEqual(response.status_code, 200)
        edge_data = response.context['graph_data']['edges'][0]['data']
        self.assertIn('source_taxon_pk', edge_data)
        self.assertIn('target_taxon_pk', edge_data)
        self.assertIn(reverse('core:co-abundance-edge-detail'), edge_data['edge_detail_url'])
        self.assertIn('support_mode=rolled_up', edge_data['edge_detail_url'])

    def test_directional_taxon_network_page_uses_compact_supporting_evidence_preview(self):
        response = self.client.get(reverse('core:co-abundance-network'), {'group_rank': 'leaf'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supporting Evidence')
        self.assertNotContains(response, 'Current graph payload')
        self.assertContains(response, 'Open evidence')
        self.assertContains(response, 'Leaf supports')
        self.assertContains(response, 'name="support_mode"')
        self.assertContains(response, 'name="mixed_threshold"')
        self.assertNotContains(response, 'name="branch"')
        self.assertContains(response, 'Download PNG')
        self.assertContains(response, 'Download SVG')
        self.assertContains(response, '@tone-row/cytoscape-svg@1.0.2/cytoscape-svg.js')
        self.assertContains(response, 'id="supporting-evidence"', html=False)
        self.assertEqual(len(response.context['edge_preview']), 3)
        self.assertEqual(response.context['edge_page_obj'].paginator.count, 3)
        self.assertIn(
            reverse('core:co-abundance-edge-detail'),
            response.context['edge_preview'][0]['data']['edge_detail_url'],
        )

    @patch('core.views.build_directional_taxon_network')
    def test_directional_taxon_network_page_supporting_evidence_preview_is_paginated(self, mock_builder):
        mock_builder.return_value = {
            'nodes': [],
            'edges': [
                {
                    'data': {
                        'id': f'edge-{index}',
                        'source': f'taxon-{index}',
                        'target': f'taxon-{index + 1}',
                        'source_taxon_pk': index,
                        'target_taxon_pk': index + 1,
                        'source_label': f'Taxon {index:02d}',
                        'target_label': f'Taxon {index + 1:02d}',
                        'dominant_pattern': 'same_direction',
                        'total_support': 1,
                        'comparison_count': 1,
                        'study_count': 1,
                    }
                }
                for index in range(1, 10)
            ],
            'summary': {
                'edge_count': 9,
                'node_count': 0,
                'taxon_count': 0,
                'study_count': 0,
                'grouping_rank': 'leaf',
                'skipped_rollup_count': 0,
                'minimum_support': 1,
                'pattern_filter': 'all',
                'same_direction_edge_count': 9,
                'opposite_direction_edge_count': 0,
                'mixed_edge_count': 0,
                'total_support_count': 9,
                'comparison_support_count': 9,
            },
        }

        response = self.client.get(reverse('core:co-abundance-network'), {'edge_page': '2'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['edge_page_obj'].number, 2)
        self.assertEqual(response.context['edge_page_obj'].paginator.count, 9)
        self.assertEqual(len(response.context['edge_preview']), 1)
        self.assertContains(response, 'edge_page=1')
        self.assertNotContains(response, '#supporting-evidence')
        self.assertContains(response, 'Showing 9-9 of 9 graph edges.')

    def test_co_abundance_edge_detail_page_renders_supporting_evidence(self):
        response = self.client.get(
            reverse('core:co-abundance-edge-detail'),
            {
                'group_rank': 'leaf',
                'pattern': 'all',
                'min_support': '1',
                'source_taxon': self.taxon_a.pk,
                'target_taxon': self.taxon_c.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Co-abundance Edge Evidence')
        self.assertContains(response, 'Leaf supports')
        self.assertContains(response, 'Mixed threshold')
        self.assertEqual(response.context['edge_evidence']['dominant_pattern'], 'opposite_direction')
        self.assertEqual(response.context['edge_evidence']['comparison_count'], 2)
        self.assertEqual(response.context['edge_evidence']['total_support'], 2)
        self.assertEqual(response.context['comparison_page_obj'].paginator.count, 2)
        self.assertEqual(response.context['finding_page_obj'].paginator.count, 4)

    def test_co_abundance_edge_detail_page_allows_lineage_aware_taxon_query(self):
        response = self.client.get(
            reverse('core:co-abundance-edge-detail'),
            {
                'group_rank': 'leaf',
                'taxon': 'Lachnospiraceae',
                'pattern': 'all',
                'min_support': '1',
                'source_taxon': self.taxon_a.pk,
                'target_taxon': self.taxon_c.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['edge_evidence']['dominant_pattern'], 'opposite_direction')

    def test_co_abundance_edge_detail_page_404s_when_edge_is_filtered_out(self):
        response = self.client.get(
            reverse('core:co-abundance-edge-detail'),
            {
                'group_rank': 'leaf',
                'pattern': 'same_direction',
                'min_support': '1',
                'source_taxon': self.taxon_a.pk,
                'target_taxon': self.taxon_c.pk,
            },
        )

        self.assertEqual(response.status_code, 404)


class StaffHomeViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.staff_user = self.user_model.objects.create_user(
            username='staff',
            password='testpass123',
            is_staff=True,
        )
        self.normal_user = self.user_model.objects.create_user(
            username='normal',
            password='testpass123',
            is_staff=False,
        )

    def test_staff_home_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('core:staff-home'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_staff_home_renders_for_staff_user(self):
        self.client.login(username='staff', password='testpass123')

        response = self.client.get(reverse('core:staff-home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff Workspace')
        self.assertContains(response, reverse('imports:upload'))
        self.assertContains(response, reverse('admin:index'))
        self.assertContains(response, reverse('core:model-diagram'))

    def test_staff_home_is_not_available_to_non_staff_users(self):
        self.client.login(username='normal', password='testpass123')

        response = self.client.get(reverse('core:staff-home'))

        self.assertEqual(response.status_code, 404)

    def test_model_diagram_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('core:model-diagram'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    @patch('core.views.render_model_diagram_svg', return_value='<svg />')
    def test_model_diagram_renders_for_staff_user(self, render_model_diagram_svg_mock):
        self.client.login(username='staff', password='testpass123')

        response = self.client.get(reverse('core:model-diagram'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Model Diagram')
        self.assertContains(response, reverse('core:model-diagram-download', args=['svg']))
        self.assertContains(response, reverse('core:model-diagram-download', args=['png']))
        render_model_diagram_svg_mock.assert_called_once_with()

    @patch('core.views.render_model_diagram', return_value=b'<svg />')
    def test_model_diagram_svg_download_renders_for_staff_user(self, render_model_diagram_mock):
        self.client.login(username='staff', password='testpass123')

        response = self.client.get(reverse('core:model-diagram-download', args=['svg']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="mindb-schema.svg"',
        )
        self.assertEqual(response.content, b'<svg />')
        render_model_diagram_mock.assert_called_once_with('svg')

    @patch('core.views.render_model_diagram', return_value=b'png-bytes')
    def test_model_diagram_png_download_renders_for_staff_user(self, render_model_diagram_mock):
        self.client.login(username='staff', password='testpass123')

        response = self.client.get(reverse('core:model-diagram-download', args=['png']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="mindb-schema.png"',
        )
        self.assertEqual(response.content, b'png-bytes')
        render_model_diagram_mock.assert_called_once_with('png')


class ModelDiagramRendererTests(TestCase):
    @patch('core.model_diagram.subprocess.run')
    def test_render_model_diagram_svg_encodes_dot_input(self, subprocess_run_mock):
        subprocess_run_mock.return_value.returncode = 0
        subprocess_run_mock.return_value.stdout = b'<svg />'
        subprocess_run_mock.return_value.stderr = b''

        svg = render_model_diagram_svg()

        self.assertEqual(svg, '<svg />')
        self.assertIsInstance(subprocess_run_mock.call_args.kwargs['input'], bytes)
