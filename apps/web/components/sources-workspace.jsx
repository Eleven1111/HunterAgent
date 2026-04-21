"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  createSourceRunRequest,
  dashboardSummaryRequest,
  getSourceRunRequest,
  listSourceAdaptersRequest,
  listSourceRunsRequest,
  promoteSourceItemRequest,
  reviewSourceItemRequest
} from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialForm() {
  return {
    job_order_id: "",
    source_name: "structured-import",
    source_label: "",
    full_name: "",
    current_company: "",
    current_title: "",
    city: "",
    email: "",
    phone: "",
    resume_text: ""
  };
}

export function SourcesWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [jobs, setJobs] = useState([]);
  const [sourceRuns, setSourceRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [activeRunId, setActiveRunId] = useState("");
  const [adapterSpecs, setAdapterSpecs] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [promotionResult, setPromotionResult] = useState(null);
  const [featureState, setFeatureState] = useState("unknown");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function loadRunDetails(token, runId) {
    if (!runId) {
      setActiveRun(null);
      setActiveRunId("");
      return;
    }
    const payload = await getSourceRunRequest(token, runId);
    setActiveRun(payload);
    setActiveRunId(runId);
  }

  async function refresh(preferredRunId = "") {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const dashboard = await dashboardSummaryRequest(stored.token);
    setJobs(dashboard.jobs || []);
    setForm((current) => ({
      ...current,
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || ""
    }));
    try {
      const [runs, adapters] = await Promise.all([
        listSourceRunsRequest(stored.token),
        listSourceAdaptersRequest(stored.token)
      ]);
      setSourceRuns(runs);
      setAdapterSpecs(adapters);
      setFeatureState("enabled");
      const nextRunId = preferredRunId || activeRunId || runs[0]?.id || "";
      await loadRunDetails(stored.token, nextRunId);
    } catch (error) {
      if (error.message === "Experimental sourcing is disabled") {
        setFeatureState("disabled");
        setSourceRuns([]);
        setAdapterSpecs([]);
        setActiveRun(null);
        setActiveRunId("");
      } else {
        setFeatureState("error");
        setMessage(error.message);
      }
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSelectRun(runId) {
    if (!session.token) {
      return;
    }
    setBusy(`run:${runId}`);
    setMessage("");
    try {
      await loadRunDetails(session.token, runId);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleCreateRun(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy("create");
    setMessage("");
    try {
      const response = await createSourceRunRequest(session.token, {
        job_order_id: form.job_order_id,
        source_name: form.source_name,
        items: [
          {
            full_name: form.full_name,
            current_company: form.current_company,
            current_title: form.current_title,
            city: form.city,
            email: form.email,
            phone: form.phone,
            resume_text: form.resume_text
          }
        ],
        source_config: {
          source_label: form.source_label
        }
      });
      setMessage(`Buffered source run ${response.run.id} with ${response.items.length} candidate item.`);
      setPromotionResult(null);
      setForm(initialForm());
      await refresh(response.run.id);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleReview(itemId, decision) {
    if (!session.token) {
      return;
    }
    setBusy(itemId);
    setMessage("");
    try {
      const response = await reviewSourceItemRequest(session.token, itemId, {
        decision,
        note: `${decision} in workbench`
      });
      setPromotionResult(null);
      setMessage(`Item ${response.item.id} marked ${response.item.review_status}.`);
      await refresh(activeRunId);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handlePromote(itemId) {
    if (!session.token) {
      return;
    }
    setBusy(itemId);
    setMessage("");
    try {
      const response = await promoteSourceItemRequest(session.token, itemId);
      setPromotionResult(response);
      setMessage(`Promoted buffered item into candidate ${response.candidate.id}.`);
      await refresh(activeRunId);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  const activeAdapter = adapterSpecs.find((adapter) => adapter.name === form.source_name);
  const activeItems = activeRun?.items || [];

  return (
    <div className="grid">
      <div className="span-4">
        <Panel
          title="Controlled source import"
          copy="Only manual, provenance-tagged imports are exposed in the release lane. Every buffered item must be reviewed before it can promote into the candidate system."
        >
          {featureState === "disabled" ? (
            <div className="tiny">
              Experimental sourcing is currently disabled. Set `ENABLE_EXPERIMENTAL_SOURCING=true` before using this lane.
            </div>
          ) : (
            <form className="composer" onSubmit={handleCreateRun}>
              <select
                className="inline-input"
                value={form.job_order_id}
                onChange={(event) => setForm((current) => ({ ...current, job_order_id: event.target.value }))}
              >
                <option value="">Attach to job</option>
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title}
                  </option>
                ))}
              </select>
              <select
                className="inline-input"
                value={form.source_name}
                onChange={(event) => setForm((current) => ({ ...current, source_name: event.target.value }))}
              >
                {adapterSpecs.map((adapter) => (
                  <option key={adapter.name} value={adapter.name}>
                    {adapter.name}
                  </option>
                ))}
              </select>
              {activeAdapter ? <div className="tiny">{activeAdapter.description}</div> : null}
              <input
                className="inline-input"
                value={form.source_label}
                onChange={(event) => setForm((current) => ({ ...current, source_label: event.target.value }))}
                placeholder="Provenance label (for example, referral sheet or partner handoff)"
              />
              <input
                className="inline-input"
                value={form.full_name}
                onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                placeholder="Candidate name"
              />
              <input
                className="inline-input"
                value={form.current_title}
                onChange={(event) => setForm((current) => ({ ...current, current_title: event.target.value }))}
                placeholder="Current title"
              />
              <input
                className="inline-input"
                value={form.current_company}
                onChange={(event) => setForm((current) => ({ ...current, current_company: event.target.value }))}
                placeholder="Current company"
              />
              <input
                className="inline-input"
                value={form.city}
                onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))}
                placeholder="City"
              />
              <input
                className="inline-input"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="Email"
              />
              <input
                className="inline-input"
                value={form.phone}
                onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
                placeholder="Phone"
              />
              <textarea
                value={form.resume_text}
                onChange={(event) => setForm((current) => ({ ...current, resume_text: event.target.value }))}
                placeholder="Paste normalized source summary or extracted notes"
              />
              <button
                className="button"
                type="submit"
                disabled={busy === "create" || !form.job_order_id || !form.source_name || !form.source_label || !form.full_name || !form.resume_text}
              >
                {busy === "create" ? "Buffering..." : "Create source run"}
              </button>
            </form>
          )}
          {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
          {promotionResult ? (
            <div className="callout" style={{ marginTop: "16px" }}>
              <div className="eyebrow">Promotion handoff</div>
              <div className="row-title">{promotionResult.candidate.full_name || promotionResult.candidate.id}</div>
              <div className="tiny">
                Candidate {promotionResult.candidate.id}
                {promotionResult.pipeline_id ? ` entered pipeline ${promotionResult.pipeline_id}.` : " reused an existing candidate record."}
              </div>
              <div className="tiny">
                {promotionResult.candidate.email_masked || "No email"} · {promotionResult.candidate.phone_masked || "No phone"}
              </div>
              <div className="action-row" style={{ marginTop: "12px" }}>
                <Link className="button secondary" href="/candidates">Open candidates</Link>
                <Link className="button secondary" href="/jobs">Open jobs</Link>
                <Link className="button secondary" href="/submissions">Open submissions</Link>
              </div>
            </div>
          ) : null}
        </Panel>
      </div>

      <div className="span-3">
        <Panel title="Source runs" copy="Select a buffered run to inspect full item evidence before approve, reject, or promote.">
          <DenseTable
            columns={[
              { key: "source_name", label: "Source" },
              { key: "item_count", label: "Items" },
              { key: "status", label: "Status" }
            ]}
            rows={sourceRuns}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {sourceRuns.map((run) => (
              <button
                key={run.id}
                type="button"
                className={`list-row${activeRunId === run.id ? " active" : ""}`}
                style={{ width: "100%", textAlign: "left", background: "transparent", border: "1px solid var(--edge)" }}
                onClick={() => handleSelectRun(run.id)}
                disabled={busy === `run:${run.id}`}
              >
                <div>
                  <div className="eyebrow">{run.status}</div>
                  <div className="row-title">{run.source_name}</div>
                </div>
                <div className="tiny">{run.item_count} items</div>
                <div className="tiny">{run.job_order_id}</div>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="span-5">
        <Panel title="Run detail" copy="Review raw payload, normalized draft, provenance, and decision history before moving anything into the main candidate truth path.">
          {!activeRun ? (
            <div className="tiny">Select a source run to inspect buffered items.</div>
          ) : (
            <>
              <div className="callout" style={{ marginBottom: "18px" }}>
                <div className="eyebrow">{activeRun.run.status}</div>
                <div className="row-title">{activeRun.run.source_name}</div>
                <div className="tiny">Run {activeRun.run.id} · Job {activeRun.run.job_order_id}</div>
              </div>
              <div className="list">
                {activeItems.map((item) => (
                  <div className="list-row" key={item.id} style={{ display: "block" }}>
                    <div className="action-row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div className="eyebrow">{item.review_status}</div>
                        <div className="row-title">{item.normalized_draft?.full_name || item.id}</div>
                        <div className="tiny">
                          {item.raw_payload?.source_label || "No provenance label"}
                          {item.raw_payload?.source_url ? ` · ${item.raw_payload.source_url}` : ""}
                        </div>
                      </div>
                      <div className="action-row">
                        <button
                          className="button secondary"
                          type="button"
                          disabled={featureState !== "enabled" || busy === item.id || item.review_status !== "PENDING"}
                          onClick={() => handleReview(item.id, "APPROVED")}
                        >
                          Approve
                        </button>
                        <button
                          className="button secondary"
                          type="button"
                          disabled={featureState !== "enabled" || busy === item.id || item.review_status !== "PENDING"}
                          onClick={() => handleReview(item.id, "REJECTED")}
                        >
                          Reject
                        </button>
                        <button
                          className="button secondary"
                          type="button"
                          disabled={featureState !== "enabled" || busy === item.id || item.review_status !== "APPROVED" || Boolean(item.promoted_candidate_id)}
                          onClick={() => handlePromote(item.id)}
                        >
                          Promote
                        </button>
                      </div>
                    </div>
                    <div className="grid" style={{ marginTop: "14px" }}>
                      <div className="span-6">
                        <div className="eyebrow">Normalized draft</div>
                        <pre className="tiny">{JSON.stringify(item.normalized_draft, null, 2)}</pre>
                      </div>
                      <div className="span-6">
                        <div className="eyebrow">Raw payload</div>
                        <pre className="tiny">{JSON.stringify(item.raw_payload, null, 2)}</pre>
                      </div>
                    </div>
                    <div style={{ marginTop: "14px" }}>
                      <div className="eyebrow">Review history</div>
                      {item.reviews?.length ? (
                        <div className="list" style={{ marginTop: "10px" }}>
                          {item.reviews.map((review) => (
                            <div className="list-row" key={review.id}>
                              <div>
                                <div className="eyebrow">{review.decision}</div>
                                <div className="row-title">{review.reviewer_id}</div>
                              </div>
                              <div className="tiny">{review.note || "No note"}</div>
                              <div className="tiny">{review.created_at}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="tiny" style={{ marginTop: "10px" }}>No review decisions yet.</div>
                      )}
                    </div>
                    {item.promoted_candidate_id ? (
                      <div className="tiny" style={{ marginTop: "12px" }}>
                        Promoted candidate: {item.promoted_candidate_id}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}
