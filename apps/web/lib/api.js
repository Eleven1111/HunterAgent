import { fallbackDashboard } from "@/lib/demo-data";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchJson(path, fallback) {
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!response.ok) {
      return fallback;
    }
    return await response.json();
  } catch {
    return fallback;
  }
}

export async function getDashboardData() {
  const [clients, jobs, candidates, approvals, audits] = await Promise.all([
    fetchJson("/api/v1/clients", []),
    fetchJson("/api/v1/job-orders", []),
    fetchJson("/api/v1/candidates", []),
    fetchJson("/api/v1/approvals", []),
    fetchJson("/api/v1/audit-logs", [])
  ]);

  if (!jobs.length && !clients.length) {
    return fallbackDashboard;
  }

  return {
    hero: {
      title: "Consultant control plane.",
      copy: "The workbench is the operating surface. Chat is a fast path into the same scoring, drafting, approval, and replay services."
    },
    metrics: [
      { label: "Open jobs", value: String(jobs.length).padStart(2, "0"), foot: `${clients.length} active clients` },
      { label: "Candidates", value: String(candidates.length).padStart(2, "0"), foot: "PII masked in default lists" },
      { label: "Pending approvals", value: String(approvals.filter((item) => item.status === "PENDING").length).padStart(2, "0"), foot: "Formal writes are gated" },
      { label: "Audit events", value: String(audits.length).padStart(2, "0"), foot: "Replay-ready event trail" }
    ],
    jobs: jobs.slice(0, 4).map((job) => ({
      title: `${job.title} / ${job.client_id}`,
      owner: job.owner_id,
      stage: job.status,
      count: `${job.must_have?.length || 0} must-have signals`
    })),
    approvals: approvals.slice(0, 4).map((approval) => ({
      title: `${approval.action} -> ${approval.resource_id}`,
      owner: approval.requested_by,
      status: approval.status
    })),
    audits: audits.slice(0, 6).map((audit) => ({
      event: audit.event_type,
      resource: audit.resource_type,
      detail: audit.resource_id
    })),
    candidates: candidates.slice(0, 6).map((candidate) => ({
      name: candidate.full_name,
      title: candidate.current_title || "Title pending",
      company: candidate.current_company || "Company pending",
      city: candidate.city || "City pending",
      source: candidate.source_type
    }))
  };
}

