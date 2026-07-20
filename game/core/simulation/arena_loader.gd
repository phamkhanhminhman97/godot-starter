class_name ArenaLoader
extends RefCounted
## Đọc file arena JSON (tọa độ trong file là PIXEL cho dễ thiết kế tay; quy
## đổi sang sim units — nhân 1000, D-005 — ngay khi load, sim không bao giờ
## thấy số pixel). Đọc file qua FileAccess — I/O thuần, không cần Node,
## không vi phạm D-004.

static func load_platforms(path: String) -> Array[Platform]:
	var platforms: Array[Platform] = []
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("ArenaLoader: khong mo duoc file %s (loi=%s)" % [path, FileAccess.get_open_error()])
		return platforms

	var parsed = JSON.parse_string(file.get_as_text())
	file.close()

	if typeof(parsed) != TYPE_DICTIONARY or not parsed.has("platforms"):
		push_error("ArenaLoader: file %s khong dung dinh dang (thieu key 'platforms')" % path)
		return platforms

	for entry in parsed["platforms"]:
		var p := Platform.new()
		p.x = int(entry["x"]) * 1000
		p.y = int(entry["y"]) * 1000
		p.width = int(entry["width"]) * 1000
		platforms.append(p)

	return platforms
