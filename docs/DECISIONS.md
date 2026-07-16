# DECISIONS.md — Sổ quyết định đã khóa (dogfighter)

> Nguồn sự thật cho MỌI quyết định bất biến của dự án. Ngày lập: 2026-07-15.
> Cơ chế: Council deliberation 3 vòng (Torvalds 1.5× · Feynman · Aurelius, đồng thuận 3.5/3.5) + cross-review Claude/Codex trước đó. Chairman Codex fail (CLI hỏng) → coordinator tổng hợp.
> Quy tắc dùng: quyết định mới = append ID mới. Đảo ngược = đổi Trạng thái + ghi lý do, KHÔNG xóa. `LOCKED` chỉ mở lại khi điều kiện đảo ngược xảy ra và có bằng chứng. `REVIEW-AT-GATE` = chốt tại gate ghi kèm.

---

## D-001 · Engine — LOCKED
**Quyết định:** Godot 4.x stable. Pin phiên bản chính xác vào dòng dưới đây ngay khi cài; chỉ nâng version ở ĐẦU milestone, không nâng giữa chừng.
**Phiên bản pin:** `4.7.1.stable` (xác nhận 2026-07-15, góc dưới phải Godot editor)
**Lý do:** Editor tooling cho solo dev chưa có nền gamedev; native export đa nền tảng; một project cho Web + desktop.
**Điều kiện đảo ngược:** Milestone 0 time-box 1 tuần làm việc thực tế fail vì blocker chứng minh được (không export được target bắt buộc / không tách được sim khỏi scene tree / gamepad hoặc Web build không đạt tối thiểu dù cấu hình đúng) → quay lại TypeScript + PixiJS, mất đúng 1 tuần. "Godot còn lạ tay" KHÔNG phải blocker. Sau khi Movement Lab qua gate: đóng vĩnh viễn.

## D-002 · Ngôn ngữ — LOCKED
**Quyết định:** Typed GDScript cho toàn bộ game core. Không C#.
**Lý do:** Godot 4 chưa export project C# lên Web; Web demo là yêu cầu thật. Server/relay sau này dùng ngôn ngữ user giỏi (Go/TS/…) — không cần cùng ngôn ngữ với client.
**Điều kiện đảo ngược:** Godot hỗ trợ C# Web export ổn định VÀ có nhu cầu thật sự về C# — khi đó mới cân nhắc, không sớm hơn.

## D-003 · Renderer — LOCKED
**Quyết định:** Compatibility renderer (WebGL2) cho MỌI target (desktop + web).
**Lý do:** Parity tuyệt đối giữa web và native; một renderer để QA.
**Điều kiện đảo ngược:** Bằng chứng đo được rằng Compatibility không kham nổi nhu cầu render thật (chưa từng có dấu hiệu với game 2D scope này).

## D-004 · Kiến trúc simulation — LOCKED
**Quyết định:** Sim tất định 60 tick/s cố định; sim là GDScript thuần (`RefCounted`), KHÔNG kế thừa `Node`, không phụ thuộc scene tree. **Cấm trong sim:** engine physics (`move_and_slide`, `RigidBody2D`), `Area2D`/`RayCast2D` cho hit, `Tween`/`AnimationPlayer` ảnh hưởng gameplay, signal engine làm nguồn sự thật, `Time.*`/wall clock, `randf/randi` global. Renderer chỉ đọc snapshot + event list. Mọi input (local/bot/replay/remote) đi qua CÙNG một tick-command format. Animation contract: gameplay event (`spawn`/`hit`/`reload`/`ko`…) do sim thực thi đúng 1 lần ở tick xác định; renderer không tự phát event.
**Lý do:** Determinism/rollback/replay sống hay chết ở ranh giới này; đây cũng là nền cho test tự động.
**Điều kiện đảo ngược:** Không có. Đây là nguyên tắc nền của toàn dự án.

