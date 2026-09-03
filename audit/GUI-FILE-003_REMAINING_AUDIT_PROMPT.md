# GUI-FILE-003 Remaining Audit

Repository: `mskomek/hpc-client-gui`
Branch: `develop`

Bu çalışma yalnızca uzaktaki repository üzerinde analiz ve kanıt toplama içindir. Üretim kodu, testler ve parity metadata değiştirilmemelidir.

## Başlangıç

Önce çalıştır:

```text
git branch --show-current
git log -1 --oneline
git status --short
```

Gerçek HEAD’i raporla; `develop` ve en az `3d219c2` beklenir. Fark varsa gerçek durumu esas al.

## Amaç

`GUI-FILE-003` satırının güncel durumunu gerçek wx davranış kanıtlarıyla denetle. Source-string aramaları ve policy testleri tek başına parity kanıtı değildir.

İncele:

```text
src/hpc_gui/wx_local_files.py
src/hpc_gui/wx_remote_files_view.py
src/hpc_gui/wx_shell.py
src/hpc_gui/wx_transfer_workspace.py
src/hpc_gui/services/file_context_actions.py
src/hpc_gui/services/file_clipboard.py
src/hpc_gui/services/transfer_controller.py
src/hpc_gui/services/transfer_session_controller.py
src/hpc_gui/services/parity_matrix.py
tests/test_wx_*.py
tests/test_transfer_*.py
src/hpc_gui/ui/widgets/local_dir_panel.py
src/hpc_gui/ui/widgets/remote_dir_panel.py
docs/v2/GUI_KEYBOARD_INTERACTION_CONTRACT.md
docs/v2/GUI_POINTER_INTERACTION_CONTRACT.md
```

## Davranış kanıtı

Aşağıdaki maddeleri `PROVEN`, `PARTIAL`, `MISSING` veya `NOT APPLICABLE` olarak sınıflandır. Her satırda gerçek test adı, visible wx assertion, backend çağrısı ve thread/lifecycle kanıtını ver:

1. Local/remote right-click: unselected row, multiselection, background, keyboard context.
2. Local/remote selection cardinality ve action visibility.
3. Open, Open With, Edit, Edit in New Window ayrımı.
4. Local/remote Rename: success, cancel, invalid, conflict, backend error.
5. Local/remote Delete: single, multi, recursive directory, mixed selection, confirmation, failure.
6. Local/remote Copy, Cut/Move, Paste; background ve clicked-folder target.
7. Remote Copy Path’ın system clipboard’a yazılması ve backend’e gitmemesi.
8. Remote Move history ve `Ctrl+Z` ile son başarılı move undo.
9. Keyboard: Ctrl+A/C/X/V/Z, Backspace, F2, F5, Delete.
10. Transfer boundary: `TransferItem → TransferSessionController → TransferController → backend`.
11. Conflict ask/overwrite/skip/rename/resume kararlarının execution’ı değiştirmesi.
12. Transfer progress, user cancel, success/failure/cancel cleanup, shutdown cleanup.
13. Backend/filesystem mutation işlemlerinin GUI thread dışında çalışması.
14. Close-in-flight, navigate-in-flight, stale completion, post-close error.
15. Reconnect sırasında tek operasyonun tek session snapshot kullanması.
16. Runtime EN/TR context-menu label değişimi.
17. Gerçek wx event kullanan deterministic stress ve ölçülen metrikler.

Özellikle gerçek davranışla kontrol et: remote Paste no-op mu, Copy Path backend’e gidiyor mu, Ctrl+Z gerçekten move undo mu, conflict ask GUI kararına ulaşıyor mu, tamamlanan transfer session’ları temizleniyor mu, geç callback kapalı frame’e erişiyor mu, stale refresh yeni navigasyonu eziyor mu?

## Komutlar

Uygun mevcut dosyaları ayrı süreçlerde çalıştır:

```powershell
python -m pytest -q tests/test_wx_file_action_policy.py tests/test_wx_local_files.py tests/test_wx_remote_files.py tests/test_wx_remote_file_actions_behavior.py tests/test_wx_file_actions_behavior.py tests/test_wx_file_actions_lifecycle.py tests/test_wx_file_actions_stress.py tests/test_wx_file_transfer_integration.py tests/test_wx_remote_move_undo.py tests/test_wx_editor.py tests/test_wx_editor_window_parity.py tests/test_wx_remote_editor_flow.py tests/test_wx_editor_cross_view_actions.py tests/test_wx_shell.py --cache-clear
python -m pytest -q tests/test_transfer_concurrency.py tests/test_local_transfer_gate.py --cache-clear
python scripts/qt_removal_gate.py
```

Paketli wx smoke başarısızsa tam JSON çıktısını ve bunun FILE değişikliklerinden bağımsız olup olmadığını raporla. Qt gate’i değiştirme.

## Çıktı formatı

Şu bölümleri kullan:

```text
Repository state
Current parity state
Proven behavior
Partial behavior
Missing production behavior
Missing real-wx evidence
Transfer lifecycle evidence
Thread/lifecycle/race evidence
Stress counts and invariants
Exact remaining GUI-FILE-003 blockers
Smallest next implementation step
```

Kurallar: `GUI-FILE-003: COVERED` yalnızca tüm kullanıcı akışları gerçek wx testleriyle kanıtlanmışsa verilebilir. Test sayılarını çalıştırmadan tahmin etme. Credential, password, token, private key veya belge içeriği raporlama. Qt/PySide6/shiboken6 ve `DEFAULT_GUI_RUNTIME = "qt"` değiştirme. Audit sonunda `git status --short` temiz olmalıdır.
