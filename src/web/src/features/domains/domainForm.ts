export interface DraftDomainOption {
  domain: string;
  label: string;
}

export function normalizeDomainLabel(input: string): string {
  return input.trim().replace(/\s+/g, " ");
}

export function slugifyDomainLabel(input: string): string {
  const label = normalizeDomainLabel(input);
  return label
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
}

export function buildDraftDomainOption(input: string): DraftDomainOption | null {
  const label = normalizeDomainLabel(input);
  if (!label) {
    return null;
  }

  return {
    domain: slugifyDomainLabel(label) || "ai_agent",
    label,
  };
}
