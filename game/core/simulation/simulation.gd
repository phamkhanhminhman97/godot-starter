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
	var jump_pressed := cmd.jump and not player.prev_jump_held
	var jump_released := not cmd.jump and player.prev_jump_held
	player.prev_jump_held = cmd.jump

	# Đứng đất luôn nạp lại coyote NGAY (an toàn — đứng đất thì luôn đủ điều
	# kiện nhảy tick này). Đang bay thì KHÔNG trừ ở đây — trừ sau khi đã dùng
	# giá trị để check, nếu không sẽ lệch 1 tick (tick cuối cùng còn coyote
	# sẽ bị trừ về 0 trước khi kịp kiểm tra, không bao giờ nhảy được).
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

	# Trọng lực + fast-fall (fast-fall có trần rơi cao hơn MAX_FALL thường).
	if not vy_overridden:
		player.vy = mini(player.vy + GRAVITY, MAX_FALL)
		if cmd.drop and player.vy > 0:
			player.vy = FAST_FALL

	player.y += player.vy

	if player.y >= GROUND_Y and player.vy >= 0:
		player.y = GROUND_Y
		player.vy = 0
		if not player.grounded:
			player.used_double_jump = false
		player.grounded = true
	else:
		player.grounded = false

func _apply_friction(vx: int) -> int:
	if vx > 0:
		return maxi(0, vx - FRICTION)
	if vx < 0:
		return mini(0, vx + FRICTION)
	return 0