## D-005 · Determinism & toán integer — LOCKED
**Quyết định:** State authoritative là SỐ NGUYÊN: integer sub-pixel `1 px = 1000 sim units` (position, velocity, knockback, instability, timers); weight dạng permille; aim lượng tử 8 hướng qua bảng vector nguyên định trước (vd `(707,707)`) — không trig/sqrt trong sim (khoảng cách so bằng bình phương); mọi phép chia nguyên đi qua `fixed_math.gd` với rounding rule định nghĩa MỘT lần; PRNG seeded nằm trong snapshot (chỉ tồn tại nếu mechanic thật sự cần random); serialize theo canonical field order; FNV-1a hash mỗi 30 tick. Hash test phải phủ CẢ khác biệt platform LẪN engine-version bump (Dictionary iteration order là hành vi không được bảo đảm theo contract — đã kiểm chứng docs Godot; không dựa vào nó cho logic).
**Lý do:** Float chỉ sống ở renderer/camera/VFX. Integer loại bỏ cả lớp nghi ngờ desync và làm replay/rollback kiểm chứng được bằng máy.
**Điều kiện đảo ngược:** Không có cho nguyên tắc; giá trị số cụ thể (scale 1000, bảng aim) đổi được qua decision record mới.

## D-006 · Hệ thống tài liệu — LOCKED
**Quyết định:** (1) `docs/DECISIONS.md` (file này) = quyết định khóa. (2) `docs/roadmap-claude-final.md` = **roadmap điều hành canonical duy nhất** (bản ngắn, dùng hằng ngày). (3) `docs/roadmap-codex-final.md` = **acceptance handbook** — nguồn gate/criteria chi tiết khi viết spec từng milestone; không phải roadmap điều hành. (4) `design/specs/<milestone>.md` = task + acceptance của milestone hiện tại. (5) `docs/NOT-NOW.md` = backlog Later; cấm implement thẳng từ đây. (6) Hai bản gốc `roadmap-claude.md`/`roadmap-codex.md` chuyển vào `archive/` — tham khảo lịch sử. (7) **Charter `CLAUDE.md` mỏng phải được tái tạo ở root TRƯỚC khi bắt đầu M0** (trỏ về hierarchy này, kiến trúc bất biến D-004/D-005, rule skill D-015) — để mọi phiên agent sau không đi sai kiến trúc.
**Lý do:** Hiện có 4 roadmap và 2 bản tự nhận canonical — mầm loạn cho mọi phiên làm việc sau; charter đang nằm trong archive nên không phiên nào nạp được rule.
**Điều kiện đảo ngược:** Cấu trúc tài liệu đổi được qua decision record mới; nguyên tắc "một nguồn sự thật điều hành duy nhất" thì không.

## D-007 · Phần cứng dev & chiến lược platform — LOCKED
**Quyết định:** Máy dev duy nhất = **Mac mini M4 (macOS, arm64)** — được chấp nhận là đủ, KHÔNG phải blocker. Phân vai platform:
- **macOS native** = build dev/daily playtest (chạy trực tiếp, vòng lặp nhanh nhất). KHÔNG ship SKU macOS công khai trước khi có demand signal sau launch; build private đưa tay tester không cần notarization.
- **Web (desktop browser)** = kênh playtest external (greybox trước production art).
- **Windows x86_64 native, cross-export từ macOS** = sản phẩm Steam thương mại. Cross-export qua export templates dựng sẵn — không cần máy Windows để build; Steam không bắt buộc Authenticode.
- Linux/Steam Deck: sau khi Windows ổn định. macOS store SKU: chỉ khi dữ liệu đòi hỏi.
**Lý do:** Hội đồng 3.5/3.5: kiến trúc sim integer platform-độc-lập đã "trả lãi" đúng lúc này; ~90% lộ trình (M0–M8) không cần phần cứng Windows; rủi ro thật còn lại hẹp và muộn (GPU perf, input layer) — xử bằng gate, không bằng mua sắm.
**Điều kiện đảo ngược:** Tripwires tại D-009.

