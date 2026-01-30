import json
import graphviz
import os

def generate_interaction_graph(rules_data, output_filename_prefix="smart_building_rules_graph"):
    """
    generate the interaction graph based on the rule data.
    """
    dot = graphviz.Digraph('SmartBuildingRules', comment='Smart Building Control Rule Interaction Graph')
    dot.attr(rankdir='LR', splines='spline', nodesep='0.7', ranksep='1.5', overlap='prism', concentrate='false', compound='true', charset='UTF-8')

    all_channels = set()
    for rule in rules_data:
        triggers = rule.get('triggers', [])
        if isinstance(triggers, dict):
            triggers = [triggers]
        for trigger_block in triggers:
            conditions = trigger_block.get('conditions', [])
            if not isinstance(conditions, list):
                conditions = [conditions] if isinstance(conditions, dict) else []
            for cond in conditions:
                if cond and isinstance(cond, dict):
                    for key in ['implicit_channel', 'implicit_physical_channel', 'implicit_system_channel']:
                        if cond.get(key):
                            all_channels.add(cond[key])
        for action in rule.get('actions', []):
            if action and isinstance(action, dict):
                for key in ['implicit_channel', 'implicit_physical_channel', 'implicit_system_channel']:
                    if action.get(key):
                        all_channels.add(action[key])

    for channel_name in sorted(list(all_channels)):
        channel_type = "Unknown"
        for rule in rules_data:
            triggers = rule.get('triggers', [])
            if isinstance(triggers, dict):
                triggers = [triggers]
            for trigger_block in triggers:
                conditions = trigger_block.get('conditions', [])
                if not isinstance(conditions, list):
                    conditions = [conditions] if isinstance(conditions, dict) else []
                for cond in conditions:
                    if cond and isinstance(cond, dict):
                        if cond.get('implicit_physical_channel') == channel_name:
                            channel_type = "Physical"
                        elif cond.get('implicit_system_channel') == channel_name:
                            channel_type = "System"
                        elif cond.get('implicit_channel') == channel_name:
                            channel_type = "Unknown"
            for action in rule.get('actions', []):
                if action and isinstance(action, dict):
                    if action.get('implicit_physical_channel') == channel_name:
                        channel_type = "Physical"
                    elif action.get('implicit_system_channel') == channel_name:
                        channel_type = "System"
                    elif action.get('implicit_channel') == channel_name:
                        channel_type = "Unknown"
        node_id = f'CH_{channel_name.replace(":", "_").replace(".", "_")}'
        dot.node(node_id, 
                 label=f"{channel_name} [{channel_type}]", 
                 shape='ellipse', 
                 style='filled', 
                 fillcolor='#FFC0CB',
                 fontcolor='black',
                 color='red',
                 penwidth='1.5')

    for rule in rules_data:
        rule_id_safe = rule['rule_id'].replace(":", "_").replace(".", "_")

        current_rule_action_node_ids = []
        for act_idx, action in enumerate(rule.get('actions', [])):
            if not isinstance(action, dict): continue
            action_device = action.get('device_name', 'N/A')
            action_command = action.get('command', 'N/A')
            action_value_raw = action.get('value', '')
            action_value = str(action_value_raw) if action_value_raw is not None else ''
            action_label = f"Action_{rule_id_safe}:{action_device}.{action_command}({action_value})"

            action_node_id = f'A_{rule_id_safe}_{act_idx}'
            dot.node(action_node_id, 
                     label=action_label, 
                     shape='box', 
                     style='filled,rounded', 
                     fillcolor='#FFFACD',
                     color='#BDB76B',
                     fontcolor='#4A4A4A')
            current_rule_action_node_ids.append(action_node_id)

            for key in ['implicit_channel', 'implicit_physical_channel', 'implicit_system_channel']:
                if action.get(key):
                    channel_name = action[key]
                    channel_node_id = f'CH_{channel_name.replace(":", "_").replace(".", "_")}'
                    dot.edge(action_node_id, channel_node_id, color='red', penwidth='1.5')

        triggers = rule.get('triggers', [])
        if isinstance(triggers, dict):
            triggers = [triggers]
        for trigger_block_idx, trigger_block in enumerate(triggers):
            if not isinstance(trigger_block, dict): continue

            conditions = trigger_block.get('conditions', [])
            logical_operator = trigger_block.get('logical_operator')

            if not isinstance(conditions, list):
                conditions = [conditions] if isinstance(conditions, dict) else []
            if not conditions: continue

            condition_node_ids_for_this_block = []
            for cond_idx, cond in enumerate(conditions):
                if not isinstance(cond, dict): continue

                cond_device = cond.get('device_name', 'N/A')
                cond_attribute = cond.get('attribute', 'N/A')
                cond_operator = cond.get('operator', '')
                cond_value_raw = cond.get('value', '')
                cond_value = str(cond_value_raw) if cond_value_raw is not None else ''
                condition_label = f"Trigger_({rule_id_safe}):{cond_device}.{cond_attribute}{cond_operator}{cond_value}"
                condition_node_id = f'T_{rule_id_safe}_{cond_idx}'
                dot.node(condition_node_id, 
                         label=condition_label, 
                         shape='box', 
                         style='filled,rounded', 
                         fillcolor='#E0FFFF',
                         color='#4682B4',
                         fontcolor='#3A3A3A')
                condition_node_ids_for_this_block.append(condition_node_id)

                for key in ['implicit_channel', 'implicit_physical_channel', 'implicit_system_channel']:
                    if cond.get(key):
                        channel_name = cond[key]
                        channel_node_id = f'CH_{channel_name.replace(":", "_").replace(".", "_")}'
                        dot.edge(channel_node_id, condition_node_id, color='red', penwidth='1.5')

            source_for_actions = None
            if len(condition_node_ids_for_this_block) > 1 and logical_operator and logical_operator.upper() in ["AND", "OR"]:
                logic_node_id = f'LOGIC_{rule_id_safe}_{logical_operator}'
                logical_label = f'{logical_operator.upper()}'
                dot.node(logic_node_id, 
                         label=logical_label,
                         shape='diamond', 
                         style='filled', 
                         fillcolor='#D3D3D3',
                         color='#808080',
                         fontcolor='black')
                for cond_node_id in condition_node_ids_for_this_block:
                    dot.edge(cond_node_id, logic_node_id, color='#AAAAAA', penwidth='1.0')
                source_for_actions = logic_node_id
            elif len(condition_node_ids_for_this_block) == 1:
                source_for_actions = condition_node_ids_for_this_block[0]
            elif len(condition_node_ids_for_this_block) > 1:
                implicit_and_node_id = f'IMPLICIT_AND_{rule_id_safe}_{trigger_block_idx}'
                dot.node(implicit_and_node_id, 
                         label="AND", 
                         shape='diamond', 
                         style='filled', 
                         fillcolor='#E8E8E8', 
                         color='#B0B0B0',
                         fontsize='10',
                         fontcolor='black')
                for cond_node_id in condition_node_ids_for_this_block:
                    dot.edge(cond_node_id, implicit_and_node_id, color='#C0C0C0', penwidth='1.0')
                source_for_actions = implicit_and_node_id

            if source_for_actions:
                for action_node_id in current_rule_action_node_ids:
                    dot.edge(source_for_actions, action_node_id, color='#999999', style='dashed', penwidth='1.0')

    dot_dir = os.path.join(os.path.dirname(output_filename_prefix), "DOT")
    pic_dir = os.path.join(os.path.dirname(output_filename_prefix), "PIC")
    if not os.path.exists(dot_dir):
        os.makedirs(dot_dir)
    if not os.path.exists(pic_dir):
        os.makedirs(pic_dir)

    base_name = os.path.basename(output_filename_prefix)
    dot_source_file_dot = os.path.join(dot_dir, base_name + '.dot')
    png_file = os.path.join(pic_dir, base_name + '.png')

    try:
        dot.save(dot_source_file_dot)
        print(f"DOT source file saved: {dot_source_file_dot}")

        rendered_path = dot.render(filename=base_name, directory=pic_dir, view=False, format='png', cleanup=True)
        print(f"Interaction graph generated: {png_file}")

    except graphviz.exceptions.ExecutableNotFound:
        print("Error: Graphviz executable file not found. Please ensure Graphviz is installed and added to the system PATH.")
        print("Attempting to save DOT source code...")
        try:
            dot.save(dot_source_file_dot)
            print(f"DOT source file saved: {dot_source_file_dot}")
            print(f"You can use Graphviz tool to manually compile this file (e.g.: dot -Tpng \"{dot_source_file_dot}\" -o \"{png_file}\")")
        except Exception as save_e:
            print(f"Failed to save DOT source file: {save_e}")
    except Exception as e:
        print(f"Error: {e}")
        print("Attempting to save DOT source code...")
        try:
            dot.save(dot_source_file_dot)
            print(f"DOT source file saved: {dot_source_file_dot}")
        except Exception as save_e:
            print(f"Failed to save DOT source file: {save_e}")

