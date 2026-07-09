import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { ReasonCode } from "../../lib/types";

/**
 * A true SHAP force-plot style visual (D3): features push the score left (increase risk, red) or
 * right (reduce risk, blue) from the model base value. Magnitude = |SHAP| in log-odds.
 */
export default function ShapForcePlot({ reasons }: { reasons: ReasonCode[] }) {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    if (!reasons.length) return;

    const width = ref.current?.clientWidth || 640;
    const height = 120;
    const margin = { left: 8, right: 8, top: 28, bottom: 28 };
    const innerW = width - margin.left - margin.right;

    // order: reduces_risk (blue, left segment) then increases_risk (red)
    const sorted = [...reasons].sort((a, b) => a.shap - b.shap);
    const total = d3.sum(sorted, (d) => Math.abs(d.shap)) || 1;
    const x = d3.scaleLinear().domain([0, total]).range([0, innerW]);

    const g = svg.attr("width", "100%").attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    let cursor = 0;
    const bandH = 26;
    sorted.forEach((d) => {
      const w = x(Math.abs(d.shap));
      const color = d.impact === "negative" ? "#dc2626" : "#2563eb";
      g.append("rect")
        .attr("x", cursor).attr("y", 0).attr("width", Math.max(w - 1, 0)).attr("height", bandH)
        .attr("fill", color).attr("opacity", 0.85);
      if (w > 46) {
        g.append("text")
          .attr("x", cursor + w / 2).attr("y", bandH / 2 + 4)
          .attr("text-anchor", "middle").attr("fill", "white").attr("font-size", 10)
          .text(d.feature.length > 16 ? d.feature.slice(0, 15) + "…" : d.feature);
      }
      cursor += w;
    });

    // axis label
    g.append("text").attr("x", 0).attr("y", -10).attr("font-size", 11).attr("fill", "#2563eb")
      .text("← reduces default risk");
    g.append("text").attr("x", innerW).attr("y", -10).attr("text-anchor", "end")
      .attr("font-size", 11).attr("fill", "#dc2626").text("increases default risk →");
    g.append("text").attr("x", 0).attr("y", bandH + 18).attr("font-size", 10).attr("fill", "#64748b")
      .text("Force plot: contribution of the top drivers to the PD (log-odds).");
  }, [reasons]);

  return <svg ref={ref} />;
}
