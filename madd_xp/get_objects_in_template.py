import os
import csv
import argparse
import json
from collections import deque
from simple_salesforce import Salesforce
try:
    from . import copado_helper as helper
except ImportError:
    import copado_helper as helper

def parse_arg_list(arg_list):
    """Helper to parse JSON or list inputs."""
    if not arg_list:
        return []
    if len(arg_list) == 1:
        try:
            parsed = json.loads(arg_list[0])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return arg_list

def get_arg_parser():
    parser = argparse.ArgumentParser(
        description="Extract objects from Copado Data Templates",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""EXAMPLES:
  # Run with a single template name
  mxp -u cpdXpress -t "MADD Stress Main"

  # Run with multiple template names
  mxp -u cpdXpress -t "Template A" "Template B"

  # Run with Record IDs
  mxp -u cpdXpress -i a0UQH000005LJXs2AO a0UQH000005MrUD2A0

  # Run with JSON input and custom output path
  mxp -u cpdXpress -t '["Template A", "Template B"]' -o ./export/results.csv
"""
    )

    auth_group = parser.add_argument_group('Authentication')
    auth_group.add_argument("-u", "--username", required=True, help="Salesforce CLI Org Alias (e.g., cpdXpress)")

    input_group = parser.add_argument_group('Input (At least one required)')
    input_group.add_argument("-t", "--templates", required=False, nargs='+', metavar="NAME", help="List of Root Template Names.\nAccepts space-separated strings or a JSON array.")
    input_group.add_argument("-i", "--recordId", required=False, nargs='+', metavar="ID", help="List of Root Template Record IDs.\nAccepts space-separated IDs or a JSON array.")

    output_group = parser.add_argument_group('Output')
    output_group.add_argument("-o", "--output", default=None, metavar="PATH", help="Path to output file.\nDefault: objects_list.csv (or .json)")
    output_group.add_argument("--json", action="store_true", help="Output results in JSON format instead of CSV.")

    return parser

def main():
    # --- 1. Parameters ---
    parser = get_arg_parser()
    args = parser.parse_args()

    if not args.templates and not args.recordId:
        parser.error("At least one of --templates or --recordId is required.")

    ORG_ALIAS = args.username

    ROOT_TEMPLATE_NAMES = parse_arg_list(args.templates)
    ROOT_TEMPLATE_IDS = parse_arg_list(args.recordId)
    
    ATTACHMENT_NAME = "Template Detail"
    TEMP_FOLDER_NAME = "Temp_Template_Files"
    if args.output:
        CSV_OUTPUT_FILE = args.output
    else:
        CSV_OUTPUT_FILE = "objects_list.json" if args.json else "objects_list.csv"
    
    # Define Paths
    # Use current working directory for output files
    base_dir = os.getcwd()
    templates_dir = os.path.join(base_dir, TEMP_FOLDER_NAME)
    csv_path = os.path.join(base_dir, CSV_OUTPUT_FILE)

    # Ensure output directory exists
    output_dir = os.path.dirname(csv_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    os.makedirs(templates_dir, exist_ok=True)
    print(f"File storage set to: {templates_dir}")

    # --- 2. Authentication ---
    print(f"Logging into {ORG_ALIAS}...")
    try:
        access_token, instance_url = helper.get_sf_cli_credentials(ORG_ALIAS)
        sf = Salesforce(instance_url=instance_url, session_id=access_token)
        print("Successfully connected to Salesforce.\n")
    except Exception as e:
        print("Authentication failed. Exiting.")
        return

    # --- 3. Queue Initialization ---
    # CHANGED: Visited set now tracks (template_id, input_root_name)
    # This ensures a sub-template is processed for EACH root it belongs to, but avoids infinite loops within that root's tree.
    visited_entries = set() 
    csv_rows = []
    
    # Queue stores tuples: (template_id, template_name, input_root_name)
    processing_queue = deque()

    print(f"Resolving Root Templates...")

    # 1. Process Names
    if ROOT_TEMPLATE_NAMES:
        print(f"Processing Names: {ROOT_TEMPLATE_NAMES}")
        for root_name in ROOT_TEMPLATE_NAMES:
            root_id = helper.get_template_id_by_name(sf, root_name)
            
            if root_id:
                # Enqueue with the root name as the context source
                processing_queue.append((root_id, root_name, root_name))
                print(f" -> Enqueued Root: {root_name}")
            else:
                print(f"Error: Root template '{root_name}' not found. Check spelling and quotes.")

    # 2. Process IDs
    if ROOT_TEMPLATE_IDS:
        print(f"Processing IDs: {ROOT_TEMPLATE_IDS}")
        for root_id in ROOT_TEMPLATE_IDS:
            try:
                # Query Name to ensure consistent data structure
                rec = sf.query(f"SELECT Name FROM copado__Data_Template__c WHERE Id='{root_id}' LIMIT 1")
                if rec['totalSize'] > 0:
                    root_name = rec['records'][0]['Name']
                    processing_queue.append((root_id, root_name, root_name))
                    print(f" -> Enqueued Root ID: {root_id} ({root_name})")
                else:
                    print(f"Error: Root template ID '{root_id}' not found.")
            except Exception as e:
                print(f"Error resolving Root template ID '{root_id}': {e}")

    # --- 4. Processing Loop ---
    print("\nStarting recursive template processing...")

    while processing_queue:
        # CHANGED: Unpack 3 values including the input root context
        current_id, current_name, input_root_name = processing_queue.popleft()

        # Check visitation context specific to this root
        if (current_id, input_root_name) in visited_entries:
            continue

        visited_entries.add((current_id, input_root_name))

        # Download (Helper function remains the same)
        template_json = helper.get_attachment_by_record_id(
            sf, 
            instance_url, 
            access_token, 
            current_id, 
            ATTACHMENT_NAME, 
            templates_dir,
            file_alias=current_name
        )

        if not template_json:
            print(f"   -> [WARNING] Could not download/parse JSON for: {current_name}")
            continue

        # A. Extract Info
        main_object = helper.get_main_object(template_json)
        
        # CHANGED: Root check compares current name to the context name
        is_root = (current_name == input_root_name)

        row_data = {
            "input_template": input_root_name,    # New Data Point
            "object_api": main_object if main_object else "",
            "template_name": current_name,
            "template_id": current_id,
            "is_root": is_root
        }
        csv_rows.append(row_data)

        # Log output
        obj_str = f"(Obj: {main_object})" if main_object else "(Obj: None)"
        print(f"   -> [{input_root_name}] Processed: {current_name} {obj_str}")

        # B. Enqueue Children
        children = helper.get_child_relationships(template_json)
        for child in children:
            c_id = child.get('templateId')
            # Check if this specific child has been visited *for this specific root*
            if c_id and (c_id, input_root_name) not in visited_entries:
                try:
                    c_rec = sf.query(f"SELECT Name FROM copado__Data_Template__c WHERE Id='{c_id}' LIMIT 1")
                    if c_rec['totalSize'] > 0:
                        c_name = c_rec['records'][0]['Name']
                        # Pass input_root_name forward
                        processing_queue.append((c_id, c_name, input_root_name))
                except Exception as e:
                    print(f"      -> Error resolving child {c_id}: {e}")

        # C. Enqueue Parents
        parents = helper.get_parent_relationships(template_json)
        for parent in parents:
            p_id = parent.get('templateId')
            p_name = parent.get('templateName')
            if p_id and (p_id, input_root_name) not in visited_entries:
                # Pass input_root_name forward
                processing_queue.append((p_id, p_name, input_root_name))

    # --- 5. Export to CSV ---
    print("\n" + "="*30)
    print("SAVING RESULTS")
    print("="*30)
    
    try:
        all_api_names = [row['object_api'] for row in csv_rows if row['object_api']]
        
        print("Fetching Object Labels from Salesforce...")
        labels_map = helper.get_object_labels(sf, all_api_names)
        
        for row in csv_rows:
            api_name = row['object_api']
            row['object_label'] = labels_map.get(api_name, api_name) if api_name else ""

        # CHANGED: Added 'Input Template Name' to headers
        headers = ['Input Template Name', 'Object Label', 'Object API Name', 'Template Name', 'Template Id', 'Root Template']
        
        # Sort by Input Template, then Object Label
        csv_rows.sort(key=lambda x: (x['input_template'], x['object_label'] is None, x['object_label']))

        if args.json:
            with open(csv_path, mode='w', encoding='utf-8') as f:
                json.dump(csv_rows, f, indent=4)
            print(f"Successfully wrote {len(csv_rows)} records to JSON: {csv_path}")
        else:
            with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=headers)
                writer.writeheader()
                
                for row in csv_rows:
                    writer.writerow({
                        'Input Template Name': row['input_template'], # New Column
                        'Object Label': row['object_label'],
                        'Object API Name': row['object_api'],
                        'Template Name': row['template_name'],
                        'Template Id': row['template_id'],
                        'Root Template': row['is_root']
                    })
                    
            print(f"Successfully wrote {len(csv_rows)} rows to: {csv_path}")
        
    except IOError as e:
        print(f"Error writing CSV file: {e}")

if __name__ == "__main__":
    main()