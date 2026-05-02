import type { ReportPayload } from "./reportView";

function sanitizeSegment(value: string): string {
  const normalized = value.trim().replaceAll(/\s+/g, "-").replaceAll(/[^a-zA-Z0-9_-]/g, "_");
  return normalized.length > 0 ? normalized : "report";
}

function timestampSegment(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unknown-time";
  }
  return date.toISOString().replaceAll(":", "-").replaceAll(".", "-");
}

export function buildReportExportFilename(data: ReportPayload): string {
  const domain = sanitizeSegment(data.domain);
  const userId = sanitizeSegment(data.user_id);
  const generatedAt = timestampSegment(data.generated_at);
  return `learning-report-${domain}-${userId}-${generatedAt}.json`;
}

export function serializeReportExport(data: ReportPayload): string {
  return `${JSON.stringify(data, null, 2)}\n`;
}
