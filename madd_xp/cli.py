import argparse
import sys
try:
    from . import get_objects_in_template
    from . import update_template_status
    from . import analyze_files
    from . import find_templates
except ImportError:
    import get_objects_in_template
    import update_template_status
    import analyze_files
    import find_templates

def main():
    parser = argparse.ArgumentParser(prog="mxp", description="MADD XP CLI Tool")
    subparsers = parser.add_subparsers(dest="command_root", required=True)

    # Level 1: template
    template_parser = subparsers.add_parser("template", help="Template operations")
    template_subparsers = template_parser.add_subparsers(dest="command_template", required=True)

    # Level 2: activate
    activate_parser = template_subparsers.add_parser("activate", help="Activate templates")
    update_template_status.add_args(activate_parser)
    activate_parser.set_defaults(func=lambda args: update_template_status.run(args, active=True))

    # Level 2: deactivate
    deactivate_parser = template_subparsers.add_parser("deactivate", help="Deactivate templates")
    update_template_status.add_args(deactivate_parser)
    deactivate_parser.set_defaults(func=lambda args: update_template_status.run(args, active=False))

    # Level 2: get
    get_parser = template_subparsers.add_parser("get", help="Get template information")
    get_subparsers = get_parser.add_subparsers(dest="command_get", required=True)

    # Level 3: template
    get_template_parser = get_subparsers.add_parser("template", help="Get template specific info")
    get_template_subparsers = get_template_parser.add_subparsers(dest="command_get_template", required=True)

    # Level 4: objects
    objects_parser = get_template_subparsers.add_parser("objects", help="Get objects in template")
    get_objects_in_template.add_args(objects_parser)
    objects_parser.set_defaults(func=get_objects_in_template.run)

    # Level 2: find
    find_parser = template_subparsers.add_parser("find", help="Find templates referencing specific objects")
    find_templates.add_args(find_parser)
    find_parser.set_defaults(func=find_templates.run)

    # Level 1: analytics
    analytics_parser = subparsers.add_parser("analytics", help="Analytics operations")
    analytics_subparsers = analytics_parser.add_subparsers(dest="command_analytics", required=True)

    # Level 2: files
    files_parser = analytics_subparsers.add_parser("files", help="Analyze file usage")
    analyze_files.add_args(files_parser)
    files_parser.set_defaults(func=analyze_files.run)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()