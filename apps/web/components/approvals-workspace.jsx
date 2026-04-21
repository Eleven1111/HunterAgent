"use client";

import { useEffect, useState } from "react";

import { dashboardSummaryRequest, decideApprovalRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

export function ApprovalsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [approvals, setApprovals] = useState([]);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const dashboard = await dashboardSummaryRequest(stored.token);
    setApprovals(dashboard.approvals || []);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDecision(approvalId, decision) {
    if (!session.token) {
      return;
    }
    setBusyId(approvalId);
    setMessage("");
    try {
      const response = await decideApprovalRequest(session.token, approvalId, {
        decision,
        reason: decision === "APPROVED" ? "Approved in workbench" : "Rejected in workbench"
      });
      setMessage(`Approval ${response.id} marked ${response.status}.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusyId("");
    }
  }

  return (
    <Panel title="Approval desk" copy="Owner and team-admin sessions can move formal writes from pending to approved or rejected.">
      <DenseTable
        columns={[
          { key: "action", label: "Action" },
          { key: "resource_id", label: "Resource" },
          { key: "requested_by", label: "Requester" },
          { key: "status", label: "Status" }
        ]}
        rows={approvals}
      />
      <div className="list" style={{ marginTop: "18px" }}>
        {approvals.map((approval) => (
          <div className="list-row" key={approval.id}>
            <div>
              <div className="eyebrow">{approval.resource_type}</div>
              <div className="row-title">{approval.action}</div>
            </div>
            <div className="tiny">{approval.resource_id}</div>
            <div>
              <span className={`pill ${approval.status === "APPROVED" ? "accent" : approval.status === "REJECTED" ? "danger" : "warn"}`}>
                {approval.status}
              </span>
            </div>
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
              <button
                className="button secondary"
                type="button"
                disabled={busyId === approval.id || approval.status !== "PENDING"}
                onClick={() => handleDecision(approval.id, "APPROVED")}
              >
                Approve
              </button>
              <button
                className="button secondary"
                type="button"
                disabled={busyId === approval.id || approval.status !== "PENDING"}
                onClick={() => handleDecision(approval.id, "REJECTED")}
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
      {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
    </Panel>
  );
}

