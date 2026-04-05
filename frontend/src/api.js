const API_BASE_URL =
  import.meta.env.VITE_BACK_URL || "http://localhost:5000";

export async function runAnalysis(endpoint, payload) {
  const response = await fetch(`${API_BASE_URL}/analyze/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Analysis failed");
  }

  return data;
}

export async function createAnalysisTask(payload) {
  const response = await fetch(`${API_BASE_URL}/tasks/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to create analysis task");
  }

  return data;
}

export async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to fetch task status");
  }

  return data;
}

export async function runStoredAnalysis(payload) {
  const response = await fetch(`${API_BASE_URL}/analyses/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to start stored analysis");
  }

  return data;
}


export async function getAnalysisSummary(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/summary`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to fetch analysis summary");
  }

  return data;
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
    limit,
    skip,
    sort_direction,
  });

  if (sort_field) {
    params.append("sort_field", sort_field);
  }

  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/results?${params.toString()}`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to fetch analysis results");
  }

  return data;
}

export async function assembleStoredAnalysis(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/analyses/${analysisId}/assemble`,
    {
      method: "POST",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to assemble analysis");
  }

  return data;
}