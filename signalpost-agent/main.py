"""Command-line entry point for Signalpost Agent."""
import argparse
import json
from signalpost.agent import CompanyAgent
from signalpost.collector import collect_profiles, export_profiles_json
from signalpost.database import save_profile


def main():
    parser = argparse.ArgumentParser(description="Signalpost: verified Norwegian company information agent")
    sub = parser.add_subparsers(dest="command", required=True)
    lookup = sub.add_parser("lookup", help="Look up one company by organization number")
    lookup.add_argument("org_number")
    collect = sub.add_parser("collect", help="Collect up to N real company profiles")
    collect.add_argument("--target", type=int, default=1000)
    collect.add_argument("--db", default="signalpost.db")
    export = sub.add_parser("export", help="Export stored profiles to JSON")
    export.add_argument("--output", default="profiles.json")
    export.add_argument("--db", default="signalpost.db")
    args = parser.parse_args()
    if args.command == "lookup":
        profile = CompanyAgent().fetch(args.org_number)
        result = save_profile(profile)
        print(json.dumps({"profile": profile, "tracking": result}, ensure_ascii=False, indent=2))
    elif args.command == "collect":
        result = collect_profiles(args.target, args.db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["saved_this_run"]:
            print(f"Total collected in this run: {result['saved_this_run']}. Export with: python main.py export --db {args.db}")
    elif args.command == "export":
        count = export_profiles_json(args.output, args.db)
        print(f"Exported {count} profiles to {args.output}")

if __name__ == "__main__":
    main()
