# Character Asset Standard

## Outcome

This standard makes character production repeatable and makes Godot import a
data operation instead of a per-character editing session. It does not promise
that balance or art direction will never change. It guarantees that a bundle
marked `godot-ready` already has stable names, dimensions, pivots, animation
timing, deterministic events, QA evidence, and runtime paths.

The contract has three separate layers:

```text
design/characters/<id>/       design truth and approval
art/work/characters/<id>/     editable/raw production work
game/assets/characters/<id>/  immutable approved runtime delivery
```

`art/tests/` is evidence for experiments only. Godot must never load from it.

## Source-of-truth boundaries

| Concern | Source of truth | May contain |
|---|---|---|
| Original user intent and agent scope | `character-brief.json` | Natural-language brief, target, locked constraints |
| Identity, role, weakness, moves, timing | `character-spec.json` | Design and deterministic events |
| Sheet layout and runtime paths | `asset-manifest.json` | Presentation metadata only |
| Resumable production queue | `production-plan.json` | Phase, attempts, accepted sources, next action |
| Acceptance evidence and exceptions | `qa-approval.json` | Measurements and agent/human visual review |
| Character movement/weight | `game/data/characters/<id>.json` | Integer simulation data |
| Weapon behavior | `game/data/weapons/<id>.json` | Weapon data and projectile references |
| Runtime pixels | `game/assets/characters/<id>/` | Approved RGBA PNG only |

Do not duplicate weapon statistics in a character file. Do not put hitboxes,
damage, or knockback authority into animation resources.

## Full working structure

```text
design/characters/
├── _template/
│   ├── character-spec.json
│   ├── asset-manifest.json
│   ├── qa-approval.json
│   ├── character-brief.json
│   └── production-plan.json
└── <character-id>/
    ├── character-brief.json
    ├── character-spec.json
    ├── asset-manifest.json
    ├── production-plan.json
    ├── qa-approval.json
    └── notes.md                     # optional decisions, never runtime data

art/work/characters/<character-id>/
├── source/
│   ├── identity-master.png          # approved neutral master
│   ├── turnaround.png               # front/side/back visual reference
│   ├── palette.png
│   └── editable/                    # .kra/.blend/.pxo if used
├── references/
│   ├── identity-lock.png
│   └── anchors/
│       ├── idle-anchor.png
│       └── attack-anchor.png
├── scale-profile.json
├── actions/
│   └── <state>/
│       ├── references/              # action anchor/layout guides
│       ├── prompt-used.txt
│       ├── raw-sheet.png
│       ├── processed/
│       │   ├── sheet-transparent.png
│       │   ├── <state>-01.png
│       │   ├── ...
│       │   ├── animation.gif
│       │   └── pipeline-meta.json
│       └── rejected/                # failed generations with reason
├── fx/
│   └── <effect-id>/...
├── previews/
│   ├── gameplay-scale.png
│   ├── mirror-check.png
│   └── all-states.gif
└── qa/
    └── visual-review.md

game/assets/characters/<character-id>/
├── asset-manifest.json
├── body/
│   ├── idle.png
│   ├── walk.png
│   ├── jump_start.png
│   ├── rise.png
│   ├── fall.png
│   ├── land.png
│   ├── attack.png
│   ├── hurt.png
│   ├── launch.png
│   ├── tumble.png
│   ├── death.png
│   └── ability.png
└── portrait/
    ├── select.png
    └── hud.png
```

Weapon sprites and effects belong under `game/assets/weapons/<weapon-id>/` and
`game/assets/effects/`, not in the character body directory.

## Naming contract

- Character ID: kebab-case, for example `nori-courier`.
- State IDs: exact snake_case names from the manifest.
- Runtime body sheet: `<state>.png`.
- Frame ordering: row-major, left-to-right then top-to-bottom.
- Event IDs: kebab-case and stable after playtests/replays depend on them.
- Runtime paths: `res://assets/...`; workspace paths are forbidden in a
  `godot-ready` manifest.
