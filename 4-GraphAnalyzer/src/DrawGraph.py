# Find all paths that can reach the target node, and draw graphs
import pygraphviz as pgv
import networkx as nx
import os 

def find_all_paths_to_target(dot_file_path, target_node_id):
    """
    Find all simple paths from any node in the graph to the specified target node.

    Args:
        dot_file_path (str): Path to the DOT file.
        target_node_id (str): ID of the target node.

    Returns:
        tuple: (list_of_paths, pygraphviz_graph_object or None)
               If the target node is not found or no paths exist, the list is empty.
               If loading fails, the graph object is None.
    """
    all_found_paths = []
    pgv_graph = None # Initialize as None
    try:
        pgv_graph = pgv.AGraph(dot_file_path, strict=False, directed=True)
    except Exception as e:
        print(f"Error loading DOT file '{dot_file_path}': {e}")
        return all_found_paths, None # Graph load failed

    nx_graph = nx.DiGraph(pgv_graph)

    if not nx_graph.has_node(target_node_id):
        print(f"Error: Target node '{target_node_id}' not found in the graph.")
        return all_found_paths, pgv_graph

    for source_node_id in nx_graph.nodes():
        if source_node_id == target_node_id:
            continue
        try:
            paths_from_source = list(nx.all_simple_paths(nx_graph,
                                                         source=source_node_id,
                                                         target=target_node_id))
            if paths_from_source:
                all_found_paths.extend(paths_from_source)
        except nx.NodeNotFound:
            print(f"Warning: Node '{source_node_id}' or '{target_node_id}' caused an issue during path search.")
            continue
        except Exception as e:
            print(f"Unexpected error during path search from '{source_node_id}': {e}")
            continue
    return all_found_paths, pgv_graph

def create_and_save_subgraph_with_original_styles(original_pgv_graph, paths, output_dot_path, output_image_path):
    """
    Create a subgraph containing only path elements (nodes and edges), preserving original styles.

    Args:
        original_pgv_graph (pygraphviz.AGraph): The original loaded pygraphviz graph object.
        paths (list): List containing all found paths.
        output_dot_path (str): Path to the output subgraph DOT file.
        output_image_path (str): Path to the output subgraph image file.
    """
    if not paths:
        print("Type 1 (Subgraph): No paths found; no files generated.")
        return

    path_nodes_set = set()
    path_edges_set = set()
    for path in paths:
        for node_id in path:
            path_nodes_set.add(node_id)
        for i in range(len(path) - 1):
            path_edges_set.add((path[i], path[i+1]))

    # Convert Attribute object to a standard dict to allow modification
    graph_attrs = dict(original_pgv_graph.graph_attr)
    graph_attrs.pop('charset', None) # Safely remove 'charset' from the dict copy

    # Create a new empty graph, passing in the processed attributes
    subgraph = pgv.AGraph(name=f"subgraph_{original_pgv_graph.name}",
                            directed=True,
                            strict=original_pgv_graph.graph_attr.get('strict', False),
                            **graph_attrs)

    for node_id in path_nodes_set:
        try:
            original_node = original_pgv_graph.get_node(node_id)
            subgraph.add_node(node_id)
            subgraph.get_node(node_id).attr.update(original_node.attr)
        except KeyError:
            print(f"Warning (Subgraph): Node '{node_id}' not found in the original graph; cannot add to subgraph.")

    for u_id, v_id in path_edges_set:
        try:
            original_edge = original_pgv_graph.get_edge(u_id, v_id)
            subgraph.add_edge(u_id, v_id)
            subgraph.get_edge(u_id, v_id).attr.update(original_edge.attr)
        except KeyError:
            print(f"Warning (Subgraph): Edge ({u_id} -> {v_id}) not found in the original graph; cannot add to subgraph.")
            
    try:
        subgraph.write(output_dot_path)
        print(f"\nType 1 (Subgraph): Saved DOT file containing only paths to: {output_dot_path}")
        subgraph.draw(output_image_path, prog='dot', format='png')
        print(f"Type 1 (Subgraph): Saved image file containing only paths to: {output_image_path}")
    except Exception as e:
        print(f"Type 1 (Subgraph): Error saving files: {e}")
        print("Please ensure Graphviz is installed and the 'dot' command is in your system PATH.")

