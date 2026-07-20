class_name Simulation
extends RefCounted
## Sim tất định 60 tick/s. Thuần GDScript — không Node, không engine physics (D-004).
## step() luôn trả về SimState MỚI; không sửa state truyền vào (immutability).
## Số khởi điểm theo ROADMAP §3.2 / design/specs/movement-lab.md (sim units/tick @60Hz).

const RUN_ACCEL: int = 500
const RUN_MAX: int = 4200
const FRICTION: int = 450

const AIR_ACCEL: int = 250
const AIR_MAX: int = 3400

const GRAVITY: int = 340
const MAX_FALL: int = 7000
const FAST_FALL: int = 9500

const JUMP_VEL: int = -8000
const SHORT_HOP_VEL: int = -5200
const DOUBLE_JUMP_VEL: int = -7000

const COYOTE_TICKS: int = 5
const JUMP_BUFFER_TICKS: int = 5

const GROUND_Y: int = 0

var platforms: Array[Platform] = [] # gán từ ArenaLoader.load_platforms() bên ngoài, sim không tự đọc file

func step(state: SimState, commands: Array[Command]) -> SimState:
	var next := state.duplicated()
	next.tick = state.tick + 1

	for i in range(next.players.size()):
		var player := next.players[i]
		var cmd := _command_for(commands, i)
		_step_horizontal(player, cmd)
		_step_vertical(player, cmd)

	return next

func _command_for(commands: Array[Command], player_id: int) -> Command:
	for cmd in commands:
		if cmd.player_id == player_id:
			return cmd
	return Command.new() # không input tick này = mọi field mặc định (0/false)

func _step_horizontal(player: PlayerState, cmd: Command) -> void:
	var accel := RUN_ACCEL if player.grounded else AIR_ACCEL
	var max_speed := RUN_MAX if player.grounded else AIR_MAX

	if cmd.move_x != 0:
		player.vx = clampi(player.vx + cmd.move_x * accel, -max_speed, max_speed)
		player.facing = cmd.move_x
	elif player.grounded:
		player.vx = _apply_friction(player.vx)
	# trên không, không giữ hướng thì giữ nguyên vx (không có air friction trong MVP)

	player.x += player.vx

func _step_vertical(player: PlayerState, cmd: Command) -> void:
	var prev_y := player.y # vị trí TRƯỚC khi tick này cập nhật — luật one-way platform cần giá trị này

	var jump_pressed := cmd.jump and not player.prev_jump_held
	var jump_released := not cmd.jump and player.prev_jump_held
	player.prev_jump_held = cmd.jump

	# Drop-through: giữ xuống + bấm nhảy trong khi đứng trên MỘT PLATFORM (không
	# phải mặt đất tuyệt đối) -> xuyên qua ĐÚNG platform đó, KHÔNG nhảy bình
	# thường. Chỉ platform này bị loại trừ khỏi va chạm (không phải mọi platform
	# — nếu rơi trúng platform KHÁC bên dưới, vẫn phải đáp lên nó bình thường).
	if jump_pressed and cmd.drop and player.grounded and player.on_platform:
		player.drop_through_platform = _platform_at(player)
		player.grounded = false
		player.on_platform = false
		_advance_vertical_velocity(player, cmd, false)
		_resolve_vertical_collision(player, prev_y)
		return

	if player.grounded:
		player.coyote_remaining = COYOTE_TICKS
	if jump_pressed:
		player.jump_buffer_remaining = JUMP_BUFFER_TICKS

	var can_coyote_jump := player.jump_buffer_remaining > 0 and player.coyote_remaining > 0
	var vy_overridden := false # nhảy/short-hop set vy trực tiếp tick này -> khỏi cộng trọng lực đè lên, để hằng số JUMP_VEL/SHORT_HOP_VEL quan sát được đúng y chang lúc tune

	if can_coyote_jump:
		player.vy = JUMP_VEL
		player.jump_buffer_remaining = 0
		player.coyote_remaining = 0
		player.grounded = false
		player.on_platform = false
		vy_overridden = true
	elif jump_pressed and not player.grounded and not player.used_double_jump:
		player.vy = DOUBLE_JUMP_VEL
		player.used_double_jump = true
		player.jump_buffer_remaining = 0
		vy_overridden = true

	# Trừ dần cho tick sau — chỉ khi KHÔNG vừa bị tiêu thụ ở trên (đã về 0).
	if not player.grounded and player.coyote_remaining > 0:
		player.coyote_remaining -= 1
	if not jump_pressed and player.jump_buffer_remaining > 0:
		player.jump_buffer_remaining -= 1

	# Short-hop: nhả nút sớm khi còn đang bay lên -> cắt vận tốc lên.
	if jump_released and player.vy < SHORT_HOP_VEL:
		player.vy = SHORT_HOP_VEL
		vy_overridden = true

	_advance_vertical_velocity(player, cmd, vy_overridden)
	_resolve_vertical_collision(player, prev_y)

