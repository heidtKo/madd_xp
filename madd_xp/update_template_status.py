import argparse
from simple_salesforce import Salesforce
try:
    from . import copado_helper as helper
except ImportError:
    import copado_helper as helper

def add_args(parser):
    parser.add_argument("-u", "--username", required=True, help="Salesforce CLI Org Alias")
    parser.add_argument("-i", "--ids", required=True, nargs='+', metavar="ID", help="List of Template Record IDs (Space separated or JSON array)")

def run(args, active):
    mode = "activate" if active else "deactivate"
    
    org_alias = args.username
    template_ids = helper.parse_arg_list(args.ids)
    
    if not template_ids:
        print("No IDs provided.")
        return

    print(f"Logging into {org_alias}...")
    try:
        access_token, instance_url = helper.get_sf_cli_credentials(org_alias)
        sf = Salesforce(instance_url=instance_url, session_id=access_token)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    print(f"Starting {mode} for {len(template_ids)} templates...")
    
    success_count = 0
    for t_id in template_ids:
        try:
            # Update the copado__Active__c field
            sf.Copado__Data_Template__c.update(t_id, {'copado__Active__c': active})
            print(f"[{'OK' if active else 'OK'}] {t_id} -> {'Active' if active else 'Inactive'}")
            success_count += 1
        except Exception as e:
            print(f"[ERR] {t_id}: {e}")
    
    print(f"\nCompleted. Successfully {mode}d {success_count}/{len(template_ids)} templates.")

if __name__ == "__main__":
    pass