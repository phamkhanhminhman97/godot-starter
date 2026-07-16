class_name PlayerState
extends RefCounted
## Một người chơi trong SimState. Đơn vị: sim units (D-005, 1 px = 1000 units).
## Quy ước trục Y: giống Godot màn hình — Y+ là XUỐNG. Nhảy dùng vận tốc âm.

var x: int = 0
var vx: int = 0
var y: int = 0
var vy: int = 0
var facing: int = 1 # 1 = phải, -1 = trái

var grounded: bool = true
var coyote_remaining: int = 0
var jump_buffer_remaining: int = 0
var used_double_jump: bool = false
var prev_jump_held: bool = false

func duplicated() -> PlayerState:
	var copy := PlayerState.new()
	copy.x = x
	copy.vx = vx
	copy.y = y
	copy.vy = vy
	copy.facing = facing
	copy.grounded = grounded
	copy.coyote_remaining = coyote_remaining
	copy.jump_buffer_remaining = jump_buffer_remaining
	copy.used_double_jump = used_double_jump
	copy.prev_jump_held = prev_jump_held
	return copy
