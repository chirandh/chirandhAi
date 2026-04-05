import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiFetch } from "./api/client";

const STORAGE_KEY = "chirandhai.apiKey";

type ResumeState = "created" | "proposed" | "compiling" | "ready" | "failed";
type JobStatus = "queued" | "running" | "succeeded" | "failed";

interface ProposalEdit {
  section: string;
  before: string;
  after: string;
  rationale: string;
  keyword_hits?: string[];
}

interface Proposal {
  edits: ProposalEdit[];
  ats_score?: number | null;
  linkedin_draft?: string | null;
  email_draft?: string | null;
  note?: string;
}

function Badge({ children, tone }: { children: ReactNode; tone: "neutral" | "ok" | "warn" | "bad" }) {
  const cls =
    tone === "ok"
      ? "bg-emerald-100 text-emerald-900"
      : tone === "warn"
        ? "bg-amber-100 text-amber-900"
        : tone === "bad"
          ? "bg-rose-100 text-rose-900"
          : "bg-ink-200 text-ink-800";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </span>
  );
}

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-ink-200/80 bg-white p-6 shadow-card">
      <div className="mb-4">
        <h2 className="font-display text-lg font-semibold tracking-tight text-ink-950">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-ink-500">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

async function copyText(text: string) {
  await navigator.clipboard.writeText(text);
}

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<ResumeState | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [proposeRound, setProposeRound] = useState(0);
  const [draft, setDraft] = useState<{
    latex_source: string | null;
    refined_resume_text: string | null;
    ats_score: number | null;
  } | null>(null);
  const [summary, setSummary] = useState<{ headline: string; edits_count: number; ats_score: number | null } | null>(
    null,
  );
  const [atsPreview, setAtsPreview] = useState<Record<string, unknown> | null>(null);
  const [compileJobId, setCompileJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"proposal" | "draft" | "outreach">("proposal");
  const [health, setHealth] = useState<string | null>(null);
  const [readyInfo, setReadyInfo] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const k = sessionStorage.getItem(STORAGE_KEY);
    if (k) setApiKey(k);
  }, []);

  useEffect(() => {
    if (apiKey) sessionStorage.setItem(STORAGE_KEY, apiKey);
  }, [apiKey]);

  const canUseApi = useMemo(() => apiKey.trim().length > 0, [apiKey]);

  const run = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
      setError(null);
      setBusy(true);
      try {
        return await fn();
      } catch (e) {
        if (e instanceof ApiError) setError(e.body);
        else if (e instanceof Error) setError(e.message);
        else setError(String(e));
        return undefined;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const pingHealth = () =>
    run(async () => {
      const r = await apiFetch<{ status: string }>("/health", apiKey.trim());
      setHealth(r.status);
    });

  const createSession = () =>
    run(async () => {
      const r = await apiFetch<{ session_id: string; state: ResumeState }>("/sessions", apiKey.trim(), {
        method: "POST",
        body: JSON.stringify({ resume_text: resumeText, job_description: jdText }),
      });
      setSessionId(r.session_id);
      setSessionState(r.state);
      setProposal(null);
      setDraft(null);
      setSummary(null);
      setAtsPreview(null);
      setCompileJobId(null);
      setJobStatus(null);
      setJobError(null);
      setDownloadUrl(null);
    });

  const fetchAts = () =>
    run(async () => {
      if (!sessionId) return;
      const r = await apiFetch<Record<string, unknown>>(`/sessions/${sessionId}/ats-score`, apiKey.trim());
      setAtsPreview(r);
    });

  const proposeEdits = () =>
    run(async () => {
      if (!sessionId) return;
      const r = await apiFetch<{ proposal: Proposal; state: ResumeState; propose_round: number }>(
        `/sessions/${sessionId}/propose-edits`,
        apiKey.trim(),
        { method: "POST" },
      );
      setProposal(r.proposal);
      setSessionState(r.state);
      setProposeRound(r.propose_round);
      setSummary(null);
      setDownloadUrl(null);
      setCompileJobId(null);
      setJobStatus(null);
      setJobError(null);
      const d = await apiFetch<{
        latex_source: string | null;
        refined_resume_text: string | null;
        ats_score: number | null;
      }>(`/sessions/${sessionId}/draft`, apiKey.trim());
      setDraft({
        latex_source: d.latex_source,
        refined_resume_text: d.refined_resume_text,
        ats_score: d.ats_score,
      });
    });

  const loadDraft = () =>
    run(async () => {
      if (!sessionId) return;
      const r = await apiFetch<{
        latex_source: string | null;
        refined_resume_text: string | null;
        ats_score: number | null;
        state: ResumeState;
      }>(`/sessions/${sessionId}/draft`, apiKey.trim());
      setDraft({
        latex_source: r.latex_source,
        refined_resume_text: r.refined_resume_text,
        ats_score: r.ats_score,
      });
      setSessionState(r.state);
    });

  const loadSummary = () =>
    run(async () => {
      if (!sessionId) return;
      const r = await apiFetch<{
        headline: string;
        edits_count: number;
        ats_score: number | null;
        state: ResumeState;
      }>(`/sessions/${sessionId}/summary`, apiKey.trim());
      setSummary({ headline: r.headline, edits_count: r.edits_count, ats_score: r.ats_score });
      setSessionState(r.state);
    });

  const confirmCompile = () =>
    run(async () => {
      if (!sessionId) return;
      const r = await apiFetch<{ compile_job_id: string; state: ResumeState }>(
        `/sessions/${sessionId}/confirm-compile`,
        apiKey.trim(),
        { method: "POST" },
      );
      setCompileJobId(r.compile_job_id);
      setSessionState(r.state);
      setJobStatus("queued");
      setJobError(null);
      setDownloadUrl(null);
    });

  const refreshJob = useCallback(async () => {
    if (!compileJobId || !canUseApi) return;
    setError(null);
    try {
      const r = await apiFetch<{ status: JobStatus; error_message: string | null }>(
        `/jobs/${compileJobId}/status`,
        apiKey.trim(),
      );
      setJobStatus(r.status);
      setJobError(r.error_message);
      if (r.status === "succeeded") {
        const a = await apiFetch<{ download_url: string }>(
          `/artifacts/${compileJobId}/download-url`,
          apiKey.trim(),
        );
        setDownloadUrl(a.download_url);
      } else {
        setDownloadUrl(null);
      }
    } catch (e) {
      if (e instanceof ApiError) setError(e.body);
      else if (e instanceof Error) setError(e.message);
    }
  }, [compileJobId, apiKey, canUseApi]);

  useEffect(() => {
    if (!compileJobId) return;
    void refreshJob();
  }, [compileJobId, refreshJob]);

  useEffect(() => {
    if (!compileJobId || jobStatus === "succeeded" || jobStatus === "failed") return;
    const t = window.setInterval(() => {
      void refreshJob();
    }, 2000);
    return () => window.clearInterval(t);
  }, [compileJobId, jobStatus, refreshJob]);

  const jobTone = (s: JobStatus | null): "neutral" | "ok" | "warn" | "bad" => {
    if (s === "succeeded") return "ok";
    if (s === "failed") return "bad";
    if (s === "running" || s === "queued") return "warn";
    return "neutral";
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-ink-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-xl font-bold tracking-tight text-ink-950">ChirandhAI</p>
            <p className="text-sm text-ink-500">ATS-aware edits, LaTeX draft, PDF after you confirm.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {sessionId ? <Badge tone="neutral">session {sessionId.slice(0, 8)}…</Badge> : null}
            {sessionState ? <Badge tone="warn">{sessionState}</Badge> : null}
            {health ? <Badge tone="ok">api {health}</Badge> : null}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        {error ? (
          <div
            className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 whitespace-pre-wrap"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <Card
          title="1. Connection"
          subtitle="Same key as X-API-Key (e.g. docker-dev-key when using compose). Stored only in this browser tab (sessionStorage)."
        >
          <label className="block">
            <span className="text-sm font-medium text-ink-700">API key</span>
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-1 w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm outline-none ring-accent/30 focus:ring-2"
              placeholder="••••••••"
            />
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!canUseApi || busy}
              onClick={() => void pingHealth()}
              className="rounded-xl bg-ink-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              Ping /health
            </button>
            <button
              type="button"
              disabled={!canUseApi || busy}
              onClick={() =>
                void run(async () => {
                  const r = await apiFetch<Record<string, unknown>>("/ready", apiKey.trim());
                  setReadyInfo(r);
                })
              }
              className="rounded-xl border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-800 disabled:opacity-40"
            >
              Check /ready
            </button>
          </div>
          {readyInfo ? (
            <pre className="mt-4 max-h-40 overflow-auto rounded-xl bg-ink-950 p-3 text-xs text-ink-100">
              {JSON.stringify(readyInfo, null, 2)}
            </pre>
          ) : null}
        </Card>

        <Card
          title="2. Resume & job description"
          subtitle="Paste your current resume and the target role description. The API applies minimal edits; it does not blindly rewrite everything."
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-ink-700">Resume</span>
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                rows={12}
                className="mt-1 w-full rounded-xl border border-ink-200 bg-ink-50/50 px-3 py-2 text-sm outline-none ring-accent/30 focus:ring-2"
                placeholder="Paste resume text…"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-ink-700">Job description</span>
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                rows={12}
                className="mt-1 w-full rounded-xl border border-ink-200 bg-ink-50/50 px-3 py-2 text-sm outline-none ring-accent/30 focus:ring-2"
                placeholder="Paste job description…"
              />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!canUseApi || busy || !resumeText.trim() || !jdText.trim()}
              onClick={() => void createSession()}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm disabled:opacity-40"
            >
              Create session
            </button>
            {sessionId ? (
              <button
                type="button"
                disabled={!canUseApi || busy}
                onClick={() => void fetchAts()}
                className="rounded-xl border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-800 disabled:opacity-40"
              >
                ATS score (API)
              </button>
            ) : null}
          </div>
        </Card>

        {atsPreview ? (
          <Card title="ATS preview" subtitle="From GET /sessions/{id}/ats-score">
            <pre className="max-h-64 overflow-auto rounded-xl bg-ink-950 p-4 text-xs text-ink-100">
              {JSON.stringify(atsPreview, null, 2)}
            </pre>
          </Card>
        ) : null}

        {sessionId ? (
          <Card
            title="3. Proposals & drafts"
            subtitle="Run propose-edits, review structured changes, then load the LaTeX draft before generating a PDF."
          >
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!canUseApi || busy}
                onClick={() => void proposeEdits()}
                className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm disabled:opacity-40"
              >
                Propose edits
              </button>
              <button
                type="button"
                disabled={!canUseApi || busy}
                onClick={() => void loadDraft()}
                className="rounded-xl border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-800 disabled:opacity-40"
              >
                Load draft
              </button>
              <button
                type="button"
                disabled={!canUseApi || busy}
                onClick={() => void loadSummary()}
                className="rounded-xl border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-800 disabled:opacity-40"
              >
                Summary (GPT-friendly)
              </button>
              {proposeRound > 0 ? (
                <span className="self-center text-xs text-ink-500">round {proposeRound}</span>
              ) : null}
            </div>

            {summary ? (
              <p className="mt-4 rounded-xl bg-ink-50 px-4 py-3 text-sm text-ink-800">{summary.headline}</p>
            ) : null}

            {proposal ? (
              <div className="mt-6">
                <div className="flex gap-2 border-b border-ink-200 pb-2">
                  {(
                    [
                      ["proposal", "Edits"],
                      ["draft", "Draft"],
                      ["outreach", "LinkedIn & email"],
                    ] as const
                  ).map(([k, label]) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setTab(k)}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                        tab === k ? "bg-ink-900 text-white" : "text-ink-600 hover:bg-ink-100"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {tab === "proposal" ? (
                  <div className="mt-4 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {typeof proposal.ats_score === "number" ? (
                        <Badge tone="ok">ATS {proposal.ats_score}</Badge>
                      ) : null}
                      {proposal.note ? <Badge tone="warn">{proposal.note}</Badge> : null}
                    </div>
                    <div className="overflow-x-auto rounded-xl border border-ink-200">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
                          <tr>
                            <th className="px-3 py-2">Section</th>
                            <th className="px-3 py-2">Before</th>
                            <th className="px-3 py-2">After</th>
                            <th className="px-3 py-2">Why</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-ink-100">
                          {(proposal.edits ?? []).map((e, i) => (
                            <tr key={i} className="align-top">
                              <td className="px-3 py-2 font-medium text-ink-800">{e.section}</td>
                              <td className="px-3 py-2 text-ink-600">
                                <pre className="whitespace-pre-wrap font-sans text-xs">{e.before}</pre>
                              </td>
                              <td className="px-3 py-2 text-ink-900">
                                <pre className="whitespace-pre-wrap font-sans text-xs">{e.after}</pre>
                              </td>
                              <td className="px-3 py-2 text-ink-600">
                                <span className="text-xs">{e.rationale}</span>
                                {e.keyword_hits?.length ? (
                                  <div className="mt-1 flex flex-wrap gap-1">
                                    {e.keyword_hits.map((k) => (
                                      <span key={k} className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] text-accent-fg">
                                        {k}
                                      </span>
                                    ))}
                                  </div>
                                ) : null}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}

                {tab === "draft" ? (
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-sm font-medium text-ink-700">Refined resume</span>
                        {draft?.refined_resume_text ? (
                          <button
                            type="button"
                            className="text-xs font-medium text-accent"
                            onClick={() => void copyText(draft.refined_resume_text ?? "")}
                          >
                            Copy
                          </button>
                        ) : (
                          <span className="text-xs text-ink-400">Load draft first</span>
                        )}
                      </div>
                      <pre className="max-h-80 overflow-auto rounded-xl border border-ink-200 bg-ink-50/80 p-3 text-xs text-ink-800 whitespace-pre-wrap">
                        {draft?.refined_resume_text ?? "—"}
                      </pre>
                    </div>
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-sm font-medium text-ink-700">LaTeX source</span>
                        {draft?.latex_source ? (
                          <button
                            type="button"
                            className="text-xs font-medium text-accent"
                            onClick={() => void copyText(draft.latex_source ?? "")}
                          >
                            Copy
                          </button>
                        ) : (
                          <span className="text-xs text-ink-400">Load draft first</span>
                        )}
                      </div>
                      <pre className="max-h-80 overflow-auto rounded-xl border border-ink-200 bg-ink-950 p-3 text-xs text-ink-100 whitespace-pre-wrap">
                        {draft?.latex_source ?? "—"}
                      </pre>
                    </div>
                  </div>
                ) : null}

                {tab === "outreach" ? (
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-sm font-medium text-ink-700">LinkedIn draft</span>
                        {proposal.linkedin_draft ? (
                          <button
                            type="button"
                            className="text-xs font-medium text-accent"
                            onClick={() => void copyText(proposal.linkedin_draft ?? "")}
                          >
                            Copy
                          </button>
                        ) : null}
                      </div>
                      <pre className="min-h-[8rem] whitespace-pre-wrap rounded-xl border border-ink-200 bg-ink-50/80 p-3 text-sm text-ink-800">
                        {proposal.linkedin_draft ?? "—"}
                      </pre>
                    </div>
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-sm font-medium text-ink-700">Email draft</span>
                        {proposal.email_draft ? (
                          <button
                            type="button"
                            className="text-xs font-medium text-accent"
                            onClick={() => void copyText(proposal.email_draft ?? "")}
                          >
                            Copy
                          </button>
                        ) : null}
                      </div>
                      <pre className="min-h-[8rem] whitespace-pre-wrap rounded-xl border border-ink-200 bg-ink-50/80 p-3 text-sm text-ink-800">
                        {proposal.email_draft ?? "—"}
                      </pre>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-4 text-sm text-ink-500">Run “Propose edits” to see structured changes and outreach drafts.</p>
            )}
          </Card>
        ) : null}

        {sessionId &&
        (sessionState === "proposed" ||
          sessionState === "compiling" ||
          sessionState === "ready" ||
          sessionState === "failed" ||
          compileJobId) ? (
          <Card
            title="4. PDF generation"
            subtitle="Confirms compile on the server and enqueues the Tectonic worker. Polls job status and fetches a signed download URL when ready."
          >
            {sessionState === "proposed" && !compileJobId ? (
              <button
                type="button"
                disabled={!canUseApi || busy}
                onClick={() => void confirmCompile()}
                className="rounded-xl bg-ink-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                Confirm & build PDF
              </button>
            ) : sessionState === "proposed" && compileJobId ? (
              <p className="text-sm text-ink-600">Job queued — status below.</p>
            ) : sessionState === "compiling" || compileJobId ? (
              <p className="text-sm text-ink-600">Build in progress or finished — status below.</p>
            ) : sessionState === "ready" ? (
              <p className="text-sm text-emerald-800">Session marked ready. Use the download link if the job succeeded.</p>
            ) : (
              <p className="text-sm text-ink-600">Last compile failed — see job error below.</p>
            )}

            {compileJobId ? (
              <div className="mt-6 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-ink-600">Job</span>
                  <code className="rounded bg-ink-100 px-2 py-0.5 text-xs">{compileJobId}</code>
                  {jobStatus ? <Badge tone={jobTone(jobStatus)}>{jobStatus}</Badge> : null}
                  <button
                    type="button"
                    onClick={() => void refreshJob()}
                    className="text-xs font-medium text-accent"
                  >
                    Refresh now
                  </button>
                </div>
                {jobError ? (
                  <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">{jobError}</p>
                ) : null}
                {downloadUrl ? (
                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm"
                  >
                    Download PDF
                  </a>
                ) : jobStatus === "succeeded" ? (
                  <p className="text-sm text-ink-500">Preparing signed URL…</p>
                ) : null}
              </div>
            ) : sessionState === "proposed" ? (
              <p className="mt-3 text-sm text-ink-500">Click confirm to enqueue PDF generation.</p>
            ) : null}
          </Card>
        ) : sessionId ? (
          <Card title="4. PDF generation" subtitle="Propose edits first; confirm-compile is only allowed in the proposed state.">
            <p className="text-sm text-ink-600">
              Current state: <strong>{sessionState ?? "unknown"}</strong>. Run propose-edits and wait until state is{" "}
              <code>proposed</code>.
            </p>
          </Card>
        ) : null}

        <footer className="pb-12 text-center text-xs text-ink-400">
          API docs at <code className="rounded bg-ink-100 px-1 py-0.5">/docs</code> · OpenAPI{" "}
          <code className="rounded bg-ink-100 px-1 py-0.5">/openapi.json</code>
        </footer>
      </main>
    </div>
  );
}
