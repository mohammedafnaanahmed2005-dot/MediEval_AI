import type { DashboardData, EvaluationResult } from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error("MediEval API is offline. Run .\\start.ps1 from the project folder; this page will reconnect automatically.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const getDashboard = () => request<DashboardData>("/api/dashboard");
export const getEvaluations = () => request<DashboardData["recent_evaluations"]>("/api/evaluations");
export const checkApiHealth = () => request<{ status: string }>("/api/health");

export function uploadDataset(
  file: File,
  mapping?: { ai_label_column: string; reference_answer_column: string },
): Promise<EvaluationResult> {
  const body = new FormData();
  body.append("file", file);
  if (mapping) {
    body.append("ai_label_column", mapping.ai_label_column);
    body.append("reference_answer_column", mapping.reference_answer_column);
  }
  return request<EvaluationResult>("/api/evaluations/upload", { method: "POST", body });
}

export async function downloadReport(id: string, format: "csv" | "pdf" | "docx") {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/reports/${id}/${format}`);
  } catch {
    throw new Error("MediEval API is offline. Run .\\start.ps1 from the project folder and retry the export.");
  }
  if (!response.ok) throw new Error("Could not generate the report. Try uploading the dataset again.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `medieval-evaluation-${id.slice(0, 8)}.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
