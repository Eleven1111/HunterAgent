"use client";

import { useEffect, useState } from "react";

import { createClientRequest, dashboardSummaryRequest, updateClientStageRequest } from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialForm() {
  return { name: "", industry: "", size: "", notes: "" };
}

const nextStageMap = {
  LEAD: "CONTACTED",
  CONTACTED: "NEGOTIATING",
  NEGOTIATING: "SIGNED",
  SIGNED: "ACTIVE"
};

export function ClientsWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const dashboard = await dashboardSummaryRequest(stored.token);
    setClients(dashboard.clients || []);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    if (!session.token) {
      return;
    }
    setBusy("create");
    setMessage("");
    try {
      await createClientRequest(session.token, form);
      setForm(initialForm());
      setMessage("Client created.");
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleAdvance(client) {
    const nextStage = nextStageMap[client.stage];
    if (!session.token || !nextStage) {
      return;
    }
    setBusy(client.id);
    setMessage("");
    try {
      await updateClientStageRequest(session.token, client.id, { stage: nextStage });
      setMessage(`${client.name} moved to ${nextStage}.`);
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
        <Panel title="Create client" copy="Mainline pilot lane for account creation and stage progression.">
          <form className="composer" onSubmit={handleCreate}>
            <input className="inline-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Client name" />
            <input className="inline-input" value={form.industry} onChange={(event) => setForm((current) => ({ ...current, industry: event.target.value }))} placeholder="Industry" />
            <input className="inline-input" value={form.size} onChange={(event) => setForm((current) => ({ ...current, size: event.target.value }))} placeholder="Company size" />
            <button className="button" type="submit" disabled={busy === "create" || !form.name || !form.industry}>
              {busy === "create" ? "Creating..." : "Add client"}
            </button>
            {message ? <div className="tiny">{message}</div> : null}
          </form>
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Client ledger" copy="Each client follows the allowed linear flow from lead to active account.">
          <DenseTable
            columns={[
              { key: "name", label: "Account" },
              { key: "industry", label: "Industry" },
              { key: "stage", label: "Stage" },
              { key: "owner_id", label: "Owner" }
            ]}
            rows={clients}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {clients.map((client) => (
              <div className="list-row" key={client.id}>
                <div>
                  <div className="eyebrow">{client.industry}</div>
                  <div className="row-title">{client.name}</div>
                </div>
                <div className="tiny">{client.owner_id}</div>
                <div>
                  <span className="pill accent">{client.stage}</span>
                </div>
                <div>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={!nextStageMap[client.stage] || busy === client.id}
                    onClick={() => handleAdvance(client)}
                  >
                    {nextStageMap[client.stage] ? `Advance to ${nextStageMap[client.stage]}` : "At final stage"}
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