func _advance_vertical_velocity(player: PlayerState, cmd: Command, vy_overridden: bool) -> void:
	if vy_overridden:
		return
	# Trọng lực + fast-fall (fast-fall có trần rơi cao hơn MAX_FALL thường).
	player.vy = mini(player.vy + GRAVITY, MAX_FALL)
	if cmd.drop and player.vy > 0:
		player.vy = FAST_FALL

func _resolve_vertical_collision(player: PlayerState, prev_y: int) -> void:
	player.y += player.vy

	var landing_platform := _find_landing_platform(player, prev_y)
	if landing_platform != null:
		player.y = landing_platform.y
		player.vy = 0
		if not player.grounded:
			player.used_double_jump = false
		player.grounded = true
		player.on_platform = true
		player.drop_through_platform = null
		return

	# Đã rơi hẳn xuống dưới platform đang xuyên qua -> không cần loại trừ nó
	# nữa (dọn tham chiếu; không ảnh hưởng đúng/sai vì luật crosses tự nhiên
	# đã không bao giờ bắt lại platform ở phía trên khi đang đi xuống).
	if player.drop_through_platform != null and player.y > player.drop_through_platform.y:
		player.drop_through_platform = null

	if player.y >= GROUND_Y and player.vy >= 0:
		player.y = GROUND_Y
		player.vy = 0
		if not player.grounded:
			player.used_double_jump = false
		player.grounded = true
		player.on_platform = false
		player.drop_through_platform = null
		return

	player.grounded = false
	player.on_platform = false

## Chọn platform sẽ chặn người chơi tick này, nếu có. Chỉ chặn khi: đang rơi
## xuống (vy>=0), tick trước ở TRÊN HOẶC ĐÚNG mặt platform (prev_y <= p.y —
## dùng <= chứ không phải < để người chơi ĐANG ĐỨNG YÊN trên platform (y đã
## bằng p.y sẵn) vẫn tiếp tục được platform đỡ mỗi tick, không rơi xuyên sau
## đúng 1 tick không bấm gì — đây là bug thật đã bắt được và sửa, không phải
## suy đoán), tick này đã chạm/vượt qua mặt platform (player.y >= p.y), x nằm
## trong bề rộng platform, và KHÔNG phải platform đang chủ động xuyên qua.
## Nếu nhiều platform cùng thỏa (hiếm, chồng x), chọn platform CAO NHẤT (y nhỏ
## nhất) vì đó là mặt sẽ chạm trước khi rơi từ trên xuống. Nếu 2 platform
## TRÙNG y (dị thường, không có trong lab.json hiện tại) thì phần tử đứng
## trước trong mảng `platforms` thắng — vẫn tất định vì thứ tự mảng cố định
## (ArenaLoader đọc JSON giữ nguyên thứ tự phần tử), không phải undefined
## behavior, chỉ là tie-break theo thứ tự khai báo trong file arena.
func _find_landing_platform(player: PlayerState, prev_y: int) -> Platform:
	var best: Platform = null
	for p in platforms:
		if p == player.drop_through_platform:
			continue
		var crosses := prev_y <= p.y and player.y >= p.y
		if player.vy >= 0 and crosses and p.contains_x(player.x):
			if best == null or p.y < best.y:
				best = p
	return best

func _platform_at(player: PlayerState) -> Platform:
	for p in platforms:
		if p.y == player.y and p.contains_x(player.x):
			return p
	return null

func _apply_friction(vx: int) -> int:
	if vx > 0:
		return maxi(0, vx - FRICTION)
	if vx < 0:
		return mini(0, vx + FRICTION)
	return 0
