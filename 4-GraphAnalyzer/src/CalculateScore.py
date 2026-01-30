# Calculate the score for each edge

def caculate_score(graph, edge):
    """
    Preparation:
    1.extract_dot_nodes.py
        Input: DOT   Output: JSON
        This function computes the score for a given edge based on the attributes of the source and target nodes.
        - centrality: Node betweenness centrality, representing node criticality
        - cost: Edge cost
        - stealth: Edge stealth
    2.SearchGraph.py
        Input: JSON, Target_id
        Call DirectedGraphPathFinder.get_paths_as_lists(Target_id)
        Output: List of all paths that can reach the target node
---------------------------------------------------- 
    Functionality:
    Analyze the paths returned by SearchGraph.py and compute path metrics: cost, stealth, length, and criticality.
    Results are stored in /home/calista/IoTRuleProject/4-GraphAnalyzer/output/score/, showing each path with its metrics.
    For linear paths the analysis is straightforward; for complex paths with AND logic, apply:
    - Path length = max(length of each branch) + 1
    - Total path cost = sum(cost of each branch)
    - Average stealth = min(stealth of each branch)
    - Path criticality = max(criticality of each branch)


    """ 
import csv
import os
import json
import time
import sys

sys.path.append(os.path.dirname(__file__))
from SearchPath import DirectedGraphPathFinder

