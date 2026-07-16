class_name StateHasher
extends RefCounted
## FNV-1a trên các field theo thứ tự cố định (D-005 luật 6). Dùng để phát hiện
## desync: cùng input phải luôn cho cùng hash, mọi tick.

## 0xcbf29ce484222325 (FNV offset basis) đọc theo bit two's-complement 64-bit
## có dấu — viết trực tiếp bằng hex vượt INT64_MAX nên GDScript báo lỗi parse
## (đã bắt được lỗi này bằng cách chạy qua MCP, không phải đoán).
const FNV_OFFSET: int = -3750763034362895579
const FNV_PRIME: int = 0x100000001b3

static func hash_state(state: SimState) -> int:
	var h: int = FNV_OFFSET
	h = _mix(h, state.tick)
	for player in state.players:
		h = _mix(h, player.x)
		h = _mix(h, player.vx)
		h = _mix(h, player.y)
		h = _mix(h, player.vy)
		h = _mix(h, player.facing)
		h = _mix(h, 1 if player.grounded else 0)
	return h

static func _mix(h: int, value: int) -> int:
	for i in range(8):
		var byte: int = (value >> (i * 8)) & 0xFF
		h = h ^ byte
		h = h * FNV_PRIME
	return h
