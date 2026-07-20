#!/usr/bin/env python3
"""Validate Dogfighter character design and Godot delivery contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
from typing import Any


REQUIRED_STATES = (
    "idle",
    "walk",
    "jump_start",
    "rise",
    "fall",
    "land",
    "attack",
    "hurt",
    "launch",
    "tumble",
    "death",
    "ability",
)


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"top-level JSON must be an object: {path}")
    return value


def png_info(path: Path) -> tuple[int, int, int]:
    with path.open("rb") as image_file:
        header = image_file.read(26)
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError(f"runtime sheet is not a PNG: {path}")
    if header[12:16] != b"IHDR":
        raise ValidationError(f"PNG has no IHDR at expected position: {path}")
    width, height = struct.unpack(">II", header[16:24])
    color_type = header[25]
    return width, height, color_type


def runtime_path_to_file(repo_root: Path, runtime_path: str) -> Path:
    prefix = "res://"
    if not runtime_path.startswith(prefix):
        raise ValidationError(f"godot-ready path must start with {prefix}: {runtime_path}")
    return repo_root / "game" / runtime_path[len(prefix) :]


def validate_event_frames(state_name: str, state: dict[str, Any], errors: list[str]) -> None:
    frame_count = state.get("frameCount")
    if not isinstance(frame_count, int) or frame_count <= 0:
        errors.append(f"{state_name}: frameCount must be a positive integer")
        return
    events = state.get("events", [])
    if not isinstance(events, list):
        errors.append(f"{state_name}: events must be an array")
        return
    for event in events:
        if not isinstance(event, dict):
            errors.append(f"{state_name}: every event must be an object")
            continue
        frame = event.get("frame")
        if not isinstance(frame, int) or not 0 <= frame < frame_count:
            errors.append(
                f"{state_name}: event frame {frame!r} is outside 0..{frame_count - 1}"
            )


def validate_bundle(repo_root: Path, character_id: str, require_ready: bool) -> list[str]:
    bundle_dir = repo_root / "design" / "characters" / character_id
    spec = load_json(bundle_dir / "character-spec.json")
    manifest = load_json(bundle_dir / "asset-manifest.json")
    approval = load_json(bundle_dir / "qa-approval.json")
    errors: list[str] = []

    identity = spec.get("identity", {})
    if identity.get("id") != character_id:
        errors.append("character-spec identity.id must match directory name")
    if manifest.get("characterId") != character_id:
        errors.append("asset-manifest characterId must match directory name")
    if approval.get("characterId") != character_id:
        errors.append("qa-approval characterId must match directory name")

    for section in ("identity", "combat", "animation", "artBrief", "implementationNotes"):
        if not isinstance(spec.get(section), dict):
            errors.append(f"character-spec missing object section: {section}")

    spec_states = spec.get("animation", {}).get("states", {})
    manifest_states = manifest.get("states", {})
    required_states = manifest.get("requiredStates")
    if required_states != list(REQUIRED_STATES):
        errors.append("asset-manifest requiredStates must match the canonical ordered list")

    for state_name in REQUIRED_STATES:
        spec_state = spec_states.get(state_name)
        manifest_state = manifest_states.get(state_name)
        if not isinstance(spec_state, dict):
            errors.append(f"character-spec missing required state: {state_name}")
            continue
        validate_event_frames(state_name, spec_state, errors)
        if not isinstance(manifest_state, dict):
            errors.append(f"asset-manifest missing required state: {state_name}")
            continue
        for key in ("frameCount", "fps", "loop", "events"):
            if manifest_state.get(key) != spec_state.get(key):
                errors.append(f"{state_name}: manifest {key} does not match character-spec")

    status = manifest.get("status")
    if status not in ("draft", "art-proof", "qc-passed", "godot-ready"):
        errors.append(f"unsupported manifest status: {status!r}")
    if require_ready and status != "godot-ready":
        errors.append(f"bundle status is {status!r}, expected 'godot-ready'")

    if status == "godot-ready":
        runtime = manifest.get("runtime", {})
        if runtime.get("weaponBakedIntoBody") is not False:
            errors.append("godot-ready body sheets must not bake a weapon into the character")
        if runtime.get("mirrorLeft") and not runtime.get("mirrorSafe"):
            errors.append("mirrorLeft requires mirrorSafe=true before godot-ready")
        if approval.get("approvedForGodot") is not True:
            errors.append("godot-ready bundle requires approvedForGodot=true")

        checks = approval.get("checks")
        if not isinstance(checks, dict) or not checks or any(
            value is not True for value in checks.values()
        ):
            errors.append("godot-ready bundle requires every QA check to be true")
        blockers = approval.get("blockers")
        if blockers != []:
            errors.append("godot-ready bundle requires an empty blockers array")

        frame_width = runtime.get("frameWidth")
        frame_height = runtime.get("frameHeight")
        if frame_width != 256 or frame_height != 256:
            errors.append("runtime frame size must be 256x256")

        for state_name in REQUIRED_STATES:
            state = manifest_states.get(state_name, {})
            alias = manifest.get("aliases", {}).get(state_name)
            if alias:
                if alias not in manifest_states:
                    errors.append(f"{state_name}: alias target does not exist: {alias}")
                continue
            if state.get("status") != "approved":
                errors.append(f"{state_name}: state status must be 'approved'")
            if state.get("rows", 0) * state.get("cols", 0) != state.get("frameCount"):
                errors.append(f"{state_name}: rows * cols must equal frameCount")
            sheet = state.get("sheet")
            if not isinstance(sheet, str):
                errors.append(f"{state_name}: approved state requires a runtime sheet path")
                continue
            expected_prefix = f"res://assets/characters/{character_id}/body/"
            if not sheet.startswith(expected_prefix):
                errors.append(
                    f"{state_name}: runtime sheet must live under {expected_prefix}"
                )
                continue
            try:
                sheet_file = runtime_path_to_file(repo_root, sheet)
            except ValidationError as exc:
                errors.append(str(exc))
                continue
            if not sheet_file.is_file():
                errors.append(f"{state_name}: runtime sheet does not exist: {sheet_file}")
                continue
            try:
                width, height, color_type = png_info(sheet_file)
            except ValidationError as exc:
                errors.append(str(exc))
                continue
            expected_width = frame_width * state.get("cols", 0)
            expected_height = frame_height * state.get("rows", 0)
            if (width, height) != (expected_width, expected_height):
                errors.append(
                    f"{state_name}: sheet is {width}x{height}, expected "
                    f"{expected_width}x{expected_height}"
                )
            if color_type not in (4, 6):
                errors.append(f"{state_name}: PNG must contain an alpha channel")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", help="Validate one character ID; default validates all")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Fail unless every selected bundle has godot-ready status",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    design_root = repo_root / "design" / "characters"
    if args.character:
        character_ids = [args.character]
    else:
        character_ids = sorted(
            path.name
            for path in design_root.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        )

    failed = False
    for character_id in character_ids:
        try:
            errors = validate_bundle(repo_root, character_id, args.require_ready)
        except ValidationError as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            print(f"FAIL {character_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            manifest = load_json(
                design_root / character_id / "asset-manifest.json"
            )
            print(f"PASS {character_id} ({manifest.get('status')})")

    if not character_ids:
        print("No character bundles found.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