## D-008 · Gate Milestone 0 (THAY gate cũ "Windows build chạy trên máy/VM Windows") — LOCKED
**Quyết định:** M0 pass khi và chỉ khi:
1. CI export **Windows x86_64 artifact + Web build** tự động (headless Godot).
2. **Cross-OS determinism hash-match:** cùng fixed replay + seed chạy headless trên macOS và trên `windows-latest` (GitHub Actions, x86_64 thật) → FNV-1a hash trùng TỪNG tick. Đây là load-bearing test cho tính đúng.
3. **UTM smoke (free) BẮT BUỘC test lớp input:** boot build Windows x86_64 trong Windows-ARM/UTM trên M4 → launch + **controller enumeration + button mapping + input response**. Lớp HID/controller — không phải determinism — là rủi ro platform-specific thật của game controller-first; hash không bao giờ nhìn thấy nó. UTM smoke KHÔNG phải benchmark hiệu năng.
4. **Thí nghiệm hash-match chạy NGAY TUẦN ĐẦU của M0** — nó là thí nghiệm duy nhất xác nhận hoặc phá hủy toàn bộ kế hoạch platform; mọi thứ khác xếp sau nó.
**Lý do:** Gate cũ bất khả thi (không có máy Windows) và yếu hơn (mắt người nhìn VM không bắt được desync; CI hash bắt được). "Export thành công" là fact đóng gói; "sim state giống hệt" là fact toán học — chỉ cái sau là rủi ro thật ở M0.
**Điều kiện đảo ngược:** Không cần — gate này thay thế vĩnh viễn gate cũ trong roadmap/handbook (hai file kia coi như được amend bởi D-008).

**Ghi chú triển khai — xác minh thật trên máy 2026-07-17 (không phải suy đoán):**
- `export_presets.cfg` (Web + Windows) đã test export thật, ra file dùng được (`dogfighter.exe` ~112MB, `index.wasm` ~40MB) — xác nhận D-007 "cross-export không cần máy Windows" đúng trong thực tế, không chỉ lý thuyết.
- **Bẫy quan trọng cho CI:** `godot --headless --script <path>` KHÔNG tự resolve được `class_name` toàn cục nếu chưa import project lần nào — vì `.godot/global_script_class_cache.cfg` bị gitignore (đúng chuẩn), nên **luôn bị thiếu trên checkout CI sạch**. Hậu quả nguy hiểm: script load fail nhưng **Godot vẫn thoát exit code 0** — CI tưởng xanh dù test chưa hề chạy. Bắt buộc 2 lớp phòng thủ: (1) chạy `godot --headless --import` để prime cache TRƯỚC bất kỳ `--script` nào; (2) không chỉ tin exit code — `grep` xác nhận có dòng `HASH=` thật trong stdout. Cả hai đã đưa vào `.github/workflows/ci.yml`.
- FNV offset basis (`0xcbf29ce484222325`) viết bằng hex literal vượt `INT64_MAX` — GDScript báo lỗi parse thay vì tự wrap âm như nhiều ngôn ngữ khác. Dùng literal thập phân `-3750763034362895579` (cùng bit pattern, hợp lệ).

## D-009 · Chính sách chi tiêu — LOCKED
**Quyết định:** MỌI chi tiêu (tiền/phần cứng/dịch vụ) phải **signal-gated, không bao giờ calendar-driven**. Hôm nay: **$0**. Tripwires cụ thể:
1. M0 hash-match FAIL (macOS ↔ windows-latest lệch trên sim int-only) HOẶC UTM không chạy nổi build Compatibility renderer → mua/thuê NGAY một Windows x86_64 box để debug (mini-PC cũ ~$300 hoặc cloud theo giờ) — lúc đó $0-now mới là tự dối.
2. Từ M7 (closed demo) trở đi: Windows-only crash/bug không repro được qua VM/tester trong 2 tuần → thuê cloud Windows theo giờ/tuần.
3. **$100 Steam app fee** — trả tại M9 (Steam Playtest), không sớm hơn.
4. **$99/năm Apple Developer (notarization)** — CHỈ khi quyết định ship macOS công khai (D-007).
5. Parallels — chỉ khi UTM chứng minh không đủ cho nhu cầu smoke.
6. Perf trên Windows: **timing assertion MIỄN PHÍ** trên chính windows-latest runner của hash test (fire khi vượt frame budget) — thay thế hoàn toàn "perf spot-check trả tiền theo lịch" (đề xuất này đã bị hội đồng bác và người đề xuất tự rút).
**Lý do:** "Rẻ" không phải tiêu chí — "vô điều kiện" mới là vấn đề; chi tiêu theo lịch là fear-hedge, roadmap chết vì gates không ai nhớ lý do.
**Điều kiện đảo ngược:** Từng tripwire ở trên chính là điều kiện mở két tương ứng.

