import json
import subprocess
import requests
import os
from simple_salesforce import Salesforce

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

def get_sf_cli_credentials(org_alias):
    """Retrieves access token and instance URL from SF CLI."""
    try:
        result = subprocess.run(
            ['sf', 'org', 'display', '--target-org', org_alias, '--json'],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        if data['status'] != 0:
            raise Exception(f"SF CLI Error: {data.get('message')}")
        result_data = data['result']
        return result_data['accessToken'], result_data['instanceUrl']
    except Exception as e:
        print(f"Error retrieving credentials: {str(e)}")
        raise

def get_template_id_by_name(sf, template_name):
    """Queries for a Data Template ID given its name."""
    query = f"SELECT Id, Name FROM copado__Data_Template__c WHERE Name = '{template_name}' LIMIT 1"
    results = sf.query(query)
    if results['totalSize'] == 0:
        return None
    return results['records'][0]['Id']

def get_attachment_by_record_id(sf, instance_url, access_token, record_id, attachment_name, download_dir, file_alias=None):
    """
    Downloads attachment by Record ID. 
    Returns: Parsed JSON content (dict) or None if failed.
    """
    file_query = f"""
        SELECT Id, Body, Name 
        FROM Attachment 
        WHERE ParentId = '{record_id}' 
        AND Name = '{attachment_name}' 
        LIMIT 1
    """
    file_results = sf.query(file_query)

    if file_results['totalSize'] == 0:
        print(f"Warning: No attachment named '{attachment_name}' found for ID {record_id} ({file_alias}).")
        return None

    file_record = file_results['records'][0]
    download_path = file_record['Body']
    full_url = f"{instance_url}{download_path}"
    headers = {"Authorization": "Bearer " + access_token}
    
    # Use alias if provided, otherwise use ID. Sanitize filename.
    raw_name = file_alias if file_alias else record_id
    safe_name = "".join([c for c in raw_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.')]).rstrip()
    filename = f"{safe_name}.json"
    
    print(f"Downloading template: {safe_name}...")
    response = requests.get(full_url, headers=headers)
    
    if response.status_code == 200:
        try:
            json_content = response.json()
            output_path = os.path.join(download_dir, filename)
            with open(output_path, 'w') as f:
                json.dump(json_content, f, indent=4)
            return json_content
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in attachment for {safe_name}.")
            return None
    else:
        print(f"Failed to download {safe_name}. Status: {response.status_code}")
        return None

def get_main_object(json_data):
    """Extracts the 'templateMainObject' from the 'dataTemplate' section."""
    if not json_data: 
        return None
    try:
        return json_data.get("dataTemplate", {}).get("templateMainObject")
    except AttributeError:
        return None

def get_child_relationships(json_data):
    """Extracts list of child template references."""
    if not json_data: return []
    return json_data.get("childrenObjectsReferenceList", [])

def get_parent_relationships(json_data):
    """Recursively finds parent template references."""
    collected_list = []
    def _recursive_search(data):
        if isinstance(data, dict):
            # Check for parent template reference pattern
            if data.get('fieldType') == 'reference' and data.get('deploymentTemplateNameMap'):
                name_map = data.get('deploymentTemplateNameMap')
                for t_id, t_name in name_map.items():
                    collected_list.append({
                        'templateId': t_id,
                        'templateName': t_name
                    })
            for key, value in data.items():
                _recursive_search(value)
        elif isinstance(data, list):
            for item in data:
                _recursive_search(item)
    
    if json_data:
        _recursive_search(json_data)
    return collected_list
    
def get_object_labels(sf, api_names_list):
    """
    Queries EntityDefinition to get the Label for a list of Object API Names.
    Returns: Dictionary { 'API_Name': 'Label' }
    """
    if not api_names_list:
        return {}
    
    # Remove duplicates and None values
    unique_names = list(set([n for n in api_names_list if n]))
    label_map = {}
    
    # Process in chunks of 200 to satisfy SOQL limits on EntityDefinition
    chunk_size = 200
    for i in range(0, len(unique_names), chunk_size):
        chunk = unique_names[i:i + chunk_size]
        formatted_names = "'" + "','".join(chunk) + "'"
        
        query = f"SELECT QualifiedApiName, Label FROM EntityDefinition WHERE QualifiedApiName IN ({formatted_names})"
        try:
            results = sf.query(query)
            for record in results['records']:
                # EntityDefinition returns QualifiedApiName
                label_map[record['QualifiedApiName']] = record['Label']
        except Exception as e:
            print(f"Warning: Could not fetch labels for chunk starting with {chunk[0]}. Error: {e}")
            
    return label_map