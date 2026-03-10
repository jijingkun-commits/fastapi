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

const FRIENDLY_FIELD_LABELS: Record<string, string> = {
  org_name: "机构名称",
  org_no: "机构代码",
  org_code: "机构代码",
  dept_name: "部门名称",
  dept_code: "部门代码",
  branch_name: "机构名称",
  branch_code: "机构代码",
  cust_name: "客户名称",
  cust_no: "客户编号",
  customer_name: "客户名称",
  customer_no: "客户编号",
};

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

function isTechnicalFieldLabel(label: string | undefined, key: string): boolean {
  const normalized = String(label || "").trim();
  if (!normalized) {
    return true;
  }
  if (normalized === key) {
    return true;
  }
  return /^[a-z0-9_]+$/i.test(normalized);
}

function resolveFriendlyAxisLabel(
  label: string | undefined,
  key: string,
  role: "dimension" | "measure",
): string {
  if (!isTechnicalFieldLabel(label, key)) {
    return String(label).trim();
  }

  const normalizedKey = String(key || "").trim().toLowerCase();
  const mapped = FRIENDLY_FIELD_LABELS[normalizedKey];
  if (mapped) {
    return mapped;
  }

  if (role === "measure") {
    return "指标值";
  }

  if (normalizedKey.includes("date") || normalizedKey.endsWith("_dt") || normalizedKey.includes("time")) {
    return "时间";
  }
  if (normalizedKey.endsWith("_name")) {
    return "名称";
  }
  if (normalizedKey.endsWith("_no") || normalizedKey.endsWith("_code")) {
    return "编码";
  }
  return "维度";
}

function buildBarMarkSize(count: number): number | undefined {
  if (count <= 2) return 120;
  if (count <= 4) return 72;
  if (count <= 8) return 44;
  return undefined;
}

function getRenderableChartValues(
  chart: SqlResultChartData,
): Array<Record<string, string | number>> | null {
  if (chart.data.length <= 1) {
    return null;
  }

  const values = normalizeChartValues(chart);
  return values.length > 1 ? values : null;
}

function buildVegaSpec(
  chart: SqlResultChartData,
  values: Array<Record<string, string | number>>,
  xLabel: string,
  yLabel: string,
): TopLevelSpec {
  const xType = inferXType(chart);
  const seriesName = chart.series_name || yLabel;
  const showValueLabels = chart.type === "bar" && values.length <= 12;

  const baseSpec = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.json",
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
        labelAngle: values.length <= 4 ? 0 : -32,
        labelAlign: values.length <= 4 ? "center" as const : "right" as const,
        labelBaseline: values.length <= 4 ? "top" as const : "middle" as const,
        labelPadding: 8,
        labelLimit: values.length <= 4 ? 180 : 140,
        labelOverlap: "greedy" as const,
        titlePadding: 14,
        labelExpr:
          "length(toString(datum.label)) > 10 ? slice(toString(datum.label), 0, 10) + '…' : toString(datum.label)",
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

  const barLayer = {
    mark: {
      type: "bar" as const,
      cornerRadiusTopLeft: 4,
      cornerRadiusTopRight: 4,
      size: buildBarMarkSize(values.length),
    },
    encoding: commonEncoding,
  };

  if (!showValueLabels) {
    return {
      ...baseSpec,
      ...barLayer,
    } as TopLevelSpec;
  }

  return {
    ...baseSpec,
    layer: [
      barLayer,
      {
        mark: {
          type: "text" as const,
          align: "center",
          baseline: "bottom",
          dy: -6,
          fontSize: 11,
          color: "#4b5563",
        },
        encoding: {
          x: commonEncoding.x,
          y: commonEncoding.y,
          text: { field: "__formatted_y", type: "nominal" },
        },
      },
    ],
  } as TopLevelSpec;
}

export function SqlResultChart({ chart }: SqlResultChartProps) {
  const [renderError, setRenderError] = useState<string | null>(null);
  const chartViewRef = useRef<VegaChartView | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const containerWidthRef = useRef(0);
  const renderModel = useMemo(() => {
    const values = getRenderableChartValues(chart);
    if (!values) {
      return null;
    }

    const xLabel = resolveFriendlyAxisLabel(chart.x_label, chart.x_key, "dimension");
    const yLabel = resolveFriendlyAxisLabel(chart.y_label, chart.y_key, "measure");

    return {
      spec: buildVegaSpec(chart, values, xLabel, yLabel),
      xLabel,
      yLabel,
    };
  }, [chart]);

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
    if (!container || !renderModel || typeof ResizeObserver === "undefined") {
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
  }, [refreshChartLayout, renderModel]);

  if (!renderModel) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="rounded-lg border border-gray-200 bg-white p-3"
      data-testid="sql-result-chart"
    >
      <VegaLiteChart
        className="w-full"
        spec={renderModel.spec}
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
        <span>X 轴：{renderModel.xLabel}</span>
        <span>Y 轴：{renderModel.yLabel}</span>
      </div>
    </div>
  );
}
