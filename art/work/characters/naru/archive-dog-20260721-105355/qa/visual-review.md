# Naru visual review

Reviewed on 2026-07-20 by Codex agent-led visual and numeric QA.

## Identity and readability

- The approved master, turnaround, palette, and idle scale profile agree on a
  small cream dog wearing a charcoal pointed ninja hood, muted red scarf, teal
  belt, and oversized cream paw wraps.
- Hood points, scarf tails, tail curve, and large wrapped paws remain readable
  at the 96 px gameplay proof size.
- Right-facing authored frames and the horizontal mirror proof preserve the
  intended stance and do not reveal an asymmetric baked weapon or effect.

## Animation review

- All 12 required states were inspected in raw grid form, transparent sheet
  form, per-state GIF form, and the combined animation board.
- Idle, walk, jump_start, rise, fall, land, launch, tumble, and death form a
  coherent movement and knockback vocabulary. No accepted frame is empty,
  cropped, edge-touching, paste-clamped, or missing a major identity feature.
- Attack is body-only and compatible with external weapon data. Zero-based
  frame 3 is the deterministic weapon spawn pose; no weapon, projectile, muzzle
  flash, impact, trail, dust, or shadow is baked into the body sheet.
- Ability has a slow readable brace. Zero-based frame 4 is the one-frame
  `counter-open` window, frame 5 is the `hit`, and frames 6-8 expose recovery.
  The visual sequence agrees with `character-spec.json` and
  `asset-manifest.json`.
- Hurt and death communicate recoil and defeat without embedding gameplay state
  changes, damage logic, fade logic, or despawn behavior into renderer frames.

## Numeric evidence and exception

- Every accepted sheet has zero empty frames, zero output-edge contacts, and
  zero paste clamps. Grounded states meet body-scale and profile-drift limits.
- Land records one reviewed action-specific exception: `anchor_y_std=0.0524`
  against the global `0.05` limit. All four processed frames have
  `shared_feet_y=228`, output heights of 145-146 px, body-scale CV `0.0208`, and
  profile drift `0.0329`; the measured shift comes from the intended crouch
  changing center of mass, not visible foot or pivot drift.

## Review artifacts

- `previews/all-states-contact-sheet.png`
- `previews/all-states.gif`
- `previews/gameplay-scale.png`
- `previews/mirror-check.png`

Result: approved for workspace promotion preflight. No runtime files were
created and no Godot integration was performed.
