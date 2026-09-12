/**
 * Cloud environment SSL/git diagnostics (W-05 infra).
 * Run: node scripts/cloud-env-diag.js
 */
import fs from "node:fs";
import https from "node:https";
import { execFileSync } from "node:child_process";

const DEBUG_ENDPOINT =
  "http://127.0.0.1:7397/ingest/e73ee4db-a7bc-4cb6-bc26-50605c9524df";
const SESSION_ID = "4d4256";

// #region agent log
function debugLog(hypothesisId, message, data) {
  const payload = {
    sessionId: SESSION_ID,
    runId: process.env.DEBUG_RUN_ID ?? "pre-fix",
    hypothesisId,
    location: "scripts/cloud-env-diag.js",
    message,
    data,
    timestamp: Date.now(),
  };
  fetch(DEBUG_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Debug-Session-Id": SESSION_ID,
    },
    body: JSON.stringify(payload),
  }).catch(() => {});
  try {
    fs.appendFileSync("debug-4d4256.log", `${JSON.stringify(payload)}\n`);
  } catch {
    /* optional local log file */
  }
}
// #endregion

const caPath = "/etc/ssl/certs/ca-certificates.crt";
const caExists = fs.existsSync(caPath);

// #region agent log
debugLog("H1", "ca-certificates bundle presence", {
  caPath,
  caExists,
  gitSslCainfo: process.env.GIT_SSL_CAINFO ?? null,
  sslCertFile: process.env.SSL_CERT_FILE ?? null,
});
// #endregion

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

// #region agent log
debugLog("H2", "https probe github.com", { httpsDefault, httpsCa });
// #endregion

let curlProbe = { ok: false, error: "curl-not-run" };
try {
  execFileSync("curl", ["--version"], { encoding: "utf8", timeout: 5000 });
  curlProbe = { ok: true };
} catch (err) {
  curlProbe = { ok: false, error: err.message?.split("\n")[0] ?? String(err) };
}

// #region agent log
debugLog("H5", "curl availability", curlProbe);
// #endregion

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

// #region agent log
debugLog("H3", "git ls-remote workflow-lab", gitProbe);
// #endregion

const isLinux = process.platform === "linux";
const healthy =
  (!isLinux || caExists) && curlProbe.ok && httpsDefault.ok && gitProbe.ok;
console.log(
  JSON.stringify({ healthy, caExists, curlProbe, httpsDefault, httpsCa, gitProbe }, null, 2),
);

// #region agent log
debugLog("H4", "diag summary", { healthy, caExists, curlOk: curlProbe.ok, gitOk: gitProbe.ok });
// #endregion

if (!healthy) {
  console.error("cloud-env-diag: environment not ready for git HTTPS clone");
  process.exit(1);
}
