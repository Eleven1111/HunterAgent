"use client";

import { useEffect, useState } from "react";

import {
  createInvoiceRequest,
  dashboardSummaryRequest,
  listInvoicesRequest,
  updateInvoiceRequest
} from "@/lib/client-api";
import { readStoredSession } from "@/lib/session";
import { DenseTable } from "@/components/dense-table";
import { Panel } from "@/components/panel";

function initialForm() {
  return {
    client_id: "",
    job_order_id: "",
    amount: 120000,
    currency: "CNY",
    due_date: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString().slice(0, 16),
    memo: ""
  };
}

export function InvoicesWorkspace() {
  const [session, setSession] = useState({ token: "", user: null });
  const [summary, setSummary] = useState({ clients: [], jobs: [] });
  const [invoices, setInvoices] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    const stored = readStoredSession();
    setSession(stored);
    if (!stored.token) {
      return;
    }
    const [dashboard, invoiceRows] = await Promise.all([
      dashboardSummaryRequest(stored.token),
      listInvoicesRequest(stored.token)
    ]);
    setSummary(dashboard);
    setInvoices(invoiceRows);
    setForm((current) => ({
      ...current,
      client_id: current.client_id || dashboard.clients[0]?.id || "",
      job_order_id: current.job_order_id || dashboard.jobs[0]?.id || ""
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
    setBusy("create");
    setMessage("");
    try {
      const response = await createInvoiceRequest(session.token, form);
      setMessage(`Invoice ${response.id} created.`);
      setForm(initialForm());
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy("");
    }
  }

  async function handleUpdate(invoiceId, statusValue) {
    if (!session.token) {
      return;
    }
    setBusy(invoiceId);
    setMessage("");
    try {
      const response = await updateInvoiceRequest(session.token, invoiceId, {
        status: statusValue,
        memo: `${statusValue} via workbench`
      });
      setMessage(`Invoice ${response.id} moved to ${response.status}.`);
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
        <Panel title="Invoice lite" copy="Track a pilot invoice without needing the full ERP layer.">
          <form className="composer" onSubmit={handleCreate}>
            <select className="inline-input" value={form.client_id} onChange={(event) => setForm((current) => ({ ...current, client_id: event.target.value }))}>
              <option value="">Select client</option>
              {summary.clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
            <select className="inline-input" value={form.job_order_id} onChange={(event) => setForm((current) => ({ ...current, job_order_id: event.target.value }))}>
              <option value="">Link job (optional)</option>
              {summary.jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <input className="inline-input" type="number" min="0" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
            <input className="inline-input" type="datetime-local" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} />
            <textarea value={form.memo} onChange={(event) => setForm((current) => ({ ...current, memo: event.target.value }))} placeholder="Invoice memo or fee note" />
            <button className="button" type="submit" disabled={busy === "create" || !form.client_id}>
              {busy === "create" ? "Creating..." : "Create invoice"}
            </button>
          </form>
          {message ? <div className="tiny" style={{ marginTop: "16px" }}>{message}</div> : null}
        </Panel>
      </div>

      <div className="span-7">
        <Panel title="Billing lane" copy="Advance the invoice from draft to sent to paid while keeping the pilot flow lightweight.">
          <DenseTable
            columns={[
              { key: "client_id", label: "Client" },
              { key: "amount", label: "Amount" },
              { key: "status", label: "Status" },
              { key: "due_date", label: "Due" }
            ]}
            rows={invoices.map((invoice) => ({ ...invoice, amount: `${invoice.currency} ${invoice.amount}` }))}
          />
          <div className="list" style={{ marginTop: "18px" }}>
            {invoices.slice(0, 6).map((invoice) => (
              <div className="list-row" key={invoice.id}>
                <div>
                  <div className="eyebrow">{invoice.status}</div>
                  <div className="row-title">{invoice.id}</div>
                </div>
                <div className="tiny">{invoice.client_id}</div>
                <div className="tiny">{invoice.currency} {invoice.amount}</div>
                <div className="action-row" style={{ justifyContent: "flex-end" }}>
                  <button className="button secondary" type="button" disabled={busy === invoice.id || invoice.status !== "DRAFT"} onClick={() => handleUpdate(invoice.id, "SENT")}>
                    Send
                  </button>
                  <button className="button secondary" type="button" disabled={busy === invoice.id || invoice.status === "PAID"} onClick={() => handleUpdate(invoice.id, "PAID")}>
                    Paid
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
