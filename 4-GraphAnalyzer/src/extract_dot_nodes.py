"""
extract_dot_nodes.py

This script extracts node and edge information from DOT files representing graph structures, for IoT rule analysis. It parses the DOT file, identifies nodes and edges, classifies node types, and computes betweenness centrality for each node (except AND nodes). The extracted information is output to a JSON file, including detailed node and edge attributes.

Node attributes include:
    - ID: Node identifier in the DOT file.
    - Label: Node label in the DOT file.
    - Type: Node type (trigger, action, AND, OR, physical_channel, system_channel, channel, logic).
    - Target: List of target node IDs (outgoing edges).
    - Source: List of source node IDs (incoming edges).
    - centrality: Betweenness centrality value.

Edge attributes include:
    - source: Source node ID.
    - target: Target node ID.
    - type: Edge type (explicit, physical_implicit, system_implicit).
    - cost: Edge cost (integer, varies by type).
    - stealth: Stealth score (integer, varies by type).

Main functions:
    - parse_dot(dot_path): Parse the DOT file and return a dict with 'nodes' and 'edges' lists.
    - main(): Main entry point. Parse the DOT file, compute node/edge info, and write results to JSON.

Usage:
    Run the script to process the specified DOT file and generate a JSON output containing node and edge information.

Dependencies:
    - re
    - networkx
    - os
    - time
    - json
"""
import re
import networkx as nx
import os
import time
import json

dot_path = "./4-GraphAnalyzer/input/virtualBuilding_filter_graph.dot"
ouput_path = "./4-GraphAnalyzer/output/node"

def parse_dot(dot_path):
    with open(dot_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Regex patterns for different node types
    ch_pattern = re.compile(r'^(CH_[A-Za-z0-9_]+)\s*\[label="([^"]+)"')
    a_pattern = re.compile(r'^(A_[A-Za-z0-9_]+)\s*\[label="([^"]+)"')
    t_pattern = re.compile(r'^(T_[A-Za-z0-9_]+)\s*\[label="([^"]+)"')
    logic_pattern = re.compile(r'^(LOGIC_[A-Za-z0-9_]+)\s*\[label="?([^"\] ]+)"?')
    edge_pattern = re.compile(r'^\s*([A-Za-z0-9_]+)\s*->\s*([A-Za-z0-9_]+)')

    nodes = {}
    edges = []

    for line in lines:
        line = line.strip()
        # Only process node lines starting with CH_/A_/T_/LOGIC_ or edge lines containing ->; skip others
        if not (line.startswith("CH_") or line.startswith("A_") or line.startswith("T_") or line.startswith("LOGIC_") or "->" in line):
            continue

        # Check if this line is an edge
        if "->" in line:
            edge_match = edge_pattern.match(line)
            if edge_match:
                src, tgt = edge_match.groups()
                # Special handling for LOGIC nodes
                if src.startswith("LOGIC_"):
                    edge_type = "explicit"
                    cost = 1
                    stealth = 1
                elif tgt.startswith("LOGIC_"):
                    edge_type = "explicit"
                    cost = None
                    stealth = None
                else:
                    edge_type = "explicit"
                    cost = 1
                    stealth = 1
                    src_type = nodes.get(src, {}).get("Type", "")
                    tgt_type = nodes.get(tgt, {}).get("Type", "")
                    if "physical_channel" in (src_type, tgt_type):
                        edge_type = "physical_implicit"
                        cost = 5
                        stealth = 3
                    elif "system_channel" in (src_type, tgt_type):
                        edge_type = "system_implicit"
                        cost = 3
                        stealth = 2
                edges.append({
                    "source": src,
                    "target": tgt,
                    "type": edge_type,
                    "cost": cost,
                    "stealth": stealth
                })
            continue

        # Match nodes
        node_id, label, node_type = None, None, None
        if line.startswith("CH_"):
            m = ch_pattern.match(line)
            if m:
                node_id, label = m.groups()
                if "[Physical]" in label:
                    node_type = "physical_channel"
                elif "[System]" in label:
                    node_type = "system_channel"
                else:
                    node_type = "channel"
        elif line.startswith("A_"):
            m = a_pattern.match(line)
            if m:
                node_id, label = m.groups()
                node_type = "action"
        elif line.startswith("T_"):
            m = t_pattern.match(line)
            if m:
                node_id, label = m.groups()
                node_type = "trigger"
        elif line.startswith("LOGIC_"):
            m = logic_pattern.match(line)
            if m:
                node_id, label = m.groups()
                if "AND" in node_id:
                    node_type = "AND"
                elif "OR" in node_id:
                    node_type = "OR"
                else:
                    node_type = "logic"
        if node_id:
            nodes[node_id] = {
                "ID": node_id,
                "Label": label,
                "Type": node_type,
                "Target": [],
                "Source": [],
                "centrality": 0.0
            }

    # Build Target and Source lists
    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if src in nodes:
            nodes[src]["Target"].append(tgt)
        if tgt in nodes:
            nodes[tgt]["Source"].append(src)

    # Build directed graph and compute betweenness centrality
    G = nx.DiGraph()
    G.add_nodes_from(nodes.keys())
    G.add_edges_from([(e["source"], e["target"]) for e in edges])
    # Compute centrality only for non-AND and non-channel nodes
    non_and_nodes = [nid for nid, n in nodes.items() if n["Type"] != "AND"]
    centrality = nx.betweenness_centrality(G.subgraph(non_and_nodes), normalized=True)
    for node_id in nodes:
        if nodes[node_id]["Type"] != "AND" and nodes[node_id]["Type"] not in ("physical_channel", "system_channel", "channel"):
            nodes[node_id]["centrality"] = centrality.get(node_id, 0)
        else:
            nodes[node_id]["centrality"] = 0.0

    return {
        "nodes": list(nodes.values()),
        "edges": edges
    }


def main():

    graph_info = parse_dot(dot_path)
    # Auto-generate output filename
    basename = os.path.splitext(os.path.basename(dot_path))[0]
    outname = f"{basename}_graphinfo.json"
    outpath = os.path.join(ouput_path, outname)
    # Output JSON including nodes and edges
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(graph_info, f, ensure_ascii=False, indent=2)
    print(f"Node and edge information written to: {outpath}")
    print(f"Total nodes: {len(graph_info['nodes'])}")
    print(f"Total edges: {len(graph_info['edges'])}")

if __name__ == "__main__":
    main()
