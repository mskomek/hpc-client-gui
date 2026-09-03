# ChatGPT Browser Prompt — GUI-FILE-003 Audit

GitHub repository: https://github.com/mskomek/hpc-client-gui
Branch: `develop`
Expected latest commit: `8dbeb41`

Bu görevi yalnızca audit/analiz olarak yap. Hiçbir dosyayı değiştirme, commit/push yapma ve parity statüsünü güncelleme.

Önce GitHub’daki gerçek branch, HEAD ve mevcut çalışma ağacını doğrula. Beklenen HEAD yoksa gerçek durumu raporla; varsayım yapma.

## İncelenecek kaynaklar

```text
src/hpc_gui/wx_local_files.py
src/hpc_gui/wx_remote_files_view.py
src/hpc_gui/wx_shell.py
src/hpc_gui/wx_transfer_workspace.py
src/hpc_gui/services/file_context_actions.py
src/hpc_gui/services/file_clipboard.py
src/hpc_gui/services/remote_move_history.py
src/hpc_gui/services/transfer_controller.py
src/hpc_gui/services/transfer_session_controller.py
src/hpc_gui/services/parity_matrix.py
docs/v2/V2_PARITY_STATUS.md
docs/v2/GUI_KEYBOARD_INTERACTION_CONTRACT.md
docs/v2/GUI_POINTER_INTERACTION_CONTRACT.md
src/hpc_gui/ui/widgets/local_dir_panel.py
src/hpc_gui/ui/widgets/remote_dir_panel.py
tests/test_wx_*.py
tests/test_transfer_*.py
```

## Kanıt standardı

Her maddeyi `PROVEN`, `PARTIAL`, `STRUCTURAL`, `MISSING` veya `NOT APPLICABLE` olarak işaretle. `PROVEN` yalnızca gerçek wx event → visible UI → adapter/controller → fake backend → completion akışıyla kullanılabilir. Source-string, policy veya doğrudan helper testi tek başına parity kanıtı değildir.

## Denetim kapsamı

Şunları gerçek test adı, dosya ve gözlenen sonuçla değerlendir:

- local/remote right-click: unselected row, multiselection, background ve keyboard context;
- none, one file, one directory, multi-file, multi-directory, mixed-selection action matrix;
- Open, Open With, Edit, Edit in New Window ve New Tab ayrımı;
- local/remote Rename, Delete, Copy, Cut/Move, Paste, New Folder ve failure recovery;
- remote Copy Path’ın system clipboard’a yazılması ve backend’e gitmemesi;
- remote Move history ve Ctrl+Z’nin son başarılı move’u geri alması;
- Ctrl+A/C/X/V/Z, Backspace, F2, F5 ve Delete keyboard akışları;
- `TransferItem → TransferSessionController → TransferController → backend` zinciri;
- conflict ask/overwrite/skip/rename/resume, progress, cancel ve session cleanup;
- backend/filesystem işlerinin GUI thread dışında çalışması;
- close-in-flight, navigate-in-flight, stale completion ve post-close error;
- reconnect sırasında tek operation’ın tek session snapshot kullanması;
- runtime English/Turkish context-menu label değişimi;
- gerçek wx stress sayıları ve ölçülen invariants.

Özellikle kanıtla: remote Paste no-op mu, Copy Path backend’e gidiyor mu, Ctrl+Z gerçekten move undo mu, conflict ask GUI kararına ulaşıyor mu, tamamlanan transfer session’ları temizleniyor mu ve stale callback kapalı frame’e erişiyor mu?

## Minimum stress sayıları

Gerçekten çalıştırılmış sayıları raporla; tahmin etme:

```text
right-click retarget: 200
local mutations: 100
remote mutations: 100
target switches: 200
navigate/completion races: 200
browser open/close: 50
blocked close-in-flight: 25
FILE transfer items: 100
unicode/space names: 50
```

Şu metrikleri ölçülmüş değerleriyle ver: wrong targets, stale UI overwrites, destroyed-control callbacks, leaked FILE workers, leaked wx windows, duplicate/lost transfers ve peak non-transfer mutation concurrency.

## Kontroller

Ortam destekliyorsa ayrı raporla:

```powershell
python -m pytest -q tests/test_wx_*.py --cache-clear
python -m pytest -q tests/test_transfer_concurrency.py tests/test_local_transfer_gate.py --cache-clear
python scripts/qt_removal_gate.py
```

Paketli wx smoke failure varsa tam çıktıyı raporla ve baseline olup olmadığını ayır. Windows testinden Linux/macOS runtime kanıtı çıkarma.

## Rapor formatı

Yanıtı şu başlıklarla üret:

```text
Repository state
Actual branch and HEAD
Current parity status
Proven behavior
Structural-only evidence
Missing real-wx evidence
Transfer lifecycle findings
Keyboard findings
Race/lifecycle findings
Stress counts and invariants
Exact remaining GUI-FILE-003 blockers
GUI-FILE-003 decision
Other current P0 blockers
Platform evidence
Final Qt gate
```

`GUI-FILE-003: COVERED` yalnızca tüm zorunlu kullanıcı akışları gerçek wx testleriyle kanıtlanmışsa yazılabilir; aksi halde `PARTIAL` kalmalıdır. Qt, PySide6, shiboken6 ve `DEFAULT_GUI_RUNTIME = "qt"` değiştirilmemelidir. Credential, password, private key, token veya belge içeriği raporlanmamalıdır. Audit sonunda `git status --short` temiz olmalıdır.
