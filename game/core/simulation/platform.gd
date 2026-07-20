class_name Platform
extends RefCounted
## Platform một chiều (one-way), tĩnh. Đơn vị sim units (D-005).
## Chỉ chặn khi người chơi đang RƠI XUỐNG từ phía trên — không chặn khi
## nhảy xuyên từ dưới lên (xử lý trong Simulation, dựa vào y tick trước).

var x: int = 0
var y: int = 0
var width: int = 0

func contains_x(px: int) -> bool:
	return px >= x and px <= x + width
