#!/usr/bin/env python3
"""Promote one QC-approved character workspace bundle into runtime assets."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from validate_character_bundle import (
    REQUIRED_STATES,
    ValidationError,
    build_runtime_manifest,
    load_json,
    validate_bundle,
    validate_promotable_bundle,
    workspace_path_to_file,
)


class PromotionError(Exception):
    pass


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def write_text_atomic(path: Path, value: str) -> None:
    temp_path = path.with_name(f".{path.name}.rollback")
    temp_path.write_text(value, encoding="utf-8")
    os.replace(temp_path, path)


def promotion_sources(
    repo_root: Path, character_id: str, manifest: dict[str, Any]
) -> dict[str, Path]:
    allowed_root = repo_root / "art" / "work" / "characters" / character_id
    aliases = manifest.get("aliases", {})
    result: dict[str, Path] = {}
    for state_name in REQUIRED_STATES:
        if state_name in aliases:
            continue
        workspace_sheet = manifest["states"][state_name]["workspaceSheet"]
        result[state_name] = workspace_path_to_file(
            repo_root, workspace_sheet, allowed_root
        )
    return result


def prepare_promotion(
    repo_root: Path, character_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Path]]:
    try:
        errors = validate_promotable_bundle(repo_root, character_id)
    except ValidationError as exc:
        errors = [str(exc)]
    if errors:
        formatted = "\n".join(f"  - {error}" for error in errors)
        raise PromotionError(f"bundle is not promotable:\n{formatted}")

    design_dir = repo_root / "design" / "characters" / character_id
    manifest = load_json(design_dir / "asset-manifest.json")
    approval = load_json(design_dir / "qa-approval.json")
    plan = load_json(design_dir / "production-plan.json")
    sources = promotion_sources(repo_root, character_id, manifest)

    updated_manifest = copy.deepcopy(manifest)
    updated_manifest["status"] = "godot-ready"
    aliases = updated_manifest.get("aliases", {})
    for state_name in REQUIRED_STATES:
        if state_name in aliases:
            updated_manifest["states"][state_name]["sheet"] = None
            continue
        updated_manifest["states"][state_name]["sheet"] = (
            f"res://assets/characters/{character_id}/body/{state_name}.png"
        )

    updated_approval = copy.deepcopy(approval)
    updated_approval["approvedForGodot"] = True
    updated_approval["checks"]["runtimePathsExist"] = True

    updated_plan = copy.deepcopy(plan)
    updated_plan["currentPhase"] = "godot-ready"
    updated_plan["promotion"]["preflight"] = "passed"
    updated_plan["promotion"]["approvedForPromotion"] = True
    updated_plan["promotion"]["promotedAt"] = datetime.now(timezone.utc).isoformat()
    return updated_manifest, updated_approval, updated_plan, sources


def promote_bundle(
    repo_root: Path, character_id: str, dry_run: bool = False
) -> list[tuple[Path, Path]]:
    manifest, approval, plan, sources = prepare_promotion(repo_root, character_id)
    runtime_root = repo_root / "game" / "assets" / "characters"
    destination = runtime_root / character_id
    if destination.exists():
        raise PromotionError(
            f"runtime destination already exists; promotion never overwrites: {destination}"
        )

    copies = [
        (source, destination / "body" / f"{state_name}.png")
        for state_name, source in sources.items()
    ]
    if dry_run:
        return copies

    design_dir = repo_root / "design" / "characters" / character_id
    manifest_path = design_dir / "asset-manifest.json"
    approval_path = design_dir / "qa-approval.json"
    plan_path = design_dir / "production-plan.json"
    originals = {
        manifest_path: manifest_path.read_text(encoding="utf-8"),
        approval_path: approval_path.read_text(encoding="utf-8"),
        plan_path: plan_path.read_text(encoding="utf-8"),
    }

    runtime_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{character_id}-promotion-", dir=runtime_root))
    destination_created = False
    try:
        body_dir = staging / "body"
        body_dir.mkdir()
        for state_name, source in sources.items():
            shutil.copy2(source, body_dir / f"{state_name}.png")
        write_json_atomic(staging / "asset-manifest.json", build_runtime_manifest(manifest))

        os.replace(staging, destination)
        destination_created = True
        write_json_atomic(manifest_path, manifest)
        write_json_atomic(approval_path, approval)
        write_json_atomic(plan_path, plan)

        final_errors = validate_bundle(repo_root, character_id, require_ready=True)
        if final_errors:
            formatted = "\n".join(f"  - {error}" for error in final_errors)
            raise PromotionError(f"post-promotion validation failed:\n{formatted}")
    except Exception:
        for path, original in originals.items():
            write_text_atomic(path, original)
        if destination_created:
            shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return copies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True, dest="character_id")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run every preflight check and print the copy plan without writing",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    try:
        copies = promote_bundle(repo_root, args.character_id, args.dry_run)
    except (PromotionError, ValidationError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    verb = "Would promote" if args.dry_run else "Promoted"
    print(f"{verb} character bundle: {args.character_id}")
    for source, destination in copies:
        print(
            f"  - {source.relative_to(repo_root)} -> "
            f"{destination.relative_to(repo_root)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