def load_graph_info(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    node_dict = {n['ID']: n for n in data['nodes']}
    edge_dict = {(e['source'], e['target']): e for e in data['edges']}
    return node_dict, edge_dict



def is_and_node(node_id, node_dict):
    node = node_dict.get(node_id, {})
    return node.get('Label', '') == 'AND' or node_id.endswith('AND')

def calc_path_cost(path, node_dict, edge_dict, parent=None):
    """
    Compute total path cost: iterate all single-hop simple paths and sum cost (ignore edges with cost None)
    """
    hops = []
    extract_hops(path, parent=None, hops=hops)
    total_cost = 0
    for src, dst in hops:
        edge = edge_dict.get((src, dst), None)
        if edge is not None and edge.get('cost') is not None:
            total_cost += edge['cost']
    return total_cost

def calc_path_stealth(path, node_dict, edge_dict, parent=None):
    """
    Compute path stealth: iterate all single-hop simple paths and average stealth (ignore edges with stealth None)
    """
    hops = []
    extract_hops(path, parent=None, hops=hops)
    stealth_values = []
    for src, dst in hops:
        edge = edge_dict.get((src, dst), None)
        if edge is not None and edge.get('stealth') is not None:
            stealth_values.append(edge['stealth'])
    if not stealth_values:
        return None
    return round(sum(stealth_values) / len(stealth_values), 3)

def calc_path_length(path, node_dict, edge_dict, parent=None):
    """
    Compute path length:
    - For branched structures, use max(length of each branch) + 1
    - For linear structures, sum directly
    - If a node starts with LOGIC_, subtract 1 from length
    Example: [[['A', 'B'], ['C']], 'D', 'E', 'F'] returns 5
    """
    def _count_nodes(p):
        if isinstance(p, list):
            if all(isinstance(x, list) for x in p):
                return max((_count_nodes(branch) for branch in p), default=0)
            else:
                total = 0
                for node in p:
                    total += _count_nodes(node)
                return total
        else:
            return 1

    def _count_logic_nodes(p):
        if isinstance(p, list):
            return sum(_count_logic_nodes(item) for item in p)
        else:
            return 1 if isinstance(p, str) and p.startswith("LOGIC_") else 0

    total_nodes = _count_nodes(path)  
    logic_nodes = _count_logic_nodes(path)  
    return total_nodes - logic_nodes -1

def calc_path_centrality(path, node_dict, edge_dict, parent=None):
    """
    Compute path criticality: traverse all nodes and take the maximum centrality (ignore None values)
    """
    nodes_with_centrality = extract_all_nodes_and_centrality(path, node_dict)
    centrality_values = [c for _, c in nodes_with_centrality if c is not None]
    if not centrality_values:
        return None
    return max(centrality_values)

def analyze_path(path, node_dict, edge_dict, parent=None):
    """
    Dispatch metric evaluators and return (path string, total cost, average stealth, path length, path criticality)
    """
    path_str = str(path)
    total_cost = calc_path_cost(path, node_dict, edge_dict, parent)
    avg_stealth = calc_path_stealth(path, node_dict, edge_dict, parent)
    path_length = calc_path_length(path, node_dict, edge_dict, parent)
    path_centrality = calc_path_centrality(path, node_dict, edge_dict, parent)
    return (path_str, total_cost, avg_stealth, path_length, path_centrality)

def extract_hops(path, parent=None, hops=None):
    """
    Recursively extract all single-hop short paths (including parent-child connections within and across branches).
    Example: [[['A', 'B'], ['C']], 'D', 'E', 'F']
    Identify: A->B, B->D, C->D, D->E, E->F
    """
    if hops is None:
        hops = []
    if isinstance(path, list):
        if all(isinstance(x, list) for x in path):
            branch_ends = []
            for branch in path:
                ends = extract_hops(branch, parent=None, hops=hops)
                branch_ends.append(ends)
            flat_ends = []
            for ends in branch_ends:
                if isinstance(ends, list):
                    flat_ends.extend(ends)
                else:
                    flat_ends.append(ends)
            return flat_ends
        else:
            prev = parent
            idx = 0
            while idx < len(path):
                node = path[idx]
                if isinstance(node, list):
                    branch_firsts = get_first_nodes(node)
                    if prev is not None:
                        for b in branch_firsts:
                            hops.append((prev, b))
                    branch_ends = extract_hops(node, parent=None, hops=hops)
                    next_node = path[idx+1] if idx+1 < len(path) else None
                    if next_node is not None:
                        for end in branch_ends if isinstance(branch_ends, list) else [branch_ends]:
                            if isinstance(next_node, list):
                                for b in get_first_nodes(next_node):
                                    hops.append((end, b))
                            else:
                                hops.append((end, next_node))
                    prev = next_node
                    idx += 1
                else:
                    if prev is not None and prev != node:
                        hops.append((prev, node))
                    prev = node
                    idx += 1
            if isinstance(path[-1], list):
                return extract_hops(path[-1], parent=None, hops=[])
            else:
                return path[-1]
    else:
        return path

def get_first_nodes(path):
    """
    Get all first nodes in a list structure (for connecting parent node to branch first nodes).
    """
    if isinstance(path, list):
        if all(isinstance(x, list) for x in path):
            firsts = []
            for branch in path:
                firsts.extend(get_first_nodes(branch))
            return firsts
        else:
            for node in path:
                if isinstance(node, list):
                    return get_first_nodes(node)
                else:
                    return [node]
    else:
        return [path]

def extract_all_nodes_and_centrality(path, node_dict):
    """
    Traverse all nodes and return a list of (node_id, centrality).
    Example: [[['A', 'B'], ['C']], 'D', 'E', 'F'] returns [('A', centrality), ...]
    """
    nodes = []
    def _traverse(p):
        if isinstance(p, list):
            for item in p:
                _traverse(item)
        else:
            centrality = node_dict.get(p, {}).get('centrality')
            nodes.append((p, centrality))
    _traverse(path)
    return nodes

def print_all_hops_with_metrics():
    """
    Print all single-hop short paths within each long path and their cost/stealth (supports complex nested structures).
    Automatically skip invalid loops where start equals end (e.g., X--->X).
    """
    json_base = 'virtualBuilding_graph_graphinfo_20250825_192607'
    json_path = os.path.join('/home/calista/IoTRuleProject/4-GraphAnalyzer/output/node/', f'{json_base}.json')
    target_id = 'CH_door_contact_state'

    node_dict, edge_dict = load_graph_info(json_path)
    finder = DirectedGraphPathFinder(json_path)
    all_paths = finder.get_paths_as_lists(target_id)
    for idx, path in enumerate(all_paths):
        print(f"\n=== PATH {idx+1} ===")
        hops = []
        extract_hops(path, parent=None, hops=hops)
        for src, dst in hops:
            edge = edge_dict.get((src, dst), {})
            cost = edge.get('cost', '')
            stealth = edge.get('stealth', '')
            print(f"{src}--->{dst}\tcost={cost}\tstealth={stealth}")



def main():
    # Configuration
    json_base = 'virtualBuilding_filter_graph_graphinfo'
    json_path = os.path.join('./4-GraphAnalyzer/output/node/', f'{json_base}.json')
    target_id = 'A_Rule_58_0'
    # A_Rule_58_0  Fire alarm opens the main door
    # A_Rule_129_0 card reaeder success opens the main door
    # A_Rule_142_0 Press door-open button triggers door open action
    output_dir = './4-GraphAnalyzer/output/score'
    os.makedirs(output_dir, exist_ok=True)

    # 1. Load graph info
    node_dict, edge_dict = load_graph_info(json_path)

    # 2. Get all paths (multi-dimensional list, supports AND structure)
    finder = DirectedGraphPathFinder(json_path)
    all_paths = finder.get_paths_as_lists(target_id)

    # 3. Analyze each path
    results = []
    for path in all_paths:
        res = analyze_path(path, node_dict, edge_dict, parent=None)
        results.append(res)
    
    # 4. Output results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    outname = f"score_{target_id}_{json_base}_{timestamp}.csv"
    outpath = os.path.join(output_dir, outname)
    with open(outpath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Path", "Total Cost", "Average Stealth", "Path Length", "Path Criticality"])
        for r in results:
            writer.writerow(r)
    print(f"Path score analysis results written to: {outpath}")

if __name__ == "__main__":
    main()


