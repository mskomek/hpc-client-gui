# Terminal module ownership

| Area | Owner |
| --- | --- |
| SSH authentication, PTY creation, byte decoding, complete writes, resize | `src/hpc_gui/ssh/client.py` |
| SSH-to-Qt terminal adapter | `src/hpc_gui/services/terminal_bridge.py` |
| xterm page, WebChannel, focus, font, find, clear | `src/hpc_gui/ui/widgets/terminal_widget.py` |
| Terminal status/actions presentation | `src/hpc_gui/ui/widgets/terminal_header.py` |
| Profile/connection orchestration and page layout | `src/hpc_gui/ui/widgets/login_widget.py` |
| File transfer queue/protocol behavior | `src/hpc_gui/services/transfer_controller.py` and SSH/SFTP services |
| Slurm parsing and job operations | `src/hpc_gui/services/` Slurm backends |

Future changes should follow this map. The header owns no SSH/profile logic;
the bridge does not import LoginWidget; LoginWidget remains the connection
orchestrator rather than an ANSI/VT renderer.