def create_and_save_full_highlighted_graph(original_pgv_graph_ref, paths, target_node_id, output_dot_path, output_image_path):
    """
    Highlight paths on the full graph by dimming non-path elements, then save.

    Args:
        original_pgv_graph_ref (pygraphviz.AGraph): Reference to the original loaded pygraphviz graph object.
        paths (list): List containing all found paths.
        target_node_id (str): Target node ID (not used here, reserved for future use).
        output_dot_path (str): Path to the highlighted DOT output file.
        output_image_path (str): Path to the highlighted image output file.
    """
    if not paths:
        print("Type 2 (Full Graph Highlight): No paths found; no files generated.")
        return

    # --- Manually implement smart copy to replace buggy .copy() ---
    graph_attrs = dict(original_pgv_graph_ref.graph_attr)
    graph_attrs.pop('charset', None)
    g_highlighted = pgv.AGraph(
        name=f"copy_of_{original_pgv_graph_ref.name}",
        directed=True,
        strict=original_pgv_graph_ref.graph_attr.get('strict', False),
        **graph_attrs
    )
    for node in original_pgv_graph_ref.nodes():
        g_highlighted.add_node(node.name)
        g_highlighted.get_node(node.name).attr.update(node.attr)
    for edge in original_pgv_graph_ref.edges():
        g_highlighted.add_edge(edge[0].name, edge[1].name)
        g_highlighted.get_edge(edge[0].name, edge[1].name).attr.update(edge.attr)
    # --- End manual copy ---

    # --- New styling logic: dim non-path elements ---
    # Define style for irrelevant elements (to be dimmed)
    # To make the background color effective, set style='filled'
    dimmed_attrs = {'color': '#d3d3d3', 'fontcolor': '#d3d3d3', 'style': 'filled', 'fillcolor': '#f5f5f5'} # Light gray border/font, whitesmoke fill

    # Collect all nodes and edges on the paths
    path_nodes_set = set()
    path_edges_set = set()
    for path in paths:
        for node_id in path:
            path_nodes_set.add(node_id)
        for i in range(len(path) - 1):
            path_edges_set.add((path[i], path[i+1]))

    # 1. Iterate over all nodes
    for node in g_highlighted.nodes():
        # If a node is not on any path, dim it
        if node.name not in path_nodes_set:
            for attr, value in dimmed_attrs.items():
                node.attr[attr] = value

    # 2. Iterate over all edges
    for edge in g_highlighted.edges():
        edge_tuple = (edge[0].name, edge[1].name)
        # If an edge is not on any path, dim it
        if edge_tuple not in path_edges_set:
            edge.attr['color'] = dimmed_attrs['color']
            # If an edge has a label, dim the label too
            if 'label' in edge.attr and edge.attr['label']:
                 edge.attr['fontcolor'] = dimmed_attrs['fontcolor']
    # --- End logic ---
            
    try:
        g_highlighted.write(output_dot_path)
        print(f"\nType 2 (Full Graph Highlight): Saved highlighted DOT file to: {output_dot_path}")
        g_highlighted.draw(output_image_path, prog='dot', format='png')
        print(f"Type 2 (Full Graph Highlight): Saved highlighted image file to: {output_image_path}")
    except Exception as e:
        print(f"Type 2 (Full Graph Highlight): Error saving files: {e}")
        print("Please ensure Graphviz is installed and the 'dot' command is in your system PATH.")

if __name__ == '__main__':
    # --- User configuration ---
    target_node = 'A_Rule_58_0'  # Target node ID for analysis

    input_dir = "./4-GraphAnalyzer/input/"
    output_dir_subgraph = "./4-GraphAnalyzer/output/subgraph/"
    output_dir_highlight = "./4-GraphAnalyzer/output/highlight/"
    graph_file_base = "virtualBuilding_filter_graph"  # Your input DOT filename (without .dot suffix)
    # --- End user configuration ---

    # Build full paths for input/output files
    input_graph_file = os.path.join(input_dir, graph_file_base + ".dot")

    # Name output files for Type 1 (Subgraph)
    subgraph_output_base_name = f"subgraph_to_{target_node}_from_{graph_file_base}"
    subgraph_dot_file = os.path.join(output_dir_subgraph, subgraph_output_base_name + ".dot")
    subgraph_image_file = os.path.join(output_dir_subgraph, subgraph_output_base_name + ".png")

    # Name output files for Type 2 (Full Graph Highlight)
    full_highlight_output_base_name = f"highlight_to_{target_node}_from_{graph_file_base}" # Updated name to reflect new style
    full_highlight_dot_file = os.path.join(output_dir_highlight, full_highlight_output_base_name + ".dot")
    full_highlight_image_file = os.path.join(output_dir_highlight, full_highlight_output_base_name + ".png")

    # Ensure output directories exist
    os.makedirs(output_dir_highlight, exist_ok=True)
    os.makedirs(output_dir_subgraph, exist_ok=True)

    # Check input file existence
    if not os.path.exists(input_graph_file):
        print(f"Error: Input file '{input_graph_file}' not found. Please ensure it exists at the specified path.")
        print("Script aborted.")
        exit() # Exit if input file does not exist

    print(f"Finding all paths to target node '{target_node}' (in file '{input_graph_file}')\n")
    
    paths_to_target, initial_pgv_graph = find_all_paths_to_target(input_graph_file, target_node)

    if initial_pgv_graph: # Ensure the graph loaded successfully
        if paths_to_target:
            print(f"Found {len(paths_to_target)} paths to '{target_node}':")
            for i, path in enumerate(paths_to_target):
                print(f"  Path {i+1}: {' -> '.join(path)}")

            # Generate Type 1 files: subgraph with only paths, preserving original style
            create_and_save_subgraph_with_original_styles(initial_pgv_graph, paths_to_target, subgraph_dot_file, subgraph_image_file)

            # Generate Type 2 files: full graph with non-path elements dimmed to highlight paths
            create_and_save_full_highlighted_graph(initial_pgv_graph, paths_to_target, target_node, full_highlight_dot_file, full_highlight_image_file)

        else:
            print(f"No paths to '{target_node}' were found.")
    else:
        print(f"Subsequent operations aborted due to failure to load or parse input graph '{input_graph_file}'.")
        
    print("\n" + "="*50 + "\nScript finished.\n" + "="*50)