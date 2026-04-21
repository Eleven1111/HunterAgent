"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { logoutRequest } from "@/lib/client-api";
import { clearSession, readStoredSession } from "@/lib/session";

const navItems = [
  { href: "/", label: "Dashboard", icon: "◳", meta: "Control room" },
  { href: "/clients", label: "Clients", icon: "◎", meta: "BD and active accounts" },
  { href: "/jobs", label: "Jobs", icon: "◇", meta: "Search plans and must-haves" },
  { href: "/candidates", label: "Candidates", icon: "◌", meta: "Imports and dedupe" },
  { href: "/sources", label: "Sources", icon: "◫", meta: "Experimental review lane", adminOnly: true },
  { href: "/interviews", label: "Interviews", icon: "◭", meta: "Phone screens and coordination", adminOnly: true },
  { href: "/assessments", label: "Assessments", icon: "◈", meta: "Evaluation reports", adminOnly: true },
  { href: "/submissions", label: "Submissions", icon: "▣", meta: "Drafts and approvals" },
  { href: "/invoices", label: "Invoices", icon: "◬", meta: "Invoice lite", adminOnly: true },
  { href: "/approvals", label: "Approvals", icon: "▲", meta: "Formal mutations", adminOnly: true },
  { href: "/audit", label: "Audit", icon: "↺", meta: "Replay and trace", adminOnly: true },
  { href: "/chat", label: "Chat", icon: "✦", meta: "Shared agent surface" }
];

export function WorkbenchShell({ children }) {
  const pathname = usePathname();
  const [session, setSession] = useState({ token: "", user: null });

  useEffect(() => {
    setSession(readStoredSession());
  }, []);
  const visibleNavItems = navItems.filter((item) => !item.adminOnly || session.user?.role === "owner" || session.user?.role === "team_admin");
  return (
    <div className="workbench">
      <aside className="rail">
        <div className="brand-block">
          <div className="brand-kicker">
            <span className="brand-dot" />
            HuntFlow vNext
          </div>
          <h1 className="brand-title">Dual-track.</h1>
          <p className="brand-copy">
            Mainline execution stays auditable. Experimental sourcing stays buffered.
          </p>
        </div>
        <nav className="nav-group">
          {visibleNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item${pathname === item.href ? " active" : ""}`}
            >
              <span className="nav-label">
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </span>
              <span className="nav-meta">{item.meta}</span>
            </Link>
          ))}
        </nav>
        <div className="nav-group" style={{ marginTop: "auto", paddingTop: "24px" }}>
          <div className="panel" style={{ padding: "14px 16px" }}>
            <div className="eyebrow">Session</div>
            <div className="row-title">{session.user?.name || "Unknown user"}</div>
            <div className="tiny">{session.user?.role || "No role"} · {session.user?.email || "No session"}</div>
            <button
              className="button secondary"
              type="button"
              style={{ marginTop: "12px", width: "100%" }}
              onClick={async () => {
                try {
                  await logoutRequest(session.token);
                } catch {}
                clearSession();
                window.location.href = "/login";
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
