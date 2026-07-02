const DEFAULT_WORKSPACE = "../.mpm-ladder/workspace.json";
const DEFAULT_DIRECT_SOURCES = {
  models: "../data/models.json",
  workflow: "../examples/workflows/ci-recovery.json",
  runs: "../examples/runs/ci-recovery-runs.json",
};

const OBJECTIVE_PRESETS = {
  cost_saver: { minPassRate: 0.9, minAttempts: 3 },
  reliability_first: { minPassRate: 1.0, minAttempts: 3 },
  learning_probe: { minPassRate: 0.0, minAttempts: 3 },
};

const PASS_STATUSES = new Set(["pass", "passed", "success", "succeeded"]);
const FAILURE_STATUSES = new Set(["fail", "failed", "error", "timeout"]);
const AUTOMATED_EXECUTORS = new Set(["script", "rule", "ci"]);

const state = {
  workspacePath: DEFAULT_WORKSPACE,
  workspaceDoc: null,
  workspaceBaseUrl: null,
  workflowEntry: null,
  modelsDoc: null,
  workflowDoc: null,
  runsDoc: null,
  sourceNames: { ...DEFAULT_DIRECT_SOURCES },
};

const $ = (id) => document.getElementById(id);

function html(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function money(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return value < 0.01 ? `$${value.toFixed(4)}` : `$${value.toFixed(3)}`;
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function seconds(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const minutes = Math.floor(value / 60);
  const secs = Math.round(value % 60).toString().padStart(2, "0");
  return `${minutes}:${secs}`;
}

function setStatus(message, isError = false) {
  $("sourceStatus").textContent = message;
  $("sourceStatus").classList.toggle("error", isError);
}

function setEmptyState(message) {
  $("workflowSubtitle").textContent = message;
  for (const id of ["observedMpm", "reliableMpm", "targetMpm", "automationValue", "bestCost"]) {
    $(id).textContent = "-";
  }
  for (const id of ["observedNote", "reliableNote", "targetNote", "automationNote", "bestCostNote", "profilePill", "coveragePill", "failurePill", "versionPill"]) {
    $(id).textContent = "";
  }
  $("modelRows").innerHTML = `<tr><td colspan="9" class="empty">${html(message)}</td></tr>`;
  $("semanticWorkflow").innerHTML = `<div class="empty">${html(message)}</div>`;
  $("workflowSteps").innerHTML = `<div class="empty">${html(message)}</div>`;
  $("failureChart").innerHTML = `<div class="empty">${html(message)}</div>`;
}

function readQuerySources() {
  const params = new URLSearchParams(window.location.search);
  return {
    workspace: params.get("workspace") || DEFAULT_WORKSPACE,
    models: params.get("models") || DEFAULT_DIRECT_SOURCES.models,
    workflow: params.get("workflow") || DEFAULT_DIRECT_SOURCES.workflow,
    runs: params.get("runs") || DEFAULT_DIRECT_SOURCES.runs,
  };
}

function parentUrl(path) {
  const url = new URL(path, window.location.href);
  return new URL(".", url.href);
}

function resolveFrom(baseUrl, path) {
  return new URL(path, baseUrl).href;
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} HTTP ${response.status}`);
  }
  return response.json();
}

function syncSourceInputs() {
  $("workspacePath").value = state.workspacePath;
  $("modelsPath").value = state.sourceNames.models;
  $("workflowPath").value = state.sourceNames.workflow;
  $("runsPath").value = state.sourceNames.runs;
}

async function loadWorkspace(path) {
  state.workspacePath = path;
  state.workspaceBaseUrl = parentUrl(path);
  setStatus("워크스페이스를 불러오는 중입니다.");
  state.workspaceDoc = await fetchJson(path);
  renderWorkflowOptions();
  const firstWorkflow = state.workspaceDoc.workflows?.[0];
  if (!firstWorkflow) {
    throw new Error("워크스페이스에 workflow가 없습니다.");
  }
  await loadWorkflowFromWorkspace(firstWorkflow.id);
}

function renderWorkflowOptions() {
  const workflows = state.workspaceDoc?.workflows || [];
  $("workflowSelect").innerHTML = workflows.map((workflow) => {
    return `<option value="${html(workflow.id)}">${html(workflow.name || workflow.id)}</option>`;
  }).join("");
}

async function loadWorkflowFromWorkspace(workflowId) {
  const workflows = state.workspaceDoc?.workflows || [];
  const workflow = workflows.find((item) => item.id === workflowId);
  if (!workflow) {
    throw new Error(`워크플로우를 찾을 수 없습니다: ${workflowId}`);
  }

  state.workflowEntry = workflow;
  const modelsPath = resolveFrom(state.workspaceBaseUrl, state.workspaceDoc.models_path || DEFAULT_DIRECT_SOURCES.models);
  const workflowPath = resolveFrom(state.workspaceBaseUrl, workflow.current_workflow_path);
  const runsPath = resolveFrom(state.workspaceBaseUrl, workflow.default_runs_path);
  state.sourceNames = {
    models: modelsPath,
    workflow: workflowPath,
    runs: runsPath,
  };
  syncSourceInputs();
  $("workflowSelect").value = workflow.id;
  setStatus(`${workflow.name || workflow.id} 데이터를 불러오는 중입니다.`);
  const [modelsDoc, workflowDoc, runsDoc] = await Promise.all([
    fetchJson(modelsPath),
    fetchJson(workflowPath),
    fetchJson(runsPath),
  ]);
  state.modelsDoc = modelsDoc;
  state.workflowDoc = workflowDoc;
  state.runsDoc = runsDoc;
  render();
  setStatus(`로드됨: ${state.workspaceDoc.name || state.workspaceDoc.id} / ${workflow.name || workflow.id}`);
}

function readJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        resolve(JSON.parse(String(reader.result)));
      } catch (error) {
        reject(new Error(`${file.name}: JSON 파싱 실패`));
      }
    };
    reader.onerror = () => reject(new Error(`${file.name}: 파일 읽기 실패`));
    reader.readAsText(file, "utf-8");
  });
}

async function loadFromPaths(sources) {
  setStatus("JSON 경로를 불러오는 중입니다.");
  const [modelsDoc, workflowDoc, runsDoc] = await Promise.all([
    fetchJson(sources.models),
    fetchJson(sources.workflow),
    fetchJson(sources.runs),
  ]);
  state.workspaceDoc = null;
  state.workflowEntry = null;
  state.modelsDoc = modelsDoc;
  state.workflowDoc = workflowDoc;
  state.runsDoc = runsDoc;
  state.sourceNames = { ...sources };
  syncSourceInputs();
  render();
  setStatus(`직접 로드됨: ${sources.models} / ${sources.workflow} / ${sources.runs}`);
}

async function loadFromFiles() {
  const fileMap = {
    models: $("modelsFile").files[0],
    workflow: $("workflowFile").files[0],
    runs: $("runsFile").files[0],
  };
  const missing = Object.entries(fileMap)
    .filter(([key, file]) => !file && !state[`${key}Doc`])
    .map(([key]) => key);
  if (missing.length) {
    throw new Error(`필요한 파일이 없습니다: ${missing.join(", ")}`);
  }

  setStatus("선택한 파일을 반영하는 중입니다.");
  for (const [key, file] of Object.entries(fileMap)) {
    if (file) {
      state[`${key}Doc`] = await readJsonFile(file);
      state.sourceNames[key] = file.name;
    }
  }
  state.workspaceDoc = null;
  state.workflowEntry = null;
  render();
  setStatus(`파일 로드됨: ${state.sourceNames.models} / ${state.sourceNames.workflow} / ${state.sourceNames.runs}`);
}

function tierRanks() {
  return Object.fromEntries((state.modelsDoc.tiers || []).map((tier) => [tier.id, Number(tier.rank)]));
}

function validateDocs() {
  if (!state.modelsDoc || !state.workflowDoc || !state.runsDoc) {
    throw new Error("모델, 워크플로우, 실행 로그 JSON을 모두 불러와야 합니다.");
  }
  if (!Array.isArray(state.modelsDoc.tiers) || !Array.isArray(state.modelsDoc.models)) {
    throw new Error("models JSON에는 tiers와 models 배열이 필요합니다.");
  }
  if (!Array.isArray(state.workflowDoc.steps)) {
    throw new Error("workflow JSON에는 steps 배열이 필요합니다.");
  }
  if (!Array.isArray(state.runsDoc.attempts)) {
    throw new Error("runs JSON에는 attempts 배열이 필요합니다.");
  }

  const ranks = tierRanks();
  for (const model of state.modelsDoc.models) {
    if (ranks[model.tier] === undefined) {
      throw new Error(`알 수 없는 모델 티어: ${model.id} -> ${model.tier}`);
    }
  }

  const modelIds = new Set(state.modelsDoc.models.map((model) => model.id));
  for (const attempt of state.runsDoc.attempts) {
    if (!modelIds.has(attempt.model_id)) {
      throw new Error(`실행 로그가 알 수 없는 모델을 참조합니다: ${attempt.model_id}`);
    }
  }
}

function modelsById() {
  return Object.fromEntries(state.modelsDoc.models.map((model) => [model.id, model]));
}

function workflowVersion() {
  const version = state.workflowDoc.version;
  if (version && typeof version === "object") return version.id || version.version || "unversioned";
  return state.workflowDoc.version_id || "unversioned";
}

function runProfile() {
  return {
    input_tokens: Number(state.workflowDoc.run_profile?.input_tokens ?? 100000),
    output_tokens: Number(state.workflowDoc.run_profile?.output_tokens ?? 20000),
    tool_cost_usd: Number(state.workflowDoc.run_profile?.tool_cost_usd ?? 0),
  };
}

function costFor(model) {
  const profile = runProfile();
  return profile.input_tokens / 1000000 * Number(model.input_per_mtok)
    + profile.output_tokens / 1000000 * Number(model.output_per_mtok)
    + profile.tool_cost_usd;
}

function isPass(attempt) {
  return PASS_STATUSES.has(String(attempt.status || "").toLowerCase());
}

function isFailure(attempt) {
  return FAILURE_STATUSES.has(String(attempt.status || "").toLowerCase());
}

function summarizeRuns() {
  const grouped = new Map();
  const models = modelsById();

  for (const attempt of state.runsDoc.attempts) {
    if (!grouped.has(attempt.model_id)) grouped.set(attempt.model_id, []);
    grouped.get(attempt.model_id).push(attempt);
  }

  return [...grouped.entries()].map(([modelId, rows]) => {
    const model = models[modelId];
    const passes = rows.filter(isPass).length;
    const failures = rows.filter(isFailure).length;
    const actionable = rows.filter((attempt) => isFailure(attempt) && Boolean(attempt.actionable)).length;
    const durationRows = rows.filter((attempt) => Number.isFinite(Number(attempt.duration_seconds)));
    const avgDuration = durationRows.length
      ? durationRows.reduce((sum, attempt) => sum + Number(attempt.duration_seconds), 0) / durationRows.length
      : null;
    const costRun = costFor(model);
    const labels = {};

    for (const attempt of rows) {
      if (isFailure(attempt)) {
        const label = attempt.failure_label || "UNLABELED";
        labels[label] = (labels[label] || 0) + 1;
      }
    }

    const passRate = rows.length ? passes / rows.length : null;
    return {
      model_id: modelId,
      provider: model.provider,
      tier: model.tier,
      attempts: rows.length,
      passes,
      failures,
      pass_rate: passRate,
      cost_run: costRun,
      cost_success: passes ? costRun * rows.length / passes : null,
      expected_cost_per_success: passRate ? costRun / passRate : null,
      actionable_failure_rate: failures ? actionable / failures : null,
      avg_duration_seconds: avgDuration,
      failure_labels: labels,
    };
  }).sort(sortByTierCost);
}

function sortByTierCost(a, b) {
  const ranks = tierRanks();
  return ranks[a.tier] - ranks[b.tier]
    || a.cost_run - b.cost_run
    || a.model_id.localeCompare(b.model_id);
}

function bestObserved(summaries) {
  const ranks = tierRanks();
  return summaries
    .filter((summary) => summary.passes > 0)
    .sort((a, b) => {
      return ranks[a.tier] - ranks[b.tier]
        || a.cost_run - b.cost_run
        || b.pass_rate - a.pass_rate
        || a.model_id.localeCompare(b.model_id);
    })[0] || null;
}

function bestReliable(summaries, minPassRate, minAttempts) {
  const ranks = tierRanks();
  return summaries
    .filter((summary) => summary.attempts >= minAttempts && summary.pass_rate >= minPassRate)
    .sort((a, b) => {
      return ranks[a.tier] - ranks[b.tier]
        || a.expected_cost_per_success - b.expected_cost_per_success
        || a.cost_run - b.cost_run
        || a.model_id.localeCompare(b.model_id);
    })[0] || null;
}

function workflowCoverage() {
  const ranks = tierRanks();
  let automated = 0;
  let agent = 0;
  let human = 0;
  let unknown = 0;
  const requiredTiers = [];

  for (const step of state.workflowDoc.steps) {
    const normalized = String(step.executor || "").toLowerCase();
    if (AUTOMATED_EXECUTORS.has(normalized)) automated += 1;
    else if (normalized === "human") human += 1;
    else if (ranks[step.executor] !== undefined) {
      agent += 1;
      requiredTiers.push(step.executor);
    } else {
      unknown += 1;
    }
  }

  const designRequiredTier = requiredTiers.sort((a, b) => ranks[b] - ranks[a])[0] || null;
  const total = state.workflowDoc.steps.length;
  return {
    total,
    automated,
    agent,
    human,
    unknown,
    automationCoverage: total ? automated / total : null,
    designRequiredTier,
  };
}

function decision(summary, minPassRate, minAttempts) {
  if (summary.attempts < minAttempts) return { label: "데이터 부족", className: "watch" };
  if (summary.pass_rate < minPassRate) return { label: "제외", className: "no" };
  return { label: "가능", className: "ok" };
}

function render() {
  try {
    validateDocs();
  } catch (error) {
    setEmptyState(error.message);
    setStatus(error.message, true);
    return;
  }

  const minPassRate = Number($("minPassRate").value);
  const minAttempts = Number($("minAttempts").value);
  const summaries = summarizeRuns();
  const observed = bestObserved(summaries);
  const reliable = bestReliable(summaries, minPassRate, minAttempts);
  const coverage = workflowCoverage();
  const profile = runProfile();
  const bestCost = summaries
    .filter((summary) => summary.cost_success !== null)
    .sort((a, b) => a.cost_success - b.cost_success)[0] || null;

  $("workflowSubtitle").textContent = `${state.workflowDoc.name || state.workflowDoc.id || "워크플로우"} (${state.workflowDoc.id || "id 없음"})`;
  $("profilePill").textContent = `${profile.input_tokens.toLocaleString()} 입력 + ${profile.output_tokens.toLocaleString()} 출력 토큰`;
  $("observedMpm").textContent = observed ? observed.tier : "없음";
  $("observedNote").textContent = observed ? observed.model_id : "성공 실행 없음";
  $("reliableMpm").textContent = reliable ? reliable.tier : "없음";
  $("reliableNote").textContent = reliable ? reliable.model_id : `${percent(minPassRate)} 성공률 기준`;
  $("targetMpm").textContent = state.workflowDoc.target_mpm || "n/a";

  const ranks = tierRanks();
  const targetTier = state.workflowDoc.target_mpm;
  const targetMet = reliable && targetTier && ranks[targetTier] !== undefined
    ? ranks[reliable.tier] <= ranks[targetTier]
    : null;
  $("targetNote").textContent = targetMet === null ? "신뢰 기준 미충족" : targetMet ? "신뢰 기준으로 충족" : "신뢰 기준으로 미달";
  $("automationValue").textContent = percent(coverage.automationCoverage);
  $("automationNote").textContent = `${coverage.automated}/${coverage.total} 자동화, human ${coverage.human}`;
  $("bestCost").textContent = bestCost ? money(bestCost.cost_success) : "n/a";
  $("bestCostNote").textContent = bestCost ? bestCost.model_id : "성공 실행 없음";
  $("coveragePill").textContent = `설계 요구 ${coverage.designRequiredTier || "없음"}`;
  $("versionPill").textContent = `${workflowVersion()} / ${state.runsDoc.run_set_id || "run set 없음"}`;

  renderSemanticWorkflow();
  renderRows(summaries, minPassRate, minAttempts);
  renderWorkflow();
  renderFailures(summaries);
}

function renderSemanticWorkflow() {
  const versionCount = state.workflowEntry?.versions?.length ?? 0;
  const list = (items) => {
    if (!items || !items.length) return '<div class="semantic-value">없음</div>';
    return `<ul class="list">${items.slice(0, 4).map((item) => `<li>${html(typeof item === "string" ? item : item.id || item.when || JSON.stringify(item))}</li>`).join("")}</ul>`;
  };

  $("semanticWorkflow").innerHTML = `
    <div class="semantic-item">
      <div class="semantic-label">의도</div>
      <div class="semantic-value">${html(state.workflowDoc.intent || "정의되지 않음")}</div>
    </div>
    <div class="semantic-item">
      <div class="semantic-label">소유 / 도메인 / 위험도</div>
      <div class="semantic-value">${html(state.workflowDoc.owner || "-")} / ${html(state.workflowDoc.domain || "-")} / ${html(state.workflowDoc.risk_class || "-")}</div>
    </div>
    <div class="semantic-item">
      <div class="semantic-label">버전 관리</div>
      <div class="semantic-value">현재 버전 ${html(workflowVersion())}, registry snapshot ${versionCount}개</div>
    </div>
    <div class="semantic-item">
      <div class="semantic-label">입력</div>
      ${list(state.workflowDoc.inputs)}
    </div>
    <div class="semantic-item">
      <div class="semantic-label">성공 기준</div>
      ${list(state.workflowDoc.success_criteria)}
    </div>
    <div class="semantic-item">
      <div class="semantic-label">금지 행동</div>
      ${list(state.workflowDoc.forbidden_actions)}
    </div>
  `;
}

function renderRows(summaries, minPassRate, minAttempts) {
  if (!summaries.length) {
    $("modelRows").innerHTML = '<tr><td colspan="9" class="empty">실행 로그가 비어 있습니다.</td></tr>';
    return;
  }

  $("modelRows").innerHTML = summaries.map((summary) => {
    const passWidth = `${Math.round((summary.pass_rate || 0) * 100)}%`;
    const rowDecision = decision(summary, minPassRate, minAttempts);
    return `
      <tr>
        <td>
          <div class="model-cell">
            <span class="model-id">${html(summary.model_id)}</span>
            <span class="provider">${html(summary.provider || "")}</span>
          </div>
        </td>
        <td><span class="tier">${html(summary.tier)}</span></td>
        <td>${summary.passes}/${summary.attempts}</td>
        <td>
          <div class="bar-cell">
            <div class="bar-track"><div class="bar-fill pass" style="width:${passWidth}"></div></div>
            <strong>${percent(summary.pass_rate)}</strong>
          </div>
        </td>
        <td>${money(summary.cost_run)}</td>
        <td>${money(summary.cost_success)}</td>
        <td>${seconds(summary.avg_duration_seconds)}</td>
        <td>${percent(summary.actionable_failure_rate)}</td>
        <td><span class="status ${rowDecision.className}">${rowDecision.label}</span></td>
      </tr>
    `;
  }).join("");
}

function renderWorkflow() {
  if (!state.workflowDoc.steps.length) {
    $("workflowSteps").innerHTML = '<div class="empty">워크플로우 단계가 없습니다.</div>';
    return;
  }

  $("workflowSteps").innerHTML = state.workflowDoc.steps.map((step, index) => {
    const normalized = String(step.executor || "").toLowerCase();
    const kind = AUTOMATED_EXECUTORS.has(normalized) ? "auto" : normalized === "human" ? "human" : "agent";
    return `
      <div class="step">
        <div class="step-id">${String(index + 1).padStart(2, "0")}</div>
        <div>
          <div class="step-name">${html(step.name || step.id || "이름 없음")}</div>
          <div class="provider">${html(step.intent || "")}</div>
        </div>
        <div class="executor ${kind}">${html(step.executor || "unknown")}</div>
      </div>
    `;
  }).join("");
}

function renderFailures(summaries) {
  const labels = {};
  for (const summary of summaries) {
    for (const [label, count] of Object.entries(summary.failure_labels)) {
      labels[label] = (labels[label] || 0) + count;
    }
  }

  const labelRows = Object.entries(labels).sort((a, b) => b[1] - a[1]);
  $("failurePill").textContent = `${labelRows.reduce((sum, [, count]) => sum + count, 0)}건`;

  if (!labelRows.length) {
    $("failureChart").innerHTML = '<div class="empty">실패 라벨이 없습니다.</div>';
    return;
  }

  const maxLabelCount = Math.max(1, ...labelRows.map(([, count]) => count));
  $("failureChart").innerHTML = labelRows.map(([label, count]) => {
    const width = `${Math.round(count / maxLabelCount * 100)}%`;
    const className = label === "MODEL_ERROR" ? "fail" : "";
    return `
      <div class="chart-row">
        <div class="chart-label">${html(label)}</div>
        <div class="bar-track"><div class="bar-fill ${className}" style="width:${width}"></div></div>
        <strong>${count}</strong>
      </div>
    `;
  }).join("");
}

function bindEvents() {
  $("objective").addEventListener("change", () => {
    const preset = OBJECTIVE_PRESETS[$("objective").value];
    $("minPassRate").value = String(preset.minPassRate.toFixed(2));
    $("minAttempts").value = String(preset.minAttempts);
    render();
  });
  $("minPassRate").addEventListener("input", render);
  $("minAttempts").addEventListener("input", render);
  $("loadWorkspace").addEventListener("click", async () => {
    try {
      await loadWorkspace($("workspacePath").value.trim());
    } catch (error) {
      setEmptyState(error.message);
      setStatus(error.message, true);
    }
  });
  $("workflowSelect").addEventListener("change", async () => {
    try {
      await loadWorkflowFromWorkspace($("workflowSelect").value);
    } catch (error) {
      setEmptyState(error.message);
      setStatus(error.message, true);
    }
  });
  $("loadPaths").addEventListener("click", async () => {
    try {
      await loadFromPaths({
        models: $("modelsPath").value.trim(),
        workflow: $("workflowPath").value.trim(),
        runs: $("runsPath").value.trim(),
      });
    } catch (error) {
      setEmptyState(error.message);
      setStatus(error.message, true);
    }
  });
  $("loadFiles").addEventListener("click", async () => {
    try {
      await loadFromFiles();
    } catch (error) {
      setEmptyState(error.message);
      setStatus(error.message, true);
    }
  });
}

async function init() {
  bindEvents();
  const sources = readQuerySources();
  state.workspacePath = sources.workspace;
  state.sourceNames = {
    models: sources.models,
    workflow: sources.workflow,
    runs: sources.runs,
  };
  syncSourceInputs();
  try {
    await loadWorkspace(sources.workspace);
  } catch (error) {
    setStatus(`${error.message}; 직접 JSON 경로를 시도합니다.`, true);
    try {
      await loadFromPaths({
        models: sources.models,
        workflow: sources.workflow,
        runs: sources.runs,
      });
    } catch (fallbackError) {
      setEmptyState("워크스페이스와 기본 JSON 경로를 불러오지 못했습니다. 파일을 선택해 반영하세요.");
      setStatus(fallbackError.message, true);
    }
  }
}

init();
