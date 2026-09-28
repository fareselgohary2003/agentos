const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (response.status === 401 && typeof window !== "undefined" && !path.includes("/api/auth/login")) {
    // Token is invalid/expired -> clear and redirect to login
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenPair>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload: {
    organization_name: string;
    organization_slug: string;
    email: string;
    password: string;
    full_name: string;
  }) => request<TokenPair>("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/api/auth/me"),

  listAgents: () => request<any[]>("/api/agents"),
  getAgent: (id: string) => request<any>(`/api/agents/${id}`),

  listWorkflows: () => request<any[]>("/api/workflows"),
  getWorkflow: (id: string) => request<any>(`/api/workflows/${id}`),
  executeWorkflow: (id: string, goal: string) =>
    request<{ execution_id: string; status: string }>(`/api/workflows/${id}/execute`, {
      method: "POST", body: JSON.stringify({ goal }),
    }),
  executeGoal: (goal: string) =>
    request<{ execution_id: string; status: string }>("/api/goals/execute", {
      method: "POST", body: JSON.stringify({ goal }),
    }),

  listExecutions: () => request<any[]>("/api/executions"),
  getExecution: (id: string) => request<any>(`/api/executions/${id}`),

  listApprovals: () => request<any[]>("/api/approvals"),
  approveApproval: (id: string) => request<any>(`/api/approvals/${id}/approve`, { method: "POST" }),
  rejectApproval: (id: string) => request<any>(`/api/approvals/${id}/reject`, { method: "POST" }),

  listTools: () => request<{ catalog: any[]; runtime_registered: string[] }>("/api/tools"),

  monitoringSummary: () => request<any>("/api/monitoring/summary"),
  costByModel: () => request<any[]>("/api/monitoring/cost-by-model"),

  listAuditLogs: () => request<any[]>("/api/audit-logs"),

  listEvaluations: () => request<any[]>("/api/evaluations"),
};
