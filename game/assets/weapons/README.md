# Runtime weapon assets

Weapons are independent from character body art. Each weapon owns its visible
weapon texture, projectile texture, muzzle effect, impact effect, and weapon
simulation data under `game/data/weapons/`.

Do not create a character-specific attack sheet for each weapon. The character
plays one compatible body `attack` action while the renderer attaches the
selected weapon visuals and the simulation resolves weapon data.
