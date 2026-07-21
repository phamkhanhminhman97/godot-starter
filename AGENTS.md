# Dogfighter agent rules

These rules apply to the entire repository. `docs/DECISIONS.md` remains the
architectural source of truth. When a request conflicts with a locked decision,
stop and explain the conflict before changing code or assets.

## Character work is contract-first

Every new or modified playable character must follow
`docs/CHARACTER_ASSET_STANDARD.md`.

Before creating character visuals:

1. Use the `original-pvp-character-design` skill.
2. Create or update `design/characters/<character-id>/character-spec.json`.
3. Give the character exactly one primary role and at least one explicit
   weakness and counterplay window.
4. Define deterministic animation events before producing final frames.
5. Use kebab-case IDs. IDs and published file paths are immutable after a
   character reaches `godot-ready`.

When generating or processing sprite art, use the `generate2dsprite` workflow.
Raw AI output is never a runtime asset. It must pass deterministic processing,
visual review, and bundle validation first.

## Default agent-led character workflow

When the user gives a natural-language character idea and asks the agent to
follow this file, treat it as authorization to complete the character asset
pipeline. Do not ask the user to choose role, frame budget, grid, palette,
counterplay, or processor flags unless two interpretations would materially
change the requested fantasy.

1. Choose a stable kebab-case ID and run:

   ```bash
   python3 tools/new_character_bundle.py \
     --id <character-id> \
     --name "<display name>" \
     --brief "<user's original description>"
   ```

2. Use `original-pvp-character-design` to replace every agent placeholder in
   `character-spec.json`. Choose exactly one primary role; define weakness,
   startup, active frames, recovery, interruption, and specific counterplay.
3. Synchronize every animation contract field into `asset-manifest.json`, run
   `validate_character_bundle.py`, and fix all design errors before generating
   visual frames.
4. Use `generate2dsprite` to lock one identity master, turnaround, palette, and
   scale profile. Then process one action at a time in the order recorded in
   `production-plan.json`. Update the plan after every accepted or rejected
   attempt so another agent can resume without guessing.
5. Inspect the master, raw sheet, transparent sheet, animation preview,
   gameplay-scale preview, mirror preview, and QC report. Numeric QC alone is
   never approval. Store failed attempts under the action's `rejected/` folder
   with a short reason; never hide them by weakening global thresholds.
6. A state becomes `approved` only when its `workspaceSheet` and `qcReport`
   point inside `art/work/characters/<id>/`, deterministic timing matches the
   spec, and both numeric and visual QA pass. Set the bundle to `qc-passed` only
   after all required states or approved aliases pass.
7. Set `approvedForPromotion: true` only with reviewer, review date, completed
   checks, state results, and no blockers. The promotion tool alone sets
   `approvedForGodot: true` after runtime files validate.

The default target for character-only requests is `qc-passed`; do not implement
Godot gameplay or world content. Promote only when the user asks for a runtime
bundle or explicitly asks for `godot-ready`:

```bash
python3 tools/promote_character_bundle.py --character <character-id> --dry-run
python3 tools/promote_character_bundle.py --character <character-id>
```

The promotion command never overwrites an existing runtime bundle and rolls
back partial writes when final validation fails.

## Authoritative boundaries

- Simulation/server owns state changes, hit checks, projectile spawn, knockback,
  death, cooldowns, and transitions.
- Renderer only plays the state and frame selected by simulation and displays
  event-driven cosmetic VFX/audio.
- `frameCount`, `fps`, `events`, `cancelAfterFrame`, and `onComplete` must agree
  between `character-spec.json` and `asset-manifest.json`.
- Never make gameplay depend on `AnimatedSprite2D`, `AnimationPlayer`, Tween,
  engine signals, wall-clock time, or dropped render frames.
- Event frame numbers are zero-based and must be inside
  `0..frameCount - 1`.

## Character and weapon separation

`CharacterData` and `WeaponData` are independent. A fighter is composed from
one of each at runtime.

