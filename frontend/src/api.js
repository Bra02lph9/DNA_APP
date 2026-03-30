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
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: "GET",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.error || "Failed to fetch task status");
  }

  return data;
}