# Runtime character assets

Only `godot-ready` character bundles belong here.

Each character directory must contain `asset-manifest.json`, approved body
sheets under `body/`, and portraits under `portrait/`. Do not place raw magenta
sheets, editable sources, prompts, GIF previews, rejected generations, or QC
working files under `game/`.

The shared character presentation loader must consume the manifest. Do not
create character-specific scenes or manually slice frames in the Godot editor.

See `docs/CHARACTER_ASSET_STANDARD.md` and the root `AGENTS.md`.

