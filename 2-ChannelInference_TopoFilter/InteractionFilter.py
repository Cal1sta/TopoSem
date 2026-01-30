'''
check if the interactions in interaction.json are space reachable
'''

import json
import os

# ==============================================================================
# 1. Ontology Data Representation - 
# ==============================================================================

# 1.1 device -> space location mapping
device_locations = {
    "bldg:Central_AHU": "Mechanical_Room_1", "bldg:Main_Chiller": "Mechanical_Room_1",
    "bldg:Main_Boiler": "Mechanical_Room_1", "bldg:Main_CoolingTower": "Roof",
    "bldg:VAV_1A": "Office_1A", "bldg:TempSensor_1A": "Office_1A",
    "bldg:VAV_1B": "Office_1B", "bldg:TempSensor_1B": "Office_1B",
    "bldg:VAV_2A": "Office_2A", "bldg:TempSensor_2A": "Office_2A",
    "bldg:VAV_2B": "Office_2B", "bldg:TempSensor_2B": "Office_2B",
    "bldg:VAV_2C": "Office_2C", "bldg:TempSensor_2C": "Office_2C",
    "bldg:VAV_3A": "Office_3A", "bldg:TempSensor_3A": "Office_3A",
    "bldg:VAV_3B": "Office_3B", "bldg:TempSensor_3B": "Office_3B",
    "bldg:VAV_Conf1": "Conference_Room_1", "bldg:CO2Sensor_Conf1": "Conference_Room_1",
    "bldg:VAV_ServerRoom": "Server_Room", "bldg:HumiditySensor_ServerRoom": "Server_Room",
    "bldg:Luminaire_Lobby_1": "Lobby_1", "bldg:Luminance_Sensor_Lobby_1": "Lobby_1",
    "bldg:Luminaire_Office_1A": "Office_1A", "bldg:Occupancy_Sensor_Office_1A": "Office_1A",
    "bldg:Luminaire_Office_2A": "Office_2A", "bldg:Smoke_Detector_Office_2A": "Office_2A",
    "bldg:Horn_Hallway_1": "Hallway_1", "bldg:Smoke_Detector_Office_1A": "Office_1A",
    "bldg:Camera_Hallway_1": "Hallway_1", "bldg:Reader_Office_1A": "Office_1A",
}

# 1.2 space -> floor mapping
space_floors = {
    "Office_1A": 1, "Office_1B": 1, "Conference_Room_1": 1, "Server_Room": 1,
    "Mechanical_Room_1": 1, "Lobby_1": 1, "Main_Entrance": 1, "Control_Room": 1, "Hallway_1": 1,
    "Office_2A": 2, "Office_2B": 2, "Office_2C": 2, "Conference_Room_2": 2, "Hallway_2": 2,
    "Office_3A": 3, "Office_3B": 3, "Conference_Room_3": 3, "Hallway_3": 3,
    "Roof": 4
}

# 1.3 HVAC service area
hvac_served_spaces = {
    "Office_1A", "Office_1B", "Conference_Room_1", "Server_Room", "Office_2A", "Office_2B", 
    "Office_2C", "Conference_Room_2", "Office_3A", "Office_3B", "Conference_Room_3"
}

hvac_service_zones = {
    "bldg:AHU_Floor_1": {
        "Office_1A", "Office_1B", "Conference_Room_1", "Server_Room", "Hallway_1"
    },
    "bldg:AHU_Floor_2_3": {
        "Office_2A", "Office_2B", "Office_2C", "Conference_Room_2", "Hallway_2",
        "Office_3A", "Office_3B", "Conference_Room_3", "Hallway_3"
    },
    "bldg:AHU_Server_Room_Dedicated": {
        "Server_Room" # server room may have a main AHU and a dedicated precision air conditioner
    },
    "bldg:normal":{
        "Office_1A", "Office_1B", "Conference_Room_1", "Server_Room", "Office_2A", "Office_2B", 
    "Office_2C", "Conference_Room_2", "Office_3A", "Office_3B", "Conference_Room_3"
    }
}

HVAC_MEDIATED_CHANNELS = {"temperature", "co2", "humidity", "smoke"}

# 1.4 physical adjacency relation
space_adjacencies = {
    "Hallway_1": {"Office_1A", "Office_1B", "Conference_Room_1", "Lobby_1"},
    "Office_1A": {"Hallway_1"}, "Office_1B": {"Hallway_1"}
}
ADJACENCY_MEDIATED_CHANNELS = {"sound"}

