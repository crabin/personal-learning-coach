import { beforeEach, describe, expect, it, vi } from "vitest";

const starts: string[] = [];
const destroys: string[] = [];
const colorsUsed: string[][] = [];
const hosts = new Map<string, FakeBackgroundHost>();

class FakeBackgroundHost {
  id = "";
  dataset: Record<string, string> = {};
  children: Array<{ dataset: Record<string, string> }> = [];

  append(child: { dataset: Record<string, string> }): void {
    this.children.push(child);
  }

  replaceChildren(...children: Array<{ dataset: Record<string, string> }>): void {
    this.children = children;
  }
}

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

vi.mock("color4bg", () => {
  function createMockBg(name: string) {
    return class {
      constructor(options: { dom: string; colors: string[] }) {
        const host = hosts.get(options.dom);
        const canvas = { dataset: { mockBg: name } };
        host?.append(canvas);
        starts.push(name);
        colorsUsed.push(options.colors);
      }

      start(): void {}

      destroy(): void {
        destroys.push(name);
      }
    };
  }

  return {
    AbstractShapeBg: createMockBg("abstract-shape"),
    AestheticFluidBg: createMockBg("aesthetic-fluid"),
    BlurGradientBg: createMockBg("blur-gradient"),
    WavyWavesBg: createMockBg("wavy-waves"),
  };
});

describe("project background", () => {
  beforeEach(() => {
    starts.length = 0;
    destroys.length = 0;
    colorsUsed.length = 0;
    hosts.clear();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: createMemoryStorage(),
    });
    localStorage.clear();
  });

  it("exposes the default and color4bg presets", async () => {
    const { DEFAULT_PROJECT_BACKGROUND_ID, PROJECT_BACKGROUND_PRESETS } = await import(
      "../shared/background/projectBackground"
    );

    expect(DEFAULT_PROJECT_BACKGROUND_ID).toBe("blur-gradient");
    expect(PROJECT_BACKGROUND_PRESETS.map((preset) => preset.id)).toEqual([
      "aesthetic-fluid",
      "blur-gradient",
      "abstract-shape",
      "wavy-waves",
    ]);
  });

  it("falls back to the default when storage is missing or invalid", async () => {
    const { DEFAULT_PROJECT_BACKGROUND_ID, getStoredProjectBackground } = await import(
      "../shared/background/projectBackground"
    );

    expect(getStoredProjectBackground()).toBe(DEFAULT_PROJECT_BACKGROUND_ID);

    localStorage.setItem("personal-learning-coach.projectBackground", "unknown");

    expect(getStoredProjectBackground()).toBe(DEFAULT_PROJECT_BACKGROUND_ID);
  });

  it("saves valid background choices to localStorage", async () => {
    const { PROJECT_BACKGROUND_STORAGE_KEY, saveProjectBackground } = await import(
      "../shared/background/projectBackground"
    );

    saveProjectBackground("blur-gradient");

    expect(localStorage.getItem(PROJECT_BACKGROUND_STORAGE_KEY)).toBe("blur-gradient");
  });

  it("groups color palettes by primary color and falls back to the default palette", async () => {
    const {
      DEFAULT_PROJECT_PALETTE_ID,
      PROJECT_PALETTE_GROUPS,
      getPaletteGroupForPalette,
      getStoredProjectPalette,
    } = await import("../shared/background/projectBackground");

    expect(PROJECT_PALETTE_GROUPS.map((group) => group.id)).toEqual([
      "vivid",
      "pastel",
      "blue",
      "green",
      "cream",
    ]);
    expect(getPaletteGroupForPalette("pink-peach-pastels")?.id).toBe("pastel");
    expect(getStoredProjectPalette()).toBe(DEFAULT_PROJECT_PALETTE_ID);

    localStorage.setItem("personal-learning-coach.projectPalette", "unknown");

    expect(getStoredProjectPalette()).toBe(DEFAULT_PROJECT_PALETTE_ID);
  });

  it("saves valid palette choices to localStorage", async () => {
    const { PROJECT_PALETTE_STORAGE_KEY, saveProjectPalette } = await import("../shared/background/projectBackground");

    saveProjectPalette("seashell-blues");

    expect(localStorage.getItem(PROJECT_PALETTE_STORAGE_KEY)).toBe("seashell-blues");
  });

  it("replaces the existing generated canvas when switching backgrounds", async () => {
    const { createProjectBackgroundController } = await import("../shared/background/projectBackground");
    const container = new FakeBackgroundHost();
    container.id = "projectBackgroundHost";
    container.append({ dataset: { mockBg: "stale" } });
    hosts.set(container.id, container);

    const controller = createProjectBackgroundController(container as unknown as HTMLElement);
    controller.apply("aesthetic-fluid", "pink-peach-pastels");

    expect(container.children.map((item) => item.dataset.mockBg)).toEqual(["aesthetic-fluid"]);

    controller.apply("wavy-waves", "seashell-blues");

    expect(container.children.map((item) => item.dataset.mockBg)).toEqual(["wavy-waves"]);
    expect(starts).toEqual(["aesthetic-fluid", "wavy-waves"]);
    expect(destroys).toEqual(["aesthetic-fluid"]);
    expect(colorsUsed).toEqual([
      ["#f48da2", "#f9a3a0", "#fbb7a8", "#ffd0bd", "#ffe2d4", "#c9d49a"],
      ["#9eb8d4", "#c7e7ed", "#f4eee5", "#ebd49f", "#91b9b2", "#d6efe7"],
    ]);
  });
});
