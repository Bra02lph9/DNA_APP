const API_BASE_URL = import.meta.env.VITE_BACK_URL;

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