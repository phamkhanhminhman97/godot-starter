#!/usr/bin/env python3
"""Create one canonical agent-led Dogfighter character production bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from validate_character_bundle import REQUIRED_STATES


CHARACTER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DESIGN_FILES = (
    "character-brief.json",
    "character-spec.json",
    "asset-manifest.json",
    "production-plan.json",
    "qa-approval.json",
)

ART_DIRECTORIES = (
    "source/editable",
    "references/anchors",
    "actions",
    "fx",
    "previews",
    "qa",
)

ACTION_DIRECTORIES = ("references", "processed", "rejected")


class BundleCreationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BundleCreationError(f"missing template: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BundleCreationError(f"invalid template JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleCreationError(f"template must contain a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def bundle_paths(repo_root: Path, character_id: str) -> tuple[Path, Path]:
    return (
        repo_root / "design" / "characters" / character_id,
        repo_root / "art" / "work" / "characters" / character_id,
    )


def create_bundle(
    repo_root: Path,
    character_id: str,
    display_name: str,
    user_brief: str,
    target_status: str = "qc-passed",
    dry_run: bool = False,
) -> list[Path]:
    if not CHARACTER_ID_PATTERN.fullmatch(character_id):
        raise BundleCreationError(
            "character ID must be kebab-case using lowercase letters, numbers, and hyphens"
        )
    if not display_name.strip():
        raise BundleCreationError("display name must not be empty")
    if not user_brief.strip():
        raise BundleCreationError("brief must not be empty")
    if target_status not in ("art-proof", "qc-passed"):
        raise BundleCreationError("target status must be art-proof or qc-passed")

    design_dir, art_dir = bundle_paths(repo_root, character_id)
    if design_dir.exists() or art_dir.exists():
        existing = [str(path) for path in (design_dir, art_dir) if path.exists()]
        raise BundleCreationError(
            "refusing to overwrite an existing character bundle: " + ", ".join(existing)
        )

    template_dir = repo_root / "design" / "characters" / "_template"
    templates = {name: load_json(template_dir / name) for name in DESIGN_FILES}

    brief = templates["character-brief.json"]
    brief["characterId"] = character_id
    brief["displayName"] = display_name.strip()
    brief["userBrief"] = user_brief.strip()
    brief["targetStatus"] = target_status

    spec = templates["character-spec.json"]
    spec["identity"]["id"] = character_id
    spec["identity"]["displayName"] = display_name.strip()

    manifest = templates["asset-manifest.json"]
    manifest["characterId"] = character_id

    plan = templates["production-plan.json"]
    plan["characterId"] = character_id
    plan["targetStatus"] = target_status

    approval = templates["qa-approval.json"]
    approval["characterId"] = character_id
    approval["blockers"] = [
        "Agent must complete and validate character-spec.json.",
        "Identity master, turnaround, palette, and shared scale profile are not approved.",
        "Required action sheets have not passed numeric and visual QC."
    ]

    planned = [design_dir / name for name in DESIGN_FILES]
    planned.extend(art_dir / relative for relative in ART_DIRECTORIES)
    planned.extend(
        art_dir / "actions" / state_name / relative
        for state_name in REQUIRED_STATES
        for relative in ACTION_DIRECTORIES
    )
    planned.append(art_dir / "qa" / "visual-review.md")
    if dry_run:
        return planned

    created_roots: list[Path] = []
    try:
        design_dir.mkdir(parents=True, exist_ok=False)
        created_roots.append(design_dir)
        art_dir.mkdir(parents=True, exist_ok=False)
        created_roots.append(art_dir)
        for relative in ART_DIRECTORIES:
            (art_dir / relative).mkdir(parents=True, exist_ok=True)
        for state_name in REQUIRED_STATES:
            for relative in ACTION_DIRECTORIES:
                (art_dir / "actions" / state_name / relative).mkdir(
                    parents=True, exist_ok=True
                )
        for name, value in templates.items():
            write_json(design_dir / name, value)
        (art_dir / "qa" / "visual-review.md").write_text(
            "# Visual review\n\nPending identity and per-state review.\n",
            encoding="utf-8",
        )
    except Exception:
        for root in reversed(created_roots):
            shutil.rmtree(root, ignore_errors=True)
        raise
    return planned


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, dest="character_id")
    parser.add_argument("--name", required=True, dest="display_name")
    brief_group = parser.add_mutually_exclusive_group(required=True)
    brief_group.add_argument("--brief", help="Natural-language character idea")
    brief_group.add_argument("--brief-file", type=Path, help="UTF-8 text file containing the idea")
    parser.add_argument(
        "--target-status",
        choices=("art-proof", "qc-passed"),
        default="qc-passed",
        help="How far the agent should autonomously produce this character",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        user_brief = (
            args.brief_file.read_text(encoding="utf-8")
            if args.brief_file is not None
            else args.brief
        )
        paths = create_bundle(
            args.repo_root.resolve(),
            args.character_id,
            args.display_name,
            user_brief,
            args.target_status,
            args.dry_run,
        )
    except (BundleCreationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    verb = "Would create" if args.dry_run else "Created"
    print(f"{verb} agent-led character bundle: {args.character_id}")
    for path in paths:
        print(f"  - {path.relative_to(args.repo_root.resolve())}")
    if not args.dry_run:
        print("Next: the agent must complete character-spec.json before generating visuals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
