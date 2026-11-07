declare module "plotly.js-basic-dist-min" {
  const Plotly: {
    react(
      target: HTMLElement,
      data: object[],
      layout?: object,
      config?: object,
    ): Promise<unknown>;
    newPlot(
      target: HTMLElement,
      data: object[],
      layout?: object,
      config?: object,
    ): Promise<unknown>;
    purge(target: HTMLElement): void;
    Plots: {
      resize(target: HTMLElement): void;
    };
  };
  export default Plotly;
}
