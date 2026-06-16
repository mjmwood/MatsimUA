#run the following in terminal: python look3.py <path_to_xml_input> <path_to_parquet_output>
import xml.etree.ElementTree as ET
import argparse
import os
from datetime import datetime, timedelta
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


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

def _collect_attribute_keys(xml_input_path) -> list[str]:
    """First pass: collect every distinct attribute name across all persons."""
    keys = set()
    for event, person in ET.iterparse(xml_input_path, events=('end',)):
        if person.tag != 'person':
            continue
        attrs = person.find('attributes')
        if attrs is not None:
            for attr in attrs.findall('attribute'):
                name = attr.get('name')
                if name:
                    keys.add(name)
        person.clear()
    return sorted(keys)


def _flush_buffer(buffer, all_columns, schema, writer, parquet_output_path):
    table = pa.Table.from_pydict(
        {k: [r.get(k) for r in buffer] for k in all_columns},
        schema=schema,
    )
    if writer is None:
        writer = pq.ParquetWriter(parquet_output_path, schema)
    writer.write_table(table)
    return writer


def matsim_xml_to_parquet_streaming(xml_input_path, parquet_output_path, number_unselected, batch_size=1000):
    attr_keys = _collect_attribute_keys(xml_input_path)
    plan_keys = ['number', 'utility', 'activity_type_or_mode', 'distance_travelled',
                 'duration', 'location', 'routes', 'boardingTime']
    all_columns = (
        ['id']
        + attr_keys
        + [f'selected plan {k}' for k in plan_keys]
        + [f'unselected plan ({i+1}) {k}' for i in range(number_unselected) for k in plan_keys]
    )

    plan_key_types = {
        'number':                pa.int64(),
        'utility':               pa.float64(),
        'activity_type_or_mode': pa.list_(pa.string()),
        'distance_travelled':    pa.list_(pa.float64()),
        'duration':              pa.list_(pa.string()),
        'location':              pa.list_(pa.string()),
        'routes':                pa.list_(pa.string()),
        'boardingTime':          pa.list_(pa.string()),
    }

    fields = [pa.field('id', pa.int64())]
    for k in attr_keys:
        fields.append(pa.field(k, pa.string()))
    for plan_prefix in ['selected plan'] + [f'unselected plan ({i+1})' for i in range(number_unselected)]:
        for k in plan_keys:
            fields.append(pa.field(f'{plan_prefix} {k}', plan_key_types[k]))
    schema = pa.schema(fields)


    writer = None
    buffer = []


    for event, person in ET.iterparse(xml_input_path, events=('end',)):
            if person.tag != 'person':
                continue

            row = {'id': int(person.get('id'))}

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
                    'routes': [],
                    'boardingTime': []  # <--- NEW COLUMN INITIALIZED
                }

                for element in plan:
                    if element.tag == 'activity':
                        plan_data['activity_type_or_mode'].append(element.get('type', 'N/A'))
                        plan_data['distance_travelled'].append('N/A')
                        plan_data['duration'].append(element.get('end_time', 'N/A'))
                        plan_data['location'].append(f"{element.get('x','N/A')},{element.get('y','N/A')}")
                        plan_data['routes'].append('N/A')
                        plan_data['boardingTime'].append('N/A') # <--- N/A FOR ACTIVITIES

                    elif element.tag == 'leg':
                        plan_data['activity_type_or_mode'].append(element.get('mode', 'N/A'))
                        route = element.find('route')
                        plan_data['distance_travelled'].append(route.get('distance','N/A') if route is not None else 'N/A')
                        plan_data['duration'].append(element.get('trav_time', 'N/A'))
                        plan_data['location'].append('N/A')

                        # --- Extracting Boarding Time ---
                        b_time = 'N/A'
                        if route is not None and route.text:
                            route_text = route.text.strip()
                            # Try to parse JSON from the route text
                            if route_text.startswith('{'):
                                try:
                                    route_json = json.loads(route_text)
                                    b_time = route_json.get('boardingTime', 'N/A')
                                except json.JSONDecodeError:
                                    b_time = 'N/A'
                            
                            plan_data['routes'].append(route_text if route_text else 'N/A')
                        else:
                            plan_data['routes'].append('N/A')
                        
                        plan_data['boardingTime'].append(b_time) # <--- APPENDING VALUE OR N/A
                        # --------------------------------

                # Join list fields
                # plan_data_joined = {k: "; ".join(v) if isinstance(v, list) else v for k, v in plan_data.items() if k not in ['number','utility']}
                # plan_data_joined['number'] = plan_data['number']
                # plan_data_joined['utility'] = plan_data['utility']

                _LIST_STR  = {'activity_type_or_mode', 'duration', 'routes', 'boardingTime', 'location'}
                _LIST_FLT  = {'distance_travelled', 'utility'}

                plan_data_joined = {}
                for k, v in plan_data.items():
                    if k == 'number':
                        plan_data_joined[k] = v
                    elif k == 'utility':
                        plan_data_joined[k] = float(v) if v is not None else None
                    elif k in _LIST_STR:
                        plan_data_joined[k] = v                                         # keep as list[str]
                    elif k in _LIST_FLT:
                        plan_data_joined[k] = [float(x) if x != 'N/A' else None for x in v]  # list[float]
                    else:
                        plan_data_joined[k] = "; ".join(v) if isinstance(v, list) else v      # location, boardingTime stay as strings


                if plan.get('selected') == 'yes':
                    selected_plan = plan_data_joined
                else:
                    unselected_plans.append(plan_data_joined)

            # Flattening logic...
            if selected_plan:
                for k,v in selected_plan.items():
                    row[f'selected plan {k}'] = v

            for idx in range(number_unselected):
                if idx < len(unselected_plans):
                    for k,v in unselected_plans[idx].items():
                        row[f'unselected plan ({idx+1}) {k}'] = v
                else:
                    # UPDATED to include boardingTime in null fill
                    for k in ['number','utility','activity_type_or_mode','distance_travelled','duration','location','routes','boardingTime']:
                        row[f'unselected plan ({idx+1}) {k}'] = None

            buffer.append(row)

            # if len(buffer) >= batch_size:
            #     table = pa.Table.from_pydict({k: [r.get(k) for r in buffer] for k in buffer[0]})
            #     if writer is None:
            #         writer = pq.ParquetWriter(parquet_output_path, table.schema)
            #     writer.write_table(table)
            #     buffer = []
            if len(buffer) >= batch_size:
                writer = _flush_buffer(buffer, all_columns, schema, writer, parquet_output_path)
                buffer = []

            person.clear()

    # if buffer:
    #     table = pa.Table.from_pydict({k: [r.get(k) for r in buffer] for k in buffer[0]})
    #     if writer is None:
    #         writer = pq.ParquetWriter(parquet_output_path, table.schema)
    #     writer.write_table(table)

    if buffer:
        writer = _flush_buffer(buffer, all_columns, schema, writer, parquet_output_path)


    if writer:
        writer.close()

# --- Main execution block for command-line usage ---
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Convert MATSim population XML output to a Parquet file, "
                    "extracting personal attributes and plan details."
    )
    parser.add_argument(
        "xml_input_file",
        help="Path to the input MATSim population XML file (e.g., output.xml)"
    )
    parser.add_argument(
        "parquet_output_file",
        help="Path for the output Parquet file (e.g., converted_output.parquet)"
    )
    parser.add_argument(
        "number_unselected",
        help="Number of unselected plans being considered - integer"
    )

    # Parse arguments from the command line
    args = parser.parse_args()

    # Call the conversion function with the provided file paths
    matsim_xml_to_parquet_streaming(args.xml_input_file, args.parquet_output_file, int(args.number_unselected))
