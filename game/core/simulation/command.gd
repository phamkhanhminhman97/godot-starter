class_name Command
extends RefCounted
## Input command theo tick — hình dạng cố định theo design/specs/movement-lab.md.
## Local player, bot, replay, remote player đều tạo ra Command cùng dạng này (D-004).

var tick: int = 0
var player_id: int = 0
var move_x: int = 0 # -1 | 0 | 1
var jump: bool = false
var drop: bool = false
