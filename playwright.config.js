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
    // a API não depende do aparelho: roda só no desktop
    { name: "celular", use: { ...devices["Pixel 7"] }, testIgnore: /api\.spec\.js/ },
  ],
  // o Worker de verdade (site + API do manifesto) com um D1 local, via wrangler dev
  webServer: {
    command: "npm run dev",
    url: "http://localhost:4173",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
});
