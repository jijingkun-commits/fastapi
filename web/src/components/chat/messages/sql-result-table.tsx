/**
 * SQL 查询结果表格组件
 *
 * 渲染问数助手返回的 SQL 查询结果，支持：
 * - 数据表格展示（带表头和斑马纹）
 * - SQL 语句折叠展示
 * - 大数字格式化（亿/万单位）
 * - 空结果提示
 */
import { ChevronDown, ChevronUp, Database } from "lucide-react";
import { useMemo, useState } from "react";

import { CodeBlock } from "@/components/chat/code-block";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface SqlResultTableProps {
  columns: string[];
  columnDisplayNames?: string[];
  rows: Record<string, any>[];
  totalRows?: number;
  sql?: string;
  permissionScopeApplied?: boolean;
  permissionScopeText?: string;
}

/** 格式化数值：大数字转亿/万 */
function formatValue(value: any): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") {
    const abs = Math.abs(value);
    if (abs >= 1_0000_0000)
      return `${(value / 1_0000_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 亿`;
    if (abs >= 1_0000)
      return `${(value / 1_0000).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 万`;
    if (Number.isInteger(value)) return value.toLocaleString("zh-CN");
    return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }
  return String(value);
}

function isNumericColumn(rows: Record<string, any>[], column: string): boolean {
  const values = rows
    .map((row) => row[column])
    .filter((value) => value !== null && value !== undefined && value !== "");

  return (
    values.length > 0 && values.every((value) => typeof value === "number")
  );
}

export function SqlResultTable({
  columns,
  columnDisplayNames,
  rows,
  totalRows,
  sql,
  permissionScopeApplied,
  permissionScopeText,
}: SqlResultTableProps) {
  const [showSql, setShowSql] = useState(false);
  const normalizedScopeText = (permissionScopeText || "").trim();
  const resolvedScopeHint =
    normalizedScopeText.length > 0
      ? normalizedScopeText
      : "结果已按当前账号的数据权限范围（机构/部门）过滤";
  const numericColumns = useMemo(
    () => new Set(columns.filter((column) => isNumericColumn(rows, column))),
    [columns, rows],
  );

  if (!rows || rows.length === 0) {
    return (
      <div className="border-border/60 bg-muted/30 text-muted-foreground rounded-xl border p-4 text-sm">
        查询完成，但没有找到符合条件的数据。
      </div>
    );
  }

  return (
    <div className="border-border/60 bg-card text-card-foreground w-full max-w-full min-w-0 overflow-hidden rounded-xl border shadow-sm">
      {permissionScopeApplied && (
        <div className="border-b border-amber-200/70 bg-amber-50/80 px-4 py-2 text-xs text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/20 dark:text-amber-200">
          注：{resolvedScopeHint}。
        </div>
      )}

      <div className="min-w-0">
        <Table className="w-full min-w-full table-fixed">
          <TableHeader>
            <TableRow className="border-border/60 bg-muted/35 hover:bg-muted/35">
              {columns.map((col, idx) => {
                const isNumeric = numericColumns.has(col);
                return (
                  <TableHead
                    key={col}
                    className={cn(
                      "text-foreground/80 h-auto px-4 py-3 text-xs font-semibold tracking-[0.01em]",
                      isNumeric ? "text-right" : "text-left",
                    )}
                  >
                    {columnDisplayNames?.[idx] ?? col}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, rowIndex) => (
              <TableRow
                key={rowIndex}
                className={cn(
                  "border-border/50 hover:bg-muted/20 align-top",
                  rowIndex % 2 === 1 && "bg-muted/[0.22]",
                )}
              >
                {columns.map((col, columnIndex) => {
                  const isNumeric = numericColumns.has(col);
                  return (
                    <TableCell
                      key={col}
                      className={cn(
                        "text-foreground/90 px-4 py-3 text-sm",
                        isNumeric
                          ? "text-right whitespace-nowrap tabular-nums"
                          : columnIndex === 0
                            ? "font-medium whitespace-nowrap tabular-nums"
                            : "leading-6 break-words whitespace-normal",
                      )}
                    >
                      {formatValue(row[col])}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="border-border/60 bg-muted/25 text-muted-foreground flex items-center justify-between border-t px-4 py-2 text-xs">
        <span>
          共 {(totalRows ?? rows.length).toLocaleString()} 条
          {totalRows != null && rows.length < totalRows
            ? `（已展示前 ${rows.length} 条）`
            : ""}
        </span>
        {sql && (
          <button
            onClick={() => setShowSql(!showSql)}
            className="hover:bg-muted hover:text-foreground inline-flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors"
            type="button"
          >
            <Database className="size-3.5" />
            SQL
            {showSql ? (
              <ChevronUp className="size-3.5" />
            ) : (
              <ChevronDown className="size-3.5" />
            )}
          </button>
        )}
      </div>

      {showSql && sql && (
        <div className="border-border/60 min-w-0 border-t px-4 py-3">
          <CodeBlock
            language="sql"
            label="SQL"
            code={sql}
            wrapLongLines
          />
        </div>
      )}
    </div>
  );
}
