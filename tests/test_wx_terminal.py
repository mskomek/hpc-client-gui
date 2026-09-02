from hpc_gui.wx_terminal import TerminalModel


def test_terminal_control_codes_resize_find_clear_and_font():
    sent, sizes = [], []
    model = TerminalModel(sent.append, lambda columns, rows: sizes.append((columns, rows)))
    assert model.key_input("C") == "\x03"
    assert model.key_input("D") == "\x04"
    assert model.key_input("Z") == "\x1a"
    assert model.key_input("C", shift=True) == "copy"
    assert model.resize(800, 360) == type(model.resize(800, 360))(100, 20)
    model.receive("hello ANSI\x1b[31merror")
    assert model.find("error") >= 0 and sizes[-1] == (100, 20)
    model.change_font_size(-20)
    assert model.font_size == 6
    model.clear()
    assert model.text == ""


def test_wx_terminal_keeps_ssh_renderer_optional():
    source = open("src/hpc_gui/wx_terminal.py", encoding="utf-8").read()
    assert "from PySide6" not in source and "import wx" in source
    assert "ssh.send_shell_input" in source and "ssh.resize_shell_pty" in source
