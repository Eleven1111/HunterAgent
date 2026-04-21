"use client";

import { useEffect, useState } from "react";

import {
  createSubmissionDraftRequest,
  dashboardSummaryRequest,
  listSubmissionsRequest,
  requestApprovalRequest
} from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

export function SubmissionsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ jobs: [], candidates: [] });
  const [submissions, setSubmissions] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const [dashboard, submissionRows] = await Promise.all([
      dashboardSummaryRequest(stored.token),
      listSubmissionsRequest(stored.token)
    ]);
    setSummary(dashboard);
    setSubmissions(submissionRows);
    setSelectedJobId((current) => current || dashboard.jobs[0]?.id || "");
    setSelectedCandidateId((current) => current || dashboard.candidates[0]?.id || "");
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDraft() {
    if (!session.token || !selectedJobId || !selectedCandidateId) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await createSubmissionDraftRequest(session.token, {
        job_order_id: selectedJobId,
        candidate_id: selectedCandidateId,
        include_gap_analysis: true
      });
      setDraft(response);
      setMessage(`Draft ${response.id} created.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleApprovalRequest(submissionId) {
    if (!session.token) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const approval = await requestApprovalRequest(session.token, {
        action: "submit_recommendation",
        resource_type: "submission",
        resource_id: submissionId,
        payload: { target_status: "SUBMITTED" }
      });
      setMessage(`Approval ${approval.id} requested for ${submissionId}.`);
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
        <Panel title="Draft recommendation" copy="Create the recommendation artifact before it enters the approval lane.">
          <div className="composer">
            <select className="inline-input" value={selectedJobId} onChange={(event) => setSelectedJobId(event.target.value)}>
              <option value="">Select job</option>
              {summary.jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
            <select className="inline-input" value={selectedCandidateId} onChange={(event) => setSelectedCandidateId(event.target.value)}>
              <option value="">Select candidate</option>
              {summary.candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name}
                </option>
              ))}
            </select>
            <button className="button" type="button" disabled={busy || !selectedJobId || !selectedCandidateId} onClick={handleDraft}>
              {busy ? "Drafting..." : "Create draft"}
            </button>
            {message ? <div className="tiny">{message}</div> : null}
            {draft ? <pre className="tiny" style={{ whiteSpace: "pre-wrap" }}>{draft.draft_markdown}</pre> : null}
          </div>
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Submission lane" copy="Drafts stay here until a consultant explicitly requests approval for a formal write.">
          <DenseTable
            columns={[
              { key: "id", label: "Submission" },
              { key: "status", label: "Status" },
              { key: "version", label: "Version" },
              { key: "job_order_id", label: "Job" }
            ]}
            rows={submissions}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {submissions.slice(0, 4).map((submission) => (
              <div className="list-row" key={submission.id}>
                <div>
                  <div className="eyebrow">{submission.status}</div>
                  <div className="row-title">{submission.id}</div>
                </div>
                <div className="tiny">{submission.candidate_id}</div>
                <div className="tiny">v{submission.version}</div>
                <div>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={busy || submission.status !== "DRAFT"}
                    onClick={() => handleApprovalRequest(submission.id)}
                  >
                    Request approval
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
