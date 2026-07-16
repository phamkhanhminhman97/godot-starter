extends Node2D
## Driver node duy nhất của sim (D-004). Gọi Simulation.step() trong
## _physics_process; renderer (Box) chỉ đọc snapshot, không quyết định gì.
## Input tạm dùng action có sẵn của Godot: ui_left/ui_right/ui_accept (nhảy)/
## ui_down (fast-fall) — chưa cấu hình controller riêng (việc của Phần 1 sau).

const GROUND_SCREEN_Y: float = 400.0 # chỉ để vẽ, không thuộc sim

var simulation: Simulation
var state: SimState

@onready var box: ColorRect = $Box

func _ready() -> void:
	simulation = Simulation.new()
	state = DeterminismFixture.initial_state()

func _physics_process(_delta: float) -> void:
	var cmd := Command.new()
	cmd.tick = state.tick
	cmd.player_id = 0
	if Input.is_action_pressed("ui_right"):
		cmd.move_x += 1
	if Input.is_action_pressed("ui_left"):
		cmd.move_x -= 1
	cmd.jump = Input.is_action_pressed("ui_accept")
	cmd.drop = Input.is_action_pressed("ui_down")

	state = simulation.step(state, [cmd])

	var player := state.players[0]
	box.position.x = float(player.x) / 1000.0
	box.position.y = GROUND_SCREEN_Y + float(player.y) / 1000.0 - box.size.y