- Renaming a published ID requires an explicit migration and decision record.

## Required state budget

These are production starting points, not a command to add frames without
visible benefit.

| State | Frames | FPS | Loop | Purpose |
|---|---:|---:|---:|---|
| `idle` | 4–6 | 6–8 | yes | Identity and breathing |
| `walk` | 6–8 | 10–12 | yes | Ground locomotion |
| `jump_start` | 3 | 12 | no | Anticipation before leaving ground |
| `rise` | 2 | 8 | yes | Ascending air pose |
| `fall` | 2 | 8 | yes | Descending air pose |
| `land` | 3 | 12 | no | Contact and recovery |
| `attack` | 6–9 | 12 | no | Shared weapon-compatible body action |
| `hurt` | 3–4 | 12 | no | Readable short reaction |
| `launch` | 4 | 12 | no | Strong knockback entry |
| `tumble` | 6 | 12 | yes | Airborne hitstun loop |
| `death` | 6–8 | 10–12 | no | Ring-out/stock loss presentation |
| `ability` | 6–10 | 12 | no | Character-specific action |

An alias may be used only when the visual meaning is truly identical. Example:
`rise -> fall` is normally not acceptable because ascent and descent must be
readable. Every alias must be declared in `asset-manifest.json` and approved in
QA.

## Identity lock before animation

Approve these before producing many frames:

1. One right-facing neutral master at gameplay scale.
2. Front/side/back turnaround.
3. Exact palette and material language.
4. Three immutable silhouette markers.
5. Mirror safety: no important text, logo, handed symbol, or asymmetry that
   becomes wrong when flipped.
6. Body-only rule: no production weapon or detached VFX baked into the body.

The accepted master generates the character anchor layout and shared scale
profile. Later grounded actions reuse both. A prompt alone is not an identity
lock.

## Per-state production workflow

```text
approved character spec
→ identity master and turnaround
→ action timing and deterministic event frames
→ action-specific anchor/layout guide
→ one raw multi-row sheet for one action
→ transparent processing and frame extraction
→ numeric QC
→ visual QC at 100%, gameplay scale, mirror, and loop
→ manifest entry
→ promotion gate
```

`production-plan.json` is the agent hand-off ledger. After each attempt the
agent records the state status, attempt number, and exact next action. An agent
must resume from this file instead of regenerating already accepted work.

Dynamic states such as attack, launch, tumble, and death should use square cells
with generous padding. Nori's first attack proved that narrow rectangular cells
can crop extended poses even when the overall image looks plausible.

The grid stored in `asset-manifest.json` is the final delivery grid. A final
`1x3` strip is allowed only when it was assembled deterministically from an
already-QC'd multi-row body sheet. Never ask image generation to create a raw
single-row body animation.

## Numeric QC

Default grounded-body gates:

- `empty_count == 0`
- `output_edge_touch_count == 0`
- `paste_clamped_count == 0`
- `body_scale_cv <= 0.08`
- `profile_body_scale_drift <= 0.08`
- `anchor_y_std <= 0.05`

Hurt, launch, tumble, airborne, and silhouette-changing actions may have an
action-specific threshold. The exception must preserve full anatomy, contain no
output crop/clamp, be visually reviewed, and be recorded in `qa-approval.json`.
Never weaken the global gate because one generation failed.

An approved threshold exception uses the exact metric ID (`body_scale_cv`,
`profile_body_scale_drift`, or `anchor_y_std`), includes `approved: true`, and
records the observed value and reason. Empty frames, output edge contact, and
paste clamping are never exception-eligible for promotion.

## Visual QA

Numeric QC cannot detect every important failure. Review:

- face, markings, ears, tail, costume, palette, and body ratio remain the same;
- the loop has distinct useful poses instead of repeated near-identical frames;
- one planted foot/root does not slide in grounded loops;
- attack shows wind-up, event pose, recoil, and punishable recovery;
- no weapon/VFX component contaminates the body sheet;
- mirror is readable;
- silhouette is readable at expected camera zoom on a small laptop/mobile-sized
  viewport;
