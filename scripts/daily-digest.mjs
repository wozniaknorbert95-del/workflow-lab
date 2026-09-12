const repo = process.env.GITHUB_REPOSITORY || "wozniaknorbert95-del/workflow-lab";
const trackingIssue = Number(process.env.TRACKING_ISSUE || "44");
const shouldPost = process.env.POST_COMMENT === "true";
const heading = process.env.DIGEST_HEADING || "Daily digest smoke";
const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || "";

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

function warsawDateParts(date = new Date()) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Warsaw",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const parts = Object.fromEntries(formatter.formatToParts(date).map((part) => [part.type, part.value]));
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${parts.hour}:${parts.minute}`,
  };
}

function issueLine(issue) {
  return `[#${issue.number} ${issue.title}](${issue.html_url})`;
}

function prLine(pr) {
  return `[#${pr.number} ${pr.title}](${pr.html_url})`;
}

async function listAgentIssues() {
  const issues = await github(`/issues?state=open&labels=agent&per_page=100`);
  return issues.filter((issue) => !issue.pull_request && issue.number !== trackingIssue);
}

async function listPullRequests() {
  return github(`/pulls?state=open&per_page=100`);
}

async function listRedChecks(pulls) {
  const redConclusions = new Set(["failure", "cancelled", "timed_out", "action_required"]);
  const red = [];

  for (const pr of pulls) {
    const checks = await github(`/commits/${pr.head.sha}/check-runs?per_page=100`);
    const failing = (checks.check_runs || []).filter((check) => redConclusions.has(check.conclusion));
    if (failing.length > 0) {
      red.push({ pr, checks: failing });
    }
  }

  return red;
}

function summarizeList(items, mapper) {
  if (items.length === 0) {
    return "0 — none";
  }
  return `${items.length} — ${items.map(mapper).join(", ")}`;
}

const agentIssues = await listAgentIssues();
const pulls = await listPullRequests();
const redChecks = await listRedChecks(pulls);
const { date, time } = warsawDateParts();

const redSummary = redChecks.length === 0
  ? "0 — none"
  : `${redChecks.length} — ${redChecks
      .map(({ pr, checks }) => `${prLine(pr)} (${checks.map((check) => check.name).join(", ")})`)
      .join(", ")}`;

const nextAction = pulls.length > 0
  ? `Review/merge ${prLine(pulls[0])} if CI is green.`
  : agentIssues.length > 0
    ? `Triage ${issueLine(agentIssues[0])}.`
    : "No urgent workflow-lab action; continue Batch 9 rituals.";

const digest = `## ${heading} — ${date} ${time} Europe/Warsaw

- Open agent issues: ${summarizeList(agentIssues, issueLine)}
- PRs waiting review/merge: ${summarizeList(pulls, prLine)}
- CI red: ${redSummary}
- One next action: ${nextAction}
`;

console.log(digest);

if (shouldPost) {
  await github(`/issues/${trackingIssue}/comments`, {
    method: "POST",
    body: JSON.stringify({ body: digest }),
  });
  console.log(`Posted digest to ${repo}#${trackingIssue}`);
}
