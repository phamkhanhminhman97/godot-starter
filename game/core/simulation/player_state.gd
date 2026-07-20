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
var on_platform: bool = false # đứng trên platform (khác mặt đất tuyệt đối) -> cho drop-through
## Platform ĐANG được xuyên qua (drop-through) — chỉ platform NÀY bị loại trừ
## khỏi va chạm, không phải toàn bộ danh sách platform (bug thật đã sửa: trước
## đây dùng bộ đếm tick chung, vô tình cho xuyên qua cả platform khác không
## liên quan nếu chúng nằm gần nhau theo trục y). Tham chiếu object, không
## phải id — platforms là dữ liệu tĩnh dùng chung, an toàn để so sánh bằng ==.
var drop_through_platform: Platform = null
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
	copy.on_platform = on_platform
	copy.drop_through_platform = drop_through_platform
	copy.coyote_remaining = coyote_remaining
	copy.jump_buffer_remaining = jump_buffer_remaining
	copy.used_double_jump = used_double_jump
	copy.prev_jump_held = prev_jump_held
	return copy
