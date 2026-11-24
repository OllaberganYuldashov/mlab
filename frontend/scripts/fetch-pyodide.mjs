// ADR-0006: Pyodide fayllarini `pyodide.lock.json` bo'yicha yuklab, SHA-256 ni tekshiradi va
// `public/pyodide/<versiya>/` ga qo'yadi (Vite ularni `dist/` ga ko'chiradi). Xesh mos kelmasa — build to'xtaydi.
// Fayl allaqachon bor va xeshi to'g'ri bo'lsa — qayta yuklanmaydi. Repoga binar fayl tushmaydi (.gitignore).
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const lock = JSON.parse(readFileSync(join(root, "pyodide.lock.json"), "utf8"));
const target = join(root, "public", "pyodide", lock.version);
mkdirSync(target, { recursive: true });

const sha256 = (data) => createHash("sha256").update(data).digest("hex");

async function download(url) {
  // Node fetch HTTPS_PROXY ni hisobga olmaydi; proksi bo'lsa (bulut sessiyasi) curl ishlatiladi.
  if (process.env.HTTPS_PROXY || process.env.https_proxy) {
    return execFileSync("curl", ["-sSfL", "--retry", "3", url], { maxBuffer: 64 * 1024 * 1024 });
  }
  for (let attempt = 1; ; attempt++) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return Buffer.from(await response.arrayBuffer());
    } catch (error) {
      if (attempt >= 3) throw new Error(`${url}: ${error.message}`);
      await new Promise((resolve) => setTimeout(resolve, 1000 * attempt));
    }
  }
}

let fetched = 0;
for (const entry of lock.files) {
  const path = join(target, entry.file);
  if (existsSync(path) && sha256(readFileSync(path)) === entry.sha256) continue;
  const data = await download(entry.url ?? lock.base + entry.file);
  const actual = sha256(data);
  if (actual !== entry.sha256) {
    rmSync(path, { force: true });
    console.error(`XATO: ${entry.file} xeshi mos emas (kutilgan ${entry.sha256}, kelgan ${actual})`);
    process.exit(1);
  }
  writeFileSync(`${path}.part`, data);
  renameSync(`${path}.part`, path);
  fetched++;
}
console.log(`Pyodide ${lock.version}: ${lock.files.length} fayl tayyor (${fetched} ta yuklandi).`);
