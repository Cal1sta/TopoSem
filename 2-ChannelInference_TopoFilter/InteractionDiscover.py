import os
import json

'''
After discovering implicit channels, search for interactions between rules
rule_X.deivce.actions--> implicite_channel--> rule_Y.device.triggers
The recorded data is the name of the implicit channel, rule ID, and device location
Algorithm design
Input: rule_data
Output: the name of the implicit channel, rule ID, and device location

[
    interaction_1: {
        actions:{
            "implicit_channel": "temperature",
            "rule_id": "Rule_1",
            "device_name": "VAV_1A",
            "device_location": "Office 1A"
        },
        triggers:{
            "implicit_channel": "temperature",
            "rule_id": "Rule_2",
            "device_name": "TempSensor_2A",
            "device_location": "Office 2A"
        }
    },
    interaction_2: {
    ...    }
]
'''
# The output format uses keys like interaction_1, interaction_2, etc.
# We'll adjust the output to match this format.
def format_interactions(interactions):
    formatted = {}
    for idx, interaction in enumerate(interactions, 1):
        key = f'interaction_{idx}'
        formatted[key] = interaction
    return formatted
def discover_interactions(rule_data):
    interactions = []
    # Build index for triggers by implicit channel (both physical and system)
    trigger_index = []
    for rule in rule_data:
        for cond in rule['triggers']['conditions']:
            for channel_key in ['implicit_physical_channel', 'implicit_system_channel']:
                channel = cond.get(channel_key)
                if channel:
                    trigger_index.append({
                        'implicit_channel': channel,
                        'channel_type': channel_key,
                        'rule_id': rule['rule_id'],
                        'device_name': cond.get('device_name'),
                        'device_location': next(
                            (dl['location'] for dl in rule['context']['device_locations'] if dl['device_name'] == cond.get('device_name')),
                            None
                        )
                    })

    # Find interactions: actions in one rule, triggers in another, same implicit channel
    for rule in rule_data:
        for action in rule['actions']:
            for channel_key in ['implicit_physical_channel', 'implicit_system_channel']:
                channel = action.get(channel_key)
                if channel:
                    for trig in trigger_index:
                        if (
                            trig['implicit_channel'] == channel and
                            trig['channel_type'] == channel_key and
                            trig['rule_id'] != rule['rule_id']
                        ):
                            interaction = {
                                'actions': {
                                    'implicit_channel': channel,
                                    'channel_type': channel_key,
                                    'rule_id': rule['rule_id'],
                                    'device_name': action.get('device_name'),
                                    'device_location': next(
                                        (dl['location'] for dl in rule['context']['device_locations'] if dl['device_name'] == action.get('device_name')),
                                        None
                                    )
                                },
                                'triggers': trig
                            }
                            interactions.append(interaction)

    # Save results
    output_dir = './2-ChannelInference_TopoFilter/output/interaction'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'interactions.json')
    formatted = format_interactions(interactions)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)
        print(f'Interactions discovered and saved to {output_path}')

if __name__ == '__main__':
    input_path = './2-ChannelInference_TopoFilter/output/virtualBuilding_gemini-2.5-pro_slices/virtualBuilding_gemini-2.5.json'
    with open(input_path, 'r', encoding='utf-8') as f:
        rule_data = json.load(f)
    discover_interactions(rule_data)
