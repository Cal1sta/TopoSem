# TopoSem: IoT Rule Semantic Analysis and Graph Generation Framework

## Project Structure

```
TopoSem/
├── 1-SemanticParser/          # Rule parsing and semantic analysis
├── 2-ChannelInference_TopoFilter/  # Channel inference and topology filtering
├── 3-GraphGenerator/          # Graph generation and visualization
├── 4-GraphAnalyzer/           # Graph analysis and path finding
└── ReadMe.md                  # This documentation
```

## Dependencies

- Python 3.x
- OpenAI API (for LLM integration)
- NetworkX (for graph analysis)
- Graphviz (for graph visualization)
- PyGraphviz (for graph manipulation)

## Module Descriptions

### 1. SemanticParser

**Purpose**: Converts natural language IoT automation rules into structured JSON format.

**Key Files**:
- `parser.py`: Main parsing engine using LLM integration
- `prompt.txt`: LLM prompt template for rule parsing

**Features**:
- Processes building ontology information (Brick Schema)
- Maps device attributes and capabilities
- Extracts triggers, conditions, and actions
- Generates structured JSON output with spatial context
- Supports parallel processing with threading

**Input**: Natural language rule descriptions, device attribute lists, building ontology
**Output**: Structured JSON rules with device mappings and spatial context

### 2. ChannelInference_TopoFilter

**Purpose**: Discovers implicit channels between rules and filters interactions based on spatial topology.

**Key Files**:
- `ChannelInference.py`: Main LLM-based channel inference engine
- `InteractionDiscover.py`: Discovers rule interactions via implicit channels
- `InteractionFilter.py`: Filters interactions based on spatial reachability
- `CountChannel.py`: Channel counting and statistics
- `prompt.txt`: LLM prompt for channel inference

**Features**:
- Identifies physical and system implicit channels
- Discovers cross-rule interactions
- Implements topology filtering rules
- Generates interaction reports and logs

**Input**: Structured JSON rules from SemanticParser
**Output**: Filtered interaction data with spatial validation

### 3. GraphGenerator

**Purpose**: Generates visual graph representations of rule interactions.

**Key Files**:
- `src/GraphGenerator.py`: Main graph generation engine

**Features**:
- Creates DOT format graphs using Graphviz
- Visualizes rule triggers, actions, and implicit channels
- Supports logical operators (AND/OR) in rule conditions
- Generates both DOT source files and PNG images
- Color-codes different node types:
  - Triggers: Light blue boxes
  - Actions: Light yellow boxes
  - Channels: Pink ellipses
  - Logic nodes: Gray diamonds

**Input**: Filtered interaction data from ChannelInference_TopoFilter
**Output**: DOT files and PNG graph visualizations

### 4. GraphAnalyzer

**Purpose**: Analyzes generated graphs for path discovery and scoring.

**Key Files**:
- `src/extract_dot_nodes.py`: Extracts nodes and edges from DOT files
- `src/SearchPath.py`: Finds all paths to target nodes
- `src/CalculateScore.py`: Calculates path metrics and scores
- `src/DrawGraph.py`: Creates subgraph and highlighted visualizations

**Features**:
- Extracts graph structure from DOT files
- Computes betweenness centrality for nodes
- Finds all paths to specified target nodes
- Calculates path metrics:
  - Total cost
  - Average stealth
  - Path length
  - Path criticality
- Supports complex nested path structures with AND/OR logic
- Generates subgraph and highlighted graph visualizations
- Exports analysis results to CSV format

**Input**: DOT files from GraphGenerator
**Output**: Path analysis results, metrics, and visualizations

## Usage Workflow

All commands should be run from the root `/TopoSem/` directory.

### Step 1: Parse Rules
```bash
python 1-SemanticParser/parser.py
```
- Processes natural language rules
- Generates structured JSON output
- Requires OpenAI API key configuration

### Step 2: Infer Channels and Filter Interactions
```bash
python 2-ChannelInference_TopoFilter/ChannelInference.py
python 2-ChannelInference_TopoFilter/InteractionDiscover.py
python 2-ChannelInference_TopoFilter/InteractionFilter.py
```
- Discovers implicit channels between rules
- Identifies cross-rule interactions
- Filters based on spatial topology

### Step 3: Generate Graphs
```bash
python 3-GraphGenerator/src/GraphGenerator.py
```
- Creates visual graph representations
- Generates DOT and PNG files

### Step 4: Analyze Graphs
```bash
python 4-GraphAnalyzer/src/extract_dot_nodes.py
python 4-GraphAnalyzer/src/CalculateScore.py
python 4-GraphAnalyzer/src/DrawGraph.py
```
- Extracts graph structure
- Calculates path metrics
- Generates analysis visualizations

