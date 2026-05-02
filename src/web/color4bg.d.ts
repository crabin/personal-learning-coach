declare module "color4bg" {
  interface Color4BgOptions {
    dom: string;
    colors: string[];
    seed: number;
    loop: boolean;
  }

  class Color4BgInstance {
    constructor(options: Color4BgOptions);
    start(): void;
    destroy(): void;
  }

  export class AbstractShapeBg extends Color4BgInstance {}
  export class AestheticFluidBg extends Color4BgInstance {}
  export class BlurGradientBg extends Color4BgInstance {}
  export class WavyWavesBg extends Color4BgInstance {}
}
