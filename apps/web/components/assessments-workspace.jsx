"use client";

import { useEffect, useState } from "react";

import {
  createAssessmentReportRequest,
  dashboardSummaryRequest,
  listAssessmentReportsRequest
} from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialForm() {
  return {
    job_order_id: "",
    candidate_id: "",
    phone_screen_id: "",
    status: "DRAFT"
  };
}

export function AssessmentsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ jobs: [], candidates: [], phone_screens: [] });
  const [reports, setReports] = useState([]);
  const [draft, setDraft] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const [dashboard, assessmentRows] = await Promise.all([
      dashboardSummaryRequest(stored.token),
      listAssessmentReportsRequest(stored.token)
    ]);
    setSummary(dashboard);
    setReports(assessmentRows);
    setForm((current) => ({
      ...current,
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || "",
      candidate_id: current.candidate_id || dashboard.candidates[0]?.id || "",
      phone_screen_id: current.phone_screen_id || dashboard.phone_screens?.[0]?.id || ""
    }));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await createAssessmentReportRequest(session.token, {
        job_order_id: form.job_order_id,
        candidate_id: form.candidate_id,
        phone_screen_id: form.phone_screen_id || null,
        status: form.status
      });
      setDraft(response);
      setMessage(`Assessment ${response.id} generated.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <div className="span-5">
        <Panel title="Assessment generator" copy="Turn score evidence and phone-screen readout into a reusable consultant evaluation artifact.">
          <form className="composer" onSubmit={handleCreate}>
            <select className="inline-input" value={form.job_order_id} onChange={(event) => setForm((current) => ({ ...current, job_order_id: event.target.value }))}>
              <option value="">Select job</option>
              {summary.jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <select className="inline-input" value={form.candidate_id} onChange={(event) => setForm((current) => ({ ...current, candidate_id: event.target.value }))}>
              <option value="">Select candidate</option>
              {summary.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
            </select>
            <select className="inline-input" value={form.phone_screen_id} onChange={(event) => setForm((current) => ({ ...current, phone_screen_id: event.target.value }))}>
              <option value="">Link phone screen (optional)</option>
              {(summary.phone_screens || []).map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}
            </select>
            <button className="button" type="submit" disabled={busy || !form.job_order_id || !form.candidate_id}>
              {busy ? "Generating..." : "Create assessment"}
            </button>
          </form>
          {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Assessment reports" copy="Assessment output stays structured and reusable for client-facing recommendation prep.">
          <DenseTable
            columns={[
              { key: "candidate_id", label: "Candidate" },
              { key: "job_order_id", label: "Job" },
              { key: "status", label: "Status" },
              { key: "score_snapshot", label: "Score" }
            ]}
            rows={reports}
          />
          {draft ? <pre className="code-block tiny" style={{ marginTop: "18px" }}>{draft.narrative_markdown}</pre> : null}
        </Panel>
      </div>
    </div>
  );
}
