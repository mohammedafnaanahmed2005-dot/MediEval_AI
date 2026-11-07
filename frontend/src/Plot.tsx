import { useEffect, useRef, useState, type CSSProperties } from "react";
import Plotly from "plotly.js-basic-dist-min";

type PlotProps = {
  data: object[];
  layout: object;
  config?: object;
  style?: CSSProperties;
};

export default function Plot({ data, layout, config, style }: PlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const specification = JSON.stringify({ data, layout, config });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const plot = JSON.parse(specification) as {
      data: object[];
      layout: Record<string, unknown>;
      config?: Record<string, unknown>;
    };
    let cancelled = false;
    let observer: ResizeObserver | undefined;
    setFailed(false);
    void Plotly.react(
      container,
      plot.data,
      { ...plot.layout, autosize: true },
      { ...plot.config, responsive: true },
    )
      .then(() => {
        if (cancelled) return;
        observer = new ResizeObserver(() => Plotly.Plots.resize(container));
        observer.observe(container);
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
          console.error("Could not render evaluation chart.");
        }
      });

    return () => {
      cancelled = true;
      observer?.disconnect();
      Plotly.purge(container);
    };
  }, [specification]);

  if (failed) return <div className="chart-error" role="status">Chart could not be rendered. The evaluation data is still available below.</div>;
  return <div ref={containerRef} className="plot-container" style={style} />;
}
