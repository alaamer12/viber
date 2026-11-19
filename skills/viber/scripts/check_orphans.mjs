#!/usr/bin/env node
/**
 * check_orphans.mjs — verifies every doc file has at least one incoming link.
 * Allowed orphans: docs root index.md + each first-level directory's index.md.
 *
 * Usage: node check_orphans.mjs <docs-root> [--ignore <relative-path>]...
 *
 * --ignore: repeatable. Suppresses broken-link reports for known unauthored targets.
 *           Path is relative to docs root (e.g. --ignore steering/tech/shared/playbook/foo.md).
 *
 * Exit 0 = clean, 1 = orphans found, 2 = usage error.
 */
import { readdir, readFile } from 'node:fs/promises';
import { join, relative, dirname, resolve } from 'node:path';
import { existsSync } from 'node:fs';

const args = process.argv.slice(2);
let docsRoot = null;
const ignored = new Set();

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--docs' && args[i + 1]) {
    docsRoot = resolve(args[++i]);
  } else if (args[i] === '--ignore' && args[i + 1]) {
    ignored.add(args[++i].replace(/\\/g, '/'));
  } else if (!args[i].startsWith('-') && !docsRoot) {
    docsRoot = resolve(args[i]);
  }
}

if (!docsRoot) {
  console.error('Usage: node check_orphans.mjs <docs-root> [--ignore <relative-path>]...');
  process.exit(2);
}

if (!existsSync(docsRoot)) {
  console.error(`Error: directory not found: ${docsRoot}`);
  process.exit(2);
}

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const e of entries) {
    const full = join(dir, e.name);
    if (e.isDirectory()) files.push(...await walk(full));
    else if (e.name.endsWith('.md')) files.push(full);
  }
  return files;
}

const LINK_RE = /\]\(([^)]+)\)/g;

function parseHref(raw) {
  const href = raw.split('#')[0].trim();
  if (!href || href.startsWith('http') || href.startsWith('mailto:')) return null;
  if (!href.endsWith('.md')) return null;
  return href;
}

const allFiles = await walk(docsRoot);
const fileSet = new Set(allFiles);
const incoming = new Map(allFiles.map(f => [f, 0]));
const brokenTargets = [];

for (const file of allFiles) {
  const content = await readFile(file, 'utf8');
  for (const m of content.matchAll(LINK_RE)) {
    const href = parseHref(m[1]);
    if (!href) continue;
    const target = resolve(dirname(file), href);
    if (fileSet.has(target)) {
      if (target !== file) incoming.set(target, incoming.get(target) + 1);
    } else {
      const rel = relative(docsRoot, target).replace(/\\/g, '/');
      if (!ignored.has(rel)) {
        brokenTargets.push({ from: relative(docsRoot, file), href });
      }
    }
  }
}

// Allowed orphans: root index + first-level directory indexes
const allowed = new Set();
const rootIndex = join(docsRoot, 'index.md');
if (fileSet.has(rootIndex)) allowed.add(rootIndex);

const topLevel = await readdir(docsRoot, { withFileTypes: true });
for (const e of topLevel) {
  if (e.isDirectory()) {
    const idx = join(docsRoot, e.name, 'index.md');
    if (fileSet.has(idx)) allowed.add(idx);
  }
}

const orphans = allFiles.filter(f => incoming.get(f) === 0 && !allowed.has(f));

// Report
console.log(`\n  ORPHAN CHECK — ${relative(process.cwd(), docsRoot) || '.'}`);
console.log(`  ${allFiles.length} files scanned, ${allowed.size} exempt entry points`);
if (ignored.size > 0) console.log(`  ${ignored.size} known gap(s) ignored`);
console.log('');

if (orphans.length === 0) {
  console.log('  PASS: no orphan files.\n');
} else {
  console.log(`  FAIL: ${orphans.length} orphan(s) with zero incoming links:\n`);
  for (const f of orphans.sort()) {
    console.log(`    - ${relative(docsRoot, f)}`);
  }
  console.log('');
}

if (brokenTargets.length > 0) {
  console.log(`  BROKEN LINKS: ${brokenTargets.length} link(s) point to nonexistent files:\n`);
  for (const { from, href } of brokenTargets) {
    console.log(`    ${from} -> ${href}`);
  }
  console.log('');
}

process.exit(orphans.length > 0 ? 1 : 0);