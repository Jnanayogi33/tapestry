// Copy the derived data the visualization reads into viz/public/data/ so the static
// bundle is self-contained. Run automatically before dev/build (see package.json).
import { mkdirSync, copyFileSync, existsSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const srcDir = join(repoRoot, "data");
const outDir = join(here, "..", "public", "data");

const FILES = [
  "nav_index.json",
  "example_lives.json",
  "simulation_output.json",
  "strands.csv",
  "events.csv",
  "anchors.csv",
  "regions.csv",
];

mkdirSync(outDir, { recursive: true });
let copied = 0;
const missing = [];
for (const f of FILES) {
  const src = join(srcDir, f);
  if (existsSync(src)) {
    copyFileSync(src, join(outDir, f));
    copied++;
  } else {
    missing.push(f);
  }
}
// Manifest so the app can detect what's available.
writeFileSync(join(outDir, "manifest.json"),
  JSON.stringify({ files: FILES.filter((f) => !missing.includes(f)), missing, generatedFrom: srcDir }, null, 1));

console.log(`[copy-data] copied ${copied}/${FILES.length} files to public/data/`);
if (missing.length) console.warn(`[copy-data] missing (run the pipeline first): ${missing.join(", ")}`);