def load_rules_from_file(filepath):
    """
    load the rule data from the JSON file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        return rules
    except FileNotFoundError:
        print(f"Error: input file '{filepath}' not found. Please ensure the file exists.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse JSON file '{filepath}': {e}")
        return None
    except Exception as e:
        print(f"Error: unknown error when reading or parsing file '{filepath}': {e}")
        return None

if __name__ == "__main__":
    file_name_base = "virtualBuilding_filter"
    input_dir = "./3-GraphGenerator/input/"
    output_dir = "./3-GraphGenerator/output/"

    input_file = os.path.join(input_dir, file_name_base + ".json")
    output_filename_prefix = os.path.join(output_dir, file_name_base + "_graph")

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Output directory created: {output_dir}")
        except OSError as e:
            print(f"Error: failed to create output directory '{output_dir}': {e}")
            exit()

    if not os.path.exists(input_file):
        print(f"Error: input file '{input_file}' not found. Please check the path and file name.")
        exit()

    rules_data = load_rules_from_file(input_file)

    if rules_data:
        print(f"Loaded {len(rules_data)} rules from '{input_file}'. Generating interaction graph...")
        generate_interaction_graph(rules_data, output_filename_prefix=output_filename_prefix)
    else:
        print("Failed to load rule data, cannot generate graph.")