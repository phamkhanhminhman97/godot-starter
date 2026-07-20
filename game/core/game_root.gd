extends Node2D
## Driver node duy nhất của sim (D-004). Gọi Simulation.step() trong
## _physics_process; renderer (Box + platform rects) chỉ đọc snapshot, không
## quyết định gì. Input tạm dùng action có sẵn của Godot: ui_left/ui_right/
## ui_accept (nhảy)/ui_down (fast-fall + drop-through) — chưa cấu hình
## controller riêng (việc của bước sau).

const GROUND_SCREEN_Y: float = 400.0 # chỉ để vẽ, không thuộc sim
const ARENA_PATH: String = "res://data/arenas/lab.json"
const PLATFORM_COLOR: Color = Color(0.35, 0.55, 0.4, 1)
const PLATFORM_THICKNESS_PX: float = 8.0

var simulation: Simulation
var state: SimState

@onready var box: ColorRect = $Box

func _ready() -> void:
	simulation = Simulation.new()
	simulation.platforms = ArenaLoader.load_platforms(ARENA_PATH)
	state = DeterminismFixture.initial_state()
	_spawn_platform_visuals()

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

## Platform tĩnh — vẽ 1 lần lúc _ready, không cần cập nhật mỗi tick vì không
## di chuyển. Renderer thuần túy: đọc simulation.platforms, không quyết định
## va chạm (va chạm đã tính xong bên trong Simulation).
func _spawn_platform_visuals() -> void:
	for p in simulation.platforms:
		var rect := ColorRect.new()
		rect.color = PLATFORM_COLOR
		rect.position = Vector2(float(p.x) / 1000.0, GROUND_SCREEN_Y + float(p.y) / 1000.0 - PLATFORM_THICKNESS_PX)
		rect.size = Vector2(float(p.width) / 1000.0, PLATFORM_THICKNESS_PX)
		add_child(rect)
