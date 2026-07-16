class_name SimState
extends RefCounted
## Snapshot tất định tại 1 tick. Immutable theo quy ước dự án — Simulation.step()
## luôn trả về SimState MỚI, không sửa state cũ (xem coding-style: no mutation).

var tick: int = 0
var players: Array[PlayerState] = []

func duplicated() -> SimState:
	var copy := SimState.new()
	copy.tick = tick
	for p in players:
		copy.players.append(p.duplicated())
	return copy
