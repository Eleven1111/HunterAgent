"use client";

export const USER_KEY = "huntflow_user";

export function readStoredSession() {
  if (typeof window === "undefined") {
    return { token: "", user: null };
  }
  const rawUser = window.localStorage.getItem(USER_KEY);
  const user = rawUser ? JSON.parse(rawUser) : null;
  return { token: user ? "cookie-session" : "", user };
}

export function persistSession(_token, user) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(USER_KEY);
}
