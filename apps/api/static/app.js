"use strict";

const byId = (id) => document.getElementById(id);

function safeRunPath(runId) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(runId)) {
    throw new Error("Server returned an invalid run identifier");
  }
  return `/runs/${encodeURIComponent(runId)}`;
}

async function waitForJob(jobUrl, runId, statusElement) {
  if (!/^\/runs\/jobs\/[A-Za-z0-9_.-]+$/.test(jobUrl)) {
    throw new Error("Server returned an invalid job URL");
  }
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const response = await fetch(jobUrl, {headers: {"Accept": "application/json"}});
    const job = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(job.detail || `Job status HTTP ${response.status}`);
    if (job.status === "succeeded") {
      window.location.assign(safeRunPath(runId));
      return;
    }
    if (job.status === "dead_letter" || job.status === "cancelled") {
      throw new Error("Run did not complete; inspect the job record for its sanitized error code");
    }
    statusElement.textContent = `Running (${attempt + 1})…`;
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("Run is still processing; open the runs list to check it later");
}

async function startRun(endpoint, body, statusElement, errorElement) {
  errorElement.textContent = "";
  statusElement.textContent = "Queueing…";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {"Content-Type": "application/json", "Accept": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  await waitForJob(String(data.job_url || ""), String(data.run_id || ""), statusElement);
}

const modelRunButton = byId("runBtn");
if (modelRunButton) {
  modelRunButton.addEventListener("click", async () => {
    try {
      await startRun("/runs", {
        profile: byId("profile").value.trim() || null,
        model: byId("model").value.trim() || null,
        a9_mode: byId("a9_mode").value.trim() || null,
      }, byId("status"), byId("err"));
    } catch (error) {
      byId("status").textContent = "";
      byId("err").textContent = error instanceof Error ? error.message : "Run failed";
    }
  });
}

const agentRunButton = byId("agentRunBtn");
if (agentRunButton) {
  agentRunButton.addEventListener("click", async () => {
    try {
      await startRun("/agent-runs", {
        profile: byId("agent_profile").value.trim(),
        model: byId("agent_model").value.trim() || null,
      }, byId("agentStatus"), byId("agentErr"));
    } catch (error) {
      byId("agentStatus").textContent = "";
      byId("agentErr").textContent = error instanceof Error ? error.message : "Agent run failed";
    }
  });
}
