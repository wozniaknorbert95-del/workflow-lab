import { mkdir, copyFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
await mkdir(dist, { recursive: true });
await copyFile(join(root, "src", "hello.js"), join(dist, "hello.js"));
