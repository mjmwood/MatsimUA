import xml.etree.ElementTree as ET
import csv
import argparse

def parse_score_explanation(explanation_str):
    """
    Parses the scoreExplanation string into a dictionary.
    Example: "actPerforming_util=32.7; leg_0_details=mode:car..."
    """
    data = {}
    if not explanation_str or explanation_str == 'N/A':
        return data
    
    # Split by semicolon to get individual metric pairs
    parts = explanation_str.split(';')
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            data[key.strip()] = value.strip()
    return data

def matsim_xml_to_csv_scores_streaming(xml_input_path, csv_output_path):
    """
    Extracts person attributes and flattens scoreExplanation for the 
    selected plan and up to 4 unselected plans.
    """
    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = None

        for event, person in ET.iterparse(xml_input_path, events=('end',)):
            if person.tag != 'person':
                continue

            row = {'id': person.get('id', '')}

            # 1. Extract Global Person Attributes
            attributes_element = person.find('attributes')
            if attributes_element is not None:
                for attr in attributes_element.findall('attribute'):
                    name = attr.get('name')
                    if name:
                        row[name] = attr.text

            # 2. Extract and Sort Plans
            selected_plan_data = {}
            unselected_plans_data = []

            for plan in person.findall('plan'):
                # Extract scoreExplanation if it exists
                explanation_map = {}
                plan_score = plan.get('score', 'N/A')
                
                plan_attr_elem = plan.find('attributes')
                if plan_attr_elem is not None:
                    for attr in plan_attr_elem.findall('attribute'):
                        if attr.get('name') == 'scoreExplanation':
                            explanation_map = parse_score_explanation(attr.text)
                
                # Prepare the flat dictionary for this plan
                plan_info = {'score': plan_score}
                for k, v in explanation_map.items():
                    plan_info[k] = v

                if plan.get('selected') == 'yes':
                    selected_plan_data = plan_info
                else:
                    unselected_plans_data.append(plan_info)

            # 3. Flatten Selected Plan into Row
            for k, v in selected_plan_data.items():
                row[f'selected plan {k}'] = v

            # 4. Flatten Unselected Plans (Up to 4) into Row
            for idx in range(4):
                if idx < len(unselected_plans_data):
                    for k, v in unselected_plans_data[idx].items():
                        row[f'unselected plan ({idx+1}) {k}'] = v

            # Write header on first row (gathering all keys present in the first person)
            if writer is None:
                headers = list(row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()

            writer.writerow(row)

            # Free memory
            person.clear()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract person attributes and score explanations for top 5 plans.")
    parser.add_argument("xml_input", help="Input MATSim XML file")
    parser.add_argument("csv_output", help="Output CSV file")
    
    args = parser.parse_args()
    matsim_xml_to_csv_scores_streaming(args.xml_input, args.csv_output)