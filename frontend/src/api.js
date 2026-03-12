const API_BASE_URL = "http://127.0.0.1:5000/analyze";

export async function runAnalysis(endpoint, payload) {
  const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
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