# ==============================================================================
# 2. Reachability Rules Implementation - [keep unchanged]
# ==============================================================================
def is_reachable(channel, device_locs, space_flrs, hvac_zones, adj_spaces):
    source_loc = channel['source']
    target_loc = channel['target']
    channel_type = channel['type']

    if source_loc not in space_flrs:
        return False, "Rule Error: Source device location unknown in ontology."
    
    if target_loc not in space_flrs:
        return False, "Rule Error: Target device location unknown in ontology."

    # --- Rule R1: Intra-Space ---
    # highest priority: if devices are in the same room, they are always reachable.
    if source_loc == target_loc:
        return True, "Rule R1 (Intra-Space): Devices are in the same location."

    # --- Rule R2: HVAC system mediated (System-Mediated) ---
    # second highest priority: check if there is a common HVAC service area. this check is independent of floors.
    if channel_type in HVAC_MEDIATED_CHANNELS:
        for ahu_id, zone_spaces in hvac_zones.items():
            if source_loc in zone_spaces and target_loc in zone_spaces:
                return True, f"Rule R2 (HVAC-Mediated): Locations are connected by the same AHU ({ahu_id})."
    
    # --- Rule R3: Physical adjacency (Adjacent) ---
    # third highest priority: check if they are physically adjacent, usually applicable to the same floor.

    if space_flrs.get(source_loc) == space_flrs.get(target_loc):
        if channel_type in ADJACENCY_MEDIATED_CHANNELS:
            if adj_spaces.get(source_loc) and target_loc in adj_spaces.get(source_loc):
                 return True, "Rule R3 (Adjacency): Locations are physically adjacent on the same floor."

    # --- Rule R4: Spatially separated (Spatially Separated) ---
    # if none of the above reachability rules are satisfied, it is determined to be unreachable.
    return False, "Rule R4 (Spatially Separated): No plausible physical path found."

# ==============================================================================
# 3. Main Execution Script (Main Execution Script) 
# ==============================================================================
def run_topology_filter(json_filepath, log_path='topology_filter_log.txt'):
    """
    read the interaction.json file, perform topology filtering on the physical channels, and save the log.
    """
    log_lines = []
    log_lines.append("="*40)
    log_lines.append("Starting IoTSemVer TopologyFilter")
    log_lines.append(f"Reading interactions from: {json_filepath}")
    log_lines.append("="*40)
    
    try:
        with open(json_filepath, 'r') as f:
            interactions_data = json.load(f)
    except FileNotFoundError:
        log_lines.append(f"Error: The file '{json_filepath}' was not found.")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        return
    except json.JSONDecodeError:
        log_lines.append(f"Error: The file '{json_filepath}' is not a valid JSON file.")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        return

    plausible_interactions = []
    pruned_interactions = []
    skipped_count = 0

    for interaction_id, details in interactions_data.items():
        # step 1: check if it is 'implicit_physical_channel'
        if details.get('actions', {}).get('channel_type') != 'implicit_physical_channel':
            skipped_count += 1
            continue

        log_lines.append(f"\n---> Analyzing Interaction '{interaction_id}':")
        
        # step 2: extract and normalize the device name and channel type
        source_device_location = details['actions']['device_location']
        target_device_location = details['triggers']['device_location']
        channel_type = details['actions']['implicit_channel']

        source_device_bldg = f"{source_device_location}"
        target_device_bldg = f"{target_device_location}"
        
        log_lines.append(f"     {source_device_bldg} --({channel_type})--> {target_device_bldg}")

        channel_to_check = {
            'source': source_device_bldg,
            'target': target_device_bldg,
            'type': channel_type
        }

        # step 3: call the reachability judgment function
        reachable, reason = is_reachable(
            channel_to_check,
            device_locations,
            space_floors,
            hvac_service_zones,
            space_adjacencies
        )
        
        # step 4: record and report the result
        if reachable:
            plausible_interactions.append({'id': interaction_id, 'reason': reason})
            log_lines.append(f"     [+] VERDICT: PLAUSIBLE. Reason: {reason}")
        else:
            pruned_interactions.append({'id': interaction_id, 'reason': reason})
            log_lines.append(f"     [-] VERDICT: PRUNED. Reason: {reason}")

    # step 5: print the final summary report
    log_lines.append("\n" + "="*40)
    log_lines.append("TopologyFilter Analysis Complete")
    log_lines.append("="*40)
    log_lines.append(f"Total Interactions in File: {len(interactions_data)}")
    log_lines.append(f"Skipped (Not Physical Channel): {skipped_count}")
    log_lines.append(f"Physical Channels Analyzed: {len(plausible_interactions) + len(pruned_interactions)}")
    log_lines.append(f"Plausible Interactions Found: {len(plausible_interactions)}")
    log_lines.append(f"Interactions Pruned: {len(pruned_interactions)}")

    # save the log
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))

if __name__ == '__main__':
    
    file_path = './2-ChannelInference_TopoFilter/output/interaction/interactions.json'
    output_path = './2-ChannelInference_TopoFilter/output/topologyFilter/interactions_filter.txt'

    run_topology_filter(file_path,output_path)