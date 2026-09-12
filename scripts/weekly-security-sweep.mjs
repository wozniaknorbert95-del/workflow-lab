const repo = process.env.GITHUB_REPOSITORY || "wozniaknorbert95-del/workflow-lab";
const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || "";
const shouldCreateIssue = process.env.POST_ISSUE === "true";
const overrideDate = process.env.SWEEP_DATE || "";

const [owner, name] = repo.split("/");
const baseUrl = `https://api.github.com/repos/${owner}/${name}`;
const headers = {
  "Accept": "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  ...(token ? { "Authorization": `Bearer ${token}` } : {}),
};

async function github(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GitHub API ${response.status} for ${path}: ${body.slice(0, 300)}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function warsawDate(date = new Date()) {
  if (overrideDate) {
    return overrideDate;
  }

  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Warsaw",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = Object.fromEntries(formatter.formatToParts(date).map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function isoWeekId(dateString) {
  const date = new Date(`${dateString}T00:00:00Z`);
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

async function ensureAgentLabel() {
  try {
    await github("/labels/agent");
  } catch (error) {
    if (!String(error.message).includes("GitHub API 404")) {
      throw error;
    }

    await github("/labels", {
      method: "POST",
      body: JSON.stringify({
        name: "agent",
        color: "5319e7",
        description: "Ready for Cursor/agent handling",
      }),
    });
  }
}

async function findExistingSweep(weekId) {
  const issues = await github("/issues?state=open&labels=agent&per_page=100");
  return issues.find((issue) => !issue.pull_request && issue.title.includes(weekId));
}

const date = warsawDate();
const weekId = isoWeekId(date);
const title = `chore: weekly security sweep ${weekId}`;
const body = `## Weekly security sweep — ${weekId}

Run skill \`review-bezpieczenstwa\` on \`main\` since the last sweep.

Scope:
- Check \`git diff\` / latest merged changes for secrets, .env files, passwords, tokens, and keys.
- Confirm CI parity still equals \`npm run lint\` + \`npm test\` + \`npm run build\`.
- Confirm no \`dsaas-platform-main\` or Academy work leaked into \`workflow-lab\`.
- Confirm no dual-origin, force-push, or \`--no-verify\` path was used.

Output:
- \`PASS: clean\`, or
- a blocker list with exact files/PRs and the next repair action.

Automation source: \`docs/W4-AUTOMATIONS.md\` Automation 2.`;

console.log(`Weekly security sweep candidate: ${title}`);
console.log(body);

if (shouldCreateIssue) {
  await ensureAgentLabel();
  const existing = await findExistingSweep(weekId);

  if (existing) {
    console.log(`Existing weekly security sweep issue: #${existing.number} ${existing.html_url}`);
  } else {
    const issue = await github("/issues", {
      method: "POST",
      body: JSON.stringify({
        title,
        body,
        labels: ["agent"],
      }),
    });
    console.log(`Created weekly security sweep issue: #${issue.number} ${issue.html_url}`);
  }
}
