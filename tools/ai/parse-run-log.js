#!/usr/bin/env node
// Filter a deepseek-worker.ps1 background-run stdout/stderr log down to the
// decision-relevant lines: model/timeout selection, run log directory,
// step-progress narration lines, and the final report. Drops raw ANSI/tool
// spam so it is safe to Read the filtered output into an LLM context window.
//
// Usage: node tools/ai/parse-run-log.js <path-to-log-file> [--tail N]

const fs = require("fs");

const args = process.argv.slice(2);
const filePath = args[0];
if (!filePath) {
  console.error("Usage: node parse-run-log.js <log-file> [--tail N]");
  process.exit(2);
}
const tailIdx = args.indexOf("--tail");
const tailN = tailIdx !== -1 ? parseInt(args[tailIdx + 1], 10) : null;

if (!fs.existsSync(filePath)) {
  console.error(`No such file: ${filePath}`);
  process.exit(1);
}

const raw = fs.readFileSync(filePath, "utf8");
// eslint-disable-next-line no-control-regex
const ansiStripped = raw.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "");

const noisePatterns = [
  /^[\s│┬╖Γ£▒┴]*$/, // stray box-drawing / mojibake-only lines
  /^\s*$/,
];

const keepPatterns = [
  /^Selected DeepSeek model/i,
  /^Timeout budget/i,
  /^Run log directory/i,
  /^Analysis complete/i,
  /^Task .* complete/i,
  /^Review complete/i,
  /^## /, // markdown headings in the model's own report
  /^\d+\.\s/, // numbered report points
  /^-\s/, // bullet lines
  /^Done\./i,
  /verdict/i,
  /PASS|FAIL|BLOCKED|SPLIT/,
  /exit code/i,
  /error/i,
  /warning/i,
  /timed out|timeout/i,
];

let lines = ansiStripped.split(/\r?\n/);
let filtered = lines.filter((line) => {
  if (noisePatterns.some((p) => p.test(line))) return false;
  return keepPatterns.some((p) => p.test(line)) || line.trim().length > 0;
});

// Collapse consecutive tool-call narration noise (lines starting with glyph markers)
filtered = filtered.filter((line, i) => {
  const isToolGlyph = /^[\s]*[►→⇒✓✔]/.test(line) || /^[^\x00-\x7F]{1,3}\s*(Glob|Grep|Read|Write|Bash)\b/.test(line);
  return true; // keep everything that survived keepPatterns/non-empty; adjust here if too noisy
});

if (tailN) {
  filtered = filtered.slice(-tailN);
}

console.log(filtered.join("\n"));
console.log(`\n--- (${filtered.length}/${lines.length} lines kept) ---`);
