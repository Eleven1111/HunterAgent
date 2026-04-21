"use client";

import { useEffect, useMemo, useState } from "react";

import { dashboardSummaryRequest, runScoreRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

export function JobsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ jobs: [], candidates: [] });
  const [selectedJobId, setSelectedJobId] = useState("");
  const [selectedCandidateIds, setSelectedCandidateIds] = useState([]);
  const [scoreResult, setScoreResult] = useState(null);
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
    setSelectedJobId((current) => current || dashboard.jobs[0]?.id || "");
  }

  useEffect(() => {
    refresh();
  }, []);

  const candidateRows = useMemo(
    () =>
      summary.candidates.map((candidate) => ({
        id: candidate.id,
        label: `${candidate.full_name} · ${candidate.current_title || "Title pending"}`
      })),
    [summary.candidates]
  );

  function toggleCandidate(candidateId) {
    setSelectedCandidateIds((current) =>
      current.includes(candidateId)
        ? current.filter((item) => item !== candidateId)
        : [...current, candidateId]
    );
  }

  async function handleRunScore() {
    if (!session.token || !selectedJobId || !selectedCandidateIds.length) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await runScoreRequest(session.token, {
        job_order_id: selectedJobId,
        candidate_ids: selectedCandidateIds
      });
      setScoreResult(response);
      setMessage(`Scored ${response.scores.length} candidate(s).`);
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
        <Panel title="Run shortlist scoring" copy="Select a job and candidate set, then execute the deterministic scoring pass.">
          <div className="composer">
            <select className="inline-input" value={selectedJobId} onChange={(event) => setSelectedJobId(event.target.value)}>
              <option value="">Select job</option>
              {summary.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
            <div className="list">
              {candidateRows.map((candidate) => (
                <label className="list-row" key={candidate.id} style={{ gridTemplateColumns: "auto 1fr" }}>
                  <input
                    type="checkbox"
                    checked={selectedCandidateIds.includes(candidate.id)}
                    onChange={() => toggleCandidate(candidate.id)}
                  />
                  <span className="row-title">{candidate.label}</span>
                </label>
              ))}
            </div>
            <button className="button" type="button" disabled={busy || !selectedJobId || !selectedCandidateIds.length} onClick={handleRunScore}>
              {busy ? "Scoring..." : "Run score"}
            </button>
            {message ? <div className="tiny">{message}</div> : null}
          </div>
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Job orders" copy="Scoring output is shown next to the current job ledger so ranking and lane state stay close together.">
          <DenseTable
            columns={[
              { key: "title", label: "Job" },
              { key: "owner", label: "Owner" },
              { key: "stage", label: "State" },
              { key: "count", label: "Signal" }
            ]}
            rows={summary.jobs.map((job) => ({
              id: job.id,
              title: `${job.title} / ${job.client_id}`,
              owner: job.owner_id,
              stage: job.status,
              count: `${job.must_have_count} must-have signals`
            }))}
          />
          {scoreResult ? (
            <div style={{ marginTop: "18px" }}>
              <DenseTable
                columns={[
                  { key: "candidate_id", label: "Candidate" },
                  { key: "score", label: "Score" },
                  { key: "priority", label: "Priority" },
                  { key: "reason", label: "Top reason" }
                ]}
                rows={scoreResult.scores.map((score) => ({
                  id: score.id,
                  candidate_id: score.candidate_id,
                  score: score.score,
                  priority: score.priority,
                  reason: score.reason_codes[0] || "No evidence"
                }))}
              />
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

