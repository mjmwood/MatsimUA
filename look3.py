import xml.etree.ElementTree as ET
import csv
import argparse
import os
from datetime import datetime, timedelta


def parse_time_to_seconds(time_str: str) -> int | None:
    """
    Converts an 'HH:MM:SS' string to total seconds from midnight.
    Returns None if the string is invalid or 'N/A'.
    """
    if not time_str or time_str == 'N/A':
        return None
    try:
        # Handle cases where time might be just H:M:S or HH:M:S etc.
        # datetime.strptime is more robust for parsing various time formats
        dt_object = datetime.strptime(time_str, '%H:%M:%S')
        return dt_object.hour * 3600 + dt_object.minute * 60 + dt_object.second
    except ValueError:
        return None

def seconds_to_hhmmss(total_seconds: int) -> str:
    """
    Converts total seconds to an 'HH:MM:SS' string.
    Handles negative seconds by returning 'N/A' as a duration cannot be negative.
    """
    if total_seconds is None or total_seconds < 0:
        return "N/A"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def matsim_xml_to_csv_streaming(xml_input_path, csv_output_path):
    """
    Memory-efficient streaming conversion of MATSim XML to CSV.
    """
    # Open CSV file
    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None  # Will initialize header after seeing first person

        # iterparse on 'end' events only
        for event, person in ET.iterparse(xml_input_path, events=('end',)):
            if person.tag != 'person':
                continue

            row = {}
            row['id'] = person.get('id', '')

            # --- Extract attributes ---
            attributes_element = person.find('attributes')
            if attributes_element is not None:
                for attr in attributes_element.findall('attribute'):
                    name = attr.get('name')
                    if name:
                        row[name] = attr.text

            # --- Extract plans ---
            selected_plan = None
            unselected_plans = []

            for i, plan in enumerate(person.findall('plan')):
                plan_data = {
                    'number': i,
                    'utility': plan.get('score'),
                    'activity_type_or_mode': [],
                    'distance_travelled': [],
                    'duration': [],
                    'location': [],
                    'routes': []
                }

                for element in plan:
                    if element.tag == 'activity':
                        plan_data['activity_type_or_mode'].append(element.get('type', 'N/A'))
                        plan_data['distance_travelled'].append('N/A')
                        plan_data['duration'].append(
                            element.get('end_time', 'N/A')  # simplified for example
                        )
                        plan_data['location'].append(
                            f"{element.get('x','N/A')},{element.get('y','N/A')}"
                        )
                    elif element.tag == 'leg':
                        plan_data['activity_type_or_mode'].append(element.get('mode', 'N/A'))
                        route = element.find('route')
                        plan_data['distance_travelled'].append(
                            route.get('distance','N/A') if route is not None else 'N/A'
                        )
                        plan_data['duration'].append(element.get('trav_time', 'N/A'))
                        plan_data['location'].append('N/A')

                        # --- NEW: capture route text (the list of links) or fallback info ---
                        if route is not None:
                            # Prefer the route text (sequence of links). If it's empty, fallback to start/end links.
                            route_text = route.text.strip() if route.text and route.text.strip() else None
                            if route_text:
                                plan_data['routes'].append(route_text)
                            else:
                                # try building a small descriptor from attributes if route text missing
                                start_link = route.get('start_link', '')
                                end_link = route.get('end_link', '')
                                if start_link or end_link:
                                    plan_data['routes'].append(f"{start_link}->{end_link}")
                                else:
                                    plan_data['routes'].append('N/A')
                        else:
                            plan_data['routes'].append('N/A')

                plan_data_joined = {k: "; ".join(v) if isinstance(v, list) else v for k, v in plan_data.items() if k not in ['number','utility']}
                plan_data_joined['number'] = plan_data['number']
                plan_data_joined['utility'] = plan_data['utility']

                if plan.get('selected') == 'yes':
                    selected_plan = plan_data_joined
                else:
                    unselected_plans.append(plan_data_joined)

            # Flatten selected plan
            if selected_plan:
                for k,v in selected_plan.items():
                    row[f'selected plan {k}'] = v

            # Flatten unselected plans (up to 4)
            for idx in range(4):
                if idx < len(unselected_plans):
                    for k,v in unselected_plans[idx].items():
                        row[f'unselected plan ({idx+1}) {k}'] = v
                else:
                    # Fill missing unselected plans with None
                    for k in ['number','utility','activity_type_or_mode','distance_travelled','duration','location']:
                        row[f'unselected plan ({idx+1}) {k}'] = None

            # Write header on first row
            if writer is None:
                headers = list(row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore') #added extrasaction='ignore'
                writer.writeheader()

            writer.writerow(row)

            # Important: free memory
            person.clear()

# def matsim_xml_to_csv_streaming(xml_input_path, csv_output_path):
#     """
#     Memory-efficient streaming conversion of MATSim XML to CSV.
#     Adds a `routes` column per plan which contains the route text for each leg
#     joined with " | " (one segment per leg).
#     """
#     # Open CSV file
#     with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
#         writer = None  # Will initialize header after seeing first person

#         # iterparse on 'end' events only
#         for event, person in ET.iterparse(xml_input_path, events=('end',)):
#             if person.tag != 'person':
#                 # important to clear elements we don't need to keep memory low
#                 person.clear()
#                 continue

#             row = {}
#             row['id'] = person.get('id', '')

#             # --- Extract attributes ---
#             attributes_element = person.find('attributes')
#             if attributes_element is not None:
#                 for attr in attributes_element.findall('attribute'):
#                     name = attr.get('name')
#                     if name:
#                         row[name] = attr.text

#             # --- Extract plans ---
#             selected_plan = None
#             unselected_plans = []

#             for i, plan in enumerate(person.findall('plan')):
#                 plan_data = {
#                     'number': i,
#                     'utility': plan.get('score'),
#                     'activity_type_or_mode': [],
#                     'distance_travelled': [],
#                     'duration': [],
#                     'location': [],
#                     'routes': []  # <-- new: store route for each leg (text)
#                 }

#                 for element in plan:
#                     if element.tag == 'activity':
#                         plan_data['activity_type_or_mode'].append(element.get('type', 'N/A'))
#                         plan_data['distance_travelled'].append('N/A')
#                         plan_data['duration'].append(
#                             element.get('end_time', 'N/A')  # simplified for example
#                         )
#                         plan_data['location'].append(
#                             f"{element.get('x','N/A')},{element.get('y','N/A')}"
#                         )
#                         # activity doesn't contribute to routes
#                     elif element.tag == 'leg':
#                         plan_data['activity_type_or_mode'].append(element.get('mode', 'N/A'))
#                         route = element.find('route')
#                         # distance and duration handling (as before)
#                         plan_data['distance_travelled'].append(
#                             route.get('distance', 'N/A') if route is not None else 'N/A'
#                         )
#                         plan_data['duration'].append(element.get('trav_time', 'N/A'))
#                         plan_data['location'].append('N/A')

#                         # --- NEW: capture route text (the list of links) or fallback info ---
#                         if route is not None:
#                             # Prefer the route text (sequence of links). If it's empty, fallback to start/end links.
#                             route_text = route.text.strip() if route.text and route.text.strip() else None
#                             if route_text:
#                                 plan_data['routes'].append(route_text)
#                             else:
#                                 # try building a small descriptor from attributes if route text missing
#                                 start_link = route.get('start_link', '')
#                                 end_link = route.get('end_link', '')
#                                 if start_link or end_link:
#                                     plan_data['routes'].append(f"{start_link}->{end_link}")
#                                 else:
#                                     plan_data['routes'].append('N/A')
#                         else:
#                             plan_data['routes'].append('N/A')

#                 # Join list fields into single strings for CSV
#                 plan_data_joined = {}
#                 # join lists with "; " to preserve existing behaviour, but routes use " | " between legs
#                 for k, v in plan_data.items():
#                     if k in ['number', 'utility']:
#                         plan_data_joined[k] = v
#                     else:
#                         if isinstance(v, list):
#                             if k == 'routes':
#                                 plan_data_joined[k] = " | ".join(v)  # routes separated by pipe to mark legs
#                             else:
#                                 plan_data_joined[k] = "; ".join(v)
#                         else:
#                             plan_data_joined[k] = v

#                 if plan.get('selected') == 'yes':
#                     selected_plan = plan_data_joined
#                 else:
#                     unselected_plans.append(plan_data_joined)

#             # Flatten selected plan
#             if selected_plan:
#                 for k, v in selected_plan.items():
#                     row[f'selected plan {k}'] = v

#             # Flatten unselected plans (up to 4)
#             for idx in range(4):
#                 if idx < len(unselected_plans):
#                     for k, v in unselected_plans[idx].items():
#                         row[f'unselected plan ({idx+1}) {k}'] = v
#                 else:
#                     # Fill missing unselected plans with None (keep same keys as existing)
#                     for k in ['number', 'utility', 'activity_type_or_mode', 'distance_travelled', 'duration', 'location', 'routes']:
#                         row[f'unselected plan ({idx+1}) {k}'] = None

#             # Write header on first row
#             if writer is None:
#                 headers = list(row.keys())
#                 writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
#                 writer.writeheader()

#             writer.writerow(row)

#             # Important: free memory
#             person.clear()

# --- Main execution block for command-line usage ---
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Convert MATSim population XML output to a CSV file, "
                    "extracting personal attributes and plan details."
    )
    parser.add_argument(
        "xml_input_file",
        help="Path to the input MATSim population XML file (e.g., output.xml)"
    )
    parser.add_argument(
        "csv_output_file",
        help="Path for the output CSV file (e.g., converted_output.csv)"
    )

    # Parse arguments from the command line
    args = parser.parse_args()

    # Call the conversion function with the provided file paths
    matsim_xml_to_csv_streaming(args.xml_input_file, args.csv_output_file)
