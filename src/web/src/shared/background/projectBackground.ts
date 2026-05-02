import { AbstractShapeBg, AestheticFluidBg, BlurGradientBg, WavyWavesBg } from "color4bg";

export const PROJECT_BACKGROUND_STORAGE_KEY = "personal-learning-coach.projectBackground";
export const PROJECT_PALETTE_STORAGE_KEY = "personal-learning-coach.projectPalette";
export const DEFAULT_PROJECT_BACKGROUND_ID = "blur-gradient";
export const DEFAULT_PROJECT_PALETTE_ID = "pink-peach-pastels";

export type ProjectBackgroundId =
  | "aesthetic-fluid"
  | "blur-gradient"
  | "abstract-shape"
  | "wavy-waves";
export type ProjectPaletteGroupId = "vivid" | "pastel" | "blue" | "green" | "cream";
export type ProjectPaletteId =
  | "sunset-lab"
  | "citrus-focus"
  | "pink-peach-pastels"
  | "purple-pink-pastels"
  | "pastel-cream-pinks"
  | "soft-clouds"
  | "seashell-blues"
  | "blue-purple-pastels"
  | "light-blue-green-pastels"
  | "soft-ice"
  | "brilliant-pastels"
  | "happy-peace"
  | "pastel-trend"
  | "pastel-food"
  | "cream-study";

type ProjectBackgroundConstructor = new (options: ProjectBackgroundOptions) => ProjectBackgroundInstance;

interface ProjectBackgroundOptions {
  dom: string;
  colors: string[];
  seed: number;
  loop: boolean;
}

interface ProjectBackgroundInstance {
  start(): void;
  destroy(): void;
}

interface ProjectBackgroundPreset {
  id: ProjectBackgroundId;
  label: string;
  description: string;
  seed: number;
  loop: boolean;
  create: ProjectBackgroundConstructor;
}

interface ProjectPalette {
  id: ProjectPaletteId;
  label: string;
  colors: string[];
}

interface ProjectPaletteGroup {
  id: ProjectPaletteGroupId;
  label: string;
  accent: string;
  palettes: ProjectPalette[];
}

export const PROJECT_BACKGROUND_PRESETS: ProjectBackgroundPreset[] = [
  {
    id: "aesthetic-fluid",
    label: "流体光谱",
    description: "柔和流动，适合长期学习工作台。",
    seed: 1000,
    loop: true,
    create: AestheticFluidBg,
  },
  {
    id: "blur-gradient",
    label: "雾化渐变",
    description: "低干扰色块，阅读时更安静。",
    seed: 1608,
    loop: true,
    create: BlurGradientBg,
  },
  {
    id: "abstract-shape",
    label: "抽象几何",
    description: "更清晰的结构感，适合规划任务。",
    seed: 2416,
    loop: true,
    create: AbstractShapeBg,
  },
  {
    id: "wavy-waves",
    label: "波纹曲线",
    description: "带有轻微运动感，适合复盘页面。",
    seed: 3141,
    loop: true,
    create: WavyWavesBg,
  },
];

export const PROJECT_PALETTE_GROUPS: ProjectPaletteGroup[] = [
  {
    id: "vivid",
    label: "鲜明",
    accent: "#fb3f8f",
    palettes: [
      {
        id: "sunset-lab",
        label: "日落实验室",
        colors: ["#ff4d6d", "#ff8c42", "#ffd166", "#06d6a0", "#118ab2", "#7b2cbf"],
      },
      {
        id: "citrus-focus",
        label: "柑橘专注",
        colors: ["#f72585", "#ff6b35", "#ffd60a", "#80ed99", "#00bbf9", "#9b5de5"],
      },
    ],
  },
  {
    id: "pastel",
    label: "粉彩",
    accent: "#e7b8d8",
    palettes: [
      {
        id: "pink-peach-pastels",
        label: "粉桃柔彩",
        colors: ["#f48da2", "#f9a3a0", "#fbb7a8", "#ffd0bd", "#ffe2d4", "#c9d49a"],
      },
      {
        id: "purple-pink-pastels",
        label: "紫粉粉彩",
        colors: ["#bca6df", "#d6c3ed", "#ead7f3", "#f8edf1", "#ffdbe7", "#ffc0d7"],
      },
      {
        id: "pastel-cream-pinks",
        label: "奶油粉彩",
        colors: ["#ffc5d3", "#ffd8df", "#ffe7e6", "#fff2ee", "#f5e7d8", "#f0d2ac"],
      },
      {
        id: "soft-clouds",
        label: "柔云",
        colors: ["#c9a6e8", "#e8bad5", "#ead7b0", "#f8f7ed", "#bfdce7", "#a8b7e6"],
      },
    ],
  },
  {
    id: "blue",
    label: "蓝色",
    accent: "#3b82f6",
    palettes: [
      {
        id: "seashell-blues",
        label: "贝壳蓝",
        colors: ["#9eb8d4", "#c7e7ed", "#f4eee5", "#ebd49f", "#91b9b2", "#d6efe7"],
      },
      {
        id: "blue-purple-pastels",
        label: "蓝紫粉彩",
        colors: ["#8ecae6", "#bde0fe", "#d7e3fc", "#e9d5ff", "#d8b4fe", "#c084fc"],
      },
      {
        id: "light-blue-green-pastels",
        label: "浅蓝绿粉彩",
        colors: ["#c7f0ff", "#d8f3f8", "#e6f6f0", "#c7f9d4", "#b9fbc0", "#98f5b5"],
      },
      {
        id: "soft-ice",
        label: "柔冰",
        colors: ["#cfd8f6", "#bdeff0", "#f8f5d7", "#e1f5b7", "#c8e5a7", "#d7b8eb"],
      },
    ],
  },
  {
    id: "green",
    label: "绿色",
    accent: "#22c55e",
    palettes: [
      {
        id: "brilliant-pastels",
        label: "明亮粉彩",
        colors: ["#b8f5bd", "#d6f4f1", "#f7f5ec", "#f8ed9a", "#f0bad6", "#d3b7ea"],
      },
      {
        id: "happy-peace",
        label: "快乐和平",
        colors: ["#d3a0e8", "#edbfd4", "#f4f4ce", "#cde9e6", "#bff0ba", "#f4c99d"],
      },
      {
        id: "pastel-trend",
        label: "粉彩趋势",
        colors: ["#efb7ce", "#e4b9ec", "#d8c9e8", "#ddeafa", "#bde4f4", "#a7deef"],
      },
    ],
  },
  {
    id: "cream",
    label: "奶油",
    accent: "#f5ead6",
    palettes: [
      {
        id: "pastel-food",
        label: "奶油餐盘",
        colors: ["#c9bfd6", "#f2caca", "#f5d8bd", "#f7eedc", "#bfd8d2", "#abc8c0"],
      },
      {
        id: "cream-study",
        label: "奶油书桌",
        colors: ["#f6eadf", "#f8d8c8", "#f4e6c1", "#e9f3d2", "#cfe8dd", "#d4c5f0"],
      },
    ],
  },
];