- Do not bake a production weapon, muzzle flash, projectile, impact, dust,
  trail, or screen effect into a character body sheet.
- The body `attack` animation must work with every compatible weapon.
- Weapon texture/icon, projectile, muzzle VFX, impact VFX, and weapon stats live
  outside the character body bundle.
- Art proofs with a baked weapon must remain under `art/tests/`; they cannot be
  promoted to `game/assets/characters/`.

## Canonical folders

- `design/characters/<id>/`: design spec, asset manifest, QA approval.
- `art/work/characters/<id>/`: editable sources, references, raw generations,
  processor output, previews, and rejected attempts.
- `art/tests/`: disposable pipeline proofs; never referenced by runtime data.
- `game/assets/characters/<id>/`: approved runtime PNG files only.
- `game/data/characters/<id>.json`: character simulation numbers only.
- `game/data/weapons/<id>.json`: weapon simulation numbers only.

Do not manually create a unique Godot scene or AnimationPlayer track for each
character. A shared presentation loader must consume `asset-manifest.json` and
construct the visual animations using the same contract for the whole roster.

## Required animation states

Every `godot-ready` platform-fighter character must deliver:

`idle`, `walk`, `jump_start`, `rise`, `fall`, `land`, `attack`, `hurt`,
`launch`, `tumble`, `death`, and `ability`.

The six base contract states remain `idle`, `walk`, `attack`, `hurt`, `death`,
and `ability`. Platform movement states are additional because they materially
change readability. An omitted state must use an explicit alias in the manifest;
silent fallback is forbidden.

## Sprite delivery rules

- Runtime cell size: `256x256` RGBA PNG unless a decision record changes it.
- Author right-facing frames; prototype left-facing uses horizontal mirror.
- Pivot: normalized feet-center `{ "x": 0.5, "y": 0.9 }` for grounded body
  states.
- Generate and QC one action per raw multi-row grid. Never generate unrelated
  action rows as one raw atlas.
- Use the accepted idle master to create a character anchor layout and one
  shared scale profile for all compatible grounded states.
- Body-only sheets use `component_mode=largest`, `align=feet`, and
  `scale_strategy=preserve` unless the action contract documents an exception.
- Final runtime sheets contain transparency; magenta raw sheets and preview GIFs
  stay outside `game/`.
- Do not commit a `.import` file as authored source. Godot may regenerate it.

## Promotion gate

Only promote a bundle to `game/assets/characters/<id>/` when all of these are
true:

1. Character spec and manifest are complete.
2. All required states are present or have an explicit approved alias.
3. Every sheet has correct dimensions, alpha, frame count, order, FPS, pivot,
   loop flag, and event frames.
4. No empty frame, output-edge contact, paste clamp, identity drift, unintended
   detached component, or visible crop remains.
5. `body_scale_cv <= 0.08`, `profile_body_scale_drift <= 0.08`, and grounded
   `anchor_y_std <= 0.05`, unless the state has a reviewed action-specific
   exception recorded in `qa-approval.json`.
6. Mirror, gameplay-scale readability, animation loop, and event timing have
   been visually tested.
7. `weaponBakedIntoBody` is false.
8. `qa-approval.json` has `approvedForPromotion: true` with no blockers.
9. `python3 tools/validate_character_bundle.py --character <id> --require-promotable`
   passes.
10. `tools/promote_character_bundle.py` copies the approved workspace sheets,
    sets runtime paths, and makes `--require-ready` pass transactionally.

Never change validation thresholds merely to make a failed asset pass. Keep
failed attempts for evidence, regenerate or fix the source, and record any real
exception with a reason and reviewer.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **godot-starter** (2408 symbols, 2839 relationships, 43 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/godot-starter/context` | Codebase overview, check index freshness |
| `gitnexus://repo/godot-starter/clusters` | All functional areas |
| `gitnexus://repo/godot-starter/processes` | All execution flows |
| `gitnexus://repo/godot-starter/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
