from __future__ import annotations

import binascii
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import zlib


TOOLS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS_DIR))

from new_character_bundle import BundleCreationError, create_bundle  # noqa: E402
from promote_character_bundle import promote_bundle  # noqa: E402
from validate_character_bundle import (  # noqa: E402
    REQUIRED_STATES,
    validate_bundle,
    validate_promotable_bundle,
)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def write_rgba_png(path: Path, width: int, height: int) -> None:
    pixel_row = b"\x00" + (b"\x40\x80\xC0\xFF" * width)
    payload = pixel_row * height
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(payload, level=1))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)


class CharacterBundleToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        template_target = self.repo / "design" / "characters" / "_template"
        template_target.parent.mkdir(parents=True)
        shutil.copytree(
            PROJECT_ROOT / "design" / "characters" / "_template",
            template_target,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_test_bundle(self) -> Path:
        create_bundle(
            self.repo,
            "miso-potguard",
            "Miso",
            "A small dog wearing a clay cooking pot as armor.",
        )
        return self.repo / "design" / "characters" / "miso-potguard"

    def complete_bundle_for_promotion(self, design_dir: Path) -> None:
        spec_path = design_dir / "character-spec.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["identity"]["role"] = "close-range counter defender"
        spec["identity"]["fantasy"] = "A tiny pot-armored guardian who commits to slow counters."
        spec["identity"]["silhouette"] = [
            "Wide clay pot shell",
            "Small triangular ears above the rim",
            "Low planted stance",
        ]
        spec["combat"]["primary"]["counterplay"] = "Back away during the brace, then punish recovery."
        spec["combat"]["primary"]["interruption"] = "No spawn event occurs before the active frame."
        spec["combat"]["ability"]["description"] = "A short armored counter with one active frame."
        spec["combat"]["ability"]["counterplay"] = "Feint an attack and punish the long recovery."
        spec["combat"]["ability"]["interruption"] = "The counter is lost if interrupted during startup."
        spec["combat"]["weaknesses"] = [
            "Slow recovery after every committed counter.",
            "Short range loses to patient spacing.",
        ]
        spec["artBrief"]["windUpCue"] = "The pot tilts backward before commitment."
        spec["artBrief"]["impactCue"] = "The body snaps forward while impact FX remains separate."
        spec["artBrief"]["recoveryCue"] = "The pot wobbles and exposes the face."
        write_json(spec_path, spec)

        manifest_path = design_dir / "asset-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "qc-passed"
        manifest["runtime"]["mirrorSafe"] = True
        art_root = self.repo / "art" / "work" / "characters" / "miso-potguard"
        source_root = art_root / "source"
        source_root.mkdir(parents=True, exist_ok=True)
        for name in ("identity-master.png", "turnaround.png", "palette.png"):
            write_rgba_png(source_root / name, 256, 256)
        write_json(art_root / "scale-profile.json", {"profileName": "miso-potguard"})
        (art_root / "qa" / "visual-review.md").write_text(
            "# Visual review\n\nIdentity, mirror, gameplay scale, loops, events, and alpha edges pass.\n",
            encoding="utf-8",
        )
        for state_name in REQUIRED_STATES:
            state = manifest["states"][state_name]
            processed = art_root / "actions" / state_name / "processed"
            processed.mkdir(parents=True, exist_ok=True)
            sheet = processed / "sheet-transparent.png"
            write_rgba_png(
                sheet,
                state["cols"] * manifest["runtime"]["frameWidth"],
                state["rows"] * manifest["runtime"]["frameHeight"],
            )
            report = processed / "pipeline-meta.json"
            write_json(
                report,
                {
                    "qc_summary": {
                        "frame_count": state["frameCount"],
                        "empty_count": 0,
                        "edge_touch_count": 0,
                        "paste_clamped_count": 0,
                        "body_scale_cv": 0.01,
                        "profile_body_scale_drift": 0.01,
                        "anchor_y_std": 0.01,
                    }
                },
            )
            state["status"] = "approved"
            state["workspaceSheet"] = str(sheet.relative_to(self.repo))
            state["qcReport"] = str(report.relative_to(self.repo))
        write_json(manifest_path, manifest)

        approval_path = design_dir / "qa-approval.json"
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approval["approvedForPromotion"] = True
        approval["reviewedAt"] = "2026-07-20"
        approval["reviewer"] = "Automated test reviewer"
        for check in approval["checks"]:
            approval["checks"][check] = check != "runtimePathsExist"
        approval["blockers"] = []
        approval["stateResults"] = {
            state_name: {"status": "pass"} for state_name in REQUIRED_STATES
        }
        write_json(approval_path, approval)

        plan_path = design_dir / "production-plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["currentPhase"] = "qc-passed"
        plan["identity"] = {
            "status": "approved",
            "master": str((source_root / "identity-master.png").relative_to(self.repo)),
            "turnaround": str((source_root / "turnaround.png").relative_to(self.repo)),
            "palette": str((source_root / "palette.png").relative_to(self.repo)),
            "scaleProfile": str((art_root / "scale-profile.json").relative_to(self.repo)),
        }
        for state_name in REQUIRED_STATES:
            plan["states"][state_name]["status"] = "approved"
            plan["states"][state_name]["nextAction"] = "ready-for-promotion"
        plan["promotion"]["approvedForPromotion"] = True
        write_json(plan_path, plan)

    def test_scaffold_creates_complete_canonical_structure_and_refuses_overwrite(self) -> None:
        design_dir = self.create_test_bundle()
        self.assertTrue((design_dir / "character-brief.json").is_file())
        self.assertTrue((design_dir / "production-plan.json").is_file())
        self.assertTrue(
            (
                self.repo
                / "art"
                / "work"
                / "characters"
                / "miso-potguard"
                / "references"
                / "anchors"
            ).is_dir()
        )
        self.assertTrue(
            (
                self.repo
                / "art"
                / "work"
                / "characters"
                / "miso-potguard"
                / "actions"
                / "ability"
                / "rejected"
            ).is_dir()
        )
        errors = validate_bundle(self.repo, "miso-potguard", require_ready=False)
        self.assertTrue(any("primary role" in error for error in errors))
        with self.assertRaises(BundleCreationError):
            self.create_test_bundle()

    def test_promote_publishes_sanitized_runtime_bundle_and_passes_strict_gate(self) -> None:
        design_dir = self.create_test_bundle()
        self.complete_bundle_for_promotion(design_dir)
        self.assertEqual(validate_promotable_bundle(self.repo, "miso-potguard"), [])

        copies = promote_bundle(self.repo, "miso-potguard")
        self.assertEqual(len(copies), len(REQUIRED_STATES))
        runtime_dir = (
            self.repo / "game" / "assets" / "characters" / "miso-potguard"
        )
        runtime_manifest = json.loads(
            (runtime_dir / "asset-manifest.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("workspaceSheet", runtime_manifest["states"]["idle"])
        self.assertNotIn("qcReport", runtime_manifest["states"]["idle"])
        self.assertEqual(validate_bundle(self.repo, "miso-potguard", True), [])


if __name__ == "__main__":
    unittest.main()