## D-010 · MVP scope — LOCKED
**Quyết định:** Mirror match: 1 fighter, 1 súng, 1 projectile, 1 arena ≤3 platform, 3 stocks, local 2P + 1 bot training, keyboard + controller (controller-first, thiết kế nút trước). Greybox placeholder cho tới khi qua fun-gate M2 — **placeholder = hình khối HOẶC asset free bên thứ ba** (vd Kenney.nl/itch.io CC0), miễn phí chọn cách nào giúp code/test nhanh nhất. Asset thứ ba bất kỳ license nào được dùng thoải mái cho test nội bộ (không phát hành); **PHẢI kiểm tra lại license thương mại trước khi cân nhắc giữ trong bản Steam ship** — placeholder không tự động thành production asset. KHÔNG có: dodge/parry/ledge-grab/DI (movement + recoil LÀ phòng thủ MVP), touch control, 4-player, account/ranked/progression. Trần Steam Playtest: **2 fighter + 1 arena tốt**. 4 fighter/2 arena = trần dài hạn, vượt phải có decision record (dữ liệu + chi phí + phần bị cắt).
**Lý do:** Câu hỏi duy nhất đáng trả lời trước tiên: "súng-knockback có vui không" — mọi thứ khác là nhiễu.
**Điều kiện đảo ngược:** Fun-gate M2 cho thấy người bị dồn góc không có lựa chọn hợp lý → mở thiết kế 1 cơ chế phòng thủ original (decision record mới).
**Placeholder pack đang dùng** (tất cả trong `game/assets/external/`, license đọc trực tiếp từ file kèm pack 2026-07-16, không phải suy đoán):

| Thư mục | Nguồn | License | Ghi công | Dùng cho |
|---|---|---|---|---|
| `tiny-swords/` | Tiny Swords Free Pack, pixelfrog-assets | Thương mại OK | Không cần | Archer (`Shoot`+`Arrow.png`) test projectile; Warrior test melee |
| `kenney_pixel-platformer/` | Kenney, kenney.nl | **CC0** | Không cần (khuyến khích) | Tileset/platform cho Movement Lab (M1) |
| `ForestGunner_by_RockyMullet_v1.0/` | RockyMullet, itch.io | CC-BY 4.0 | **Bắt buộc** credit "RockyMullet" nếu còn tới bản ship | Gunner (idle/walk/hurt/crouch/fall/rise) + shot FX + platform tileset riêng |
| `craftpix-net-529677-free-wizard-sprite-sheets-pixel-art/` | CraftPix.net | Royalty-free thương mại (chính sách freebie CraftPix) | Không thấy bắt buộc, độ chắc chắn thấp hơn 3 pack trên — tự kiểm tra lại trước khi ship | Fire Wizard/Lightning Mage/Wanderer Magican — Light Ball/Charge test "đạn phép" |

Tất cả an toàn dùng test nội bộ vô điều kiện. **Trước khi ship**, việc cần làm: (1) bỏ hẳn nếu đã có art gốc thay thế (khuyến nghị, theo D-015), hoặc (2) nếu còn giữ, thêm màn Credits ghi rõ RockyMullet (bắt buộc) + Kenney/pixelfrog/CraftPix (tùy chọn nhưng nên làm).

