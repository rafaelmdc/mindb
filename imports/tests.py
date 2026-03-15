from django.test import TestCase

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

from .services import build_preview, run_import


class ImportServiceTests(TestCase):
    def setUp(self):
        self.study = Study.objects.create(title='Study A', doi='10.1000/example')
        self.group_a = Group.objects.create(study=self.study, name='Case')
        self.group_b = Group.objects.create(study=self.study, name='Control')
        self.comparison = Comparison.objects.create(
            study=self.study,
            group_a=self.group_a,
            group_b=self.group_b,
            label='Case vs control',
        )
        self.organism = Organism.objects.create(
            ncbi_taxonomy_id=100,
            scientific_name='Organism A',
            rank='species',
        )
        self.metadata_variable = MetadataVariable.objects.create(
            name='smoking_status',
            display_name='Smoking Status',
            value_type=MetadataVariable.ValueType.TEXT,
        )

    def test_study_preview_reports_duplicate_doi(self):
        preview = build_preview(
            file_name='studies.csv',
            content='doi,title\n10.1000/example,Duplicate Study\n',
            import_type='study',
            batch_name='Study batch',
        )

        self.assertEqual(preview.valid_rows, [])
        self.assertEqual(len(preview.duplicates), 1)

    def test_group_preview_requires_existing_study(self):
        preview = build_preview(
            file_name='groups.csv',
            content='study_doi,study_title,name\n10.9999/missing,,Cohort X\n',
            import_type='group',
            batch_name='Group batch',
        )

        self.assertEqual(preview.valid_rows, [])
        self.assertEqual(len(preview.errors), 1)

    def test_comparison_import_creates_row(self):
        preview = build_preview(
            file_name='comparisons.csv',
            content=(
                'study_doi,study_title,group_a_name,group_b_name,label\n'
                '10.1000/example,,Case,Control,Case vs control import\n'
            ),
            import_type='comparison',
            batch_name='Comparison batch',
        ).to_dict()

        batch = run_import(preview)

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertTrue(
            Comparison.objects.filter(
                study=self.study,
                group_a=self.group_a,
                group_b=self.group_b,
                label='Case vs control import',
            ).exists()
        )

    def test_metadata_value_import_creates_value(self):
        preview = build_preview(
            file_name='metadata_values.csv',
            content=(
                'study_doi,study_title,group_name,variable_name,value_text\n'
                '10.1000/example,,Case,smoking_status,never\n'
            ),
            import_type='metadata_value',
            batch_name='Metadata value batch',
        ).to_dict()

        batch = run_import(preview)
        metadata_value = MetadataValue.objects.get(group=self.group_a, variable=self.metadata_variable)

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(metadata_value.value_text, 'never')

    def test_qualitative_finding_import_creates_batch_link(self):
        preview = build_preview(
            file_name='qualitative_findings.csv',
            content=(
                'study_doi,study_title,group_a_name,group_b_name,comparison_label,organism_scientific_name,direction,source\n'
                '10.1000/example,,Case,Control,Case vs control,Organism A,enriched,Table 2\n'
            ),
            import_type='qualitative_finding',
            batch_name='Qualitative batch',
        ).to_dict()

        batch = run_import(preview)
        finding = QualitativeFinding.objects.get(comparison=self.comparison, organism=self.organism)

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(finding.import_batch, batch)
        self.assertEqual(finding.direction, QualitativeFinding.Direction.ENRICHED)

    def test_quantitative_finding_preview_requires_numeric_value(self):
        preview = build_preview(
            file_name='quantitative_findings.csv',
            content=(
                'study_doi,study_title,group_name,organism_scientific_name,value_type,value,source\n'
                '10.1000/example,,Case,Organism A,relative_abundance,not-a-number,Table 3\n'
            ),
            import_type='quantitative_finding',
            batch_name='Quantitative batch',
        )

        self.assertEqual(preview.valid_rows, [])
        self.assertEqual(len(preview.errors), 1)

    def test_quantitative_finding_import_creates_batch_link(self):
        preview = build_preview(
            file_name='quantitative_findings.csv',
            content=(
                'study_doi,study_title,group_name,organism_scientific_name,value_type,value,source\n'
                '10.1000/example,,Case,Organism A,relative_abundance,0.42,Table 3\n'
            ),
            import_type='quantitative_finding',
            batch_name='Quantitative batch',
        ).to_dict()

        batch = run_import(preview)
        finding = QuantitativeFinding.objects.get(group=self.group_a, organism=self.organism)

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(finding.import_batch, batch)
        self.assertEqual(finding.value, 0.42)

    def test_organism_import_creates_import_batch_and_records(self):
        preview = build_preview(
            file_name='organisms.csv',
            content=(
                'ncbi_taxonomy_id,scientific_name,rank,notes\n'
                '101,Faecalibacterium prausnitzii,species,Important commensal\n'
            ),
            import_type='organism',
            batch_name='Organism batch',
        ).to_dict()

        batch = run_import(preview)

        self.assertEqual(ImportBatch.objects.count(), 1)
        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(batch.success_count, 1)
        self.assertEqual(batch.error_count, 0)
        self.assertTrue(
            Organism.objects.filter(
                ncbi_taxonomy_id=101,
                scientific_name='Faecalibacterium prausnitzii',
            ).exists()
        )

    def test_alpha_metric_import_sets_import_batch(self):
        preview = build_preview(
            file_name='alpha_metrics.csv',
            content=(
                'study_doi,study_title,group_name,metric,value,source\n'
                '10.1000/example,,Case,shannon,3.82,Table 4\n'
            ),
            import_type='alpha_metric',
            batch_name='Alpha metric batch',
        ).to_dict()

        batch = run_import(preview)
        metric = AlphaMetric.objects.get(group=self.group_a, metric='shannon')

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(metric.import_batch, batch)
        self.assertEqual(metric.value, 3.82)

    def test_beta_metric_import_sets_import_batch(self):
        preview = build_preview(
            file_name='beta_metrics.csv',
            content=(
                'study_doi,study_title,group_a_name,group_b_name,comparison_label,metric,value,source\n'
                '10.1000/example,,Case,Control,Case vs control,bray_curtis,0.37,Figure 2\n'
            ),
            import_type='beta_metric',
            batch_name='Beta metric batch',
        ).to_dict()

        batch = run_import(preview)
        metric = BetaMetric.objects.get(comparison=self.comparison, metric='bray_curtis')

        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual(metric.import_batch, batch)
        self.assertEqual(metric.value, 0.37)
