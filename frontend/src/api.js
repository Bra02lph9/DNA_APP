const API_BASE_URL =
  import.meta.env.VITE_BACK_URL || "http://localhost:5000";

async function parseResponse(response, fallbackMessage) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || fallbackMessage);
  }

  return data;
}

export async function runAnalysis(endpoint, payload) {
  const response = await fetch(`${API_BASE_URL}/analyze/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Analysis failed");
}

export async function createAnalysisTask(payload) {
  const response = await fetch(`${API_BASE_URL}/tasks/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Failed to create analysis task");
}

export async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
  return parseResponse(response, "Failed to fetch task status");
}

export async function runStoredAnalysis(payload) {
  const response = await fetch(`${API_BASE_URL}/analyses/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Failed to start stored analysis");
}

export async function getAnalysisSummary(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/summary`
  );

  return parseResponse(response, "Failed to fetch analysis summary");
}

export async function getAnalysisResults(
  analysisId,
  module,
  {
    kind = "final",
    limit = 20,
    skip = 0,
    sort_field,
    sort_direction = "asc",
  } = {}
) {
  const params = new URLSearchParams({
    module,
    kind,
    limit: String(limit),
    skip: String(skip),
    sort_direction,
  });

  if (sort_field) {
    params.append("sort_field", sort_field);
  }

  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/results?${params.toString()}`
  );

  return parseResponse(response, "Failed to fetch analysis results");
}

export async function assembleStoredAnalysis(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/assemble`,
    { method: "POST" }
  );

  return parseResponse(response, "Failed to assemble analysis");
}

export async function startOrfAlignment(
  analysisId,
  {
    identity_threshold = 0.9,
    max_orfs = 500,
    kmer_threshold = 0.5,
  } = {}
) {
  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/align-orfs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identity_threshold,
        max_orfs,
        kmer_threshold,
      }),
    }
  );

  return parseResponse(response, "Failed to start ORF alignment");
}

export async function getAlignedOrfs(
  analysisId,
  { limit = 100, skip = 0 } = {}
) {
  return getAnalysisResults(analysisId, "aligned_orfs", {
    kind: "final",
    limit,
    skip,
    sort_field: "cluster_id",
    sort_direction: "asc",
  });
}
