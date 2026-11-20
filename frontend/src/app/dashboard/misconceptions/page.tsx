"use client";
import { useEffect, useState } from "react";
import { AlertTriangle, Lightbulb, Send } from "lucide-react";
import { api } from "@/lib/api";

type M = {
  id: string;
  name: string;
  topic: string;
  affected_students: number;
  currently_affected: number;
  response_count: number;
  description: string;
  intervention: string;
};

export default function Page() {
  const [rows, setRows] = useState<M[]>([]);
  const [busyId, setBusyId] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    api<M[]>("/api/analytics/misconceptions").then(setRows).catch(() => {});
  }, []);

  async function notify(m: M) {
    const ok = window.confirm(
      `Send a revision SMS to the ${m.currently_affected} learner(s) who still show "${m.name}"?`
    );
    if (!ok) return;
    setBusyId(m.id);
    try {
      const res = await api<{ queued: number }>(`/api/misconceptions/${m.id}/notify`, {
        method: "POST",
        body: JSON.stringify({ message: drafts[m.id] || undefined }),
      });
      setNotes((n) => ({ ...n, [m.id]: `Queued for ${res.queued} learner(s). Check the SMS inbox on the USSD page.` }));
    } catch (e) {
      setNotes((n) => ({ ...n, [m.id]: e instanceof Error ? e.message : "Could not send." }));
    } finally {
      setBusyId("");
    }
  }

  return (
    <div>
      <p className="eyebrow">Understand the why</p>
      <h1 className="mt-2 text-2xl font-bold">Misconception insights</h1>
      <p className="mt-2 text-sm text-slate-500">Patterns in incorrect answers that guide targeted teaching.</p>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {rows.map((m) => (
          <article className="card p-5" key={m.id}>
            <div className="flex gap-3">
              <span className="rounded-xl bg-amber-50 p-3 text-amber-600"><AlertTriangle /></span>
              <div className="flex-1">
                <p className="eyebrow">{m.topic}</p>
                <h2 className="mt-1 font-bold">{m.name}</h2>
                <p className="mt-2 text-xs leading-5 text-slate-500">{m.description}</p>
              </div>
              <div className="text-right">
                <b className="text-2xl">{m.currently_affected}</b>
                <p className="text-[10px] text-slate-400">still affected</p>
                <p className="mt-1 text-[10px] text-slate-400">{m.affected_students} ever</p>
              </div>
            </div>
            <div className="mt-5 rounded-xl bg-indigo-50 p-4">
              <div className="flex gap-2 text-xs font-bold text-indigo-700"><Lightbulb size={15} /> Suggested intervention</div>
              <p className="mt-2 text-xs leading-5 text-slate-600">{m.intervention}</p>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <input className="field min-w-[240px] flex-1 text-xs" value={drafts[m.id] || ""} onChange={(e) => setDrafts((n) => ({ ...n, [m.id]: e.target.value }))} maxLength={300} placeholder="Optional teacher-written revision tip (up to 300 chars)" aria-label={`Revision tip for ${m.name}`} />
              <button
                className="btn flex items-center gap-2 disabled:opacity-50"
                disabled={m.currently_affected === 0 || busyId === m.id}
                onClick={() => notify(m)}
              >
                <Send size={14} /> {busyId === m.id ? "Sending…" : `Send revision SMS (${m.currently_affected})`}
              </button>
              {notes[m.id]?.startsWith("Queued for") && <p className="text-[11px] text-slate-500">{notes[m.id]}</p>}
            </div>
            <p className="mt-3 text-[10px] text-slate-400">{m.response_count} incorrect responses · A selected option is an indicator, not proof.</p>
          </article>
        ))}
      </div>
    </div>
  );
}
