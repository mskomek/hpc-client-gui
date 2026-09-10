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
