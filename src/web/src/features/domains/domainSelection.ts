export interface DomainOption {
  domain: string;
  label: string;
}

export interface DomainSelectState {
  options: DomainOption[];
  selectedDomain: string;
  hasExistingDomains: boolean;
}

const EMPTY_DOMAIN_OPTION: DomainOption = {
  domain: "",
  label: "没有领域",
};

export function buildDomainSelectState(
  existingOptions: DomainOption[],
  currentDomain: string,
  draftOption: DomainOption | null,
): DomainSelectState {
  const realOptions = existingOptions.filter((item) => item.domain.trim().length > 0);
  const hasExistingDomains = realOptions.length > 0;
  const options = draftOption ? upsertOption(realOptions, draftOption) : realOptions;

  if (options.length === 0) {
    return {
      options: [EMPTY_DOMAIN_OPTION],
      selectedDomain: "",
      hasExistingDomains,
    };
  }

  const selectedDomain = options.some((item) => item.domain === currentDomain)
    ? currentDomain
    : draftOption?.domain ?? options[0]?.domain ?? "";

  return {
    options,
    selectedDomain,
    hasExistingDomains,
  };
}

function upsertOption(options: DomainOption[], option: DomainOption): DomainOption[] {
  const existingIndex = options.findIndex((item) => item.domain === option.domain);
  if (existingIndex === -1) {
    return [...options, option];
  }
  return options.map((item, index) => (index === existingIndex ? option : item));
}
