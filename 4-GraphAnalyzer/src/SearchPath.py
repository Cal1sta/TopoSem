import json
import os
from collections import defaultdict

class DirectedGraphPathFinder:
    """
    A class for finding all paths in a directed graph that reach a specific target node.

    The graph data has two categories:
    1. Nodes:
        - Each node is a dict, with common attributes:
            - ID: Unique identifier (string)
            - Label: Node label (string)
            - Type: Node type (e.g., 'physical_channel', 'system_channel', 'action', 'trigger', 'AND')
            - Target: List of target node IDs
            - Source: List of source node IDs
            - centrality: Centrality metric (numeric, optional)
        - Access: self.nodes is a list of node dicts; self.nodes_info is a mapping {ID: node dict}

    2. Edges:
        - Each edge is a dict, with common attributes:
            - source: Source node ID (string)
            - target: Target node ID (string)
            - type: Edge type (e.g., 'explicit', 'system_implicit', 'physical_implicit')
            - cost: Edge cost (numeric)
            - stealth: Stealth score (numeric)
        - Access: self.edges is a list of edge dicts

    You can access nodes via self.nodes / self.nodes_info and edges via self.edges.
    Examples:
        - Get all nodes: for node in self.nodes: ...
        - Get all edges: for edge in self.edges: ...
        - Get details for a node: self.nodes_info['CH_door_contact_state']
    """

    def __init__(self, graph_info_path):
        """
        Initialize the path finder.
        Load graph data and split into nodes and edges for storage.
        """
        print(f"Loading graph data from {graph_info_path}...")
        try:
            self.json_basename = os.path.splitext(os.path.basename(graph_info_path))[0]
            with open(graph_info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Store full graph data
            self.graph_data = data
            # Split into nodes and edges
            self.nodes = data['nodes']  # Node list
            self.edges = data['edges']  # Edge list
            # Mapping from node ID to node info
            self.nodes_info = {node['ID']: node for node in self.nodes}
            # Predecessor map
            self.predecessors_map = self._build_predecessor_map(self.edges)
            print("Graph data loaded and preprocessed.")
        except FileNotFoundError:
            print(f"Error: File not found - {graph_info_path}")
            raise
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error: Invalid or incomplete JSON format - {e}")
            raise

    def _build_predecessor_map(self, edges):
        """Build a predecessor map from the list of edges."""
        pred_map = defaultdict(list)
        for edge in edges:
            source, target = edge.get('source'), edge.get('target')
            if source and target:
                pred_map[target].append(source)
        return pred_map

    def _find_paths_recursive(self, current_node_id, path_from_target, all_backward_paths):
        """Recursively perform DFS to find paths."""
        if current_node_id in path_from_target:
            all_backward_paths.append(path_from_target)
            return

        new_path_from_target = [current_node_id] + path_from_target
        predecessors = self.predecessors_map.get(current_node_id, [])

        if not predecessors:
            all_backward_paths.append(new_path_from_target)
            return

        is_and_case = (len(predecessors) == 1 and 
                       self.nodes_info.get(predecessors[0], {}).get('Type') == 'AND')

        if is_and_case:
            and_node_id = predecessors[0]
            path_with_and_node = [and_node_id] + new_path_from_target
            and_inputs = self.predecessors_map.get(and_node_id, [])
            
            if not and_inputs:
                all_backward_paths.append(path_with_and_node)
            else:
                for input_id in and_inputs:
                    self._find_paths_recursive(input_id, path_with_and_node, all_backward_paths)
        else:
            for pred_id in predecessors:
                self._find_paths_recursive(pred_id, new_path_from_target, all_backward_paths)

    def find_all_paths_to_target(self, target_node_id):
        """Find all paths that can reach the specified target node."""
        if target_node_id not in self.nodes_info:
            print(f"Error: Target node '{target_node_id}' does not exist in the graph.")
            return []

        print(f"Starting reverse path search from target node '{target_node_id}'...")
        backward_paths = []
        self._find_paths_recursive(target_node_id, [], backward_paths)

        forward_paths = [list(reversed(p)) for p in backward_paths]
        print(f"Search complete. Found {len(forward_paths)} raw path branches.")
        return forward_paths

    def _format_node(self, node_id):
        """Helper to format a single node for output."""
        if not isinstance(node_id, str):
            return str(node_id)
        return node_id

    def _build_forest_from_paths(self, paths):
        """Merge forward path lists into a forest rooted at each start node."""
        forest = []
        root_map = {}

        for path in paths:
            if not path: continue

            start_node_id = path[0]
            if start_node_id not in root_map:
                new_root = {'id': start_node_id, 'children': []}
                forest.append(new_root)
                root_map[start_node_id] = new_root
            
            current_node_in_tree = root_map[start_node_id]
            for node_id in path[1:]:
                found_child = next((child for child in current_node_in_tree['children'] if child['id'] == node_id), None)
                if found_child:
                    current_node_in_tree = found_child
                else:
                    new_child = {'id': node_id, 'children': []}
                    current_node_in_tree['children'].append(new_child)
                    current_node_in_tree = new_child
        
        return forest

    def _split_tree_at_or_nodes(self, node):
        """Recursively split the tree. If a non-AND node is an OR branching point, create a new tree for each branch."""
        if not node['children']:
            return [node]

        is_and_node = self.nodes_info.get(node['id'], {}).get('Type') == 'AND'

        if is_and_node:
            reconstructed_children = []
            for child in node['children']:
                reconstructed_children.extend(self._split_tree_at_or_nodes(child))
            return [{'id': node['id'], 'children': reconstructed_children}]

        split_children_branches = []
        for child in node['children']:
            split_children_branches.extend(self._split_tree_at_or_nodes(child))
        
        final_split_trees = []
        for sub_tree in split_children_branches:
            new_tree = {'id': node['id'], 'children': [sub_tree]}
            final_split_trees.append(new_tree)
            
        return final_split_trees

    def _render_tree_recursive(self, file_handle, node, prefix, is_last):
        """Recursively render a (simple) tree structure and write to file."""
        formatted_node = self._format_node(node['id'])

        connector = "└── " if is_last else "├── "
        file_handle.write(f"{prefix}{connector}{formatted_node}\n")
        
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node['children']):
            self._render_tree_recursive(file_handle, child, new_prefix, i == len(node['children']) - 1)

    def save_paths_to_files(self, paths, output_dir, target_id):
        """Build all paths into a forest, split at OR nodes, and save in tree format."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print("Building merged forest structure from paths...")
        merged_forest = self._build_forest_from_paths(paths)

        print("Splitting trees based on OR logic (keeping AND structures)...")
        final_trees = []
        for tree in merged_forest:
            final_trees.extend(self._split_tree_at_or_nodes(tree))

        print(f"Structure split into {len(final_trees)} independent path trees.")
        output_filename = f"PathsForest_Split_for_{target_id}_from_{self.json_basename}.txt"
        file_path = os.path.join(output_dir, output_filename)

        print("Writing all path trees to file...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"### Path Trees: From each start to target {target_id} ###\n")
            f.write("========================================================\n\n")

            for i, tree_root in enumerate(final_trees):
                f.write(f"--- Path Tree {i+1} ---\n")
                f.write(f"{self._format_node(tree_root['id'])}\n")

                for j, child in enumerate(tree_root['children']):
                    self._render_tree_recursive(f, child, "", j == len(tree_root['children']) - 1)

                f.write("\n========================================================\n\n")

        print(f"Path forest successfully saved to: {file_path}")

    def get_paths_as_lists(self, target_id):
        """
        Execute the full path search and processing flow, converting each final path tree
        into a multi-dimensional list and reversing all lists (including nested ones).

        Args:
            target_id (str): Target node ID.

        Returns:
            list: A list where each element is a multi-dimensional reversed list representing an independent path tree.
                  Returns an empty list if no paths are found.
        """
        def reverse_nested_list(lst):
            if isinstance(lst, list):
                # Return empty list for empty input to avoid reversed([]) error
                if not lst:
                    return []
                return [reverse_nested_list(item) for item in reversed(lst)]
            else:
                return lst

        # 1. Find all linear path branches
        all_linear_paths = self.find_all_paths_to_target(target_id)
        if not all_linear_paths:
            return []

        # 2. Build merged forest structure from linear paths
        merged_forest = self._build_forest_from_paths(all_linear_paths)

        # 3. Split trees based on OR logic to get final independent path trees
        final_trees = []
        for tree in merged_forest:
            final_trees.extend(self._split_tree_at_or_nodes(tree))

        # 4. Convert each tree to multi-dimensional list format and reverse it
        all_paths_as_lists = []
        for tree_root in final_trees:
            path_list = self._convert_tree_to_list(tree_root)
            reversed_path_list = reverse_nested_list(path_list)
            all_paths_as_lists.append(reversed_path_list)
            
        return all_paths_as_lists

    def _convert_tree_to_list(self, node):
        """
        Recursive helper function to convert a tree node (dict) into a multi-dimensional list.
        """
        node_id = node['id']

        if not node['children']:
            return [node_id]

        child_lists = [self._convert_tree_to_list(child) for child in node['children']]
        is_and_node = self.nodes_info.get(node_id, {}).get('Type') == 'AND'

        if is_and_node:
            return [node_id, child_lists]
        else:
            if child_lists:
                return [node_id] + child_lists[0]
            else:
                return [node_id]

    def get_node_info(self, node_id):
        """
        Return attribute information for a specified node ID.
        Args:
            node_id (str): Node ID
        Returns:
            dict: Node attribute dictionary; returns empty dict if not found
        
        finder.nodes_info['CH_door_contact_state']['ID']
        """
        return self.nodes_info.get(node_id, {})

    def get_edge_info(self, source_id, target_id):
        """
        Return attribute information for the edge with the specified source and target.
        Args:
            source_id (str): Edge source node ID
            target_id (str): Edge target node ID
        Returns:
            dict: Edge attribute dictionary; returns empty dict if not found
        """
        for edge in self.edges:
            if edge.get('source') == source_id and edge.get('target') == target_id:
                return edge
        return {}

def print_List():
    out_dir = '/home/calista/IoTRuleProject/4-GraphAnalyzer/output/path'
    json_base = 'Rule_withChannel_0618_graph_graphinfo_20250620_102005'
    json_path = os.path.join('/home/calista/IoTRuleProject/4-GraphAnalyzer/output/node/', f'{json_base}.json')
    target_id = 'CH_door_contact_state'  

    try:
        finder = DirectedGraphPathFinder(json_path)
        print("\n" + "="*20 + " OUTPUT " + "="*20)
        paths_for_eval = finder.get_paths_as_lists(target_id)
        
        if paths_for_eval:
            for i, path_list in enumerate(paths_for_eval):
                print(f"\n--- path tree {i+1} ---")
                print(path_list)
        else:
            print("No path to the target node was found.")

    except (FileNotFoundError, KeyError) as e:
        print(f"Error: {e}")

def save_txt():

    out_dir = '/home/calista/IoTRuleProject/4-GraphAnalyzer/output/path'
    json_base = 'Rule_withChannel_0618_graph_graphinfo_20250620_102005'
    json_path = os.path.join('/home/calista/IoTRuleProject/4-GraphAnalyzer/output/node/', f'{json_base}.json')
    target_id = 'CH_door_contact_state'  

    try:

        finder = DirectedGraphPathFinder(json_path)
        

        all_paths = finder.find_all_paths_to_target(target_id)
        

        if all_paths:
            finder.save_paths_to_files(all_paths, out_dir, target_id)
        else:
            print("No path to the target node was found.")

    except (FileNotFoundError, KeyError) as e:
        print(f"Error: {e}")

def print_node_edge_info():
    json_base = 'Rule_withChannel_0618_graph_graphinfo_20250620_102005'
    json_path = os.path.join('/home/calista/IoTRuleProject/4-GraphAnalyzer/output/node/', f'{json_base}.json')
    finder = DirectedGraphPathFinder(json_path)
    print(finder.nodes_info['CH_door_contact_state']['ID'])


if __name__ == '__main__':
    print_List()