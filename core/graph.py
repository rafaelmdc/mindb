def build_association_graph(associations):
    import networkx as nx

    graph = nx.Graph()

    for association in associations:
        study = association.sample.study
        organisms = (association.organism_1, association.organism_2)

        for organism in organisms:
            if not graph.has_node(organism.pk):
                graph.add_node(
                    organism.pk,
                    id=str(organism.pk),
                    label=organism.scientific_name,
                    taxonomy_id=organism.ncbi_taxonomy_id,
                    rank=organism.taxonomic_rank,
                    genus=organism.genus,
                    species=organism.species,
                    study_ids=set(),
                    sample_ids=set(),
                )

            graph.nodes[organism.pk]['study_ids'].add(study.pk)
            graph.nodes[organism.pk]['sample_ids'].add(association.sample.pk)

        source_id = association.organism_1.pk
        target_id = association.organism_2.pk

        if not graph.has_edge(source_id, target_id):
            graph.add_edge(
                source_id,
                target_id,
                association_count=0,
                study_ids=set(),
                sample_ids=set(),
                signs=set(),
                association_types=set(),
                values=[],
            )

        edge = graph.edges[source_id, target_id]
        edge['association_count'] += 1
        edge['study_ids'].add(study.pk)
        edge['sample_ids'].add(association.sample.pk)
        if association.sign:
            edge['signs'].add(association.sign)
        if association.association_type:
            edge['association_types'].add(association.association_type)
        if association.value is not None:
            edge['values'].append(association.value)

    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append(
            {
                'data': {
                    'id': attrs['id'],
                    'label': attrs['label'],
                    'taxonomy_id': attrs['taxonomy_id'],
                    'rank': attrs['rank'],
                    'genus': attrs['genus'],
                    'species': attrs['species'],
                    'degree': graph.degree[node_id],
                    'group': attrs['rank'] or 'unknown',
                    'study_count': len(attrs['study_ids']),
                    'sample_count': len(attrs['sample_ids']),
                }
            }
        )

    edges = []
    for source_id, target_id, attrs in graph.edges(data=True):
        average_value = None
        if attrs['values']:
            average_value = sum(attrs['values']) / len(attrs['values'])

        signs = sorted(attrs['signs'])
        association_types = sorted(attrs['association_types'])
        edges.append(
            {
                'data': {
                    'id': f'{source_id}-{target_id}',
                    'source': str(source_id),
                    'target': str(target_id),
                    'source_label': graph.nodes[source_id]['label'],
                    'target_label': graph.nodes[target_id]['label'],
                    'association_count': attrs['association_count'],
                    'study_count': len(attrs['study_ids']),
                    'sample_count': len(attrs['sample_ids']),
                    'sign': ', '.join(signs) if signs else '',
                    'association_type': ', '.join(association_types),
                    'average_value': average_value,
                    'label': association_types[0] if association_types else 'association',
                }
            }
        )

    nodes.sort(key=lambda item: item['data']['label'])
    edges.sort(key=lambda item: (item['data']['source'], item['data']['target']))

    return {
        'nodes': nodes,
        'edges': edges,
        'summary': {
            'node_count': len(nodes),
            'edge_count': len(edges),
            'association_count': sum(edge['data']['association_count'] for edge in edges),
        },
    }
