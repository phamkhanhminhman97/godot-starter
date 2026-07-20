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
	_test_platform_landing_from_above()
	_test_platform_pass_through_from_below()
	_test_drop_through_clears_platform()
	_test_resting_on_platform_stays_multiple_ticks()
	_test_drop_through_lands_on_unrelated_lower_platform()

	var total := 12
	if failures.is_empty():
		print("[movement] PASS - %d/%d test" % [total, total])
		quit(0)
	else:
		for f in failures:
			printerr("[movement] FAIL - %s" % f)
		quit(1)

func _check(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)

func _command(jump: bool = false, drop: bool = false) -> Command:
	var cmd := Command.new()
	cmd.jump = jump
	cmd.drop = drop
	return cmd

func _one_platform_sim() -> Simulation:
	var sim := Simulation.new()
	var p := Platform.new()
	p.x = 0
	p.width = 10000
	p.y = -50000
	sim.platforms = [p]
	return sim

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

func _test_platform_landing_from_above() -> void:
	var sim := _one_platform_sim()
	var p := PlayerState.new()
	p.grounded = false
	p.x = 5000 # trong be rong platform (0..10000)
	p.y = -50500 # ngay tren mat platform (-50000)
	p.vy = 1000 # dang roi xuong, du de vuot qua mat platform trong 1 tick
	sim._step_vertical(p, _command(false))
	_check(p.grounded and p.on_platform,
		"roi tu tren xuong dung x-range phai dap len platform (grounded=%s on_platform=%s)" % [p.grounded, p.on_platform])
	_check(p.y == -50000, "y phai khop dung mat platform sau khi dap (got=%d)" % p.y)
	_check(p.vy == 0, "vy phai ve 0 sau khi dap dat platform")

func _test_platform_pass_through_from_below() -> void:
	var sim := _one_platform_sim()
	var p := PlayerState.new()
	p.grounded = false
	p.x = 5000
	p.y = -49000 # duoi mat platform (-50000), tuc dang o duoi
	p.vy = -2000 # dang bay LEN, vuot qua mat platform trong 1 tick
	sim._step_vertical(p, _command(false))
	_check(not p.grounded and not p.on_platform,
		"nhay xuyen tu duoi len KHONG duoc chan boi platform (grounded=%s)" % p.grounded)
	# vy bi trong luc lam giam bot ngay trong tick nay (-2000+GRAVITY=-1660), nen
	# khong hard-code y ky vong — chi can xac nhan: (1) van con AM (tiep tuc di
	# LEN qua khoi platform, khong bi chan lai o mat -50000), (2) dung dung cong
	# thuc gravity-truoc-roi-integrate ma _advance_vertical_velocity ap dung.
	var expected_vy := Simulation.GRAVITY + (-2000)
	_check(p.vy == expected_vy,
		"trong luc phai cong vao vy ngay tick nay (got=%d, ky vong %d)" % [p.vy, expected_vy])
	_check(p.y == -49000 + expected_vy,
		"y phai = y truoc + vy DA cong trong luc (got=%d, ky vong %d)" % [p.y, -49000 + expected_vy])

func _test_drop_through_clears_platform() -> void:
	var sim := _one_platform_sim()
	var p := PlayerState.new()
	p.grounded = true
	p.on_platform = true
	p.x = 5000
	p.y = -50000 # dang dung yen tren platform
	p.vy = 0

	sim._step_vertical(p, _command(true, true)) # bam nhay + giu xuong cung tick (drop=true -> fast-fall, co the vuot qua platform ngay tick nay nen drop_through_platform co the da tu don ve null luon, khong assert field noi bo o day)
	_check(not p.grounded and not p.on_platform,
		"drop-through phai roi platform ngay tick do (grounded=%s on_platform=%s)" % [p.grounded, p.on_platform])

	for _i in range(20):
		sim._step_vertical(p, _command(false, false))
		_check(not p.on_platform,
			"khong duoc dinh lai vao platform vua xuyen qua o bat ky tick nao sau do (on_platform=%s, y=%d)" % [p.on_platform, p.y])

	_check(p.y > -50000, "phai roi han xuong duoi mat platform cu (got=%d, ky vong > -50000)" % p.y)

## Bug 1 (review đối kháng bắt được, đã sửa): dùng "<" thay vì "<=" khi so
## sánh crosses khiến người đứng yên trên platform rơi xuyên ngay sau 1 tick
## không bấm gì — vì y đã bằng đúng platform.y, tick sau prev_y không còn
## "nhỏ hơn thật sự" nên coi như không chạm nữa. Test cũ chỉ gọi
## _step_vertical 1 lần nên không lộ ra bug này.
func _test_resting_on_platform_stays_multiple_ticks() -> void:
	var sim := _one_platform_sim()
	var p := PlayerState.new()
	p.grounded = false
	p.x = 5000
	p.y = -50500
	p.vy = 1000
	sim._step_vertical(p, _command(false)) # dap len lan dau
	_check(p.grounded and p.on_platform, "phai dap len platform dung lan dau")

	for i in range(10):
		sim._step_vertical(p, _command(false)) # dung yen, khong bam gi ca, 10 tick lien
		_check(p.grounded and p.on_platform,
			"phai o LAI tren platform sau %d tick khong bam gi (grounded=%s on_platform=%s y=%d)" % [i + 1, p.grounded, p.on_platform, p.y])
	_check(p.y == -50000, "y phai giu nguyen dung mat platform sau nhieu tick dung yen (got=%d)" % p.y)

## Bug 2 (review đối kháng bắt được, đã sửa): cơ chế cũ dùng 1 bộ đếm tick
## chung cho drop-through, vô tình vô hiệu hóa va chạm với TOÀN BỘ platform
## trong cửa sổ đó — nếu có platform khác ngay bên dưới platform đang xuyên,
## người chơi sẽ xuyên luôn qua nó dù không hề định vậy. Sửa bằng cách chỉ
## loại trừ ĐÚNG platform đang được xuyên qua (so sánh theo reference).
func _test_drop_through_lands_on_unrelated_lower_platform() -> void:
	var sim := Simulation.new()
	var upper := Platform.new()
	upper.x = 0
	upper.width = 10000
	upper.y = -50000
	var lower := Platform.new()
	lower.x = 0
	lower.width = 10000
	lower.y = -20000
	sim.platforms = [upper, lower]

	var p := PlayerState.new()
	p.grounded = true
	p.on_platform = true
	p.x = 5000
	p.y = -50000
	p.vy = 0

	sim._step_vertical(p, _command(true, true)) # xuyen qua platform TREN

	var landed_on_lower := false
	for _i in range(20):
		sim._step_vertical(p, _command(false, false))
		if p.on_platform and p.y == lower.y:
			landed_on_lower = true
			break

	_check(landed_on_lower,
		"xuyen qua platform TREN xong phai dap BINH THUONG len platform DUOI khong lien quan (got y=%d on_platform=%s)" % [p.y, p.on_platform])
