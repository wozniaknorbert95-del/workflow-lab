/**
 * Cloud environment SSL/git/curl diagnostics (W-05 infra gate).
 * Run: node scripts/cloud-env-diag.js
 */
import fs from "node:fs";
import https from "node:https";
import { execFileSync } from "node:child_process";

const caPath = "/etc/ssl/certs/ca-certificates.crt";
const caExists = fs.existsSync(caPath);

function probeHttps(label, options = {}) {
  return new Promise((resolve) => {
    const req = https.get("https://github.com/", { timeout: 8000, ...options }, (res) => {
      res.resume();
      resolve({ label, ok: true, statusCode: res.statusCode });
    });
    req.on("error", (err) => resolve({ label, ok: false, error: err.message }));
    req.on("timeout", () => {
      req.destroy();
      resolve({ label, ok: false, error: "timeout" });
    });
  });
}

const httpsDefault = await probeHttps("default-agent");
const httpsCa = caExists
  ? await probeHttps("explicit-cafile", { ca: fs.readFileSync(caPath) })
  : { label: "explicit-cafile", ok: false, error: "no-ca-bundle" };

let curlProbe = { ok: false, error: "curl-not-run" };
try {
  execFileSync("curl", ["--version"], { encoding: "utf8", timeout: 5000 });
  curlProbe = { ok: true };
} catch (err) {
  curlProbe = { ok: false, error: err.message?.split("\n")[0] ?? String(err) };
}

let gitProbe = { ok: false, error: "git-not-run" };
try {
  const out = execFileSync(
    "git",
    ["ls-remote", "https://github.com/wozniaknorbert95-del/workflow-lab.git", "HEAD"],
    { encoding: "utf8", timeout: 15000 },
  );
  gitProbe = { ok: true, head: out.trim().split("\t")[0]?.slice(0, 12) };
} catch (err) {
  gitProbe = { ok: false, error: err.message?.split("\n")[0] ?? String(err) };
}

const isLinux = process.platform === "linux";
const healthy =
  (!isLinux || caExists) && curlProbe.ok && httpsDefault.ok && gitProbe.ok;
console.log(
  JSON.stringify({ healthy, caExists, curlProbe, httpsDefault, httpsCa, gitProbe }, null, 2),
);

if (!healthy) {
  console.error("cloud-env-diag: environment not ready for git HTTPS clone");
  process.exit(1);
}
