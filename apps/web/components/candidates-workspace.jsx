"use client";

import { useEffect, useState } from "react";

import { dashboardSummaryRequest, importCandidateRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialForm() {
  return {
    job_order_id: "",
    full_name: "",
    current_company: "",
    current_title: "",
    city: "",
    email: "",
    phone: "",
    resume_text: ""
  };
}

export function CandidatesWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ jobs: [], candidates: [] });
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const dashboard = await dashboardSummaryRequest(stored.token);
    setSummary(dashboard);
    setForm((current) => ({
      ...current,
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || ""
    }));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await importCandidateRequest(session.token, form);
      setMessage(response.deduped ? "Candidate deduped into an existing record." : "Candidate imported into the pipeline.");
      setForm(initialForm());
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  const rows = summary.candidates.map((candidate) => ({
    id: candidate.id,
    name: candidate.full_name,
    title: candidate.current_title || "Title pending",
    company: candidate.current_company || "Company pending",
    source: candidate.source_type
  }));

  return (
    <div className="grid">
      <div className="span-5">
        <Panel title="Import candidate" copy="Manual import remains the mainline candidate entry path for the pilot.">
          <form className="composer" onSubmit={handleSubmit}>
            <select
              className="inline-input"
              value={form.job_order_id}
              onChange={(event) => setForm((current) => ({ ...current, job_order_id: event.target.value }))}
            >
              <option value="">Attach to job</option>
              {summary.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
            <input className="inline-input" value={form.full_name} onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))} placeholder="Candidate name" />
            <input className="inline-input" value={form.current_title} onChange={(event) => setForm((current) => ({ ...current, current_title: event.target.value }))} placeholder="Current title" />
            <input className="inline-input" value={form.current_company} onChange={(event) => setForm((current) => ({ ...current, current_company: event.target.value }))} placeholder="Current company" />
            <textarea value={form.resume_text} onChange={(event) => setForm((current) => ({ ...current, resume_text: event.target.value }))} placeholder="Paste resume summary or profile notes" />
            <button className="button" type="submit" disabled={busy || !form.full_name || !form.resume_text}>
              {busy ? "Importing..." : "Import candidate"}
            </button>
            {message ? <div className="tiny">{message}</div> : null}
          </form>
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Candidate ledger" copy="This table updates from the same tenant-scoped summary feed used by the dashboard.">
          <DenseTable
            columns={[
              { key: "name", label: "Candidate" },
              { key: "title", label: "Title" },
              { key: "company", label: "Company" },
              { key: "source", label: "Source" }
            ]}
            rows={rows}
          />
        </Panel>
      </div>
    </div>
  );
}

