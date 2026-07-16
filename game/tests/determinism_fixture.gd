class_name DeterminismFixture
extends RefCounted
## Input script cố định dùng chung bởi GameRoot (self-check khi chạy tương
## tác) và tests/determinism_test.gd (CI, D-008). Một nguồn duy nhất — sửa ở
## đây thì cả hai chỗ dùng đều nhất quán (DRY).

static func scripted_moves() -> Array[int]:
	var moves: Array[int] = []
	for _t in range(20):
		moves.append(1)
	for _t in range(10):
		moves.append(0)
	for _t in range(20):
		moves.append(-1)
	for _t in range(10):
		moves.append(0)
	return moves

static func initial_state() -> SimState:
	var s := SimState.new()
	var p := PlayerState.new()
	p.x = 100 * 1000
	s.players.append(p)
	return s

static func run_scripted(moves: Array[int]) -> int:
	var sim := Simulation.new()
	var s := initial_state()
	for move_x in moves:
		var cmd := Command.new()
		cmd.tick = s.tick
		cmd.player_id = 0
		cmd.move_x = move_x
		var commands: Array[Command] = [cmd]
		s = sim.step(s, commands)
	return StateHasher.hash_state(s)
