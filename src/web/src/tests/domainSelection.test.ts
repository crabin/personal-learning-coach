import { describe, expect, it } from "vitest";

import { buildDomainSelectState } from "../features/domains/domainSelection";

describe("domain select state", () => {
  it("shows an explicit empty option when the user has no learning domains", () => {
    expect(buildDomainSelectState([], "ai_agent", null)).toEqual({
      options: [{ domain: "", label: "没有领域" }],
      selectedDomain: "",
      hasExistingDomains: false,
    });
  });

  it("keeps a draft domain selectable without treating it as an existing domain", () => {
    expect(buildDomainSelectState([], "", { domain: "python", label: "Python" })).toEqual({
      options: [{ domain: "python", label: "Python" }],
      selectedDomain: "python",
      hasExistingDomains: false,
    });
  });

  it("selects a real existing domain when one is available", () => {
    expect(
      buildDomainSelectState(
        [{ domain: "model_training", label: "模型训练" }],
        "",
        null,
      ),
    ).toEqual({
      options: [{ domain: "model_training", label: "模型训练" }],
      selectedDomain: "model_training",
      hasExistingDomains: true,
    });
  });
});
