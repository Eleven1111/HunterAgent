"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { meRequest } from "@/lib/client-api";
import { clearSession, persistSession, readStoredSession } from "@/lib/session";

export function AuthGate({ children }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    async function resolveSession() {
      try {
        const user = await meRequest();
        persistSession("cookie-session", user);
        if (active) {
          setReady(true);
        }
      } catch {
        clearSession();
        if (active) {
          router.replace("/login");
        }
      }
    }
    const { token } = readStoredSession();
    if (!token) {
      resolveSession();
      return;
    }
    resolveSession();
    return () => {
      active = false;
    };
  }, [router]);

  if (!ready) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <div className="panel" style={{ width: "min(480px, 92vw)" }}>
          <div className="panel-title">Checking session...</div>
          <p className="panel-copy">The workbench requires a valid server session.</p>
        </div>
      </div>
    );
  }

  return children;
}
