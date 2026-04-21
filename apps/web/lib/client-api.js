"use client";

import { clearSession } from "@/lib/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function request(path, options = {}, token = "") {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token && token !== "cookie-session" ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }
  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
    }
    const detail = payload?.detail || "Request failed";
    throw new Error(detail);
  }
  return payload;
}

export async function loginRequest(email, password) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function meRequest(token) {
  return request("/api/v1/auth/me", {}, token);
}

export async function logoutRequest(token) {
  return request(
    "/api/v1/auth/logout",
    {
      method: "POST"
    },
    token
  );
}

export async function dashboardSummaryRequest(token) {
  return request("/api/v1/dashboard/summary", {}, token);
}

export async function createClientRequest(token, body) {
  return request(
    "/api/v1/clients",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function createJobRequest(token, body) {
  return request(
    "/api/v1/job-orders",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function updateClientStageRequest(token, clientId, body) {
  return request(
    `/api/v1/clients/${clientId}/stage`,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function importCandidateRequest(token, body) {
  return request(
    "/api/v1/candidates/import",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function runScoreRequest(token, body) {
  return request(
    "/api/v1/match-scores/run",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listSubmissionsRequest(token) {
  return request("/api/v1/submissions", {}, token);
}

export async function createSubmissionDraftRequest(token, body) {
  return request(
    "/api/v1/submissions/draft",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function submitSubmissionWithTokenRequest(token, submissionId, body) {
  return request(
    `/api/v1/submissions/${submissionId}/submit`,
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function requestApprovalRequest(token, body) {
  return request(
    "/api/v1/approvals",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listApprovalsRequest(token) {
  return request("/api/v1/approvals", {}, token);
}

export async function decideApprovalRequest(token, approvalId, body) {
  return request(
    `/api/v1/approvals/${approvalId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listAuditLogsRequest(token) {
  return request("/api/v1/audit-logs", {}, token);
}

export async function replayRunRequest(token, runId) {
  return request(`/api/v1/runs/${runId}/replay`, {}, token);
}

export async function listSourceRunsRequest(token) {
  return request("/api/v1/source-runs", {}, token);
}

export async function getSourceRunRequest(token, runId) {
  return request(`/api/v1/source-runs/${runId}`, {}, token);
}

export async function listSourceAdaptersRequest(token) {
  return request("/api/v1/source-adapters", {}, token);
}

export async function createSourceRunRequest(token, body) {
  return request(
    "/api/v1/source-runs",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function reviewSourceItemRequest(token, itemId, body) {
  return request(
    `/api/v1/source-items/${itemId}/review`,
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function promoteSourceItemRequest(token, itemId) {
  return request(
    `/api/v1/source-items/${itemId}/promote`,
    {
      method: "POST"
    },
    token
  );
}

export async function listPhoneScreensRequest(token) {
  return request("/api/v1/phone-screens", {}, token);
}

export async function createPhoneScreenRequest(token, body) {
  return request(
    "/api/v1/phone-screens",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function updatePhoneScreenRequest(token, screenId, body) {
  return request(
    `/api/v1/phone-screens/${screenId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listAssessmentReportsRequest(token) {
  return request("/api/v1/assessment-reports", {}, token);
}

export async function createAssessmentReportRequest(token, body) {
  return request(
    "/api/v1/assessment-reports",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listInterviewPlansRequest(token) {
  return request("/api/v1/interview-plans", {}, token);
}

export async function createInterviewPlanRequest(token, body) {
  return request(
    "/api/v1/interview-plans",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function updateInterviewPlanRequest(token, planId, body) {
  return request(
    `/api/v1/interview-plans/${planId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function listInvoicesRequest(token) {
  return request("/api/v1/invoices", {}, token);
}

export async function createInvoiceRequest(token, body) {
  return request(
    "/api/v1/invoices",
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    token
  );
}

export async function updateInvoiceRequest(token, invoiceId, body) {
  return request(
    `/api/v1/invoices/${invoiceId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    token
  );
}
