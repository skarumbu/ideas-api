#!/usr/bin/env python3
"""
One-time backfill: assigns project_id to any idea missing one, resolving by
its `project` name string. Creates the project if no project with that name
exists yet — this is the deliberate registration step create_idea's
reject-on-miss now expects to have already happened for any *new* idea; for
this one-time cleanup of pre-existing data, doing it automatically is fine.

Not wired into the deploy pipeline or exposed as a route — run once by hand:

    IDEAS_TABLE_CONNECTION_STRING=... python scripts/backfill_project_ids.py [--dry-run]
"""
import argparse

from ideas import list_ideas, update_idea
from projects import create_project, get_project_by_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    orphaned = [idea for idea in list_ideas() if not idea.get("project_id")]

    if not orphaned:
        print("No orphaned ideas found.")
        return

    print(f"Found {len(orphaned)} idea(s) missing project_id:")
    for idea in orphaned:
        name = (idea.get("project") or "").strip()
        if not name:
            print(f"  SKIP {idea['id']} ({idea['title']!r}) — no project name set, needs manual triage")
            continue

        project = get_project_by_name(name)
        if project:
            print(f"  {idea['id']} ({idea['title']!r}) -> existing project '{name}' ({project['id']})")
        else:
            print(f"  {idea['id']} ({idea['title']!r}) -> no project named '{name}' yet, creating one")
            if not args.dry_run:
                project = create_project(name)

        if not args.dry_run and project:
            update_idea(idea["id"], {"project_id": project["id"]})

    if args.dry_run:
        print("\nDry run — no changes written. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    main()
