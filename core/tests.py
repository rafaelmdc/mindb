from django.test import TestCase
from django.urls import reverse

from database.models import Organism, RelativeAssociation, Sample, Study


class HomeViewTests(TestCase):
    def setUp(self):
        study = Study.objects.create(title='Study A')
        sample = Sample.objects.create(study=study, label='Sample A')
        organism_a = Organism.objects.create(
            ncbi_taxonomy_id=101,
            scientific_name='Organism A',
            taxonomic_rank='species',
        )
        organism_b = Organism.objects.create(
            ncbi_taxonomy_id=202,
            scientific_name='Organism B',
            taxonomic_rank='species',
        )
        RelativeAssociation.objects.create(
            sample=sample,
            organism_1=organism_a,
            organism_2=organism_b,
            association_type='correlation',
        )

    def test_home_page_renders_counts_and_navigation(self):
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Microbiome Association Database')
        self.assertContains(response, 'Studies')
        self.assertContains(response, 'Samples')
        self.assertContains(response, 'Organisms')
        self.assertContains(response, 'Associations')
        self.assertContains(response, reverse('database:browser-home'))
        self.assertContains(response, reverse('imports:upload'))
        self.assertContains(response, reverse('core:graph'))


class GraphViewTests(TestCase):
    def setUp(self):
        self.study_a = Study.objects.create(title='Study A')
        self.study_b = Study.objects.create(title='Study B')
        self.sample_a = Sample.objects.create(study=self.study_a, label='Sample A')
        self.sample_b = Sample.objects.create(study=self.study_b, label='Sample B')
        self.organism_a = Organism.objects.create(
            ncbi_taxonomy_id=101,
            scientific_name='Faecalibacterium prausnitzii',
            taxonomic_rank='species',
            genus='Faecalibacterium',
            species='prausnitzii',
        )
        self.organism_b = Organism.objects.create(
            ncbi_taxonomy_id=202,
            scientific_name='Bacteroides fragilis',
            taxonomic_rank='species',
            genus='Bacteroides',
            species='fragilis',
        )
        self.organism_c = Organism.objects.create(
            ncbi_taxonomy_id=303,
            scientific_name='Roseburia intestinalis',
            taxonomic_rank='species',
            genus='Roseburia',
            species='intestinalis',
        )
        RelativeAssociation.objects.create(
            sample=self.sample_a,
            organism_1=self.organism_a,
            organism_2=self.organism_b,
            association_type='correlation',
            sign=RelativeAssociation.Sign.POSITIVE,
            value=0.7,
        )
        RelativeAssociation.objects.create(
            sample=self.sample_b,
            organism_1=self.organism_a,
            organism_2=self.organism_c,
            association_type='cooccurrence',
            sign=RelativeAssociation.Sign.NEGATIVE,
            value=-0.5,
        )

    def test_graph_page_renders_summary(self):
        response = self.client.get(reverse('core:graph'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Interaction Graph')
        self.assertEqual(response.context['graph_data']['summary']['node_count'], 3)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 2)

    def test_graph_page_filters_by_sign(self):
        response = self.client.get(
            reverse('core:graph'),
            {'sign': RelativeAssociation.Sign.POSITIVE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['graph_data']['summary']['node_count'], 2)
        self.assertEqual(response.context['graph_data']['summary']['edge_count'], 1)
