#!/usr/bin/env python3
"""Validate Dogfighter character design, QC, and runtime delivery contracts."""

from __future__ import annotations

import argparse
import copy
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

STATE_CONTRACT_KEYS = (
    "frameCount",
    "fps",
    "loop",
    "events",
    "cancelAfterFrame",
    "onComplete",
)

QC_POLICIES = ("grounded-body", "airborne-body", "silhouette-changing-body")

PROMOTION_CHECKS = (
    "identityLocked",
    "allRequiredStatesPresent",
    "manifestMatchesSpec",
    "numericQcPassed",
    "visualQcPassed",
    "mirrorPassed",
    "gameplayScalePassed",
    "alphaEdgesPassed",
    "weaponSeparated",
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


def workspace_path_to_file(
    repo_root: Path, workspace_path: str, allowed_root: Path
) -> Path:
    candidate = (repo_root / workspace_path).resolve()
    resolved_root = allowed_root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValidationError(
            f"workspace path must stay under {resolved_root}: {workspace_path}"
        ) from exc
    return candidate


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _designed_text(value: Any) -> bool:
    return _non_empty(value) and not value.strip().lower().startswith(
        ("agent must", "replace with")
    )


def _approved_exception(
    approval: dict[str, Any], state_name: str, rule: str
) -> bool:
    exceptions = approval.get("exceptions", [])
    if not isinstance(exceptions, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("state") == state_name
        and item.get("rule") == rule
        and item.get("approved") is True
        and _non_empty(item.get("reason"))
        for item in exceptions
    )


def validate_event_frames(
    state_name: str, state: dict[str, Any], errors: list[str]
) -> None:
    frame_count = state.get("frameCount")
    if not isinstance(frame_count, int) or frame_count <= 0:
        errors.append(f"{state_name}: frameCount must be a positive integer")
        return
    fps = state.get("fps")
    if not isinstance(fps, (int, float)) or fps <= 0:
        errors.append(f"{state_name}: fps must be positive")
    if not isinstance(state.get("loop"), bool):
        errors.append(f"{state_name}: loop must be boolean")
    if not _non_empty(state.get("onComplete")):
        errors.append(f"{state_name}: onComplete must be explicit")
    cancel_after = state.get("cancelAfterFrame")
    if cancel_after is not None and (
        not isinstance(cancel_after, int) or not 0 <= cancel_after < frame_count
    ):
        errors.append(
            f"{state_name}: cancelAfterFrame {cancel_after!r} is outside "
            f"0..{frame_count - 1}"
        )

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
        if not _non_empty(event.get("type")) or not _non_empty(event.get("id")):
            errors.append(f"{state_name}: every event requires non-empty type and id")


def validate_action_contract(
    action_name: str,
    action: Any,
    animation_state: Any,
    errors: list[str],
) -> None:
    if not isinstance(action, dict):
        errors.append(f"combat.{action_name} must be an object")
        return
    for field in ("name", "counterplay", "interruption"):
        if not _designed_text(action.get(field)):
            errors.append(f"combat.{action_name}.{field} must be explicit")
    startup = action.get("startupFrames")
    recovery = action.get("recoveryFrames")
    active = action.get("activeFrames")
    if not isinstance(startup, int) or startup < 1:
        errors.append(f"combat.{action_name}.startupFrames must be a positive integer")
    if not isinstance(recovery, int) or recovery < 1:
        errors.append(f"combat.{action_name}.recoveryFrames must be a positive integer")
    if not isinstance(active, list) or not active or any(
        not isinstance(frame, int) for frame in active
    ):
        errors.append(f"combat.{action_name}.activeFrames must contain frame numbers")
        return
    if not isinstance(animation_state, dict):
        return
    frame_count = animation_state.get("frameCount")
    if isinstance(frame_count, int) and any(
        frame < 0 or frame >= frame_count for frame in active
    ):
        errors.append(f"combat.{action_name}.activeFrames exceed animation bounds")
    event_frames = {
        event.get("frame")
        for event in animation_state.get("events", [])
        if isinstance(event, dict) and event.get("type") in ("hit", "spawn")
    }
    if not set(active).issubset(event_frames):
        errors.append(
            f"combat.{action_name}.activeFrames must match deterministic hit/spawn events"
        )


def build_runtime_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the sanitized manifest copied beside approved runtime PNGs."""
    runtime_manifest = copy.deepcopy(manifest)
    for state in runtime_manifest.get("states", {}).values():
        if not isinstance(state, dict):
            continue
        state.pop("workspaceSheet", None)
        state.pop("qcReport", None)
        state.pop("qcPolicy", None)
    return runtime_manifest


def validate_bundle(repo_root: Path, character_id: str, require_ready: bool) -> list[str]:
    bundle_dir = repo_root / "design" / "characters" / character_id
    spec = load_json(bundle_dir / "character-spec.json")
    manifest = load_json(bundle_dir / "asset-manifest.json")
    approval = load_json(bundle_dir / "qa-approval.json")
    errors: list[str] = []

    identity = spec.get("identity", {})
    if identity.get("id") != character_id:
        errors.append("character-spec identity.id must match directory name")
    if not _non_empty(identity.get("displayName")):
        errors.append("character-spec identity.displayName must be explicit")
    if not _designed_text(identity.get("role")):
        errors.append("character-spec must define exactly one scalar primary role")
    if not _designed_text(identity.get("fantasy")):
        errors.append("character-spec identity.fantasy must be fully designed")
    silhouette = identity.get("silhouette")
    if not isinstance(silhouette, list) or len(silhouette) < 2 or any(
        not _designed_text(item) for item in silhouette
    ):
        errors.append("character-spec requires at least two readable silhouette traits")
    if manifest.get("characterId") != character_id:
        errors.append("asset-manifest characterId must match directory name")
    if approval.get("characterId") != character_id:
        errors.append("qa-approval characterId must match directory name")

    for section in ("identity", "combat", "animation", "artBrief", "implementationNotes"):
        if not isinstance(spec.get(section), dict):
            errors.append(f"character-spec missing object section: {section}")

    combat = spec.get("combat", {})
    weaknesses = combat.get("weaknesses") if isinstance(combat, dict) else None
    if not isinstance(weaknesses, list) or not weaknesses or any(
        not _designed_text(item) for item in weaknesses
    ):
        errors.append("character-spec requires at least one explicit weakness")

    spec_states = spec.get("animation", {}).get("states", {})
    manifest_states = manifest.get("states", {})
    validate_action_contract(
        "primary", combat.get("primary"), spec_states.get("attack"), errors
    )
    validate_action_contract(
        "ability", combat.get("ability"), spec_states.get("ability"), errors
    )
    ability = combat.get("ability") if isinstance(combat, dict) else None
    if isinstance(ability, dict) and not _designed_text(ability.get("description")):
        errors.append("combat.ability.description must be fully designed")

    art_brief = spec.get("artBrief", {})
    for field in ("spriteSheet", "windUpCue", "impactCue", "recoveryCue"):
        if not _designed_text(art_brief.get(field)):
            errors.append(f"artBrief.{field} must be fully designed")
    implementation = spec.get("implementationNotes", {})
    if implementation.get("eventsAreAuthoritative") is not True:
        errors.append("implementationNotes.eventsAreAuthoritative must be true")

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
        for key in STATE_CONTRACT_KEYS:
            if manifest_state.get(key) != spec_state.get(key):
                errors.append(f"{state_name}: manifest {key} does not match character-spec")
        if manifest_state.get("qcPolicy") not in QC_POLICIES:
            errors.append(f"{state_name}: unsupported qcPolicy")

    aliases = manifest.get("aliases", {})
    if not isinstance(aliases, dict):
        errors.append("asset-manifest aliases must be an object")
        aliases = {}
    for state_name, target in aliases.items():
        if state_name not in REQUIRED_STATES or target not in REQUIRED_STATES:
            errors.append(f"invalid state alias: {state_name} -> {target}")
        elif state_name == target or target in aliases:
            errors.append(f"state aliases must be direct and non-cyclic: {state_name} -> {target}")

    status = manifest.get("status")
    if status not in ("draft", "art-proof", "qc-passed", "godot-ready"):
        errors.append(f"unsupported manifest status: {status!r}")
    if require_ready and status != "godot-ready":
        errors.append(f"bundle status is {status!r}, expected 'godot-ready'")

    brief_path = bundle_dir / "character-brief.json"
    plan_path = bundle_dir / "production-plan.json"
    if not brief_path.is_file():
        errors.append("bundle requires character-brief.json")
    if not plan_path.is_file():
        errors.append("bundle requires production-plan.json")
    if brief_path.is_file() and plan_path.is_file():
        brief = load_json(brief_path)
        plan = load_json(plan_path)
        if brief.get("characterId") != character_id:
            errors.append("character-brief characterId must match directory name")
        if brief.get("displayName") != identity.get("displayName"):
            errors.append("character-brief displayName must match character-spec")
        if not _designed_text(brief.get("userBrief")):
            errors.append("character-brief userBrief must be explicit")
        if brief.get("autonomyMode") != "agent-led":
            errors.append("character-brief autonomyMode must be 'agent-led'")
        if brief.get("targetStatus") not in ("art-proof", "qc-passed"):
            errors.append("character-brief targetStatus must be art-proof or qc-passed")
        if plan.get("characterId") != character_id:
            errors.append("production-plan characterId must match directory name")
        if plan.get("targetStatus") != brief.get("targetStatus"):
            errors.append("production-plan targetStatus must match character-brief")
        plan_states = plan.get("states", {})
        if not isinstance(plan_states, dict) or set(plan_states) != set(REQUIRED_STATES):
            errors.append("production-plan states must match the canonical state set")

    if status == "godot-ready":
        runtime = manifest.get("runtime", {})
        if runtime.get("weaponBakedIntoBody") is not False:
            errors.append("godot-ready body sheets must not bake a weapon into the character")
        if runtime.get("mirrorLeft") and not runtime.get("mirrorSafe"):
            errors.append("mirrorLeft requires mirrorSafe=true before godot-ready")
        if approval.get("approvedForPromotion") is not True:
            errors.append("godot-ready bundle requires approvedForPromotion=true")
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
            alias = aliases.get(state_name)
            if alias:
                continue
            if state.get("status") != "approved":
                errors.append(f"{state_name}: state status must be 'approved'")
            if state.get("rows", 0) * state.get("cols", 0) != state.get("frameCount"):
                errors.append(f"{state_name}: rows * cols must equal frameCount")
            sheet = state.get("sheet")
            if not isinstance(sheet, str):
                errors.append(f"{state_name}: approved state requires a runtime sheet path")
                continue
            expected = f"res://assets/characters/{character_id}/body/{state_name}.png"
            if sheet != expected:
                errors.append(f"{state_name}: runtime sheet must be exactly {expected}")
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

        runtime_manifest_path = (
            repo_root
            / "game"
            / "assets"
            / "characters"
            / character_id
            / "asset-manifest.json"
        )
        try:
            runtime_manifest = load_json(runtime_manifest_path)
        except ValidationError as exc:
            errors.append(str(exc))
        else:
            if runtime_manifest != build_runtime_manifest(manifest):
                errors.append("runtime asset-manifest does not match sanitized design manifest")

    return errors


def validate_promotable_bundle(repo_root: Path, character_id: str) -> list[str]:
    """Validate a qc-passed workspace bundle before any runtime files are written."""
    errors = validate_bundle(repo_root, character_id, require_ready=False)
    bundle_dir = repo_root / "design" / "characters" / character_id
    manifest = load_json(bundle_dir / "asset-manifest.json")
    approval = load_json(bundle_dir / "qa-approval.json")
    runtime = manifest.get("runtime", {})
    states = manifest.get("states", {})
    aliases = manifest.get("aliases", {})

    if manifest.get("status") != "qc-passed":
        errors.append("promotion requires manifest status 'qc-passed'")
    if runtime.get("weaponBakedIntoBody") is not False:
        errors.append("promotion requires weaponBakedIntoBody=false")
    if runtime.get("mirrorLeft") and not runtime.get("mirrorSafe"):
        errors.append("promotion requires mirrorSafe=true when mirrorLeft=true")
    if approval.get("approvedForPromotion") is not True:
        errors.append("promotion requires approvedForPromotion=true")
    if not _non_empty(approval.get("reviewer")) or not _non_empty(
        approval.get("reviewedAt")
    ):
        errors.append("promotion requires reviewer and reviewedAt evidence")
    checks = approval.get("checks", {})
    for check in PROMOTION_CHECKS:
        if checks.get(check) is not True:
            errors.append(f"promotion QA check is not true: {check}")
    if approval.get("blockers") != []:
        errors.append("promotion requires an empty blockers array")

    state_results = approval.get("stateResults", {})
    if not isinstance(state_results, dict):
        errors.append("promotion requires stateResults evidence")
        state_results = {}

    frame_width = runtime.get("frameWidth")
    frame_height = runtime.get("frameHeight")
    if frame_width != 256 or frame_height != 256:
        errors.append("promotion requires 256x256 runtime cells")
    allowed_root = repo_root / "art" / "work" / "characters" / character_id

    plan = load_json(bundle_dir / "production-plan.json")
    identity = plan.get("identity", {})
    if plan.get("currentPhase") != "qc-passed":
        errors.append("production-plan currentPhase must be 'qc-passed'")
    if plan.get("promotion", {}).get("approvedForPromotion") is not True:
        errors.append("production-plan must record approvedForPromotion=true")
    if not isinstance(identity, dict) or identity.get("status") != "approved":
        errors.append("production-plan identity status must be 'approved'")
    for field in ("master", "turnaround", "palette", "scaleProfile"):
        value = identity.get(field) if isinstance(identity, dict) else None
        if not isinstance(value, str):
            errors.append(f"promotion identity evidence is missing: {field}")
            continue
        try:
            evidence_file = workspace_path_to_file(repo_root, value, allowed_root)
        except ValidationError as exc:
            errors.append(f"identity {field}: {exc}")
            continue
        if not evidence_file.is_file():
            errors.append(f"identity evidence does not exist: {evidence_file}")

    visual_review = allowed_root / "qa" / "visual-review.md"
    if not visual_review.is_file():
        errors.append("promotion requires art workspace qa/visual-review.md")
    else:
        review_text = visual_review.read_text(encoding="utf-8").strip()
        if len(review_text) < 40 or "pending" in review_text.lower():
            errors.append("visual-review.md must contain completed review evidence")

    for state_name in REQUIRED_STATES:
        if state_name in aliases:
            continue
        state = states.get(state_name, {})
        plan_state = plan.get("states", {}).get(state_name, {})
        if plan_state.get("status") != "approved":
            errors.append(f"{state_name}: production-plan status must be 'approved'")
        result = state_results.get(state_name, {})
        if result.get("status") not in ("pass", "approved"):
            errors.append(f"{state_name}: stateResults requires pass evidence")
        if state.get("status") != "approved":
            errors.append(f"{state_name}: promotion requires state status 'approved'")
        rows = state.get("rows")
        cols = state.get("cols")
        frame_count = state.get("frameCount")
        if not all(isinstance(value, int) and value > 0 for value in (rows, cols)):
            errors.append(f"{state_name}: rows and cols must be positive integers")
            continue
        if rows * cols != frame_count:
            errors.append(f"{state_name}: rows * cols must equal frameCount")

        workspace_sheet = state.get("workspaceSheet")
        if not isinstance(workspace_sheet, str):
            errors.append(f"{state_name}: approved state requires workspaceSheet")
            continue
        try:
            sheet_file = workspace_path_to_file(repo_root, workspace_sheet, allowed_root)
        except ValidationError as exc:
            errors.append(f"{state_name}: {exc}")
            continue
        if not sheet_file.is_file():
            errors.append(f"{state_name}: workspace sheet does not exist: {sheet_file}")
        else:
            try:
                width, height, color_type = png_info(sheet_file)
            except ValidationError as exc:
                errors.append(f"{state_name}: {exc}")
            else:
                expected_size = (frame_width * cols, frame_height * rows)
                if (width, height) != expected_size:
                    errors.append(
                        f"{state_name}: workspace sheet is {width}x{height}, expected "
                        f"{expected_size[0]}x{expected_size[1]}"
                    )
                if color_type not in (4, 6):
                    errors.append(f"{state_name}: workspace PNG must contain alpha")

        qc_report = state.get("qcReport")
        if not isinstance(qc_report, str):
            errors.append(f"{state_name}: approved state requires qcReport")
            continue
        try:
            report_file = workspace_path_to_file(repo_root, qc_report, allowed_root)
            report = load_json(report_file)
        except ValidationError as exc:
            errors.append(f"{state_name}: {exc}")
            continue
        summary = report.get("qc_summary")
        if not isinstance(summary, dict):
            errors.append(f"{state_name}: qcReport is missing qc_summary")
            continue
        for metric in ("empty_count", "edge_touch_count", "paste_clamped_count"):
            if summary.get(metric) != 0:
                errors.append(f"{state_name}: {metric} must be zero")
        if summary.get("frame_count") != frame_count:
            errors.append(f"{state_name}: QC frame_count does not match frameCount")

        if state.get("qcPolicy") == "grounded-body":
            thresholds = (
                ("body_scale_cv", 0.08),
                ("profile_body_scale_drift", 0.08),
                ("anchor_y_std", 0.05),
            )
            for metric, limit in thresholds:
                value = summary.get(metric)
                if metric == "profile_body_scale_drift" and value is None:
                    if state_name == "idle":
                        continue
                    errors.append(f"{state_name}: QC metric is missing: {metric}")
                    continue
                if not isinstance(value, (int, float)):
                    errors.append(f"{state_name}: QC metric is missing: {metric}")
                elif value > limit and not _approved_exception(
                    approval, state_name, metric
                ):
                    errors.append(f"{state_name}: {metric} {value:.4f} exceeds {limit:.2f}")

    return list(dict.fromkeys(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", help="Validate one character ID; default validates all")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Fail unless every selected bundle has godot-ready status",
    )
    parser.add_argument(
        "--require-promotable",
        action="store_true",
        help="Fail unless every selected bundle is safe to promote",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.require_ready and args.require_promotable:
        print("Choose only one of --require-ready or --require-promotable.")
        return 2
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
            if args.require_promotable:
                errors = validate_promotable_bundle(repo_root, character_id)
            else:
                errors = validate_bundle(repo_root, character_id, args.require_ready)
        except ValidationError as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            print(f"FAIL {character_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            manifest = load_json(design_root / character_id / "asset-manifest.json")
            gate = "promotable" if args.require_promotable else manifest.get("status")
            print(f"PASS {character_id} ({gate})")

    if not character_ids:
        print("No character bundles found.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
