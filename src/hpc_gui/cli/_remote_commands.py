from __future__ import annotations
import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import CLIConnectionError, CLISession
from ._shared import _emit, _emit_remote_result, _local_sha256, _validate_remote_tokens

def _run_edit(args: argparse.Namespace) -> int:
    session = None
    temporary = None
    try:
        session = CLISession.open(args)
        before = session.files.sha256(args.remote_path)
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.basename(args.remote_path))
        temporary = handle.name
        handle.close()
        session.files.download(args.remote_path, temporary)
        editor = args.editor or os.environ.get("TRUBA_EDITOR") or os.environ.get("EDITOR")
        if not editor or "\x00" in editor:
            raise RuntimeError("No editor configured; use --editor PROGRAM or set TRUBA_EDITOR.")
        command = shlex.split(editor, posix=False)
        result = subprocess.run([*command, temporary], check=False)
        if result.returncode:
            raise RuntimeError(f"Editor exited with code {result.returncode}.")
        if _local_sha256(temporary) == before:
            _emit({"remote_path": args.remote_path, "changed": False, "status": "unchanged"}, output_format=args.format, quiet=args.quiet)
            return ExitCode.SUCCESS
        if session.files.sha256(args.remote_path) != before:
            raise RuntimeError("Remote file changed while it was being edited; upload was refused.")
        session.files.upload(temporary, args.remote_path)
        if args.verify and session.files.sha256(args.remote_path) != _local_sha256(temporary):
            raise RuntimeError("Remote edit verification failed: uploaded content does not match.")
        _emit({"remote_path": args.remote_path, "changed": True, "status": "updated"}, output_format=args.format, quiet=args.quiet)
        return ExitCode.SUCCESS
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(f"Remote edit failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass

def _run_remote_command(args: argparse.Namespace, command: str) -> int:
    session = None
    try:
        session = CLISession.open(args)
        if session.ssh is None:
            raise CLIConnectionError("This command requires --transport sftp.")
        return _emit_remote_result(*session.ssh.run(command, timeout_s=args.timeout), args)
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    except Exception as exc:
        emit_error(f"Remote command failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()

def _run_sh(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    try:
        _validate_remote_tokens(command)
        return _run_remote_command(args, shlex.join(command))
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE

def _run_script(args: argparse.Namespace) -> int:
    tokens = ["bash", args.remote_script, *args.arguments]
    try:
        _validate_remote_tokens(tokens)
        return _run_remote_command(args, shlex.join(tokens))
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE

def _shell_channel_is_active(channel) -> bool:
    return channel is not None and not getattr(channel, "closed", False)

def _run_terminal(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        emit_error("terminal requires an interactive terminal.", exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    session = None
    terminal_started = False
    try:
        profile = str(getattr(args, "profile", None) or "default profile")
        print(
            f"Connecting to {profile}; authenticating and opening the remote terminal...",
            file=sys.stderr,
            flush=True,
        )
        session = CLISession.open(args)
        if session.ssh is None:
            raise CLIConnectionError("This command requires --transport sftp.")
        session.ssh.resize_shell_pty(args.cols, args.rows)
        from hpc_gui.cli.terminal_input import terminal_key_reader

        print(
            "SSH connected. Remote terminal is ready; use Ctrl+Enter for dialog buttons, Ctrl+C to close.",
            file=sys.stderr,
            flush=True,
        )
        with terminal_key_reader() as read_key:
            terminal_started = True
            while True:
                key = read_key()
                if key == "\x03":
                    print("Closing remote terminal...", file=sys.stderr, flush=True)
                    break
                if key and not session.ssh.send_shell_input(key):
                    break
                if not key and not _shell_channel_is_active(
                    getattr(session.ssh, "_shell_channel", None)
                ):
                    break
        return ExitCode.SUCCESS
    except KeyboardInterrupt:
        print("Terminal connection cancelled.", file=sys.stderr, flush=True)
        return 130
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(f"Terminal failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()
        if terminal_started and sys.stdout.isatty():
            # Remote full-screen programs can leave the local console in an
            # alternate screen or hide its cursor when the SSH channel closes.
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l\r\n")
            sys.stdout.flush()


def _run_interactive(args: argparse.Namespace, dispatch) -> int:
    if args.format == "json" or not sys.stdin.isatty():
        emit_error("interactive requires a text-mode terminal.", exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    while True:
        try:
            line = input("hpc> ")
        except EOFError:
            return ExitCode.SUCCESS
        if line.strip().lower() in {"exit", "quit"}:
            return ExitCode.SUCCESS
        if not line.strip():
            continue
        try:
            nested = shlex.split(line)
        except ValueError as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            continue
        if nested[:1] == ["interactive"]:
            print("interactive cannot be nested", file=sys.stderr)
            continue
        dispatch(nested)
