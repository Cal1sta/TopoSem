import json
from collections import Counter

def count_channels(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)


    system_channels = []
    physical_channels = []


    triggers_system_channels = []
    triggers_physical_channels = []
    actions_system_channels = []
    actions_physical_channels = []

    for rule in rules:
        triggers = rule.get('triggers', {})
        conditions = triggers.get('conditions', [])
        for cond in conditions:
            sys_ch = cond.get('implicit_system_channel')
            phy_ch = cond.get('implicit_physical_channel')
            if sys_ch:
                system_channels.append(sys_ch)
                triggers_system_channels.append(sys_ch)
            if phy_ch:
                physical_channels.append(phy_ch)
                triggers_physical_channels.append(phy_ch)

        actions = rule.get('actions', [])
        for act in actions:
            sys_ch = act.get('implicit_system_channel')
            phy_ch = act.get('implicit_physical_channel')
            if sys_ch:
                system_channels.append(sys_ch)
                actions_system_channels.append(sys_ch)
            if phy_ch:
                physical_channels.append(phy_ch)
                actions_physical_channels.append(phy_ch)

    system_count = Counter(system_channels)
    physical_count = Counter(physical_channels)
    triggers_system_count = Counter(triggers_system_channels)
    triggers_physical_count = Counter(triggers_physical_channels)
    actions_system_count = Counter(actions_system_channels)
    actions_physical_count = Counter(actions_physical_channels)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("all system_channel counts:\n")
        for k, v in system_count.items():
            f.write(f"{k}: {v}\n")
        f.write("\nall physical_channel counts:\n")
        for k, v in physical_count.items():
            f.write(f"{k}: {v}\n")

        f.write("\ntriggers of system_channel counts:\n")
        for k, v in triggers_system_count.items():
            f.write(f"{k}: {v}\n")
        f.write("\ntriggers of physical_channel counts:\n")
        for k, v in triggers_physical_count.items():
            f.write(f"{k}: {v}\n")

        f.write("\nactions of system_channel counts:\n")
        for k, v in actions_system_count.items():
            f.write(f"{k}: {v}\n")
        f.write("\nactions of physical_channel counts:\n")
        for k, v in actions_physical_count.items():
            f.write(f"{k}: {v}\n")

if __name__ == '__main__':
    count_channels(
        './2-ChannelInference_TopoFilter/output/virtualBuilding_gemini-2.5-pro_slices/virtualBuilding_gemini-2.5.json',
        './2-ChannelInference_TopoFilter/output/ChannelCount/channel_count_result.txt'
    )