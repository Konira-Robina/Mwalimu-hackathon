
"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Eye, Plus, Search } from "lucide-react";
import { api } from "@/lib/api";

type S = {
  id: string;
  student_code: string;
  name: string;
  phone_number: string;
};

type C = {
  id: string;
  name: string;
};

type StudentResults = {
  student: S;
  attempts: {
    attempt_id: string;
    assessment_title: string;
    assessment_type: string;
    score: number;
    total: number;
    completed: boolean;
    created_at: string | null;
    responses: {
      question: string;
      topic: string;
      selected_answer: string;
      correct: boolean;
      misconception: string | null;
    }[];
  }[];
};

function latestCompletedAttempt(
  attempts: StudentResults["attempts"],
  type: "baseline" | "followup",
) {
  return attempts
    .filter((attempt) => {
      const attemptType = attempt.assessment_type.toLowerCase().replace(/[-_\s]/g, "");
      return attempt.completed && attemptType === type;
    })
    .reduce<StudentResults["attempts"][number] | null>((latest, attempt) => {
      if (!latest) return attempt;
      const latestTime = latest.created_at ? Date.parse(latest.created_at) : 0;
      const attemptTime = attempt.created_at ? Date.parse(attempt.created_at) : 0;
      return Number.isFinite(attemptTime) && attemptTime > latestTime
        ? attempt
        : latest;
    }, null);
}

function scorePercentage(attempt: StudentResults["attempts"][number]) {
  if (
    !Number.isFinite(attempt.score) ||
    !Number.isFinite(attempt.total) ||
    attempt.total <= 0
  ) {
    return null;
  }
  return (attempt.score / attempt.total) * 100;
}