## D-011 · Combat core — REVIEW-AT-GATE (Gate B, sau Knockback Lab M2)
**Quyết định:** A/B test bắt buộc: Mode A (fixed knockback — vị trí quyết định ring-out) vs Mode B (escalating instability — trận leo thang, hiển thị rõ trên HUD). Chọn bằng playtest note với 5 câu hỏi chuẩn (hiểu vì sao văng? trận lê thê? người thua có cửa hồi? hit đầu còn nghĩa? có đổi vị trí theo instability?) — KHÔNG chọn bằng tranh luận. Recoil lên người bắn = candidate bản sắc riêng; giữ CHỈ nếu tester hiểu và dùng được sau ≤3 trận không cần tutorial dài.

**Mô hình stats — bổ sung 2026-07-16:** Nhân vật và súng là **2 Resource độc lập, compose tại combat resolution**, không phải súng gắn cứng vào nhân vật. `CharacterData` (weight_pct, move_speed, jump stats — không có health) × `WeaponData` (base_knockback, fire_rate_ticks, projectile_speed, recoil_impulse, ammo) — công thức D-011 gốc đã ngầm làm đúng việc này (`weight_pct` từ nhân vật, `knockback/weaponMult` từ súng). Fighter trong sim = cặp `{character, weapon}` bất kỳ, đổi 1 bên không đụng file ảnh nào. **Ràng buộc bắt buộc để giữ art tuyến tính (N+M) thay vì nhân (N×M):** animation `shoot` dùng CHUNG cho mỗi nhân vật bất kể súng nào — súng chỉ hiện qua icon nhỏ gắn tay/nòng + `projectile_texture` + số liệu recoil/rung màn hình, KHÔNG được thiết kế pose "shoot" riêng theo từng súng.
**Lý do:** Compose theo data giữ balance/feel-tuning hoàn toàn tách khỏi art (đúng D-004); ràng buộc animation dùng chung ngăn asset phình theo tổ hợp nhân vật×súng khi roster mở rộng.
**Lý do:** Cơ chế lõi phải được chọn bởi dữ liệu người chơi, không bởi mentor nào (Claude hay Codex).

## D-012 · Art pipeline — REVIEW-AT-GATE (Gate C, tại art proof) · Sửa 2026-07-15
**Quyết định:** Đổi hướng ưu tiên sang **pixel art 2 pha**, dùng **Aseprite** làm công cụ hoàn thiện chính (~$20 hoặc build free từ source; export sprite sheet + JSON khớp thẳng `frameCount/fps/events` của animation contract, không cần converter riêng). Hướng phải + mirror trái, pivot chân giữa (giữ nguyên từ bản cũ). Sản xuất thật vẫn đợi qua fun-gate M2 (không đổi D-010) — pha A dùng để LUYỆN công cụ song song với M0–M2 bằng sprite nháp không-canon, không phải để mở khóa production sớm.

**AI generation — cập nhật (nới so với bản gốc):** Concept/reference/marketing: tự do. **Draft/base cho frame sản xuất:** ĐƯỢC PHÉP dùng công cụ AI pixel-sprite chuyên dụng (PixelLab/PixelBox/Sprite-AI hoặc tương đương — loại tự sinh nhiều hướng/frame nhất quán từ 1 nhân vật gốc), với điều kiện MỌI frame phải qua tay chỉnh trong Aseprite trước khi vào game: canh lưới pixel chuẩn, khóa palette cố định, chỉnh pivot đúng, đúng frame count theo bảng budget bên dưới. **Vẫn cấm:** xuất thẳng output AI vào game chưa qua bước làm sạch tay; dùng AI tạo hẳn 50+ frame độc lập không qua công cụ chuyên nhất quán (rủi ro lệch mặt/tỷ lệ giữa frame của gen chung chung vẫn còn thật).

