// @ts-check
const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:4173",
    trace: "retain-on-failure",
    // sem rolagem suave: o site troca por rolagem instantânea e os cliques não pegam o painel em movimento
    reducedMotion: "reduce",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "celular", use: { ...devices["Pixel 7"] } },
  ],
  // servidor estático de site/ (tests/servidor.py aguenta os navegadores em paralelo)
  webServer: {
    command: "python3 tests/servidor.py 4173",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
  },
});
