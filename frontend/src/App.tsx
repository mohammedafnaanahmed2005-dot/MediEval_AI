import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, ArrowDownToLine, ArrowRight, BarChart3, Check,
  ChevronDown, CircleHelp, ClipboardCheck, Database, FileSpreadsheet, FileText,
  HeartPulse, LayoutDashboard, LoaderCircle, Menu, Plus, Search, ShieldCheck,
  Sparkles, Upload, X,
} from "lucide-react";
import { API_URL, checkApiHealth, downloadReport, getDashboard, getEvaluations, uploadDataset } from "./api";
import type { DashboardData, EvaluationResult, Finding } from "./types";

type Page = "overview" | "evaluate" | "history";
const Plot = lazy(() => import("./Plot"));
const emptySummary: DashboardData["summary"] = {
  evaluations: 0, records: 0, issues: 0, missing: 0, unsupported: 0, average_score: null,
};

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [dashboard, setDashboard] = useState<DashboardData>({
    summary: emptySummary, recent_evaluations: [], trend: [],
  });
  const [history, setHistory] = useState<DashboardData["recent_evaluations"]>([]);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  const [search, setSearch] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await checkApiHealth();
      const [data, evaluations] = await Promise.all([getDashboard(), getEvaluations()]);
      setDashboard(data);
      setHistory(evaluations);
      setApiOnline(true);
      setError("");
    } catch (reason) {
      setApiOnline(false);
      setError(reason instanceof Error ? reason.message : "Could not load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (apiOnline) return;
    const timer = window.setInterval(() => {
      void checkApiHealth()
        .then(() => refresh())
        .catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [apiOnline, refresh]);

  async function processFile(
    file: File,
    mapping?: { ai_label_column: string; reference_answer_column: string },
  ) {
    setError("");
    setBusy(true);
    try {
      const evaluation = await uploadDataset(file, mapping);
      setResult(evaluation);
      setSourceFile(file);
      setPage("evaluate");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed. Please check the file and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function loadDemo() {
    setError("");
    setBusy(true);
    try {
      const response = await fetch("/demo-labs.csv");
      if (!response.ok) throw new Error("The included synthetic example could not be loaded.");
      const file = new File([await response.blob()], "demo-labs.csv", { type: "text/csv" });
      await processFile(file);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the demo dataset.");
      setBusy(false);
    }
  }

  async function exportReport(id: string, format: "csv" | "pdf" | "docx") {
    setError("");
    try {
      await downloadReport(id, format);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Report download failed.");
    }
  }

  const filteredHistory = useMemo(
    () => history.filter((item) => item.filename.toLowerCase().includes(search.toLowerCase())),
    [history, search],
  );
  const allIssues = result ? [...result.validation.issues, ...result.evaluation.issues] : [];
  const nav = (
    <nav className="sidebar-nav" aria-label="Main navigation">
      <p className="nav-section">WORKSPACE</p>
      <NavButton active={page === "overview"} onClick={() => { setPage("overview"); setMobileNav(false); }} icon={<LayoutDashboard size={18} />} label="Overview" />
      <NavButton active={page === "evaluate"} onClick={() => { setPage("evaluate"); setMobileNav(false); }} icon={<ClipboardCheck size={18} />} label="Evaluate dataset" />
      <NavButton active={page === "history"} onClick={() => { setPage("history"); setMobileNav(false); }} icon={<BarChart3 size={18} />} label="Evaluation history" />
      <p className="nav-section nav-spaced">RESOURCES</p>
      <a className="nav-link" href={`${API_URL}/docs`} target="_blank" rel="noreferrer"><CircleHelp size={18} /> API documentation <ArrowRight size={14} className="nav-external" /></a>
      <div className="sidebar-help">
        <div className="help-icon"><ShieldCheck size={20} /></div>
        <strong>Evidence first</strong>
        <p>Every finding is grounded in supplied data. Nothing here is a diagnosis.</p>
        <button onClick={() => { setPage("evaluate"); setMobileNav(false); }}>How it works <ArrowRight size={14} /></button>
      </div>
    </nav>
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Activity size={21} strokeWidth={2.6} /></div>
          <div><strong>MediEval<span> AI</span></strong><small>DATA EVALUATION</small></div>
        </div>
        {nav}
        <div className="sidebar-bottom">
          <span className="avatar">ME</span>
          <div><strong>Evaluation workspace</strong><small>Local environment</small></div>
          <ChevronDown size={16} />
        </div>
      </aside>
      {mobileNav && <div className="mobile-backdrop" onClick={() => setMobileNav(false)}>{nav}</div>}
      <main className="main-area">
        <header className="topbar">
          <div className="mobile-brand"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open menu"><Menu size={20} /></button><strong>MediEval <span>AI</span></strong></div>
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{pageTitle(page)}</strong></div>
          <div className="topbar-right">
            <span className={`system-status ${apiOnline ? "" : "system-offline"}`}><i /> {apiOnline ? "System operational" : "API reconnecting · retrying"}</span>
            <button className="icon-button help-top" title="API documentation" onClick={() => window.open(`${API_URL}/docs`, "_blank", "noopener,noreferrer")}><CircleHelp size={18} /></button>
          </div>
        </header>
        {error && <div className="alert alert-error" role="alert"><AlertTriangle size={17} />{error}<button onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button></div>}
        <div className="page-content">
          {page === "overview" && (
            <Overview
              dashboard={dashboard} loading={loading} onEvaluate={() => setPage("evaluate")}
              onDemo={() => void loadDemo()} onExport={exportReport}
              onHistory={() => setPage("history")}
            />
          )}
          {page === "evaluate" && (
            <EvaluatePage
              result={result} busy={busy} inputRef={inputRef} issues={allIssues}
              sourceFile={sourceFile}
              onFile={(file) => void processFile(file)}
              onDemo={() => void loadDemo()}
              onMapColumns={(mapping) => {
                if (sourceFile) void processFile(sourceFile, mapping);
              }}
              onExport={exportReport}
              onClear={() => { setResult(null); setSourceFile(null); setError(""); }}
            />
          )}
          {page === "history" && (
            <HistoryPage
              history={filteredHistory} search={search} onSearch={setSearch}
              onEvaluate={() => setPage("evaluate")} onExport={exportReport}
            />
          )}
        </div>
        <footer className="footer">
          <span>© {new Date().getFullYear()} MediEval AI</span>
          <span><ShieldCheck size={14} /> For research and evaluation only · Not for clinical decision-making</span>
        </footer>
      </main>
    </div>
  );
}

function Overview({
  dashboard, loading, onEvaluate, onDemo, onExport, onHistory,
}: {
  dashboard: DashboardData; loading: boolean; onEvaluate: () => void; onDemo: () => void;
  onExport: (id: string, format: "csv" | "pdf" | "docx") => Promise<void>;
  onHistory: () => void;
}) {
  const summary = dashboard.summary;
  const recent = dashboard.recent_evaluations;
  return (
    <>
      <div className="page-heading heading-row">
        <div><p className="eyebrow">YOUR QUALITY COMMAND CENTER</p><h1>Good morning <span className="wave">✦</span></h1><p className="page-subtitle">A clear view of your dataset quality and AI evaluation performance.</p></div>
        <div className="heading-actions"><button className="button button-secondary" onClick={onDemo}><Sparkles size={16} /> Try demo data</button><button className="button button-primary" onClick={onEvaluate}><Plus size={17} /> New evaluation</button></div>
      </div>
      <div className="safety-banner"><div className="safety-icon"><ShieldCheck size={18} /></div><div><strong>Built for responsible evaluation</strong><span>Findings are evidence-based. Clinical flags always require human review — this is not a diagnostic tool.</span></div><span className="banner-tag">SAFETY FIRST</span></div>
      <div className="section-title-row"><div><h2>At a glance</h2><p>Aggregate results across your evaluations</p></div><span className="updated-note">{loading ? <><LoaderCircle size={14} className="spin" /> Updating</> : <><i /> Live data</>}</span></div>
      <div className="stats-grid">
        <StatCard label="Records analyzed" value={formatNumber(summary.records)} detail={`${summary.evaluations} evaluation${summary.evaluations === 1 ? "" : "s"} completed`} icon={<Database />} tone="blue" />
        <StatCard label="Data quality flags" value={formatNumber(summary.issues)} detail={`${formatNumber(summary.missing)} missing values detected`} icon={<AlertTriangle />} tone="amber" />
        <StatCard label="Average AI score" value={summary.average_score === null ? "—" : `${summary.average_score.toFixed(1)}`} detail={summary.average_score === null ? "Requires verified reference answers" : "Weighted score out of 100"} icon={<Activity />} tone="green" />
        <StatCard label="Unsupported claims" value={formatNumber(summary.unsupported)} detail="Flagged for human review" icon={<ShieldCheck />} tone="purple" />
      </div>
      <div className="charts-grid">
        <section className="panel trend-panel">
          <div className="panel-head"><div><h3>Evaluation performance</h3><p>Score trend across recent runs</p></div><span className="chart-legend"><i /> Overall score</span></div>
          {recent.length > 0 ? (
            <Suspense fallback={<ChartLoading />}>
            <Plot
              data={[{
                x: dashboard.trend.map((item, index) => `${item.date} · ${index + 1}`),
                y: dashboard.trend.map((item) => item.score),
                type: "scatter", mode: "lines+markers", connectgaps: false,
                line: { color: "#3984f6", width: 3, shape: "spline" },
                marker: { color: "#3984f6", size: 8, line: { color: "white", width: 2 } },
                hovertemplate: "%{x}<br>Score: %{y:.1f}<extra></extra>",
              }]}
              layout={{
                autosize: true, height: 245, margin: { l: 38, r: 12, t: 12, b: 35 },
                paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                font: { family: "Inter, sans-serif", size: 11, color: "#8794a8" },
                xaxis: { showgrid: false, zeroline: false, tickfont: { size: 10 } },
                yaxis: { range: [0, 100], dtick: 25, gridcolor: "#edf1f6", zeroline: false },
                showlegend: false,
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
            />
            </Suspense>
          ) : <ChartEmpty onClick={onDemo} />}
        </section>
        <section className="panel breakdown-panel">
          <div className="panel-head"><div><h3>Evaluation breakdown</h3><p>AI output classification results</p></div><span className="mini-badge">ALL RUNS</span></div>
          {recent.length > 0 ? (
            <Suspense fallback={<ChartLoading />}>
            <Plot
              data={[{
                labels: ["Supported", "Review required"],
                values: [
                  Math.max(0, summary.records - summary.unsupported),
                  summary.unsupported,
                ],
                type: "pie", hole: 0.74, sort: false,
                marker: { colors: ["#3984f6", "#f3a83b"], line: { color: "#fff", width: 4 } },
                textinfo: "none", hovertemplate: "%{label}: %{value}<extra></extra>",
              }]}
              layout={{
                autosize: true, height: 245, margin: { l: 0, r: 0, t: 3, b: 3 },
                paper_bgcolor: "transparent", showlegend: false,
                annotations: [{ text: String(summary.unsupported), showarrow: false, font: { size: 27, color: "#1d2b42", family: "Inter, sans-serif" } }, { text: "flagged", showarrow: false, y: 0.39, font: { size: 10, color: "#8794a8" } }],
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
            />
            </Suspense>
          ) : <ChartEmpty onClick={onDemo} />}
          <div className="donut-legend"><span><i className="legend-blue" /> Supported outputs</span><span><i className="legend-amber" /> Review required</span></div>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-head"><div><h3>Recent evaluations</h3><p>Your latest dataset quality runs</p></div><button className="text-button" onClick={onHistory}>View all <ArrowRight size={14} /></button></div>
        {recent.length > 0 ? (
          <EvaluationTable items={recent.slice(0, 5)} onExport={onExport} />
        ) : <div className="table-empty"><div className="empty-icon"><FileSpreadsheet size={22} /></div><strong>No evaluations yet</strong><span>Upload a dataset or try the synthetic sample to see your insights.</span><button className="button button-primary button-small" onClick={onDemo}><Sparkles size={15} /> Load sample dataset</button></div>}
      </section>
    </>
  );
}

function EvaluatePage({
  result, busy, inputRef, issues, sourceFile, onFile, onDemo, onMapColumns, onExport, onClear,
}: {
  result: EvaluationResult | null; busy: boolean; inputRef: React.RefObject<HTMLInputElement>;
  sourceFile: File | null;
  issues: Finding[]; onFile: (file: File) => void; onDemo: () => void;
  onMapColumns: (mapping: { ai_label_column: string; reference_answer_column: string }) => void;
  onExport: (id: string, format: "csv" | "pdf" | "docx") => Promise<void>; onClear: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const verification = result?.evaluation.verification_summary ?? {
    verified: 0, not_verified: 0, unscored: 0, scored: 0,
  };
  const qualityCounts = [
    { label: "Data quality", count: issues.filter((issue) => issue.category === "data_quality").length, color: "#3984f6" },
    { label: "Human review", count: issues.filter((issue) => issue.category === "clinical_review").length, color: "#f0ac50" },
    { label: "AI safety", count: issues.filter((issue) => issue.category === "ai_safety").length, color: "#8a78d6" },
  ];
  const metricValues = result ? [
    { label: "Overall score", value: result.evaluation.metrics.overall_score === null ? null : result.evaluation.metrics.overall_score / 100, color: "#7c73cf" },
    { label: "Accuracy", value: result.evaluation.metrics.accuracy, color: "#3984f6" },
    { label: "Precision", value: result.evaluation.metrics.precision, color: "#4b9fc5" },
    { label: "Recall", value: result.evaluation.metrics.recall, color: "#43a889" },
    { label: "F1 score", value: result.evaluation.metrics.f1, color: "#8a78d6" },
    { label: "Hallucination rate", value: result.evaluation.metrics.hallucination_rate, color: "#df7767" },
  ].filter((item) => item.value !== null) : [];
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">DATASET WORKFLOW</p>
        <div className="heading-row"><div><h1>Evaluate a dataset</h1><p className="page-subtitle">Validate medical data and test AI outputs against verified evidence.</p></div>{result && <button className="button button-secondary" onClick={onClear}><Plus size={16} /> New evaluation</button>}</div>
      </div>
      {!result ? (
        <div className="upload-layout">
          <section className={`upload-card ${dragging ? "drag-active" : ""}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); const file = event.dataTransfer.files[0]; if (file) onFile(file); }}>
            <div className="upload-icon"><Upload size={23} /></div>
            <h2>{busy ? "Evaluating your dataset…" : "Upload your dataset"}</h2>
            <p>Drag and drop your data file here, or browse to choose a file.</p>
            <input ref={inputRef} className="file-input" type="file" accept=".csv,.xlsx,.xls,.json" onChange={(event) => { const file = event.target.files?.[0]; if (file) onFile(file); event.currentTarget.value = ""; }} />
            <button className="button button-primary" disabled={busy} onClick={() => inputRef.current?.click()}>{busy ? <LoaderCircle size={16} className="spin" /> : <Upload size={16} />}{busy ? "Processing…" : "Choose a file"}</button>
            <span className="accepted-files">CSV · Excel · JSON <i /> Up to 10 MB</span>
            {busy && <div className="progress-track"><span /></div>}
          </section>
          <aside className="upload-aside">
            <div className="aside-card"><div className="aside-heading"><div className="aside-icon"><Sparkles size={17} /></div><h3>Try a sample dataset</h3></div><p>Explore the full workflow with 8 synthetic lab records. No real patient data.</p><button className="sample-link" disabled={busy} onClick={onDemo}>Load synthetic example <ArrowRight size={15} /></button><div className="sample-chip"><FileSpreadsheet size={14} /> demo-labs.csv <span>8 records</span></div></div>
            <div className="aside-card privacy-card"><div className="aside-heading"><div className="aside-icon privacy"><ShieldCheck size={17} /></div><h3>Your data stays private</h3></div><ul><li><Check size={14} /> Raw rows are never saved to the database</li><li><Check size={14} /> Identifier fields are redacted in previews</li><li><Check size={14} /> Only aggregate metrics are retained</li></ul></div>
          </aside>
        </div>
      ) : (
        <div className="results">
          <div className="result-banner">
            <div className="result-file-icon"><FileSpreadsheet size={20} /></div><div className="result-file-name"><strong>{result.filename}</strong><span>{result.validation.record_count.toLocaleString()} records · {result.validation.column_count} columns · Evaluated {formatDate(result.created_at)}</span></div>
            <div className="result-actions"><ReportButtons id={result.id} onExport={onExport} /><button className="button button-primary button-small" onClick={onClear}><Plus size={15} /> New run</button></div>
          </div>
          <div className="result-stats">
            <StatCard label="Records analyzed" value={result.validation.record_count.toLocaleString()} detail="Rows processed in memory" icon={<Database />} tone="blue" />
            <StatCard label="Data quality flags" value={result.validation.quality_summary.data_quality_issue_count.toString()} detail={`${result.validation.missing_value_count} missing values`} icon={<AlertTriangle />} tone="amber" />
            <StatCard label="AI evaluation score" value={result.evaluation.metrics.overall_score === null ? "N/A" : result.evaluation.metrics.overall_score.toFixed(1)} detail={result.evaluation.has_reference_answers ? "Weighted score out of 100" : "Add verified answers to score"} icon={<Activity />} tone="green" />
            <StatCard label="Unsupported claims" value={result.evaluation.unsupported_count.toString()} detail={`${result.validation.quality_summary.clinical_review_count} clinical review flags`} icon={<ShieldCheck />} tone="purple" />
          </div>
          <ColumnMappingPanel
            key={result.id}
            result={result}
            disabled={busy || !sourceFile}
            onApply={onMapColumns}
          />
          <div className="verification-counts" aria-label="Reference verification summary">
            <div className="verification-count verified"><Check size={16} /><span>Verified</span><strong>{verification.verified}</strong></div>
            <div className="verification-count not-verified"><X size={16} /><span>Not verified</span><strong>{verification.not_verified}</strong></div>
            <div className="verification-count unscored"><CircleHelp size={16} /><span>Unscored</span><strong>{verification.unscored}</strong></div>
            <p>“Verified” means the AI label matches a supplied reference answer. Missing labels or reference answers are unscored, not counted as verified.</p>
          </div>
          <div className="charts-grid result-charts">
            <section className="panel result-chart-panel">
              <div className="panel-head"><div><h3>Verified vs. not verified</h3><p>AI labels compared with supplied reference answers</p></div><span className="mini-badge">{verification.scored} SCORED</span></div>
              {result.validation.record_count > 0 ? (
                <Suspense fallback={<ChartLoading />}>
                  <Plot
                    data={[{
                      labels: ["Verified", "Not verified", "Unscored"],
                      values: [verification.verified, verification.not_verified, verification.unscored],
                      type: "pie", hole: 0.68, sort: false,
                      marker: { colors: ["#46a77e", "#e27668", "#bdc7d4"], line: { color: "#fff", width: 3 } },
                      textinfo: "label+percent",
                      textposition: "outside",
                      hovertemplate: "%{label}: %{value} record(s)<extra></extra>",
                    }]}
                    layout={{
                      autosize: true, height: 260, margin: { l: 15, r: 15, t: 15, b: 15 },
                      paper_bgcolor: "transparent", showlegend: false,
                      font: { family: "DM Sans, sans-serif", size: 10, color: "#68798f" },
                      annotations: [{ text: String(verification.scored), showarrow: false, font: { size: 25, color: "#1d2b42", family: "DM Sans, sans-serif" } }, { text: "scored", showarrow: false, y: 0.39, font: { size: 10, color: "#8794a8" } }],
                    }}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: "100%" }}
                  />
                </Suspense>
              ) : <div className="comparison-empty"><CircleHelp size={18} /><span>No records have both an AI output label and a reference answer, so verification cannot be scored yet.</span></div>}
            </section>
            <section className="panel result-chart-panel">
              <div className="panel-head"><div><h3>Dataset review findings</h3><p>Findings detected in this uploaded file</p></div><span className="mini-badge">{issues.length} FINDINGS</span></div>
              {issues.length ? (
                <Suspense fallback={<ChartLoading />}>
                  <Plot
                    data={[{
                      x: qualityCounts.map((item) => item.count),
                      y: qualityCounts.map((item) => item.label),
                      type: "bar", orientation: "h",
                      marker: { color: qualityCounts.map((item) => item.color), line: { color: "#fff", width: 1 } },
                      text: qualityCounts.map((item) => String(item.count)),
                      textposition: "outside",
                      hovertemplate: "%{y}: %{x} finding(s)<extra></extra>",
                    }]}
                    layout={{
                      autosize: true, height: 260, margin: { l: 105, r: 30, t: 15, b: 30 },
                      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                      font: { family: "DM Sans, sans-serif", size: 10, color: "#68798f" },
                      xaxis: { rangemode: "tozero", dtick: 1, gridcolor: "#edf1f6", zeroline: false, title: { text: "Findings" } },
                      yaxis: { showgrid: false, zeroline: false, automargin: true },
                      showlegend: false,
                    }}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: "100%" }}
                  />
                </Suspense>
              ) : <div className="comparison-empty"><Check size={18} /><span>No data-quality or review findings were detected in this dataset.</span></div>}
            </section>
          </div>
          <section className="panel metric-panel">
            <div className="panel-head"><div><h3>AI evaluation metrics</h3><p>Classification performance measured against verified reference answers</p></div>{result.evaluation.has_reference_answers ? <span className="verified-tag"><Check size={13} /> VERIFIED REFERENCES</span> : <span className="mini-badge">NO REFERENCES</span>}</div>
            <div className="metric-grid">
              <Metric label="Accuracy" value={result.evaluation.metrics.accuracy} />
              <Metric label="Precision" value={result.evaluation.metrics.precision} />
              <Metric label="Recall" value={result.evaluation.metrics.recall} />
              <Metric label="F1 score" value={result.evaluation.metrics.f1} />
              <Metric label="Hallucination rate" value={result.evaluation.metrics.hallucination_rate} />
            </div>
            {metricValues.length > 0 && (
              <Suspense fallback={<ChartLoading />}>
                <Plot
                  data={[{
                    x: metricValues.map((item) => (item.value ?? 0) * 100),
                    y: metricValues.map((item) => item.label),
                    type: "bar",
                    orientation: "h",
                    marker: { color: metricValues.map((item) => item.color), line: { color: "#fff", width: 1 } },
                    text: metricValues.map((item) => `${((item.value ?? 0) * 100).toFixed(1)}%`),
                    textposition: "outside",
                    cliponaxis: false,
                    hovertemplate: "%{y}: %{x:.1f}%<extra></extra>",
                  }]}
                  layout={{
                    autosize: true, height: 245, margin: { l: 135, r: 45, t: 10, b: 35 },
                    paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                    font: { family: "DM Sans, sans-serif", size: 10, color: "#68798f" },
                    xaxis: { range: [0, 110], dtick: 25, ticksuffix: "%", gridcolor: "#edf1f6", zeroline: false, title: { text: "Score" } },
                    yaxis: { showgrid: false, zeroline: false, automargin: true },
                    showlegend: false,
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: "100%" }}
                />
              </Suspense>
            )}
            <div className="method-note"><ShieldCheck size={16} /><span>{result.evaluation.methodology}</span></div>
          </section>
              <section className="panel comparison-panel">
            <div className="panel-head"><div><h3>Prediction comparison</h3><p>AI classifications compared with verified reference answers</p></div><span className="mini-badge">{result.evaluation.has_reference_answers ? "REFERENCE COMPARISON" : "NO REFERENCES"}</span></div>
            {result.evaluation.comparison.length ? (
              <Suspense fallback={<ChartLoading />}>
                <Plot
                  data={[{
                    x: result.evaluation.comparison.map((item) => `${item.reference.replaceAll("_", " ")} → ${item.prediction.replaceAll("_", " ")}`),
                    y: result.evaluation.comparison.map((item) => item.count),
                    type: "bar",
                    marker: { color: result.evaluation.comparison.map((item) => item.reference === item.prediction ? "#53ab84" : "#f0ac50"), line: { color: "#fff", width: 1 } },
                    hovertemplate: "%{x}<br>Records: %{y}<extra></extra>",
                  }]}
                  layout={{
                    autosize: true, height: 245, margin: { l: 38, r: 12, t: 12, b: 55 },
                    paper_bgcolor: "transparent", plot_bgcolor: "transparent",
                    font: { family: "Inter, sans-serif", size: 10, color: "#8794a8" },
                    xaxis: { showgrid: false, zeroline: false, tickangle: -20 },
                    yaxis: { dtick: 1, gridcolor: "#edf1f6", zeroline: false, title: { text: "Records" } },
                    showlegend: false,
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: "100%" }}
                />
              </Suspense>
            ) : <div className="comparison-empty"><ShieldCheck size={18} /><span>Select an AI output and reference answer column above to show the prediction comparison chart.</span></div>}
          </section>
          <section className="panel issues-panel">
            <div className="panel-head"><div><h3>Findings &amp; review flags</h3><p>Data quality and clinical review are reported separately</p></div><span className="issue-total">{issues.length} finding{issues.length === 1 ? "" : "s"}</span></div>
            {issues.length ? <div className="findings-list">{issues.map((issue, index) => <FindingRow key={`${issue.code}-${index}`} issue={issue} />)}</div> : <div className="no-issues"><span><Check size={19} /></span><div><strong>No issues detected</strong><p>All evaluated checks passed for the supplied data.</p></div></div>}
          </section>
          <div className="results-columns">
            <section className="panel schema-panel">
              <div className="panel-head"><div><h3>Column profile</h3><p>Inferred fields and data types</p></div></div>
              <div className="table-scroll"><table className="data-table"><thead><tr><th>Column</th><th>Type</th><th>Missing</th></tr></thead><tbody>{result.columns.map((column) => <tr key={column.name}><td><span className="column-name">{column.name}</span>{column.identifier_redacted && <span className="redacted-tag">REDACTED</span>}</td><td><span className="type-pill">{column.inferred_type}</span></td><td className={column.missing_count ? "count-warning" : ""}>{column.missing_count}</td></tr>)}</tbody></table></div>
            </section>
            <section className="panel preview-panel">
              <div className="panel-head"><div><h3>Record preview</h3><p>First {result.preview.length} rows · identifier values hidden</p></div><span className="lock-tag"><ShieldCheck size={13} /> REDACTED</span></div>
              <div className="table-scroll"><table className="data-table preview-table"><thead><tr>{result.columns.slice(0, 5).map((column) => <th key={column.name}>{column.name}</th>)}</tr></thead><tbody>{result.preview.map((row, index) => <tr key={index}>{result.columns.slice(0, 5).map((column) => <td key={column.name} title={String(row[column.name] ?? "—")}>{String(row[column.name] ?? "—")}</td>)}</tr>)}</tbody></table></div>
            </section>
          </div>
          <section className="panel findings-records">
            <div className="panel-head"><div><h3>Record-level evaluation</h3><p>Rule-based interpretations using only supplied reference bounds</p></div><span className="mini-badge">{result.evaluation.evaluated_record_count} RECORDS</span></div>
            <div className="table-scroll"><table className="data-table"><thead><tr><th>Record</th><th>AI output</th><th>Reference</th><th>Evidence-based explanation</th><th>Reference check &amp; safety</th></tr></thead><tbody>{result.evaluation.record_findings.slice(0, 100).map((finding) => <tr key={finding.record_number}><td className="record-id">#{finding.record_number}</td><td><span className={`label-pill ${finding.prediction}`}>{finding.prediction.replaceAll("_", " ")}</span></td><td>{finding.reference?.replaceAll("_", " ") ?? "—"}</td><td className="explanation-cell">{finding.explanation}</td><td className="status-cell"><span className={`status-pill ${finding.verified === true ? "status-safe" : finding.verified === false ? "status-risk" : "status-neutral"}`}>{finding.verified === true ? <><Check size={12} /> Verified</> : finding.verified === false ? <><X size={12} /> Not verified</> : <><CircleHelp size={12} /> Unscored</>}</span>{finding.unsupported_claim && <span className="status-pill status-risk">Unsupported claim</span>}{finding.human_review_required && <span className="status-pill status-review">Human review</span>}</td></tr>)}</tbody></table></div>
            {result.evaluation.record_findings.length > 100 && <div className="table-foot">Showing first 100 of {result.evaluation.record_findings.length.toLocaleString()} records.</div>}
          </section>
          <div className="privacy-footnote"><ShieldCheck size={15} /><span>{result.privacy.stored_fields} Raw rows remain transient and are not retained after processing.</span></div>
        </div>
      )}
    </>
  );
}

function HistoryPage({
  history, search, onSearch, onEvaluate, onExport,
}: {
  history: DashboardData["recent_evaluations"]; search: string; onSearch: (value: string) => void;
  onEvaluate: () => void; onExport: (id: string, format: "csv" | "pdf" | "docx") => Promise<void>;
}) {
  return (
    <>
      <div className="page-heading heading-row">
        <div><p className="eyebrow">YOUR WORKSPACE</p><h1>Evaluation history</h1><p className="page-subtitle">Review aggregate results and download privacy-conscious reports.</p></div>
        <button className="button button-primary" onClick={onEvaluate}><Plus size={17} /> New evaluation</button>
      </div>
      <section className="panel history-panel">
        <div className="history-toolbar"><div><h3>All evaluations <span className="count-chip">{history.length}</span></h3><p>Raw datasets are not stored; only aggregate summary data is retained.</p></div><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search by filename…" /></label></div>
        {history.length ? <EvaluationTable items={history} onExport={onExport} /> : <div className="table-empty"><div className="empty-icon"><FileText size={22} /></div><strong>{search ? "No matching evaluations" : "Your history is empty"}</strong><span>{search ? "Try a different filename." : "Completed dataset evaluations will appear here."}</span>{!search && <button className="button button-primary button-small" onClick={onEvaluate}><Plus size={15} /> Start an evaluation</button>}</div>}
      </section>
    </>
  );
}

function StatCard({ label, value, detail, icon, tone }: {
  label: string; value: string; detail: string; icon: React.ReactNode; tone: string;
}) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}>{icon}</div><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong><span className="stat-detail">{detail}</span></div>;
}

function Metric({ label, value }: { label: string; value: number | null }) {
  const percentage = value === null ? null : value * 100;
  return <div className="metric-item"><div className="metric-label">{label}<span>{value === null ? "—" : `${percentage!.toFixed(1)}%`}</span></div><div className="metric-track"><i style={{ width: `${percentage ?? 0}%` }} className={label === "Hallucination rate" ? "metric-danger" : ""} /></div></div>;
}

function ColumnMappingPanel({
  result, disabled, onApply,
}: {
  result: EvaluationResult;
  disabled: boolean;
  onApply: (mapping: { ai_label_column: string; reference_answer_column: string }) => void;
}) {
  const [aiColumn, setAiColumn] = useState(result.evaluation.column_mapping.ai_label ?? "");
  const [referenceColumn, setReferenceColumn] = useState(result.evaluation.column_mapping.reference_answer ?? "");
  const ready = Boolean(aiColumn && referenceColumn);
  return (
    <section className={`panel mapping-panel ${ready ? "mapping-detected" : "mapping-needed"}`}>
      <div className="mapping-copy">
        <span className="mapping-icon">{ready ? <Check size={16} /> : <CircleHelp size={16} />}</span>
        <div>
          <strong>{ready ? "AI and reference columns matched" : "Choose columns for AI evaluation"}</strong>
          <p>{ready
            ? "Confirm these fields are the model output and its verified reference. Change them if the chart results look unexpected."
            : "We could not identify both fields automatically. Choose the CSV columns containing the AI output and its verified reference answer."}</p>
        </div>
      </div>
      <div className="mapping-controls">
        <label>
          <span>AI output / prediction</span>
          <select value={aiColumn} onChange={(event) => setAiColumn(event.target.value)} disabled={disabled}>
            <option value="">Not selected</option>
            {result.columns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>)}
          </select>
        </label>
        <label>
          <span>Verified reference answer</span>
          <select value={referenceColumn} onChange={(event) => setReferenceColumn(event.target.value)} disabled={disabled}>
            <option value="">Not selected</option>
            {result.columns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>)}
          </select>
        </label>
        <button
          className="button button-secondary mapping-apply"
          disabled={disabled}
          onClick={() => onApply({ ai_label_column: aiColumn, reference_answer_column: referenceColumn })}
        >
          {disabled ? <LoaderCircle size={15} className="spin" /> : <Activity size={15} />}
          {disabled ? "Re-evaluating…" : "Update evaluation"}
        </button>
      </div>
    </section>
  );
}

function FindingRow({ issue }: { issue: Finding }) {
  const tone = issue.severity === "high" ? "high" : issue.severity === "review" ? "review" : "medium";
  return <div className={`finding-row ${issue.category === "clinical_review" ? "clinical-finding" : ""}`}><div className={`finding-marker ${tone}`}>{issue.category === "clinical_review" ? <HeartPulse size={15} /> : <AlertTriangle size={15} />}</div><div className="finding-main"><div className="finding-head"><strong>{issue.message}</strong><span className={`severity-chip ${tone}`}>{issue.category === "clinical_review" ? "HUMAN REVIEW" : issue.severity.toUpperCase()}</span></div><span className="finding-category">{issue.category.replaceAll("_", " ")}</span></div></div>;
}

function EvaluationTable({ items, onExport }: {
  items: DashboardData["recent_evaluations"];
  onExport: (id: string, format: "csv" | "pdf" | "docx") => Promise<void>;
}) {
  return <div className="table-scroll"><table className="data-table evaluation-table"><thead><tr><th>Dataset</th><th>Date</th><th>Records</th><th>Data flags</th><th>AI score</th><th>AI safety</th><th>Export</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><div className="dataset-cell"><span className="dataset-icon"><FileSpreadsheet size={16} /></span><strong title={item.filename}>{item.filename}</strong></div></td><td>{formatDate(item.created_at)}</td><td>{item.record_count.toLocaleString()}</td><td><span className={item.issue_count ? "data-warning" : "data-ok"}>{item.issue_count || <Check size={13} />}{item.issue_count ? " flags" : " clean"}</span></td><td><strong className="score-value">{item.score === null ? "—" : item.score.toFixed(1)}</strong>{item.score !== null && <span className="score-max"> / 100</span>}</td><td>{item.unsupported_count ? <span className="status-pill status-risk">{item.unsupported_count} flagged</span> : <span className="status-pill status-safe"><Check size={12} /> Clear</span>}</td><td><ReportButtons id={item.id} onExport={onExport} /></td></tr>)}</tbody></table></div>;
}

function ReportButtons({ id, onExport }: {
  id: string; onExport: (id: string, format: "csv" | "pdf" | "docx") => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const formats: Array<{ format: "pdf" | "docx" | "csv"; label: string }> = [
    { format: "pdf", label: "Download PDF" }, { format: "docx", label: "Download Word" }, { format: "csv", label: "Export CSV" },
  ];
  return <div className="report-menu-wrap"><button className="icon-button report-trigger" title="Download report" onClick={() => setOpen(!open)}><ArrowDownToLine size={15} /></button>{open && <><button className="menu-dismiss" aria-label="Close export menu" onClick={() => setOpen(false)} /><div className="report-menu">{formats.map((item) => <button key={item.format} onClick={() => { setOpen(false); void onExport(id, item.format); }}><FileText size={14} />{item.label}</button>)}</div></>}</div>;
}

function NavButton({ active, onClick, icon, label }: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return <button className={`nav-link ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span>{active && <i className="nav-active-mark" />}</button>;
}

function ChartEmpty({ onClick }: { onClick: () => void }) {
  return <div className="chart-empty"><div className="chart-empty-icon"><BarChart3 size={20} /></div><strong>Charts will appear here</strong><span>Run an evaluation to visualize your data.</span><button onClick={onClick}>Try demo data <ArrowRight size={13} /></button></div>;
}

function ChartLoading() {
  return <div className="chart-loading"><LoaderCircle size={18} className="spin" /> Loading interactive chart…</div>;
}

function pageTitle(page: Page) {
  return page === "overview" ? "Overview" : page === "evaluate" ? "Evaluate dataset" : "Evaluation history";
}

function formatNumber(value: number) {
  return value.toLocaleString();
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
