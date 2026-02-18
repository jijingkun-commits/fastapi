/**
 * SQL 查询结果图表组件（Vega-Lite）
 *
 * 渲染问数助手 `sql_result.data.chart` 结构，支持：
 * - 柱状图 (bar)
 * - 折线图 (line)
 * - 饼图 (pie)
 */
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import dynamic from "next/dynamic";
import type { TopLevelSpec } from "vega-lite";
import type { SqlResultChartData } from "@/types/message";

interface SqlResultChartProps {
  chart: SqlResultChartData;
}

interface VegaChartView {
  resize: () => void;
  runAsync: () => Promise<unknown>;
}

interface VegaLiteProps {
  spec: TopLevelSpec;
  options?: {
    actions?: boolean;
    renderer?: "svg" | "canvas";
  };
  onEmbed?: (result: { view: VegaChartView }) => void;
  onError?: (error: unknown) => void;
  className?: string;
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

function normalizeDimensionValue(value: unknown): string {
  if (value === null || value === undefined) return "未知";
  const text = String(value).trim();
  return text || "未知";
}

function coerceChartNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (value === null || value === undefined) {
    return null;
  }

  const text = String(value).trim().replace(/,/g, "");
  if (!text) {
    return null;
  }

  const unitMatch = text.match(/^(-?\d+(?:\.\d+)?)(亿|万)?$/);
  if (unitMatch) {
    const base = Number(unitMatch[1]);
    if (!Number.isFinite(base)) {
      return null;
    }
    const unit = unitMatch[2];
    if (unit === "亿") {
      return base * 1_0000_0000;
    }
    if (unit === "万") {
      return base * 1_0000;
    }
    return base;
  }

  const numeric = Number(text);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeChartValues(chart: SqlResultChartData): Array<Record<string, string | number>> {
  const values: Array<Record<string, string | number>> = [];

  for (const item of chart.data) {
    const yValue = coerceChartNumber(item[chart.y_key]);
    if (yValue === null) {
      continue;
    }

    const nextItem = { ...item } as Record<string, string | number>;
    nextItem[chart.x_key] = normalizeDimensionValue(item[chart.x_key]);
    nextItem[chart.y_key] = yValue;
    nextItem.__formatted_y = formatValue(item[chart.y_key]);
    values.push(nextItem);
  }

  return values;
}

function isDateLike(value: unknown): boolean {
  if (typeof value !== "string") return false;
  const text = value.trim();
  if (!text) return false;
  return /^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.test(text) || /^\d{8}$/.test(text);
}

function inferXTypeByFieldMeta(chart: SqlResultChartData): "temporal" | "nominal" | null {
  const semanticType = chart.field_meta?.[chart.x_key]?.semantic_type;
  if (semanticType === "temporal") {
    return "temporal";
  }
  if (semanticType === "numeric" || semanticType === "categorical") {
    return "nominal";
  }
  return null;
}

function inferXType(chart: SqlResultChartData): "temporal" | "nominal" {
  const semanticType = inferXTypeByFieldMeta(chart);
  if (semanticType) {
    return semanticType;
  }

  const samples = chart.data.slice(0, 10).map((item) => item[chart.x_key]);
  if (samples.length === 0) return "nominal";
  const dateLikeCount = samples.filter((value) => isDateLike(value)).length;
  return dateLikeCount >= Math.ceil(samples.length * 0.6) ? "temporal" : "nominal";
}

function buildVegaSpec(
  chart: SqlResultChartData,
  values: Array<Record<string, string | number>>,
): TopLevelSpec {
  const xType = inferXType(chart);
  const xLabel = chart.x_label || chart.x_key;
  const yLabel = chart.y_label || chart.y_key;
  const seriesName = chart.series_name || yLabel;

  const baseSpec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    title: chart.title,
    width: "container",
    height: 300,
    autosize: {
      type: "fit-x",
      contains: "content",
      resize: true,
    },
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
  const xAxis = chart.type === "bar" && xType === "nominal"
    ? {
        labelAngle: -32,
        labelAlign: "right" as const,
        labelBaseline: "middle" as const,
        labelPadding: 8,
        labelLimit: 120,
        labelOverlap: "greedy" as const,
        titlePadding: 14,
        labelExpr:
          "length(toString(datum.label)) > 8 ? slice(toString(datum.label), 0, 8) + '…' : toString(datum.label)",
      }
    : undefined;

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
    x: {
      field: chart.x_key,
      type: xType,
      title: xLabel,
      ...(xAxis ? { axis: xAxis } : {}),
    },
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
  const chartViewRef = useRef<VegaChartView | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const containerWidthRef = useRef(0);
  const normalizedValues = useMemo(() => normalizeChartValues(chart), [chart]);
  const spec = useMemo(() => buildVegaSpec(chart, normalizedValues), [chart, normalizedValues]);

  const refreshChartLayout = useCallback(() => {
    requestAnimationFrame(() => {
      const view = chartViewRef.current;
      if (!view) {
        return;
      }
      view.resize();
      void view.runAsync();
    });
  }, []);

  useEffect(() => {
    setRenderError(null);
    chartViewRef.current = null;
  }, [chart]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const currentWidth = Math.floor(entry.contentRect.width);
        if (currentWidth <= 0) {
          continue;
        }

        if (Math.abs(currentWidth - containerWidthRef.current) >= 1) {
          containerWidthRef.current = currentWidth;
          refreshChartLayout();
          break;
        }
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, [refreshChartLayout, spec]);

  if (!chart || !Array.isArray(chart.data) || chart.data.length === 0) {
    return null;
  }

  if (normalizedValues.length === 0) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
        图表未渲染：未识别到可用数值列，请查看下方表格数据。
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="rounded-lg border border-gray-200 bg-white p-3"
      data-testid="sql-result-chart"
    >
      <VegaLiteChart
        className="w-full"
        spec={spec}
        options={{ actions: false, renderer: "svg" }}
        onEmbed={(result) => {
          chartViewRef.current = result.view;
          containerWidthRef.current = containerRef.current?.clientWidth ?? 0;
          refreshChartLayout();
        }}
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
