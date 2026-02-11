/**
 * SQL 查询结果表格组件
 * 
 * 渲染问数助手返回的 SQL 查询结果，支持：
 * - 数据表格展示（带表头和斑马纹）
 * - SQL 语句折叠展示
 * - 大数字格式化（亿/万单位）
 * - 空结果提示
 */
import { useState } from "react";
import { ChevronDown, ChevronUp, Database } from "lucide-react";

interface SqlResultTableProps {
  columns: string[];
  columnDisplayNames?: string[];
  rows: Record<string, any>[];
  totalRows: number;
  sql?: string;
}

/** 格式化数值：大数字转亿/万 */
function formatValue(value: any): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") {
    const abs = Math.abs(value);
    if (abs >= 1_0000_0000) return `${(value / 1_0000_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 亿`;
    if (abs >= 1_0000) return `${(value / 1_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 万`;
    if (Number.isInteger(value)) return value.toLocaleString("zh-CN");
    return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function SqlResultTable({ columns, columnDisplayNames, rows, totalRows, sql }: SqlResultTableProps) {
  const [showSql, setShowSql] = useState(false);

  if (!rows || rows.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
        查询完成，但没有找到符合条件的数据。
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden">
      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {columns.map((col, idx) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left font-medium text-gray-700 whitespace-nowrap"
                >
                  {columnDisplayNames?.[idx] ?? col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}
              >
                {columns.map((col) => (
                  <td
                    key={col}
                    className="px-3 py-2 text-gray-800 whitespace-nowrap"
                  >
                    {formatValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 底栏：行数 + SQL 折叠 */}
      <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-500">
        <span>
          共 {totalRows.toLocaleString()} 条
          {rows.length < totalRows ? `（已展示前 ${rows.length} 条）` : ""}
        </span>
        {sql && (
          <button
            onClick={() => setShowSql(!showSql)}
            className="flex items-center gap-1 hover:text-gray-700 transition-colors"
          >
            <Database className="h-3 w-3" />
            SQL
            {showSql ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
      </div>

      {/* SQL 展开区 */}
      {showSql && sql && (
        <div className="border-t border-gray-200 bg-gray-900 p-3">
          <pre className="text-xs text-green-400 whitespace-pre-wrap break-all font-mono">
            {sql}
          </pre>
        </div>
      )}
    </div>
  );
}