export default function Students() {
  const [rows, R] = useState<S[]>([]);
  const [classes, Cs] = useState<C[]>([]);
  const [q, Q] = useState("");
  const [open, O] = useState(false);
  const [name, N] = useState("");
  const [code, Co] = useState("");
  const [phone, P] = useState("+256");
  const [cid, Ci] = useState("");
  const [msg, M] = useState("");

  const [selectedStudent, setSelectedStudent] = useState<S | null>(null);
  const [studentResults, setStudentResults] =
    useState<StudentResults | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");

  async function load() {
    const [s, c] = await Promise.all([
      api<S[]>("/api/students"),
      api<C[]>("/api/classes"),
    ]);

    R(s);
    Cs(c);

    if (c[0]) Ci(c[0].id);
  }

  useEffect(() => {
    load().catch((e) => M(e.message));
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();

    try {
      await api("/api/students", {
        method: "POST",
        body: JSON.stringify({
          name,
          student_code: code,
          phone_number: phone,
          class_id: cid,
        }),
      });

      O(false);
      N("");
      Co("");
      await load();
      M("Learner added");
    } catch (e) {
      M(e instanceof Error ? e.message : "Could not add learner");
    }
  }

  async function viewDetails(student: S) {
    setSelectedStudent(student);
    setStudentResults(null);
    setDetailsError("");
    setDetailsLoading(true);

    try {
      const results = await api<StudentResults>(
        `/api/students/${student.id}/results`,
      );

      setStudentResults(results);
    } catch (e) {
      setDetailsError(
        e instanceof Error ? e.message : "Could not load learner results.",
      );
    } finally {
      setDetailsLoading(false);
    }
  }

  function closeDetails() {
    setSelectedStudent(null);
    setStudentResults(null);
    setDetailsError("");
  }

  const filtered = rows.filter((s) =>
    (s.name + s.student_code + s.phone_number)
      .toLowerCase()
      .includes(q.toLowerCase()),
  );

  const baselineAttempt = studentResults
    ? latestCompletedAttempt(studentResults.attempts, "baseline")
    : null;
  const followupAttempt = studentResults
    ? latestCompletedAttempt(studentResults.attempts, "followup")
    : null;
  const baselinePercentage = baselineAttempt
    ? scorePercentage(baselineAttempt)
    : null;
  const followupPercentage = followupAttempt
    ? scorePercentage(followupAttempt)
    : null;
  const canCompare = baselinePercentage !== null && followupPercentage !== null;
  const improvement = canCompare
    ? followupPercentage - baselinePercentage
    : null;

  return (
    <div>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Classroom directory</p>
          <h1 className="mt-2 text-2xl font-bold">Students</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage learners and SMS contact details.
          </p>
        </div>

        {!selectedStudent && (
          <button
            className="btn flex items-center gap-2"
            onClick={() => O(!open)}
          >
            <Plus size={15} /> Add student
          </button>
        )}
      </div>

      {msg && <p className="mb-3 text-xs text-indigo-600">{msg}</p>}

      {open && !selectedStudent && (
        <form
          onSubmit={add}
          className="card mb-5 grid gap-3 p-5 md:grid-cols-4"
        >
          <input
            className="field"
            placeholder="Name"
            value={name}
            onChange={(e) => N(e.target.value)}
            required
          />

          <input
            className="field"
            placeholder="Learner ID"
            value={code}
            onChange={(e) => Co(e.target.value)}
            required
          />

          <input
            className="field"
            value={phone}
            onChange={(e) => P(e.target.value)}
            required
          />

          <select
            className="field"
            value={cid}
            onChange={(e) => Ci(e.target.value)}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <button className="btn md:col-span-4">Save learner</button>
        </form>
      )}

      {selectedStudent ? (
        <div className="space-y-5">
          <button
            onClick={closeDetails}
            className="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            <ArrowLeft size={16} /> Back to students
          </button>

          <div className="card p-5">
            <p className="eyebrow">Learner profile</p>
            <h2 className="mt-2 text-xl font-bold">
              {selectedStudent.name}
            </h2>

            <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
              <p>
                <span className="font-semibold">Learner ID:</span>{" "}
                {selectedStudent.student_code}
              </p>
              <p>
                <span className="font-semibold">Phone:</span>{" "}
                {selectedStudent.phone_number}
              </p>
              <p>
                <span className="font-semibold">Status:</span> Registered
              </p>
            </div>
          </div>

          {detailsLoading && (
            <p className="py-6 text-center text-sm text-slate-500">
              Loading learner results...
            </p>
          )}

          {detailsError && (
            <p className="card p-5 text-sm text-red-600">
              Could not load results: {detailsError}
            </p>
          )}

          {studentResults && (
            <>
              <section className="card p-5">
                <div>
                  <p className="eyebrow">Learning recovery</p>
                  <h2 className="mt-2 text-lg font-bold">Baseline and follow-up</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Compare the learner’s most recent completed assessments.
                  </p>
                </div>

                {!baselineAttempt || !followupAttempt ? (
                  <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
                    Complete both a baseline and a follow-up assessment to see a recovery comparison.
                    {!baselineAttempt && !followupAttempt
                      ? " No completed attempts are available for either assessment."
                      : !baselineAttempt
                        ? " A completed baseline assessment is still needed."
                        : " A completed follow-up assessment is still needed."}
                  </p>
                ) : !canCompare ? (
                  <p className="mt-4 rounded-lg bg-amber-50 p-4 text-sm text-amber-800">
                    A percentage comparison is unavailable because one or both completed assessments have no valid question total.
                  </p>
                ) : (
                  <>
                    <div className="mt-5 grid gap-4 sm:grid-cols-2">
                      {[
                        { label: "Baseline", attempt: baselineAttempt, percentage: baselinePercentage, color: "bg-indigo-500" },
                        { label: "Follow-up", attempt: followupAttempt, percentage: followupPercentage, color: "bg-emerald-500" },
                      ].map(({ label, attempt, percentage, color }) => (
                        <div key={label} className="rounded-xl border border-slate-100 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
                              <p className="mt-1 text-sm font-semibold">{attempt.assessment_title}</p>
                            </div>
                            <p className="shrink-0 text-right text-lg font-bold">
                              {attempt.score}/{attempt.total}
                              <span className="block text-sm font-medium text-slate-500">{percentage.toFixed(1)}%</span>
                            </p>
                          </div>
                          <div
                            className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-100"
                            role="progressbar"
                            aria-label={`${label} score`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={Math.max(0, Math.min(100, percentage))}
                          >
                            <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className={`mt-4 rounded-lg p-4 ${improvement! > 0 ? "bg-emerald-50 text-emerald-800" : improvement === 0 ? "bg-slate-50 text-slate-700" : "bg-amber-50 text-amber-800"}`}>
                      <p className="font-semibold">
                        {improvement! > 0 ? "Improved" : improvement === 0 ? "No change" : "Needs further support"}
                        <span className="ml-2 font-bold">
                          {improvement! > 0 ? "+" : ""}{improvement!.toFixed(1)} percentage points
                        </span>
                      </p>
                      <p className="mt-1 text-sm">
                        {improvement! > 0
                          ? "The follow-up score is higher than the baseline score."
                          : improvement === 0
                            ? "The baseline and follow-up scores are the same."
                            : "The follow-up score is lower; consider another focused explanation."}
                      </p>
                    </div>
                  </>
                )}
              </section>

              <div>
                <h2 className="mb-3 text-lg font-bold">Assessment history</h2>

                {studentResults.attempts.length === 0 ? (
                  <div className="card p-5 text-sm text-slate-500">
                    This learner has not attempted any assessments yet.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {studentResults.attempts.map((attempt) => (
                      <div key={attempt.attempt_id} className="card p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <h3 className="font-semibold">
                              {attempt.assessment_title}
                            </h3>
                            <p className="mt-1 text-xs capitalize text-slate-500">
                              {attempt.assessment_type} assessment
                            </p>
                            {attempt.created_at && (
                              <p className="mt-1 text-xs text-slate-400">
                                {new Date(
                                  attempt.created_at,
                                ).toLocaleString()}
                              </p>
                            )}
                          </div>

                          <div className="text-right">
                            <p className="text-xl font-bold">
                              {attempt.score}/{attempt.total}
                            </p>
                            <span
                              className={`text-xs font-medium ${
                                attempt.completed
                                  ? "text-emerald-700"
                                  : "text-amber-700"
                              }`}
                            >
                              {attempt.completed ? "Completed" : "Incomplete"}
                            </span>
                          </div>
                        </div>

                        {attempt.responses.length > 0 && (
                          <div className="mt-5 space-y-3 border-t pt-4">
                            <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">
                              Answers and misconceptions
                            </h4>

                            {attempt.responses.map((response, index) => (
                              <div
                                key={`${attempt.attempt_id}-${index}`}
                                className="rounded-lg bg-slate-50 p-4"
                              >
                                <p className="text-xs text-slate-500">
                                  {response.topic}
                                </p>

                                <p className="mt-1 text-sm font-semibold">
                                  {index + 1}. {response.question}
                                </p>

                                <p className="mt-2 text-sm text-slate-700">
                                  Selected answer: {response.selected_answer}
                                </p>

                                <p
                                  className={`mt-2 text-xs font-semibold ${
                                    response.correct
                                      ? "text-emerald-700"
                                      : "text-red-600"
                                  }`}
                                >
                                  {response.correct
                                    ? "Correct answer"
                                    : "Incorrect answer"}
                                </p>

                                {response.misconception && (
                                  <p className="mt-2 text-xs text-amber-800">
                                    Identified misconception:{" "}
                                    {response.misconception}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {!attempt.responses.length && (
                          <p className="mt-4 border-t pt-3 text-xs text-slate-400">
                            No answers have been recorded for this attempt.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b p-5">
            <b className="text-sm">
              Registered learners · {rows.length}
            </b>

            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-3 text-slate-400"
              />
              <input
                className="field w-48 pl-9"
                placeholder="Search"
                value={q}
                onChange={(e) => Q(e.target.value)}
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[10px] uppercase text-slate-400">
                <tr>
                  <th className="p-4">Learner</th>
                  <th className="p-4">Learner ID</th>
                  <th className="p-4">Phone</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Action</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((s) => (
                  <tr key={s.id} className="border-t">
                    <td className="p-4 font-semibold">{s.name}</td>
                    <td className="p-4">{s.student_code}</td>
                    <td className="p-4">{s.phone_number}</td>
                    <td className="p-4 text-emerald-700">Registered</td>
                    <td className="p-4">
                      <button
                        onClick={() => viewDetails(s)}
                        className="flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800"
                      >
                        <Eye size={14} /> View details
                      </button>
                    </td>
                  </tr>
                ))}

                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="p-6 text-center text-slate-500"
                    >
                      No learners found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
