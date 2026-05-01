import { describe, expect, it } from "vitest";

import { buildDraftDomainOption, normalizeDomainLabel, slugifyDomainLabel } from "./domainForm";

describe("domain form helpers", () => {
  it("normalizes domain labels without losing readable spacing", () => {
    expect(normalizeDomainLabel("  AI   Agent  ")).toBe("AI Agent");
  });

  it("builds ascii-friendly keys for latin labels", () => {
    expect(slugifyDomainLabel("System Design 101")).toBe("system_design_101");
  });

  it("keeps chinese labels valid when generating a domain key", () => {
    expect(slugifyDomainLabel("机器 学习")).toBe("机器_学习");
  });

  it("returns both the stored key and the visible label for new domains", () => {
    expect(buildDraftDomainOption("Python 基础")).toEqual({
      domain: "python_基础",
      label: "Python 基础",
    });
  });

  it("ignores empty drafts", () => {
    expect(buildDraftDomainOption("   ")).toBeNull();
  });
});
