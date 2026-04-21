"use client";

import { useEffect, useState } from "react";

import {
  createInterviewPlanRequest,
  createPhoneScreenRequest,
  dashboardSummaryRequest,
  listInterviewPlansRequest,
  listPhoneScreensRequest,
  updateInterviewPlanRequest,
  updatePhoneScreenRequest
} from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialScreenForm() {
  return {
    job_order_id: "",
    candidate_id: "",
    scheduled_at: new Date().toISOString().slice(0, 16),
    duration_minutes: 30
  };
}

function initialPlanForm() {
  return {
    job_order_id: "",
    candidate_id: "",
    interviewer_name: "",
    stage: "CLIENT_INTERVIEW",
    scheduled_at: new Date().toISOString().slice(0, 16),
    location: "",
    notes: ""
  };
}

export function InterviewsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ jobs: [], candidates: [] });
  const [phoneScreens, setPhoneScreens] = useState([]);
  const [interviewPlans, setInterviewPlans] = useState([]);
  const [screenForm, setScreenForm] = useState(initialScreenForm);
  const [planForm, setPlanForm] = useState(initialPlanForm);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const [dashboard, screens, plans] = await Promise.all([
      dashboardSummaryRequest(stored.token),
      listPhoneScreensRequest(stored.token),
      listInterviewPlansRequest(stored.token)
    ]);
    setSummary(dashboard);
    setPhoneScreens(screens);
    setInterviewPlans(plans);
    setScreenForm((current) => ({
      ...current,
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || "",
      candidate_id: current.candidate_id || dashboard.candidates[0]?.id || ""
    }));
    setPlanForm((current) => ({
      ...current,
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || "",
      candidate_id: current.candidate_id || dashboard.candidates[0]?.id || ""
    }));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreateScreen(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy("create-screen");
    setMessage("");
    try {
      const response = await createPhoneScreenRequest(session.token, screenForm);
      setMessage(`Phone screen ${response.id} scheduled.`);
      setScreenForm(initialScreenForm());
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleUpdateScreen(screenId, statusValue, recommendation) {
    if (!session.token) {
      return;
    }
    setBusy(screenId);
    setMessage("");
    try {
      const response = await updatePhoneScreenRequest(session.token, screenId, {
        status: statusValue,
        call_summary: `${statusValue} via workbench.`,
        recommendation
      });
      setMessage(`Phone screen ${response.id} moved to ${response.status}.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleCreatePlan(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy("create-plan");
    setMessage("");
    try {
      const response = await createInterviewPlanRequest(session.token, planForm);
      setMessage(`Interview plan ${response.id} created.`);
      setPlanForm(initialPlanForm());
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleUpdatePlan(planId, statusValue) {
    if (!session.token) {
      return;
    }
    setBusy(planId);
    setMessage("");
    try {
      const response = await updateInterviewPlanRequest(session.token, planId, {
        status: statusValue,
        notes: `${statusValue} in workbench`
      });
      setMessage(`Interview plan ${response.id} moved to ${response.status}.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="grid">
      <div className="span-5">
        <Panel title="Phone screen lane" copy="Schedule the internal screening call before producing the formal assessment.">
          <form className="composer" onSubmit={handleCreateScreen}>
            <select className="inline-input" value={screenForm.job_order_id} onChange={(event) => setScreenForm((current) => ({ ...current, job_order_id: event.target.value }))}>
              <option value="">Select job</option>
              {summary.jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <select className="inline-input" value={screenForm.candidate_id} onChange={(event) => setScreenForm((current) => ({ ...current, candidate_id: event.target.value }))}>
              <option value="">Select candidate</option>
              {summary.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
            </select>
            <input className="inline-input" type="datetime-local" value={screenForm.scheduled_at} onChange={(event) => setScreenForm((current) => ({ ...current, scheduled_at: event.target.value }))} />
            <input className="inline-input" type="number" min="15" step="15" value={screenForm.duration_minutes} onChange={(event) => setScreenForm((current) => ({ ...current, duration_minutes: Number(event.target.value) }))} />
            <button className="button" type="submit" disabled={busy === "create-screen" || !screenForm.job_order_id || !screenForm.candidate_id}>
              {busy === "create-screen" ? "Scheduling..." : "Schedule phone screen"}
            </button>
          </form>
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Phone screen log" copy="Use this log to close out the screening call and hand a recommendation into the assessment lane.">
          <DenseTable
            columns={[
              { key: "candidate_id", label: "Candidate" },
              { key: "job_order_id", label: "Job" },
              { key: "status", label: "Status" },
              { key: "scheduled_at", label: "Scheduled" }
            ]}
            rows={phoneScreens}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {phoneScreens.slice(0, 6).map((screen) => (
              <div className="list-row" key={screen.id}>
                <div>
                  <div className="eyebrow">{screen.status}</div>
                  <div className="row-title">{screen.id}</div>
                </div>
                <div className="tiny">{screen.candidate_id}</div>
                <div className="tiny">{screen.scheduled_at}</div>
                <div className="action-row" style={{ justifyContent: "flex-end" }}>
                  <button className="button secondary" type="button" disabled={busy === screen.id || screen.status === "COMPLETED"} onClick={() => handleUpdateScreen(screen.id, "COMPLETED", "Advance to client interview")}>
                    Complete
                  </button>
                  <button className="button secondary" type="button" disabled={busy === screen.id || screen.status === "COMPLETED"} onClick={() => handleUpdateScreen(screen.id, "COMPLETED", "Hold in reserve")}>
                    Hold
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="span-5">
        <Panel title="Interview coordination" copy="Coordinate the next client-facing interview once the phone screen has been closed.">
          <form className="composer" onSubmit={handleCreatePlan}>
            <select className="inline-input" value={planForm.job_order_id} onChange={(event) => setPlanForm((current) => ({ ...current, job_order_id: event.target.value }))}>
              <option value="">Select job</option>
              {summary.jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <select className="inline-input" value={planForm.candidate_id} onChange={(event) => setPlanForm((current) => ({ ...current, candidate_id: event.target.value }))}>
              <option value="">Select candidate</option>
              {summary.candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
            </select>
            <input className="inline-input" value={planForm.interviewer_name} onChange={(event) => setPlanForm((current) => ({ ...current, interviewer_name: event.target.value }))} placeholder="Interviewer name" />
            <input className="inline-input" type="datetime-local" value={planForm.scheduled_at} onChange={(event) => setPlanForm((current) => ({ ...current, scheduled_at: event.target.value }))} />
            <input className="inline-input" value={planForm.location} onChange={(event) => setPlanForm((current) => ({ ...current, location: event.target.value }))} placeholder="Location or meeting link" />
            <button className="button secondary" type="submit" disabled={busy === "create-plan" || !planForm.job_order_id || !planForm.candidate_id || !planForm.interviewer_name}>
              {busy === "create-plan" ? "Coordinating..." : "Create interview plan"}
            </button>
          </form>
          {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Coordination board" copy="Advance plans from planned to confirmed to completed without leaving the workbench.">
          <DenseTable
            columns={[
              { key: "interviewer_name", label: "Interviewer" },
              { key: "stage", label: "Stage" },
              { key: "status", label: "Status" },
              { key: "scheduled_at", label: "Scheduled" }
            ]}
            rows={interviewPlans}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {interviewPlans.slice(0, 6).map((plan) => (
              <div className="list-row" key={plan.id}>
                <div>
                  <div className="eyebrow">{plan.stage}</div>
                  <div className="row-title">{plan.interviewer_name}</div>
                </div>
                <div className="tiny">{plan.candidate_id}</div>
                <div className="tiny">{plan.scheduled_at}</div>
                <div className="action-row" style={{ justifyContent: "flex-end" }}>
                  <button className="button secondary" type="button" disabled={busy === plan.id || plan.status === "CONFIRMED" || plan.status === "COMPLETED"} onClick={() => handleUpdatePlan(plan.id, "CONFIRMED")}>
                    Confirm
                  </button>
                  <button className="button secondary" type="button" disabled={busy === plan.id || plan.status === "COMPLETED"} onClick={() => handleUpdatePlan(plan.id, "COMPLETED")}>
                    Complete
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
