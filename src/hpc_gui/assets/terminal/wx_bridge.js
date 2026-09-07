(() => {
  "use strict";

  const terminal = new Terminal({
    convertEol: false,
    scrollback: 2000,
    cursorBlink: true,
    fontFamily: "Cascadia Code, Consolas, 'Courier New', monospace",
    fontSize: 14,
    allowTransparency: false,
  });
  const fit = new FitAddon.FitAddon();
  terminal.loadAddon(fit);
  const el = document.getElementById("terminal");
  terminal.open(el);

  function postToPython(msg) {
    const data = JSON.stringify(msg);
    try {
      if (window.hpc && window.hpc.postMessage) {
        window.hpc.postMessage(data);
        return;
      }
    } catch (e) {}
    try {
      if (window.chrome && window.chrome.webview && window.chrome.webview.postMessage) {
        window.chrome.webview.postMessage(data);
        return;
      }
    } catch (e) {}
    try {
      if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.hpc) {
        window.webkit.messageHandlers.hpc.postMessage(data);
        return;
      }
    } catch (e) {}
    // Fallback for wx message handler via AddScriptMessageHandler('hpc')
    try {
      if (window.wx_msg && window.wx_msg.postMessage) {
        window.wx_msg.postMessage(data);
        return;
      }
    } catch (e) {}
  }

  window.hpcWrite = (data) => {
    try {
      terminal.write(data);
    } catch (e) {}
  };

  window.hpcClear = () => {
    try {
      terminal.clear();
    } catch (e) {}
  };

  window.hpcFocus = () => {
    try {
      terminal.focus();
    } catch (e) {}
  };

  window.hpcSetFontSize = (size) => {
    try {
      terminal.options.fontSize = size;
      fit.fit();
      postToPython({
        type: "resize",
        cols: terminal.cols,
        rows: terminal.rows,
        pixelWidth: terminal.element ? terminal.element.clientWidth : 0,
        pixelHeight: terminal.element ? terminal.element.clientHeight : 0,
      });
    } catch (e) {}
  };

  window.hpcFit = () => {
    try {
      fit.fit();
      postToPython({
        type: "resize",
        cols: terminal.cols,
        rows: terminal.rows,
        pixelWidth: terminal.element ? terminal.element.clientWidth : 0,
        pixelHeight: terminal.element ? terminal.element.clientHeight : 0,
      });
    } catch (e) {}
  };

  // Input: xterm is authority for all keys, including Ctrl, navigation, Unicode, paste
  terminal.onData((data) => {
    postToPython({ type: "input", data: data });
  });

  // Resize observer: when WebView resizes, fit and notify
  let resizeTimer = null;
  const scheduleFit = () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      window.hpcFit();
    }, 50);
  };
  window.addEventListener("resize", scheduleFit);

  // Expose test-only helper for parity evidence (reads buffer without bypassing renderer)
  window.hpcGetState = () => {
    try {
      const buffer = terminal.buffer.active;
      return {
        cols: terminal.cols,
        rows: terminal.rows,
        cursorX: buffer.cursorX,
        cursorY: buffer.cursorY,
        viewportY: buffer.viewportY,
        baseY: buffer.baseY,
      };
    } catch (e) {
      return { cols: terminal.cols, rows: terminal.rows };
    }
  };

  // Ready handshake — after xterm + fit are initialized
  // Delay slightly to ensure WebView message handler is registered on Python side before posting ready
  setTimeout(() => {
    try {
      fit.fit();
    } catch (e) {}
    postToPython({ type: "ready" });
    // Also trigger initial resize so Python knows cols/rows
    try {
      postToPython({
        type: "resize",
        cols: terminal.cols,
        rows: terminal.rows,
        pixelWidth: terminal.element ? terminal.element.clientWidth : 0,
        pixelHeight: terminal.element ? terminal.element.clientHeight : 0,
      });
    } catch (e) {}
  }, 50);

  // Prevent external navigation from xterm content (defense in depth)
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (a) {
      const href = a.getAttribute("href") || "";
      if (href && !href.startsWith("file:") && !href.startsWith("#")) {
        e.preventDefault();
      }
    }
  });
})();
