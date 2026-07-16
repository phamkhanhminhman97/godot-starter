extends SceneTree
## Test M0 (D-008): cùng input script chạy 2 lần phải cho cùng hash mỗi tick.
## Chạy headless, không cần scene/window:
##   godot --headless --script res://tests/determinism_test.gd
## LƯU Ý: project phải được import ít nhất 1 lần trước đó (cache
## .godot/global_script_class_cache.cfg phải tồn tại) để class_name toàn cục
## resolve được — trên CI/fresh checkout, chạy `godot --headless --import`
## (hoặc mở editor 1 lần) trước bước này. Xem .github/workflows/ci.yml.
## Exit code 0 = pass, 1 = fail — CI đọc exit code để quyết định xanh/đỏ.
## In "HASH=<int>" ra stdout để workflow tách hash so sánh giữa các OS.

func _init() -> void:
	var moves := DeterminismFixture.scripted_moves()
	var hash_a := DeterminismFixture.run_scripted(moves)
	var hash_b := DeterminismFixture.run_scripted(moves)

	if hash_a != hash_b:
		printerr("[determinism] FAIL - hash lech trong cung 1 lan chay: %d != %d" % [hash_a, hash_b])
		quit(1)
		return

	print("[determinism] PASS - %d tick" % moves.size())
	print("HASH=%d" % hash_a)
	quit(0)
