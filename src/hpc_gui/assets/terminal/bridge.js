(() => {
  "use strict";
  const terminal = new Terminal({ convertEol: false, scrollback: 2000, cursorBlink: true });
  const fit = new FitAddon.FitAddon();
  terminal.loadAddon(fit);
  terminal.open(document.getElementById("terminal"));

  window.hpcFit = () => {
    fit.fit();
    if (window.hpcBridge) {
      window.hpcBridge.resize(terminal.cols, terminal.rows, terminal.element?.clientWidth || 0, terminal.element?.clientHeight || 0);
    }
  };
  window.hpcFocus = () => terminal.focus();
  window.hpcClear = () => terminal.clear();
  window.hpcSetFontSize = (size) => {
    terminal.options.fontSize = size;
    fit.fit();
  };

  new QWebChannel(qt.webChannelTransport, (channel) => {
    window.hpcBridge = channel.objects.terminal;
    window.hpcBridge.output.connect((text) => terminal.write(text));
    terminal.onData((data) => window.hpcBridge.send_input(data));
    window.hpcFit();
  });
})();
