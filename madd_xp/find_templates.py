import csv
import json
import os
import argparse
from simple_salesforce import Salesforce
try:
    from . import copado_helper as helper
except ImportError:
    import copado_helper as helper

def add_args(parser):
    parser.add_argument("-u", "--username", required=True, help="Salesforce CLI Org Alias")
    parser.add_argument("-obj", "--objects", required=True, nargs='+', help="List of Object API Names (space-separated, comma-separated string, or JSON array)")
    parser.add_argument("--active", action="store_true", help="Only list active templates")
    parser.add_argument("-o", "--output", default="found_templates.csv", help="Path to output file")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

def run(args):
    org_alias = args.username
    raw_objects = helper.parse_arg_list(args.objects)
    
    # Handle comma-separated string if it wasn't parsed as JSON
    target_objects = []
    for item in raw_objects:
        if "," in item and not item.strip().startswith("["):
            target_objects.extend([x.strip() for x in item.split(",") if x.strip()])
        else:
            target_objects.append(item)
            
    active_only = args.active
    output_path = args.output
    json_output = args.json

    print(f"Searching for templates in {org_alias}...")
    print(f"Target Objects: {target_objects}")
    if active_only:
        print("Filter: Active templates only")

    try:
        access_token, instance_url = helper.get_sf_cli_credentials(org_alias)
        sf = Salesforce(instance_url=instance_url, session_id=access_token)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    if not target_objects:
        print("No target objects provided.")
        return

    # Build Query
    safe_objects = [x.replace("'", "\\'") for x in target_objects]
    objects_in_clause = "'" + "','".join(safe_objects) + "'"
    
    query = f"SELECT Id, Name, copado__Main_Object__c, copado__Active__c FROM copado__Data_Template__c WHERE copado__Main_Object__c IN ({objects_in_clause})"
    
    if active_only:
        query += " AND copado__Active__c = true"

    try:
        result = sf.query_all(query)
        records = result['records']
    except Exception as e:
        print(f"Error querying templates: {e}")
        return

    print(f"Found {len(records)} templates.")

    output_rows = []
    for rec in records:
        output_rows.append({
            "object_api_name": rec.get("copado__Main_Object__c"),
            "template_name": rec.get("Name"),
            "template_id": rec.get("Id"),
            "url": f"{instance_url}/{rec.get('Id')}",
            "active": rec.get("copado__Active__c")
        })

    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if json_output:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_rows, f, indent=4)
        else:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["object_api_name", "template_name", "template_id", "url", "active"])
                writer.writeheader()
                writer.writerows(output_rows)
        print(f"Results saved to {output_path}")
    except IOError as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    pass