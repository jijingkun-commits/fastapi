/**
 * SQL 查询结果图表组件（Vega-Lite）
 *
 * 渲染问数助手 `sql_result.data.chart` 结构，支持：
 * - 柱状图 (bar)
 * - 折线图 (line)
 * - 饼图 (pie)
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import type { ComponentType } from "react";
import dynamic from "next/dynamic";
import type { TopLevelSpec } from "vega-lite";
import type { SqlResultChartData } from "@/types/message";

interface SqlResultChartProps {
  chart: SqlResultChartData;
}

interface VegaLiteProps {
  spec: TopLevelSpec;
  options?: {
    actions?: boolean;
    renderer?: "svg" | "canvas";
  };
  onError?: (error: unknown) => void;
}

const VegaLiteChart = dynamic(
  () => import("react-vega").then((mod) => mod.VegaEmbed),
  { ssr: false },
) as ComponentType<VegaLiteProps>;

/** 格式化数值：大数字转亿/万 */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") {
    const abs = Math.abs(value);
    if (abs >= 1_0000_0000) {
      return `${(value / 1_0000_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 亿`;
    }
    if (abs >= 1_0000) {
      return `${(value / 1_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 万`;
    }
    if (Number.isInteger(value)) {
      return value.toLocaleString("zh-CN");
    }
    return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }
  return String(value);
}

function isDateLike(value: unknown): boolean {
  if (typeof value !== "string") return false;
  const text = value.trim();
  if (!text) return false;
  return /^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.test(text) || /^\d{8}$/.test(text);
}

function inferXType(chart: SqlResultChartData): "temporal" | "nominal" {
  const samples = chart.data.slice(0, 10).map((item) => item[chart.x_key]);
  if (samples.length === 0) return "nominal";
  const dateLikeCount = samples.filter((value) => isDateLike(value)).length;
  return dateLikeCount >= Math.ceil(samples.length * 0.6) ? "temporal" : "nominal";
}

function buildVegaSpec(chart: SqlResultChartData): TopLevelSpec {
  const xType = inferXType(chart);
  const xLabel = chart.x_label || chart.x_key;
  const yLabel = chart.y_label || chart.y_key;
  const seriesName = chart.series_name || yLabel;

  const values = chart.data.map((item) => {
    const nextItem: Record<string, string | number> = { ...item };
    const rawY = item[chart.y_key];
    nextItem.__formatted_y = formatValue(rawY);
    return nextItem;
  });

  const baseSpec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    title: chart.title,
    width: "container",
    height: 300,
    data: { values },
    config: {
      axis: {
        labelFontSize: 12,
        titleFontSize: 12,
      },
      legend: {
        labelFontSize: 12,
        titleFontSize: 12,
      },
      view: {
        stroke: "#e5e7eb",
      },
    },
  } as TopLevelSpec;

  const yAxisLabelExpr = "abs(datum.value) >= 100000000 ? format(datum.value/100000000, ',.2f') + ' 亿' : abs(datum.value) >= 10000 ? format(datum.value/10000, ',.2f') + ' 万' : format(datum.value, ',.2f')";

  if (chart.type === "pie") {
    return {
      ...baseSpec,
      mark: { type: "arc", innerRadius: 50 },
      encoding: {
        theta: { field: chart.y_key, type: "quantitative", title: yLabel },
        color: { field: chart.x_key, type: "nominal", title: xLabel },
        tooltip: [
          { field: chart.x_key, type: "nominal", title: xLabel },
          { field: "__formatted_y", type: "nominal", title: seriesName },
        ],
      },
    };
  }

  const commonEncoding = {
    x: { field: chart.x_key, type: xType, title: xLabel },
    y: {
      field: chart.y_key,
      type: "quantitative" as const,
      title: yLabel,
      axis: { labelExpr: yAxisLabelExpr },
    },
    tooltip: [
      { field: chart.x_key, type: xType, title: xLabel },
      { field: "__formatted_y", type: "nominal" as const, title: seriesName },
    ],
  };

  if (chart.type === "line") {
    return {
      ...baseSpec,
      mark: { type: "line", point: true },
      encoding: commonEncoding,
    };
  }

  return {
    ...baseSpec,
    mark: { type: "bar", cornerRadiusTopLeft: 4, cornerRadiusTopRight: 4 },
    encoding: commonEncoding,
  };
}

export function SqlResultChart({ chart }: SqlResultChartProps) {
  const [renderError, setRenderError] = useState<string | null>(null);
  const spec = useMemo(() => buildVegaSpec(chart), [chart]);

  useEffect(() => {
    setRenderError(null);
  }, [chart]);

  if (!chart || !Array.isArray(chart.data) || chart.data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3" data-testid="sql-result-chart">
      <VegaLiteChart
        spec={spec}
        options={{ actions: false, renderer: "svg" }}
        onError={(error) => {
          console.error("[SqlResultChart] 图表渲染失败", error);
          setRenderError("图表渲染失败，请查看下方表格数据。");
        }}
      />
      {renderError && (
        <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {renderError}
        </div>
      )}
      <div className="mt-1 flex items-center gap-4 text-xs text-gray-500">
        <span>X 轴：{chart.x_label || chart.x_key}</span>
        <span>Y 轴：{chart.y_label || chart.y_key}</span>
      </div>
    </div>
  );
}