- **Pha A — LF2-tier (nhân vật đầu tiên, học nhanh):** canvas làm việc 64×64px, nhân vật cao ~48–56px trong khung. Tô màu phẳng, palette giới hạn 8–16 màu/nhân vật, gần như không anti-alias. Frame budget rút gọn mạnh so với bản 3D-render cũ (~25–35 frame/fighter, không phải 57):
  | State | Frame | State | Frame |
  |---|---:|---|---:|
  | idle | 2–4 | shoot/attack | 3–5 |
  | walk/run | 4–6 | hurt | 1–2 |
  | jump/rise/fall/land | 1–2 mỗi state | launch/tumble | 2–3 |
  | | | ko | 3–5 |
  Kỹ năng cần thật ở tier này là **animation principles** (pose/timing), không phải rendering — silhouette phải đọc được ngay vì không có chi tiết để che lỗi.
- **Pha B — Dead Cells/Katana Zero-tier (polish, sau khi fun-gate M2 pass + tay đã quen Pha A):** nâng canvas lên ~96–128px, thêm frame cho mượt, giữ nguyên silhouette/thiết kế đã chứng minh từ Pha A (vẽ lại độ nét cao hơn, không redesign từ đầu — tái dùng chứ không lãng phí công Pha A).
**Lý do:** Painted/vector (kiểu Brawlhalla) đòi hỏi kỹ năng illustration + skeletal rig chuyên nghiệp, khó đạt hơn pixel với người mới, và không khớp animation contract frame-rời-rạc hiện có. LF2-tier là mức pixel dễ đạt nhất cho người mới nhưng một mình thì đọc "quá retro" trên Steam 2026 — nâng cấp lên Dead Cells-tier sau khi chứng minh gameplay giải quyết rủi ro thương mại mà không phá kỷ luật "không đầu tư art lớn trước fun-gate".

## D-013 · Netcode ladder — LOCKED (thứ tự) · Gate D điều khiển thời điểm
**Quyết định:** Online CHỈ mở sau gate Replay & Determinism hardening (golden replay suite + soak test + snapshot/restore chuẩn). Trình tự: transport abstraction → WebSocket relay (room/forward input, không authoritative) → delay-based lockstep làm **diagnostic stepping stone** (không phải trải nghiệm online công bố chính thức nếu còn stall) → snapshot ring buffer → prediction → rollback/resim + network simulator (0/40/80/120/150ms, jitter, loss). Desync report = replay + first divergent hash. Steam Remote Play Together = streaming fallback cho local MP (host cài, khách nhận stream) — KHÔNG thay rollback, KHÔNG có web cross-play.
**Lý do:** Rollback là phần khó nhất dự án; nền tảng chưa chứng minh tất định thì netcode chỉ là nợ.

## D-014 · Timeline framing — LOCKED
**Quyết định:** Forecast 12–24 tháng tới Steam Playtest (2 fighter); khoảng trung thực 15–30 tháng @ ~10h/tuần. **Gates quyết định đi tiếp, không phải lịch.** Hoàn thành sớm → qua gate sớm; không thêm scope để lấp thời gian. Nhịp bắt buộc: mỗi 2 tuần một build chạy được + clip + playtest note.
**Lý do:** Con số là dự báo; kỷ luật gate là thứ có giá trị thật (bài học Stardew: làm đều + giữ scope, không phải nhồi mọi hệ thống trong một năm).

## D-015 · IP & character design — LOCKED
**Quyết định:** Quy ước thể loại (knockback, ring-out, stocks, one-way platform, hitstun) dùng tự do. CẤM sao chép tên/nhân vật/art/map layout/số liệu/move-list của bất kỳ game cụ thể nào. Mọi lần tạo/sửa nhân vật BẮT BUỘC qua skill `original-pvp-character-design` và lưu `character-spec.json` hoàn chỉnh vào `design/characters/`.
**Lý do:** Original ở hệ thống và visual world là ranh giới pháp lý lẫn bản sắc thương mại.

---

## Nhật ký đảo ngược / sửa đổi

| Ngày | Decision | Thay đổi | Bằng chứng |
|---|---|---|---|
| — | — | (chưa có) | — |
