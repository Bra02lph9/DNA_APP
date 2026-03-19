const API_BASE_URL = import.meta.env.VITE_BACK_URL;

export async function runAnalysis(endpoint, payload) {
  const url = `${API_BASE_URL}/${endpoint}`;

  console.log("VITE_BACK_URL =", API_BASE_URL);
  console.log("Final URL =", url);
  console.log("Payload =", payload);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  console.log("HTTP status =", response.status);

  const text = await response.text();
  console.log("Raw response =", text);

  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Backend did not return JSON. Status: ${response.status}`);
  }

  if (!response.ok) {
    throw new Error(data?.error || "Analysis failed");
  }

  return data;
}