"use client";

import { useEffect, useMemo, useState } from "react";

import { listAuditLogsRequest, replayRunRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function statusTone(value) {
  if (value === "APPROVED" || value === "COMPLETED" || value === "SUBMITTED") {
    return "accent";
  }
  if (value === "REJECTED" || value === "FAILED") {
    return "danger";
  }
  return "warn";
}

function formatDate(value) {
  if (!value) {
    return "No timestamp";
  }
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function renderValue(value) {
  if (value === null || value === undefined) {
    return "None";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

export function AuditWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [logs, setLogs] = useState([]);
  const [replay, setReplay] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function load() {
      const stored = readStoredSession();
      setSession(stored);
      if (!stored.token) {
        return;
      }
      try {
        const response = await listAuditLogsRequest(stored.token);
        setLogs(response);
      } catch (error) {
        setMessage(error.message);
      }
    }
    load();
  }, []);

  const timelineEntries = useMemo(() => {
    if (!replay) {
      return [];
    }
    const stepEntries = replay.run.steps.map((step, index) => ({
      id: `step-${step.step_id}`,
      kind: "STEP",
      order: index,
      title: step.summary,
      subtitle: step.kind,
      status: step.status,
      timestamp: replay.run.started_at,
      detail: step.output,
      diff: null
    }));
    const eventEntries = replay.audit_events.map((event, index) => ({
      id: event.id,
      kind: "EVENT",
      order: replay.run.steps.length + index,
      title: `${event.event_type} · ${event.resource_type}`,
      subtitle: event.resource_id,
      status: event.metadata?.decision || event.event_type,
      timestamp: event.created_at,
      detail: event.metadata,
      diff: event.state_diff
    }));
    return [...stepEntries, ...eventEntries].sort((left, right) => left.order - right.order);
  }, [replay]);

  async function handleReplay(runId) {
    if (!session.token || !runId) {
      return;
    }
    try {
      const response = await replayRunRequest(session.token, runId);
      setReplay(response);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <div className="grid">
      <div className="span-5">
        <Panel title="Audit replay lane" copy="Recent audited events from the same mainline flow that drives scoring, drafting, and approvals.">
          <DenseTable
            columns={[
              { key: "event_type", label: "Event" },
              { key: "resource_type", label: "Resource" },
              { key: "resource_id", label: "Resource ID" },
              { key: "actor_user_id", label: "Actor" }
            ]}
            rows={logs}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {logs.slice(0, 8).map((log) => (
              <div className="list-row" key={log.id}>
                <div>
                  <div className="eyebrow">{formatDate(log.created_at)}</div>
                  <div className="row-title">{log.event_type}</div>
                </div>
                <div className="tiny">{log.resource_type}</div>
                <div className="tiny">{log.run_id || "No run"}</div>
                <div>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={!log.run_id}
                    onClick={() => handleReplay(log.run_id)}
                  >
                    Open replay
                  </button>
                </div>
              </div>
            ))}
          </div>
          {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
        </Panel>
      </div>

      <div className="span-7">
        <Panel
          title="Run timeline"
          copy={replay ? "Replay keeps run steps, audited mutations, and state changes in one linear strip." : "Select an event with a run id to inspect the full replay timeline."}
        >
          {replay ? (
            <div className="timeline-shell">
              <div className="timeline-head">
                <div>
                  <div className="eyebrow">{replay.run.channel} · {formatDate(replay.run.started_at)}</div>
                  <div className="row-title">{replay.run.goal}</div>
                </div>
                <div className="action-row" style={{ justifyContent: "flex-end" }}>
                  <span className={`pill ${statusTone(replay.run.status)}`}>{replay.run.status}</span>
                  <span className="pill">{replay.run.model_name || "No model"}</span>
                  <span className="pill">{replay.run.model_version || "No version"}</span>
                </div>
              </div>
              <div className="timeline">
                {timelineEntries.map((entry, index) => (
                  <article className="timeline-card" key={entry.id}>
                    <div className="timeline-marker">{index + 1}</div>
                    <div className="timeline-body">
                      <div className="timeline-meta">
                        <span className="eyebrow">{entry.kind}</span>
                        <span className={`pill ${statusTone(entry.status)}`}>{entry.status}</span>
                        <span className="tiny">{formatDate(entry.timestamp)}</span>
                      </div>
                      <h3 className="timeline-title">{entry.title}</h3>
                      <div className="tiny">{entry.subtitle}</div>
                      {entry.diff?.before || entry.diff?.after ? (
                        <div className="diff-grid">
                          <div className="diff-card">
                            <div className="eyebrow">Before</div>
                            <pre className="code-block tiny">{renderValue(entry.diff.before)}</pre>
                          </div>
                          <div className="diff-card">
                            <div className="eyebrow">After</div>
                            <pre className="code-block tiny">{renderValue(entry.diff.after)}</pre>
                          </div>
                        </div>
                      ) : null}
                      {entry.detail && Object.keys(entry.detail).length ? (
                        <pre className="code-block tiny">{JSON.stringify(entry.detail, null, 2)}</pre>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="tiny">No replay loaded yet.</div>
          )}
        </Panel>
      </div>
    </div>
  );
}
