"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GraduationCap, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

export default function Login() {
  const [email, E] = useState("teacher@demo.com");
  const [password, P] = useState("RadarDemo123!");
  const [error, Err] = useState("");
  const [busy, B] = useState(false);
  const r = useRouter();

  async function go(e: React.FormEvent) {
    e.preventDefault();
    B(true);
    try {
      const x = await api<{ access_token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("radar_token", x.access_token);
      r.push("/dashboard");
    } catch (e) {
      Err(e instanceof Error ? e.message : "Login failed");
    } finally {
      B(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-[#211d62] p-12 text-white lg:flex">
        <div className="flex items-center gap-3"><GraduationCap size={30} /><b>Mwalimu</b></div>
        <div className="max-w-lg">
          <p className="eyebrow text-indigo-200">Understand. Teach. Improve.</p>
          <h1 className="mt-5 text-5xl font-bold leading-tight">Don't just mark answers. <span className="text-indigo-300">Understand them.</span></h1>
          <p className="mt-6 leading-7 text-indigo-100">An AI-powered learning recovery platform that helps teachers identify learner misconceptions, provide personalised feedback, and measure learning progress.</p>
        </div>
        <small className="text-indigo-200">© 2026 Mwalimu · Hackathon demo</small>
      </div>
      <div className="flex items-center justify-center p-7">
        <form onSubmit={go} className="w-full max-w-sm">
          <div className="mb-7 flex items-center gap-3 lg:hidden"><GraduationCap className="text-indigo-600" /><b>Mwalimu</b></div>
          <p className="eyebrow">Teacher portal</p>
          <h2 className="mt-2 text-3xl font-bold">Welcome back</h2>
          <p className="mt-2 text-sm text-slate-500">Sign in to understand what's happening in your classroom.</p>
          <label className="label mt-8">Email address</label>
          <input className="field" type="email" value={email} onChange={(e) => E(e.target.value)} />
          <label className="label mt-5">Password</label>
          <input className="field" type="password" value={password} onChange={(e) => P(e.target.value)} />
          {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
          <button className="btn mt-7 flex w-full items-center justify-center gap-2" disabled={busy}>{busy ? "Signing in..." : "Sign in to dashboard"}<ArrowRight size={16} /></button>
          <div className="mt-6 rounded-xl bg-indigo-50 p-4 text-xs leading-6 text-indigo-800"><b>Demo access</b><br />teacher@demo.com<br />RadarDemo123!</div>
        </form>
      </div>
    </div>
  );
}
