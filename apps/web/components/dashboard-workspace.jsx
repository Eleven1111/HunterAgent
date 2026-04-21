"use client";

import { startTransition, useEffect, useState } from "react";

import { fallbackDashboard } from "@/lib/demo-data";
import { createClientRequest, createJobRequest, dashboardSummaryRequest, meRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { MetricRow } from "@/components/metric-row";
import { Panel } from "@/components/panel";

function initialClientForm() {
  return { name: "", industry: "", size: "", notes: "" };
}

function initialJobForm() {
  return { client_id: "", title: "", level: "", jd: "", must_have: "" };
}

export function DashboardWorkspace() {
  const [summary, setSummary] = useState(fallbackDashboard);
  const [session, setSession] = useState({ token: "", user: null });
  const [clientForm, setClientForm] = useState(initialClientForm);
  const [jobForm, setJobForm] = useState(initialJobForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    try {
      const [user, dashboard] = await Promise.all([
        meRequest(stored.token),
        dashboardSummaryRequest(stored.token)
      ]);
      startTransition(() => {
        setSession({ token: stored.token, user });
        setSummary({
          hero: {
            title: `Good hunting, ${user.name}.`,
            copy: "Workbench and chat are now reading from the same API session rather than demo-only fallback data."
          },
          metrics: [
            {
              label: "Open jobs",
              value: String(dashboard.metrics.open_jobs).padStart(2, "0"),
              foot: `${dashboard.clients.length} active clients`
            },
            {
              label: "Candidates",
              value: String(dashboard.metrics.candidates).padStart(2, "0"),
              foot: "Masked by default"
            },
            {
              label: "Pending approvals",
              value: String(dashboard.metrics.pending_approvals).padStart(2, "0"),
              foot: "Formal writes remain gated"
            },
            {
              label: "Buffered source items",
              value: String(dashboard.metrics.buffered_source_items).padStart(2, "0"),
              foot: "Experimental lane only"
            },
            {
              label: "Phone screens",
              value: String(dashboard.metrics.phone_screens).padStart(2, "0"),
              foot: "Internal screening calls"
            },
            {
              label: "Assessments",
              value: String(dashboard.metrics.assessment_reports).padStart(2, "0"),
              foot: "Ready for consultant packaging"
            },
            {
              label: "Interviews",
              value: String(dashboard.metrics.scheduled_interviews).padStart(2, "0"),
              foot: "Planned or confirmed"
            },
            {
              label: "Open invoices",
              value: String(dashboard.metrics.open_invoices).padStart(2, "0"),
              foot: "Pilot billing lane"
            }
          ],
          jobs: dashboard.jobs.map((job) => ({
            id: job.id,
            title: `${job.title} / ${job.client_id}`,
            owner: job.owner_id,
            stage: job.status,
            count: `${job.must_have_count} must-have signals`
          })),
          approvals: dashboard.approvals.map((approval) => ({
            id: approval.id,
            title: `${approval.action} -> ${approval.resource_id}`,
            owner: approval.requested_by,
            status: approval.status
          })),
          audits: dashboard.audits.map((audit) => ({
            id: audit.id,
            event: audit.event_type,
            resource: audit.resource_type,
            detail: audit.resource_id
          })),
          candidates: dashboard.candidates.map((candidate) => ({
            id: candidate.id,
            name: candidate.full_name,
            title: candidate.current_title || "Title pending",
            company: candidate.current_company || "Company pending",
            city: candidate.city || "City pending",
            source: candidate.source_type
          })),
          clients: dashboard.clients
        });
        setJobForm((current) => ({
          ...current,
          client_id:
            current.client_id || dashboard.clients[0]?.id || ""
        }));
      });
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreateClient(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createClientRequest(session.token, clientForm);
      setClientForm(initialClientForm());
      await refresh();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateJob(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createJobRequest(session.token, {
        client_id: jobForm.client_id,
        title: jobForm.title,
        level: jobForm.level,
        jd: jobForm.jd,
        must_have: jobForm.must_have
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      });
      setJobForm(initialJobForm());
      await refresh();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <div>
            <div className="hero-kicker">Mainline control room</div>
            <h1>{summary.hero.title}</h1>
            <p>{summary.hero.copy}</p>
          </div>
          <div className="tiny">
            {session.user ? `${session.user.email} · ${session.user.role}` : "Demo fallback"}
          </div>
        </div>
        <div className="hero-side">
          <div className="signal-stack">
            <div className="signal">
              <div className="signal-label">Session actor</div>
              <div className="signal-value">{session.user?.name || "Not resolved"}</div>
            </div>
            <div className="signal">
              <div className="signal-label">Write discipline</div>
              <div className="signal-value">Approval gated</div>
            </div>
            <div className="signal">
              <div className="signal-label">Experimental sourcing</div>
              <div className="signal-value">Buffered review lane</div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid">
        <div className="span-12">
          <MetricRow items={summary.metrics} />
        </div>

        <div className="span-7">
          <Panel title="Open search lanes" copy="Live data from the aggregated dashboard summary endpoint.">
            <div className="list">
              {summary.jobs.map((job) => (
                <div className="list-row" key={job.id || job.title}>
                  <div>
                    <div className="eyebrow">Job</div>
                    <div className="row-title">{job.title}</div>
                  </div>
                  <div className="tiny">{job.owner}</div>
                  <div>
                    <span className="pill accent">{job.stage}</span>
                  </div>
                  <div className="tiny">{job.count}</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <div className="span-5">
          <Panel title="Quick create" copy="Pilot surface for creating clients and search lanes without leaving the dashboard.">
            <form className="composer" onSubmit={handleCreateClient}>
              <input
                className="inline-input"
                value={clientForm.name}
                onChange={(event) => setClientForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Client name"
              />
              <input
                className="inline-input"
                value={clientForm.industry}
                onChange={(event) => setClientForm((current) => ({ ...current, industry: event.target.value }))}
                placeholder="Industry"
              />
              <div className="composer-row">
                <input
                  className="inline-input"
                  value={clientForm.size}
                  onChange={(event) => setClientForm((current) => ({ ...current, size: event.target.value }))}
                  placeholder="Size"
                />
                <button className="button" type="submit" disabled={busy}>
                  Add client
                </button>
              </div>
            </form>
            <form className="composer" onSubmit={handleCreateJob}>
              <select
                className="inline-input"
                value={jobForm.client_id}
                onChange={(event) => setJobForm((current) => ({ ...current, client_id: event.target.value }))}
              >
                <option value="">Select client</option>
                {(summary.clients || []).map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
              <input
                className="inline-input"
                value={jobForm.title}
                onChange={(event) => setJobForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Job title"
              />
              <input
                className="inline-input"
                value={jobForm.must_have}
                onChange={(event) => setJobForm((current) => ({ ...current, must_have: event.target.value }))}
                placeholder="Must-haves, comma separated"
              />
              <button className="button secondary" type="submit" disabled={busy || !jobForm.client_id}>
                Add job
              </button>
            </form>
            {error ? <div className="tiny" style={{ color: "var(--danger)" }}>{error}</div> : null}
          </Panel>
        </div>

        <div className="span-6">
          <Panel title="Recent candidate motion" copy="Imports and promoted source items still converge into one candidate system.">
            <div className="list">
              {summary.candidates.map((candidate) => (
                <div className="list-row" key={candidate.id || candidate.name}>
                  <div>
                    <div className="eyebrow">{candidate.source}</div>
                    <div className="row-title">{candidate.name}</div>
                  </div>
                  <div className="tiny">{candidate.title}</div>
                  <div className="tiny">{candidate.company}</div>
                  <div className="tiny">{candidate.city}</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <div className="span-6">
          <Panel title="Approval and audit pulse" copy="Writes and replay stay adjacent in the operating surface.">
            <div className="list">
              {summary.approvals.map((approval) => (
                <div className="list-row" key={approval.id || approval.title}>
                  <div>
                    <div className="eyebrow">Approval</div>
                    <div className="row-title">{approval.title}</div>
                  </div>
                  <div className="tiny">{approval.owner}</div>
                  <div>
                    <span className="pill warn">{approval.status}</span>
                  </div>
                  <div className="tiny">Diff ready</div>
                </div>
              ))}
              {summary.audits.slice(0, 3).map((audit) => (
                <div className="list-row" key={audit.id || `${audit.event}-${audit.detail}`}>
                  <div>
                    <div className="eyebrow">{audit.resource}</div>
                    <div className="row-title">{audit.event}</div>
                  </div>
                  <div className="tiny">{audit.detail}</div>
                  <div>
                    <span className="pill">{audit.resource}</span>
                  </div>
                  <div className="tiny">Replayable</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}
