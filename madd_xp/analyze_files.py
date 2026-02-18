import csv
import argparse
from collections import defaultdict
from simple_salesforce import Salesforce
try:
    from . import copado_helper as helper
except ImportError:
    import copado_helper as helper

def add_args(parser):
    parser.add_argument("-u", "--username", required=True, help="Salesforce CLI Org Alias")
    parser.add_argument("-o", "--output", default="copado_file_storage_report.csv", help="Path to output CSV file")

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def run(args):
    org_alias = args.username
    output_path = args.output
    
    print(f"Analyzing Copado file storage in org: {org_alias}")

    try:
        access_token, instance_url = helper.get_sf_cli_credentials(org_alias)
        sf = Salesforce(instance_url=instance_url, session_id=access_token)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # 1. Get Data Sets linked to User Stories via Data Commits
    print("Querying User Story Data Commits...")
    commits_query = "SELECT copado__User_Story__c, copado__Data_Set__c FROM copado__User_Story_Data_Commit__c WHERE copado__Data_Set__c != null"
    
    try:
        commits_res = sf.query_all(commits_query)
        commits = commits_res['records']
    except Exception as e:
        print(f"Error querying Data Commits: {e}")
        return

    if not commits:
        print("No User Story Data Commits found.")
        return

    story_datasets = defaultdict(set)
    dataset_ids = set()

    for commit in commits:
        story_id = commit["copado__User_Story__c"]
        dataset_id = commit["copado__Data_Set__c"]
        story_datasets[story_id].add(dataset_id)
        dataset_ids.add(dataset_id)

    print(f"Found {len(dataset_ids)} unique Data Sets across {len(story_datasets)} User Stories.")

    # 2. Get ContentDocumentLinks for these Data Sets
    print("Querying ContentDocumentLinks...")
    dataset_id_list = list(dataset_ids)
    doc_links = []
    
    for chunk in chunk_list(dataset_id_list, 200):
        ids_string = "'" + "','".join(chunk) + "'"
        link_query = f"SELECT ContentDocumentId, LinkedEntityId FROM ContentDocumentLink WHERE LinkedEntityId IN ({ids_string})"
        try:
            res = sf.query_all(link_query)
            doc_links.extend(res['records'])
        except Exception as e:
            print(f"Error querying ContentDocumentLink chunk: {e}")

    dataset_to_docs = defaultdict(list)
    all_doc_ids = set()
    for link in doc_links:
        dataset_to_docs[link["LinkedEntityId"]].append(link["ContentDocumentId"])
        all_doc_ids.add(link["ContentDocumentId"])

    print(f"Found {len(all_doc_ids)} ContentDocuments linked to Data Sets.")

    # 3. Get ContentVersions (Files) details
    print("Querying ContentVersions...")
    doc_id_list = list(all_doc_ids)
    files = []

    for chunk in chunk_list(doc_id_list, 200):
        ids_string = "'" + "','".join(chunk) + "'"
        file_query = f"SELECT Id, ContentDocumentId, Title, FileExtension, ContentSize, PathOnClient FROM ContentVersion WHERE ContentDocumentId IN ({ids_string}) AND IsLatest = true"
        try:
            res = sf.query_all(file_query)
            files.extend(res['records'])
        except Exception as e:
            print(f"Error querying ContentVersion chunk: {e}")

    # 4. Process Files
    doc_file_map = {f["ContentDocumentId"]: f for f in files}

    total_files_records = 0
    total_size_records = 0
    total_files_template = 0
    total_size_template = 0

    for story_id, d_ids in story_datasets.items():
        for d_id in d_ids:
            doc_ids = dataset_to_docs.get(d_id, [])
            for doc_id in doc_ids:
                file_info = doc_file_map.get(doc_id)
                if not file_info:
                    continue
                
                path = (file_info.get("PathOnClient") or "").lower()
                title = (file_info.get("Title") or "").lower()
                ext = (file_info.get("FileExtension") or "").lower()
                size = file_info.get("ContentSize", 0)
                
                is_records = path.endswith(".records.csv") or title.endswith(".records")
                is_template = path.endswith(".template") or ext == "template"

                if is_records:
                    total_files_records += 1
                    total_size_records += size
                elif is_template:
                    total_files_template += 1
                    total_size_template += size

    # 5. Calculate Averages
    num_stories = len(story_datasets)
    if num_stories > 0:
        total_datasets_linked = sum(len(s) for s in story_datasets.values())
        avg_datasets = total_datasets_linked / num_stories
        
        avg_files_records = total_files_records / num_stories
        avg_files_template = total_files_template / num_stories
    else:
        avg_datasets = 0
        avg_files_records = 0
        avg_files_template = 0

    # 6. Generate Report
    print(f"Generating report: {output_path}")
    try:
        with open(output_path, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Metric", "Value", "Unit"])
            writer.writerow(["Total Data Sets (Unique)", len(dataset_ids), "Count"])
            writer.writerow(["Total User Stories with Data Sets", num_stories, "Count"])
            writer.writerow(["Average Data Sets per Story", f"{avg_datasets:.2f}", "Count"])
            
            writer.writerow([])
            writer.writerow(["File Type", "Total Count", "Total Size (MB)", "Avg Count per Story"])
            writer.writerow([".records.csv", total_files_records, f"{total_size_records / (1024 * 1024):.2f}", f"{avg_files_records:.2f}"])
            writer.writerow([".template", total_files_template, f"{total_size_template / (1024 * 1024):.2f}", f"{avg_files_template:.2f}"])
            writer.writerow(["Combined", total_files_records + total_files_template, f"{(total_size_records + total_size_template) / (1024 * 1024):.2f}", f"{(avg_files_records + avg_files_template):.2f}"])
        print("Done.")
    except IOError as e:
        print(f"Error writing to file {output_path}: {e}")

if __name__ == "__main__":
    pass