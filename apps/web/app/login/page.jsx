"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import { loginRequest } from "@/lib/client-api";
import { persistSession } from "@/lib/session";

const DEMO_USERS = [
  { email: "owner@huntflow.local", password: "hunter-owner", label: "Owner demo" },
  { email: "consultant@huntflow.local", password: "hunter-consultant", label: "Consultant demo" }
];
const DEMO_MODE = process.env.NEXT_PUBLIC_ENABLE_DEMO_SEED === "true";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_MODE ? DEMO_USERS[1].email : "");
  const [password, setPassword] = useState(DEMO_MODE ? DEMO_USERS[1].password : "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await loginRequest(email, password);
      persistSession(payload.access_token, payload.user);
      startTransition(() => {
        router.replace("/");
      });
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: "24px" }}>
      <section className="hero" style={{ width: "min(1100px, 100%)" }}>
        <div className="hero-copy">
          <div>
            <div className="hero-kicker">Pilot access</div>
            <h1>Enter the workbench.</h1>
            <p>
              {DEMO_MODE
                ? "This login can use seeded demo users so the workbench can run against live routes while keeping auth on the server session."
                : "Sign in with a provisioned account."}
            </p>
          </div>
          {DEMO_MODE ? (
            <div className="slash-list">
              {DEMO_USERS.map((user) => (
                <button
                  key={user.email}
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    setEmail(user.email);
                    setPassword(user.password);
                  }}
                >
                  {user.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="hero-side">
          <form className="composer" onSubmit={handleSubmit}>
            <input className="inline-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
            <input
              className="inline-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
            />
            <button className="button" type="submit" disabled={busy}>
              {busy ? "Signing in..." : "Sign in"}
            </button>
            {error ? <div className="tiny" style={{ color: "var(--danger)" }}>{error}</div> : null}
          </form>
        </div>
      </section>
    </div>
  );
}
