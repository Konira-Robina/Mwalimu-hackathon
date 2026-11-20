"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowDownLeft,
  CheckCircle2,
  Clock3,
  Delete,
  LoaderCircle,
  MessageSquareText,
  Phone,
  RotateCcw,
  Send,
  Smartphone,
} from "lucide-react";
import { api, apiForm } from "@/lib/api";

type SmsMessage = {
  id: string;
  recipient: string;
  message: string;
  delivery_status: "demo" | "accepted" | "failed" | string;
  created_at: string | null;
};

type Interaction = {
  sequence: number;
  selection: string;
  response: string;
  createdAt: string;
  error?: boolean;
};

type Conversation = {
  id: string;
  phoneNumber: string;
  serviceCode: string;
  text: string;
  startedAt: string;
  state: "ongoing" | "completed";
  interactions: Interaction[];
};

type UssdStatus = { configured: boolean; mode: string };

function formatDate(date: string | null) {
  if (!date) return "Time unavailable";
  const parsed = new Date(date);
  return Number.isNaN(parsed.getTime()) ? "Time unavailable" : parsed.toLocaleString();
}

function displayMessage(message: string) {
  return message;
}

function newSessionId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function UssdSimulator() {
  const [sessions, setSessions] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("+256700000001");
  const [serviceCode, setServiceCode] = useState("*123#");
  const [selection, setSelection] = useState("");
  const [messages, setMessages] = useState<SmsMessage[]>([]);
  const [network, setNetwork] = useState<UssdStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const screenRef = useRef<HTMLDivElement>(null);
  const active = sessions.find((session) => session.id === activeId) ?? null;

  useEffect(() => {
    api<UssdStatus>("/api/ussd/status")
      .then(setNetwork)
      .catch(() => setNetwork(null));
  }, []);

  useEffect(() => {
    screenRef.current?.scrollTo({ top: screenRef.current.scrollHeight, behavior: "smooth" });
  }, [active?.interactions.length, activeId]);

  useEffect(() => {
    api<SmsMessage[]>("/api/ussd/messages")
      .then(setMessages)
      .catch(() => setMessages([]));
  }, []);

  function updateSession(id: string, update: (session: Conversation) => Conversation) {
    setSessions((current) => current.map((session) => session.id === id ? update(session) : session));
  }

  // SMS feedback is sent in the background after the USSD reply, so poll the inbox for a few seconds.
  async function refreshInbox() {
    for (const wait of [0, 1500, 3000, 5000]) {
      await new Promise((resolve) => setTimeout(resolve, wait));
      try {
        setMessages(await api<SmsMessage[]>("/api/ussd/messages"));
      } catch {
        /* keep the last known inbox */
      }
    }
  }

  async function callback(session: Conversation, text: string, submitted: string) {
    setBusy(true);
    setError("");
    try {
      const form = new URLSearchParams({
        sessionId: session.id,
        serviceCode: session.serviceCode,
        phoneNumber: session.phoneNumber,
        text,
      });
      const response = await apiForm<string>("/api/ussd/callback", form, {
        headers: { "X-Mwalimu-Simulator": "true" },
      });
      const ended = response.trimStart().startsWith("END");
      updateSession(session.id, (current) => ({
        ...current,
        text,
        state: ended ? "completed" : "ongoing",
        interactions: [
          ...current.interactions,
          {
            sequence: current.interactions.length + 1,
            selection: submitted,
            response,
            createdAt: new Date().toISOString(),
          },
        ],
      }));
      if (ended) {
        void refreshInbox(); // not awaited, so the keypad stays usable
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not reach the USSD service. Try again.";
      setError(message);
      updateSession(session.id, (current) => ({
        ...current,
        interactions: [
          ...current.interactions,
          {
            sequence: current.interactions.length + 1,
            selection: submitted,
            response: message,
            createdAt: new Date().toISOString(),
            error: true,
          },
        ],
      }));
    } finally {
      setBusy(false);
    }
  }

  async function startSession() {
    const phone = phoneNumber.trim();
    if (!/^\+?[0-9]{8,15}$/.test(phone)) {
      setError("Enter a phone number with 8 to 15 digits, optionally starting with +.");
      return;
    }
    if (!serviceCode.trim()) {
      setError("Enter a service code to start the USSD session.");
      return;
    }
    const session: Conversation = {
      id: newSessionId(),
      phoneNumber: phone,
      serviceCode: serviceCode.trim(),
      text: "",
      startedAt: new Date().toISOString(),
      state: "ongoing",
      interactions: [],
    };
    setSessions((current) => [session, ...current]);
    setActiveId(session.id);
    setSelection("");
    await callback(session, "", "Dialed " + session.serviceCode);
  }

  async function sendSelection(value = selection.trim()) {
    if (!active || active.state !== "ongoing" || busy) return;
    if (!value) {
      setError("Enter a response using the keypad before sending.");
      return;
    }
    const text = active.text ? `${active.text}*${value}` : value;
    setSelection("");
    await callback(active, text, value);
  }

  function chooseSession(session: Conversation) {
    setActiveId(session.id);
    setPhoneNumber(session.phoneNumber);
    setServiceCode(session.serviceCode);
    setSelection("");
    setError("");
  }

  const networkLabel = !network?.configured
    ? "Simulated network · local SMS"
    : network.mode === "sandbox"
      ? "Simulated network · AT Sandbox"
      : "Simulated network · SMS kept local";

  return (
    <div className="mx-auto max-w-[1350px]">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Understand. Teach. Improve.</p>
          <h1 className="mt-2 text-2xl font-bold">USSD Simulator</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Try the learner quiz journey through Mwalimu’s existing USSD service. This is a simulation, not a mobile network connection.
          </p>
        </div>
        <span className="rounded-full bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700">{networkLabel}</span>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(310px,390px)_minmax(0,1fr)]">
        <section className="card mx-auto w-full max-w-[390px] p-4 sm:p-6" aria-label="Simulated mobile phone">
          <div className="mx-auto w-full max-w-[310px] rounded-[2.4rem] border-[7px] border-slate-800 bg-slate-900 p-2 shadow-xl">
            <div className="overflow-hidden rounded-[1.75rem] bg-[#f4f5f8]">
              <div className="flex items-center justify-between bg-white px-5 py-3 text-[10px] font-bold text-slate-600">
                <span>9:41</span>
                <span className="flex items-center gap-2">
                  <span className="flex h-3 items-end gap-[2px]" aria-hidden="true">
                    <i className="h-1 w-[3px] rounded-sm bg-emerald-500" />
                    <i className="h-1.5 w-[3px] rounded-sm bg-emerald-500" />
                    <i className="h-2 w-[3px] rounded-sm bg-emerald-500" />
                    <i className="h-3 w-[3px] rounded-sm bg-emerald-500" />
                  </span>
                  <span>SIMULATED</span>
                </span>
              </div>

              <div className="flex items-center justify-between border-y border-slate-100 bg-white px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="rounded-lg bg-indigo-100 p-2 text-indigo-700"><Smartphone size={16} /></span>
                  <div><p className="text-xs font-bold">USSD session</p><p className="text-[10px] text-slate-400">Mwalimu · {active?.serviceCode || serviceCode}</p></div>
                </div>
                {busy && <LoaderCircle className="animate-spin text-indigo-600" size={16} />}
              </div>

              <div ref={screenRef} className="h-[300px] space-y-3 overflow-y-auto p-4" aria-live="polite">
                {!active && (
                  <div className="mt-16 text-center text-xs leading-5 text-slate-500">
                    <Phone className="mx-auto mb-3 text-indigo-500" size={24} />
                    Enter a phone number and dial the service code to begin.
                  </div>
                )}
                {active?.interactions.map((item) => (
                  <div key={`${active.id}-${item.sequence}`}>
                    {item.sequence > 1 && (
                      <div className="ml-auto mb-2 w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-3 py-2 text-xs text-white">
                        Sent: {item.selection}
                      </div>
                    )}
                    <div className={`whitespace-pre-wrap rounded-2xl rounded-tl-sm p-3 text-xs leading-5 shadow-sm ${item.error ? "bg-red-50 text-red-700" : "bg-white text-slate-700"}`}>
                      {displayMessage(item.response) || (item.error ? "Service unavailable" : "Waiting for response…")}
                    </div>
                    <p className="mt-1 px-1 text-[9px] text-slate-400">Step {item.sequence} · {formatDate(item.createdAt)}</p>
                  </div>
                ))}
                {busy && <p className="text-center text-[10px] text-slate-400">Waiting for Mwalimu…</p>}
              </div>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <label className="label">Learner phone number</label>
            <input className="field" inputMode="tel" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} disabled={!!active && active.state === "ongoing"} placeholder="+256700000001" />
            <label className="label">Service code</label>
            <input className="field" value={serviceCode} onChange={(e) => setServiceCode(e.target.value)} disabled={!!active && active.state === "ongoing"} />

            <div className="grid grid-cols-3 gap-2 pt-1" aria-label="Numeric keypad">
              {["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "delete"].map((key, index) => (
                key === "" ? <span key={`blank-${index}`} /> : (
                  <button
                    key={key}
                    type="button"
                    className="rounded-xl border border-slate-200 bg-white py-2.5 text-sm font-bold text-slate-700 hover:bg-indigo-50 disabled:opacity-50"
                    disabled={busy || !active || active.state !== "ongoing"}
                    onClick={() => key === "delete" ? setSelection((value) => value.slice(0, -1)) : setSelection((value) => value + key)}
                    aria-label={key === "delete" ? "Clear last digit" : `Enter ${key}`}
                  >
                    {key === "delete" ? <Delete size={16} className="mx-auto" /> : key}
                  </button>
                )
              ))}
            </div>
            <input
              className="field text-center text-base font-bold tracking-widest"
              aria-label="USSD response"
              value={selection}
              onChange={(e) => setSelection(e.target.value.replace(/[^0-9]/g, ""))}
              onKeyDown={(e) => { if (e.key === "Enter") void sendSelection(); }}
              placeholder="Enter menu choice or learner ID"
              disabled={busy || !active || active.state !== "ongoing"}
            />
            {error && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
            <div className="grid grid-cols-2 gap-2">
              {!active || active.state === "completed" ? (
                <button className="btn col-span-2 flex items-center justify-center gap-2" onClick={() => void startSession()} disabled={busy}>
                  {busy ? <LoaderCircle size={15} className="animate-spin" /> : <Phone size={15} />} Dial / new session
                </button>
              ) : (
                <>
                  <button className="btn flex items-center justify-center gap-2" onClick={() => void sendSelection()} disabled={busy || !selection.trim()}>
                    {busy ? <LoaderCircle size={15} className="animate-spin" /> : <Send size={15} />} Send
                  </button>
                  <button className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50" onClick={() => void sendSelection("0")} disabled={busy}>
                    End session
                  </button>
                </>
              )}
            </div>
          </div>
        </section>

        <div className="space-y-5">
          <section className="card p-5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2"><MessageSquareText size={17} className="text-indigo-600" /><h2 className="font-bold">Simulated SMS inbox</h2></div>
              <span className="text-[10px] text-slate-400">Latest 100 · backend records</span>
            </div>
            {messages.length ? (
              <div className="mt-4 space-y-3">
                {messages.map((message) => (
                  <article key={message.id} className="rounded-xl border border-slate-100 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-xs font-semibold text-slate-700">To {message.recipient}</p>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${message.delivery_status === "accepted" || message.delivery_status === "sandbox_accepted" ? "bg-sky-50 text-sky-700" : message.delivery_status === "failed" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"}`}>
                        {message.delivery_status === "sandbox_accepted" ? "Accepted by Africa’s Talking Sandbox" : message.delivery_status === "accepted" ? "Accepted by provider" : message.delivery_status === "failed" ? "Provider failed" : "Simulated locally"}
                      </span>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-[10px] text-slate-400"><Clock3 size={12} />{formatDate(message.created_at)}</p>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-5 text-slate-700">{displayMessage(message.message)}</p>
                    {(message.delivery_status === "accepted" || message.delivery_status === "sandbox_accepted") && <p className="mt-2 text-[10px] text-sky-700">Provider acceptance does not confirm handset delivery.</p>}
                  </article>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-xl bg-slate-50 p-5 text-center text-xs text-slate-500">
                <MessageSquareText size={20} className="mx-auto mb-2 text-slate-300" />
                No SMS feedback recorded for this number yet.
              </div>
            )}
            <p className="mt-3 text-[10px] leading-4 text-slate-400">Messages are loaded from the backend log. Local demo messages are simulated and are not sent to a phone.</p>
          </section>

          <section className="card p-5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2"><ArrowDownLeft size={17} className="text-indigo-600" /><h2 className="font-bold">Conversation history</h2></div>
              <button className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800" onClick={() => { setActiveId(""); setSelection(""); setError(""); }}>
                <RotateCcw size={13} /> New session
              </button>
            </div>
            {!sessions.length ? (
              <p className="mt-4 rounded-xl bg-slate-50 p-5 text-center text-xs text-slate-500">Your sessions from this visit will appear here.</p>
            ) : (
              <div className="mt-4 space-y-3">
                {sessions.map((session) => (
                  <article key={session.id} className={`rounded-xl border p-4 ${session.id === activeId ? "border-indigo-200 bg-indigo-50/50" : "border-slate-100"}`}>
                    <button className="flex w-full items-start justify-between gap-3 text-left" onClick={() => chooseSession(session)}>
                      <span><span className="block text-xs font-bold text-slate-700">{session.phoneNumber}</span><span className="mt-1 block text-[10px] text-slate-400">{formatDate(session.startedAt)} · {session.interactions.length} interactions</span></span>
                      <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold ${session.state === "ongoing" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                        {session.state === "ongoing" ? "Ongoing" : "Completed"}
                      </span>
                    </button>
                    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                      {session.interactions.map((item) => (
                        <div key={`${session.id}-history-${item.sequence}`} className="text-xs">
                          <p className="font-semibold text-slate-600">{item.sequence}. {item.selection}</p>
                          <p className={`mt-1 whitespace-pre-wrap leading-5 ${item.error ? "text-red-600" : "text-slate-500"}`}>{displayMessage(item.response)}</p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
          <p className="flex items-start gap-2 rounded-xl bg-indigo-50 p-4 text-xs leading-5 text-indigo-800">
            <CheckCircle2 className="mt-0.5 shrink-0" size={15} /> The simulator sends each response to the existing Mwalimu callback. The backend’s menu, score, and feedback remain authoritative.
          </p>
        </div>
      </div>
    </div>
  );
}
