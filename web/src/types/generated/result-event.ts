export const KNOWN_RESULT_DATA_TYPES = [
  "todo_list",
  "sql_result",
  "image",
  "table",
  "chart",
  "text",
] as const;

export type KnownResultDataType = (typeof KNOWN_RESULT_DATA_TYPES)[number];

export interface ResultEventEnvelope {
  id: string;
  source: string;
  specversion?: string;
  type?: string;
  sequence_number: number;
  timestamp: string;
  thread_id: string;
  run_id: string;
}

export interface ResultEventBase<TDataType extends string = string> {
  event?: "result";
  data_type: TDataType;
  data: Record<string, unknown>;
  message?: string;
  envelope?: ResultEventEnvelope;
  result_contract_version?: string;
}

export type KnownResultEvent = ResultEventBase<KnownResultDataType>;

export type GenericResultEvent = ResultEventBase<string>;

export type ResultEventUnion = KnownResultEvent | GenericResultEvent;
