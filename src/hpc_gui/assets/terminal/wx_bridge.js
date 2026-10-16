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

  const clipboardCopyPrefix = "\u0000HPCGUI_CLIPBOARD_COPY\u0000";
  const clipboardPasteRequest = "\u0000HPCGUI_CLIPBOARD_PASTE\u0000";
  const clipboardEscapePrefix = "\u0000HPCGUI_CLIPBOARD_ESC\u0000";

  window.hpcClear = () => {
    try {
      terminal.clear();
    } catch (e) {}
  };

  window.hpcPaste = (text) => {
    try {
      terminal.paste(text);
    } catch (e) {}
  };

  // ── Search state (Find / Find Next / Find Previous) ──
  let _lastQuery = "";
  let _lastRow = 0;
  let _lastCol = 0;
  let _lastDirection = 1; // 1 = forward, -1 = backward

  function _searchBuffer(query, startRow, startCol, direction) {
    const buffer = terminal.buffer.active;
    const totalRows = buffer.baseY + terminal.rows;
    if (!query || totalRows <= 0) return null;
    for (let i = 0; i < totalRows; i++) {
      const idx = direction === 1
        ? (startRow + i) % totalRows
        : (startRow - i + totalRows) % totalRows;
      const line = buffer.getLine(idx);
      if (!line) continue;
      const text = line.translateToString(true);
      const col = direction === 1
        ? (idx === startRow ? text.indexOf(query, startCol) : text.indexOf(query))
        : (idx === startRow ? text.lastIndexOf(query, startCol - 1) : text.lastIndexOf(query));
      if (col >= 0) {
        const selLen = query.length;
        terminal.select(col, idx, selLen);
        terminal.scrollToLine(idx);
        return { row: idx, col: col, endCol: col + selLen };
      }
    }
    return null;
  }

  window.hpcFind = (query) => {
    try {
      if (!query) return false;
      _lastQuery = query;
      _lastDirection = 1;
      const buffer = terminal.buffer.active;
      _lastRow = buffer.cursorY + buffer.viewportY;
      _lastCol = buffer.cursorX;
      const result = _searchBuffer(query, _lastRow, _lastCol, 1);
      if (result) {
        _lastRow = result.row;
        _lastCol = result.endCol;
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  };

  window.hpcFindNext = () => {
    try {
      if (!_lastQuery) return false;
      _lastDirection = 1;
      const result = _searchBuffer(_lastQuery, _lastRow, _lastCol, 1);
      if (result) {
        _lastRow = result.row;
        _lastCol = result.endCol;
        return true;
      }
      // Wrap to beginning
      const wrapped = _searchBuffer(_lastQuery, 0, 0, 1);
      if (wrapped) {
        _lastRow = wrapped.row;
        _lastCol = wrapped.endCol;
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  };

  window.hpcFindPrev = () => {
    try {
      if (!_lastQuery) return false;
      _lastDirection = -1;
      const result = _searchBuffer(_lastQuery, _lastRow, _lastCol, -1);
      if (result) {
        _lastRow = result.row;
        _lastCol = result.col;
        return true;
      }
      // Wrap to end
      const buffer = terminal.buffer.active;
      const totalRows = buffer.baseY + buffer.viewportY + terminal.rows;
      const wrapped = _searchBuffer(_lastQuery, totalRows, totalRows, -1);
      if (wrapped) {
        _lastRow = wrapped.row;
        _lastCol = wrapped.col;
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
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

  // Clipboard shortcuts use the native clipboard through the existing bridge.
  terminal.attachCustomKeyEventHandler((event) => {
    if (event.type !== "keydown") return true;
    const isMac = /Mac|iPhone|iPad/.test(navigator.platform || "");
    const modifier = isMac ? event.metaKey : event.ctrlKey;
    if (!modifier) return true;
    const key = String(event.key || "").toLowerCase();
    const shortcut = event.shiftKey || isMac;
    if (!shortcut || (key !== "c" && key !== "v")) return true;
    event.preventDefault();
    if (key === "c") {
      const selection = terminal.getSelection();
      if (selection) {
        postToPython({ type: "input", data: clipboardCopyPrefix + selection });
      }
    } else {
      postToPython({ type: "input", data: clipboardPasteRequest });
    }
    return false;
  });

  // Input: xterm is authority for normal keys, navigation, Unicode, and paste.
  terminal.onData((data) => {
    // Escape text that resembles our control protocol so user content remains
    // ordinary terminal input. Shortcut requests are posted directly above.
    if (data.startsWith(clipboardCopyPrefix)
        || data === clipboardPasteRequest
        || data.startsWith(clipboardEscapePrefix)) {
      data = clipboardEscapePrefix + data;
    }
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

  // ── Test helpers: read xterm buffer state for behavioral verification ──
  window.hpcGetLineText = (row) => {
    try {
      const buffer = terminal.buffer.active;
      const line = buffer.getLine(row);
      if (!line) return null;
      return line.translateToString(true);
    } catch (e) {
      return null;
    }
  };

  window.hpcGetBufferText = () => {
    try {
      const buffer = terminal.buffer.active;
      const totalRows = buffer.baseY + terminal.rows;
      const lines = [];
      for (let i = 0; i < totalRows; i++) {
        const line = buffer.getLine(i);
        if (line) {
          lines.push(line.translateToString(true));
        }
      }
      return lines.join("\n");
    } catch (e) {
      return "";
    }
  };

  window.hpcGetScreenState = () => {
    try {
      const buffer = terminal.buffer.active;
      const activeBufferType = buffer.type; // 0 = normal, 1 = alternate
      const cursorX = buffer.cursorX;
      const cursorY = buffer.cursorY;
      const baseY = buffer.baseY;
      const viewportY = buffer.viewportY;
      const totalRows = buffer.baseY + terminal.rows;
      const lines = [];
      const maxLines = Math.min(totalRows, 500);
      for (let i = 0; i < maxLines; i++) {
        const line = buffer.getLine(i);
        if (line) {
          const text = line.translateToString(true);
          const attrs = [];
          for (let c = 0; c < text.length; c++) {
            const cell = line.getCell(c);
            if (cell) {
              const fg = cell.getFgColor();
              const bg = cell.getBgColor();
              const fgMode = cell.isFgDefault() ? "default" : (cell.isFgRgb() ? "rgb" : "color");
              attrs.push({ ch: text[c], fg, bg, fgMode });
            }
          }
          lines.push({ text, attrs });
        }
      }
      return {
        cols: terminal.cols,
        rows: terminal.rows,
        bufferType: activeBufferType,
        cursorX,
        cursorY,
        baseY,
        viewportY,
        totalRows,
        lines,
      };
    } catch (e) {
      return { error: String(e) };
    }
  };

  window.hpcGetAlternateScreenActive = () => {
    try {
      return terminal.buffer.active.type === 1;
    } catch (e) {
      return false;
    }
  };

  // WebKitGTK disallows wxWebView.RunScript under script-src 'self'.
  // A local file:// fragment navigates within this existing document;
  // no script evaluation, network request, or command file is involved.
  // Commands carry terminal contents briefly in the fragment. Remove it
  // from browser history immediately, and never echo command arguments.
  const nativeCommands = new Set([
    "hpcWrite", "hpcClear", "hpcPaste", "hpcFocus", "hpcSetFontSize",
    "hpcFit", "hpcFind", "hpcFindNext", "hpcFindPrev", "hpcGetScreenState",
  ]);

  function handleNativeFragment() {
    const hash = window.location.hash || "";
    if (!hash.startsWith("#hpc=")) return;
    let msg;
    try {
      msg = JSON.parse(decodeURIComponent(hash.slice(5)));
    } catch (e) {
      return;
    }
    try {
      window.history.replaceState(null, "", window.location.href.split("#")[0]);
    } catch (e) {
      // No URL logging or external navigation even when history is disabled.
    }
    const ack = () => postToPython({ type: "bridge-ack", seq: msg.seq });
    if (!msg || !Number.isSafeInteger(msg.seq) || !nativeCommands.has(msg.op)
        || typeof msg.channel !== "string" || !/^[0-9a-f]{32}$/.test(msg.channel)) return;
    const stored = /^hpc-terminal:([0-9a-f]{32}):(\d+)$/.exec(window.name || "");
    const lastNativeSequence = stored && stored[1] === msg.channel
      ? Number(stored[2]) : 0;
    // A reload may reset page globals while a late fragment is still in flight.
    // Persist only the random channel and sequence in this WebView context so
    // the command stays at-most-once without placing terminal data in storage.
    if (msg.seq <= lastNativeSequence) {
      ack();
      return;
    }
    window.name = `hpc-terminal:${msg.channel}:${msg.seq}`;
    const seq = msg.seq;
    try {
      switch (msg.op) {
        case "hpcWrite":
          if (typeof msg.arg !== "string") break;
          terminal.write(msg.arg, ack); // ACK only after buffer update
          return;
        case "hpcPaste":
        case "hpcFind":
          if (typeof msg.arg !== "string") break;
          window[msg.op](msg.arg);
          break;
        case "hpcSetFontSize":
          if (!Number.isInteger(msg.arg) || msg.arg < 6 || msg.arg > 32) break;
          window.hpcSetFontSize(msg.arg);
          break;
        case "hpcGetScreenState":
          postToPython({
            type: "bridge-response",
            seq, op: "hpcGetScreenState",
            value: window.hpcGetScreenState(),
          });
          break;
        default:
          if (msg.arg !== null) break;
          window[msg.op]();
      }
    } catch (e) {
      // Invalid native command must not become a successful readback.
    }
    ack(); // Release the serial queue even if a command is malformed.
  }
  window.addEventListener("hashchange", handleNativeFragment);
  if ((window.location.hash || "").startsWith("#hpc=")) {
    handleNativeFragment();
  }

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

  window.hpcResetFindState = () => {
    _lastQuery = "";
    _lastRow = 0;
    _lastCol = 0;
    _lastDirection = 1;
  };

  // Keyboard shortcuts: F3 = find next, Shift+F3 = find previous
  document.addEventListener("keydown", (e) => {
    if (e.key === "F3") {
      e.preventDefault();
      if (e.shiftKey) {
        window.hpcFindPrev();
      } else {
        window.hpcFindNext();
      }
    }
  });

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
