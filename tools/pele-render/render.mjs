#!/usr/bin/env bun
// Pele renderer for this project's .mmd sources — Mermaid text in, themed SVG out,
// no browser, no install: Pele is imported straight from the CDN (bun caches URL
// imports). Outputs land in artifacts/pele/ (generated, gitignored).
//
// usage:
//   bun tools/pele-render/render.mjs --all                 # every docs/diagrams/*.mmd
//   bun tools/pele-render/render.mjs path/to/diagram.mmd   # one or more files
//   ... -o custom/out/dir                                  # override output dir
//
// Pele comes from the CDN — no package, no node_modules. bun 1.4.4 on Windows
// crashes on URL imports, so we fetch the ESM once and cache it beside this
// script (.pele.cache.js, gitignored); delete it to force a refresh.
// Node-side text widths use Pele's Arial metrics table — labels may pad slightly;
// the in-browser pages (pele.mount) measure on canvas and are the true visual.

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PELE_URL = "https://cdn.jsdelivr.net/npm/pele@1.6.0/dist/pele.js";

async function loadPele() {
  const cache = join(HERE, ".pele.cache.js");
  if (!existsSync(cache)) {
    const res = await fetch(PELE_URL);
    if (!res.ok) throw new Error(`CDN fetch failed: HTTP ${res.status} for ${PELE_URL}`);
    writeFileSync(cache, await res.text());
  }
  return import(pathToFileURL(cache).href);
}

const { render } = await loadPele();

const ROOT = resolve(HERE, "..", "..");
const DIAGRAMS = join(ROOT, "docs", "diagrams");

const args = process.argv.slice(2);
const wantAll = args.includes("--all");
const oAt = args.indexOf("-o");
const outDir = resolve(oAt >= 0 && args[oAt + 1] ? args[oAt + 1] : join(ROOT, "artifacts", "pele"));
const files = args.filter(
  (a, i) => !a.startsWith("--") && !(oAt >= 0 && (i === oAt + 1 || i === oAt)),
);

let inputs = files;
if (wantAll) inputs = readdirSync(DIAGRAMS).filter((f) => f.endsWith(".mmd")).map((f) => join(DIAGRAMS, f));
if (inputs.length === 0) {
  console.error("usage: render.mjs --all | <file.mmd>... [-o outDir]");
  process.exit(2);
}

mkdirSync(outDir, { recursive: true });
let failed = 0;
for (const src of inputs) {
  const name = basename(src).replace(/\.mmd$/, "");
  try {
    const { svg, width, height, type } = render(readFileSync(src, "utf8"));
    const dest = join(outDir, `${name}.svg`);
    writeFileSync(dest, svg);
    console.log(`ok   ${name.padEnd(18)} ${type.padEnd(12)} ${String(width).padStart(4)}x${String(height).padEnd(5)} ${String(svg.length).padStart(7)} B  -> ${dest}`);
  } catch (err) {
    failed += 1;
    console.error(`FAIL ${name}: ${err.message}`);
  }
}
process.exit(failed ? 1 : 0);
