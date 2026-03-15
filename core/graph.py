def build_comparison_graph(findings):
    comparison_nodes = {}
    organism_nodes = {}
    edge_map = {}

    for finding in findings:
        comparison = finding.comparison
        organism = finding.organism
        comparison_node_id = f'comparison-{comparison.pk}'
        organism_node_id = f'organism-{organism.pk}'

        comparison_node = comparison_nodes.setdefault(
            comparison_node_id,
            {
                'id': comparison_node_id,
                'label': comparison.label,
                'node_type': 'comparison',
                'study_title': comparison.study.title,
                'group_a': comparison.group_a.name,
                'group_b': comparison.group_b.name,
                'study_ids': {comparison.study_id},
                'neighbors': set(),
            },
        )
        comparison_node['study_ids'].add(comparison.study_id)
        comparison_node['neighbors'].add(organism_node_id)

        organism_node = organism_nodes.setdefault(
            organism_node_id,
            {
                'id': organism_node_id,
                'label': organism.scientific_name,
                'node_type': 'organism',
                'rank': organism.rank,
                'taxonomy_id': organism.ncbi_taxonomy_id,
                'study_ids': set(),
                'neighbors': set(),
            },
        )
        organism_node['study_ids'].add(comparison.study_id)
        organism_node['neighbors'].add(comparison_node_id)

        edge_key = (comparison_node_id, organism_node_id)
        edge = edge_map.setdefault(
            edge_key,
            {
                'source': comparison_node_id,
                'target': organism_node_id,
                'finding_count': 0,
                'study_ids': set(),
                'directions': {},
                'sources': set(),
            },
        )
        edge['finding_count'] += 1
        edge['study_ids'].add(comparison.study_id)
        edge['directions'][finding.direction] = edge['directions'].get(finding.direction, 0) + 1
        edge['sources'].add(finding.source)

    nodes = []
    for attrs in comparison_nodes.values():
        nodes.append(
            {
                'data': {
                    'id': attrs['id'],
                    'label': attrs['label'],
                    'node_type': attrs['node_type'],
                    'degree': len(attrs['neighbors']),
                    'study_count': len(attrs['study_ids']),
                    'group': attrs['node_type'],
                    'study_title': attrs['study_title'],
                    'group_a': attrs['group_a'],
                    'group_b': attrs['group_b'],
                }
            }
        )
    for attrs in organism_nodes.values():
        nodes.append(
            {
                'data': {
                    'id': attrs['id'],
                    'label': attrs['label'],
                    'node_type': attrs['node_type'],
                    'degree': len(attrs['neighbors']),
                    'study_count': len(attrs['study_ids']),
                    'group': attrs['node_type'],
                    'rank': attrs['rank'],
                    'taxonomy_id': attrs['taxonomy_id'],
                }
            }
        )

    edges = []
    for edge in edge_map.values():
        directions = edge['directions']
        dominant_direction = sorted(
            directions.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
        edges.append(
            {
                'data': {
                    'id': f"{edge['source']}-{edge['target']}",
                    'source': edge['source'],
                    'target': edge['target'],
                    'source_label': comparison_nodes[edge['source']]['label'],
                    'target_label': organism_nodes[edge['target']]['label'],
                    'finding_count': edge['finding_count'],
                    'study_count': len(edge['study_ids']),
                    'direction_summary': ', '.join(
                        f'{direction}: {count}'
                        for direction, count in sorted(directions.items())
                    ),
                    'dominant_direction': dominant_direction,
                    'source_count': len(edge['sources']),
                    'label': dominant_direction,
                }
            }
        )

    nodes.sort(key=lambda item: (item['data']['node_type'], item['data']['label']))
    edges.sort(key=lambda item: (item['data']['source'], item['data']['target']))

    comparison_count = sum(1 for node in nodes if node['data']['node_type'] == 'comparison')
    organism_count = sum(1 for node in nodes if node['data']['node_type'] == 'organism')

    return {
        'nodes': nodes,
        'edges': edges,
        'summary': {
            'node_count': len(nodes),
            'edge_count': len(edges),
            'finding_count': sum(edge['data']['finding_count'] for edge in edges),
            'comparison_count': comparison_count,
            'organism_count': organism_count,
        },
    }