export function getStoredProjectBackground(storage: Storage = localStorage): ProjectBackgroundId {
  return parseProjectBackgroundId(storage.getItem(PROJECT_BACKGROUND_STORAGE_KEY));
}

export function saveProjectBackground(id: ProjectBackgroundId, storage: Storage = localStorage): void {
  storage.setItem(PROJECT_BACKGROUND_STORAGE_KEY, id);
}

export function getStoredProjectPalette(storage: Storage = localStorage): ProjectPaletteId {
  return parseProjectPaletteId(storage.getItem(PROJECT_PALETTE_STORAGE_KEY));
}

export function saveProjectPalette(id: ProjectPaletteId, storage: Storage = localStorage): void {
  storage.setItem(PROJECT_PALETTE_STORAGE_KEY, id);
}

export function parseProjectBackgroundId(value: string | null): ProjectBackgroundId {
  if (PROJECT_BACKGROUND_PRESETS.some((preset) => preset.id === value)) {
    return value as ProjectBackgroundId;
  }
  return DEFAULT_PROJECT_BACKGROUND_ID;
}

export function parseProjectPaletteId(value: string | null): ProjectPaletteId {
  if (findProjectPalette(value)) {
    return value as ProjectPaletteId;
  }
  return DEFAULT_PROJECT_PALETTE_ID;
}

export function getPaletteGroupForPalette(id: ProjectPaletteId): ProjectPaletteGroup | undefined {
  return PROJECT_PALETTE_GROUPS.find((group) => group.palettes.some((palette) => palette.id === id));
}

export function getFirstPaletteForGroup(id: ProjectPaletteGroupId): ProjectPaletteId {
  return PROJECT_PALETTE_GROUPS.find((group) => group.id === id)?.palettes[0]?.id ?? DEFAULT_PROJECT_PALETTE_ID;
}

export function getProjectPaletteColors(id: ProjectPaletteId): string[] {
  return findProjectPalette(id)?.colors ?? findProjectPalette(DEFAULT_PROJECT_PALETTE_ID)?.colors ?? [];
}

export function createProjectBackgroundController(container: HTMLElement): {
  apply: (id: ProjectBackgroundId, paletteId?: ProjectPaletteId) => ProjectBackgroundId;
} {
  let currentInstance: ProjectBackgroundInstance | null = null;

  return {
    apply(id: ProjectBackgroundId, paletteId = DEFAULT_PROJECT_PALETTE_ID): ProjectBackgroundId {
      const preset = PROJECT_BACKGROUND_PRESETS.find((item) => item.id === id);
      const selected =
        preset ??
        PROJECT_BACKGROUND_PRESETS.find((item) => item.id === DEFAULT_PROJECT_BACKGROUND_ID) ??
        PROJECT_BACKGROUND_PRESETS[0];
      currentInstance?.destroy();
      container.replaceChildren();
      container.dataset.background = selected.id;
      container.dataset.state = "loading";

      try {
        currentInstance = new selected.create({
          dom: ensureHostId(container),
          colors: getProjectPaletteColors(paletteId),
          seed: selected.seed,
          loop: selected.loop,
        });
        container.dataset.state = "ready";
      } catch {
        currentInstance = null;
        container.replaceChildren();
        container.dataset.state = "fallback";
      }

      return selected.id;
    },
  };
}

function findProjectPalette(id: string | null): ProjectPalette | undefined {
  return PROJECT_PALETTE_GROUPS.flatMap((group) => group.palettes).find((palette) => palette.id === id);
}

function ensureHostId(container: HTMLElement): string {
  if (!container.id) {
    container.id = "projectBackgroundHost";
  }
  return container.id;
}
