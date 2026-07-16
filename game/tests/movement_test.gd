extends SceneTree
## Test Movement Lab (coyote time, jump buffer, short-hop, double-jump reset).
## White-box: gọi thẳng Simulation._step_vertical() để kiểm soát chính xác
## precondition — chưa có platform để test "rời mép" tự nhiên bằng đi bộ, việc
## đó thêm integration test khi có one-way platform (bước kế tiếp).
## Chạy: godot --headless --script res://tests/movement_test.gd (sau khi đã
## `--headless --import` ít nhất 1 lần — xem ghi chú trong determinism_test.gd).

var failures: Array[String] = []

func _init() -> void:
	_test_coyote_window_allows_jump()
	_test_coyote_window_expires()
	_test_jump_buffer_counts_down()
	_test_jump_buffer_expires_to_zero()
	_test_short_hop_cuts_velocity()
	_test_full_hop_keeps_rising_velocity()
	_test_double_jump_resets_on_landing()

	if failures.is_empty():
		print("[movement] PASS - 7/7 test")
		quit(0)
	else:
		for f in failures:
			printerr("[movement] FAIL - %s" % f)
		quit(1)

func _check(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)

func _command(jump: bool = false) -> Command:
	var cmd := Command.new()
	cmd.jump = jump
	return cmd

func _airborne_player(coyote_remaining: int, used_double_jump: bool = false) -> PlayerState:
	var p := PlayerState.new()
	p.grounded = false
	p.y = -1000000 # rất cao — không được rơi chạm đất giữa 1 test (vài tick)
	p.vy = -100
	p.coyote_remaining = coyote_remaining
	p.used_double_jump = used_double_jump
	return p

func _test_coyote_window_allows_jump() -> void:
	var sim := Simulation.new()
	# chặn double-jump để chỉ còn đúng 1 cách nhảy: qua coyote path
	var p := _airborne_player(1, true)
	sim._step_vertical(p, _command(true))
	_check(p.vy == Simulation.JUMP_VEL,
		"coyote còn 1 tick phải cho full jump (vy=%d, ky vong %d)" % [p.vy, Simulation.JUMP_VEL])

func _test_coyote_window_expires() -> void:
	var sim := Simulation.new()
	var p := _airborne_player(0, false)
	sim._step_vertical(p, _command(true))
	_check(p.vy == Simulation.DOUBLE_JUMP_VEL,
		"coyote het phai roi ve double jump (vy=%d, ky vong %d)" % [p.vy, Simulation.DOUBLE_JUMP_VEL])

func _test_jump_buffer_counts_down() -> void:
	var sim := Simulation.new()
	# chặn cả 2 đường nhảy (coyote=0, double đã dùng) để chỉ còn đo bộ đếm buffer
	var p := _airborne_player(0, true)
	sim._step_vertical(p, _command(true))
	_check(p.jump_buffer_remaining == Simulation.JUMP_BUFFER_TICKS,
		"bam nhay phai nap du buffer (got=%d)" % p.jump_buffer_remaining)
	for _i in range(Simulation.JUMP_BUFFER_TICKS - 1):
		sim._step_vertical(p, _command(false))
	_check(p.jump_buffer_remaining == 1,
		"buffer phai dem nguoc dung tung tick (got=%d, ky vong 1)" % p.jump_buffer_remaining)

func _test_jump_buffer_expires_to_zero() -> void:
	var sim := Simulation.new()
	var p := _airborne_player(0, true)
	sim._step_vertical(p, _command(true))
	for _i in range(Simulation.JUMP_BUFFER_TICKS):
		sim._step_vertical(p, _command(false))
	_check(p.jump_buffer_remaining == 0,
		"buffer phai ve 0 sau dung JUMP_BUFFER_TICKS tick khong bam (got=%d)" % p.jump_buffer_remaining)

func _test_short_hop_cuts_velocity() -> void:
	var sim := Simulation.new()
	var p := PlayerState.new()
	p.grounded = true
	sim._step_vertical(p, _command(true))
	_check(p.vy == Simulation.JUMP_VEL, "phai bat dau bang full jump velocity")
	sim._step_vertical(p, _command(false)) # nha nut ngay tick sau
	_check(p.vy == Simulation.SHORT_HOP_VEL,
		"nha som phai cat xuong short-hop velocity (got=%d, ky vong %d)" % [p.vy, Simulation.SHORT_HOP_VEL])

func _test_full_hop_keeps_rising_velocity() -> void:
	var sim := Simulation.new()
	var p := PlayerState.new()
	p.grounded = true
	sim._step_vertical(p, _command(true))
	var vy_after_jump := p.vy
	sim._step_vertical(p, _command(true)) # van giu nut
	_check(p.vy == vy_after_jump + Simulation.GRAVITY,
		"giu nut thi trong luc van cong don binh thuong (got=%d, ky vong %d)" % [p.vy, vy_after_jump + Simulation.GRAVITY])

func _test_double_jump_resets_on_landing() -> void:
	var sim := Simulation.new()
	var p := _airborne_player(0, true) # gia lap da dung double jump tren khong
	p.y = -100
	p.vy = 200 # dang roi xuong, sap cham dat
	sim._step_vertical(p, _command(false))
	_check(p.grounded, "phai cham dat khi y vuot qua GROUND_Y trong luc roi")
	_check(not p.used_double_jump, "cham dat phai reset double jump")