- alpha edges have no magenta fringe;
- frame order matches row-major manifest order.

## Godot import contract

Godot should use one shared `CharacterView` and one shared manifest loader for
the whole roster. The loader must:

1. Read `res://assets/characters/<id>/asset-manifest.json`.
2. Load each sheet named by the manifest.
3. Slice `rows × cols` cells of `frameWidth × frameHeight` in row-major order.
4. Create/reuse SpriteFrames using manifest FPS and loop settings.
5. Apply the shared normalized pivot/offset.
6. Mirror the right-facing art for left-facing presentation when allowed.
7. Play only the simulation-selected state/frame.
8. Display sound/VFX when simulation emits the matching deterministic event.

There must be no per-character scene editing, hand-entered FPS, hand-cropped
AtlasTextures, or AnimationPlayer gameplay event tracks. A bundle that needs
those adjustments is not `godot-ready`.

## Promotion lifecycle

```text
draft → art-proof → qc-passed → godot-ready
```

- `draft`: design is still changing.
- `art-proof`: enough output to test identity/pipeline; not runtime content.
- `qc-passed`: all required art and metadata passed asset checks and the agent
  reviewer set `approvedForPromotion: true` with no blockers.
- `godot-ready`: the promotion tool copied sanitized runtime assets, runtime
  paths exist, and the strict validator passes. This status does not mean Godot
  gameplay or the shared presentation loader has already been implemented.

Run:

```bash
python3 tools/validate_character_bundle.py --character <character-id>
python3 tools/validate_character_bundle.py --character <character-id> --require-promotable
python3 tools/validate_character_bundle.py --character <character-id> --require-ready
```

The second command is the pre-promotion gate. The third is the post-promotion
runtime gate.

To start the next character, use the scaffold command. It creates design truth,
the resumable production plan, and every canonical art workspace directory:

```bash
python3 tools/new_character_bundle.py \
  --id <character-id> \
  --name "<display name>" \
  --brief "<natural-language character idea>"
python3 tools/validate_character_bundle.py --character <character-id>
```

The first validation intentionally rejects agent placeholders. The agent must
use `original-pvp-character-design` to complete role, weakness, timing,
counterplay, deterministic events, and art brief before image generation. Do
not create a second ad-hoc folder structure for a new character.

After all state sheets and reports live under `art/work/characters/<id>/`, the
manifest is `qc-passed`, and QA approves promotion, run:

```bash
python3 tools/promote_character_bundle.py --character <character-id> --dry-run
python3 tools/promote_character_bundle.py --character <character-id>
```

The command refuses overwrite, stages copies before publishing, writes a
sanitized runtime manifest, updates the two approval phases, validates the
result, and rolls back on failure. It does not create Godot scenes or gameplay.

## One-line autonomous request

This is sufficient input for an agent:

> Dựa vào AGENTS.md, tạo nhân vật Miso: một chú chó nhỏ đeo nồi đất làm giáp,
> chuyên giữ khoảng cách gần và phản đòn chậm nhưng mạnh. Hoàn thành tới
> qc-passed, chưa làm Godot.

The agent owns role selection, counterplay, full spec, identity lock, prompts,
state grids, processing parameters, numeric QC, visual QC, rejected attempts,
manifest updates, and the final report. The user still owns the final creative
direction and may reject an identity even when it passes technical QC.

## Worked example: Nori

Nori lives at `design/characters/nori-courier/`. It is intentionally marked
`art-proof`, not `godot-ready`. It demonstrates a complete design/manifest/QA
record and documents real blockers:

- only idle, walk, attack, and hurt exist;
- jump/air/land/launch/tumble/death/ability are missing;
- the proof frames bake a brass pistol into the body, which violates the locked
  character/weapon separation;
- walk required a reviewed relaxed anchor threshold and source-edge allowance;
- current proof files live under `art/tests/`, not the production workspace.

This honesty is part of the standard: incomplete assets may be useful evidence,
but they must not silently become production assets.
