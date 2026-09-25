// @ts-check
// Fluxo principal do "Monte sua urna" com os dados reais de site/dados/.
const { test, expect } = require("@playwright/test");

// qualquer erro de JavaScript na página faz o teste falhar
let erros = [];
let errosEsperados = [];
test.beforeEach(async ({ page, context }) => {
  erros = [];
  errosEsperados = [];
  page.on("pageerror", (e) => erros.push(e.message));
  page.on("console", (m) => m.type() === "error" && erros.push(m.text()));
  // o WhatsApp não é aberto de verdade nos testes
  await context.route("https://wa.me/**", (r) => r.fulfill({ body: "whatsapp" }));
});

test.afterEach(async () => {
  const inesperados = erros.filter((e) => !errosEsperados.some((esperado) => e.includes(esperado)));
  expect(inesperados, "erros de JavaScript na página").toEqual([]);
});

async function escolherEstado(page, uf) {
  await page.goto("/#urna");
  await page.locator("#uf-select").selectOption(uf);
  await page.locator("#start").click();
}

async function escolherPrimeira(page) {
  const card = page.locator(".cand").first();
  await expect(card).toBeVisible();
  const numero = (await card.locator(".num").textContent())?.trim();
  await card.click();
  await page.locator("#next").click();
  return numero;
}

test("página tem os metadados básicos", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Vota Nelas/);
  await expect(page.locator('meta[name="viewport"]')).toHaveAttribute("content", /width=device-width/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /og\.png$/);
  expect((await page.request.get("/og.png")).ok()).toBeTruthy();
  expect((await page.request.get("/favicon.svg")).ok()).toBeTruthy();
});

test("monta a urna completa e envia a colinha pelo WhatsApp", async ({ page, context }) => {
  await escolherEstado(page, "SP");

  await expect(page.locator(".step-title")).toHaveText("Deputada federal");
  await expect(page.locator("#count-lbl")).toContainText("candidatas neste cargo");
  const fed = await escolherPrimeira(page);

  await expect(page.locator(".step-title")).toHaveText("Deputada estadual");
  const est = await escolherPrimeira(page);

  await expect(page.locator(".step-title")).toHaveText("Senadora (1º voto)");
  const sen1 = await escolherPrimeira(page);

  // o 1º voto para o Senado não pode aparecer de novo no 2º
  await expect(page.locator(".step-title")).toHaveText("Senadora (2º voto)");
  await expect(page.locator(".cand .num", { hasText: new RegExp(`^${sen1}$`) })).toHaveCount(0);
  await escolherPrimeira(page);

  await expect(page.locator(".step-title")).toHaveText("Governadora");
  await escolherPrimeira(page);

  await expect(page.locator(".step-title")).toHaveText("Presidenta");
  await escolherPrimeira(page);

  await expect(page.locator(".step-title")).toHaveText("Sua urna tem 6 mulheres.");
  await expect(page.locator("#slots .digits").first()).toHaveAttribute("aria-label", `número ${fed}`);

  const [whatsapp] = await Promise.all([context.waitForEvent("page"), page.locator("#share").click()]);
  const texto = new URL(whatsapp.url()).searchParams.get("text") || "";
  expect(texto).toContain(`*${fed}*`);
  expect(texto).toContain(`*${est}*`);
  expect(texto).toContain("(SP)");
  // o link aponta para o próprio site, nunca para o protótipo no claude.ai
  expect(texto).toContain("http://localhost:4173/");
  expect(texto).not.toContain("claude.ai");
});

test("busca por nome ignora acentos", async ({ page }) => {
  await escolherEstado(page, "SP");
  const nome = (await page.locator(".cand .nm").first().textContent())?.trim() || "";
  const semAcento = nome.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  await page.locator("#q").fill(semAcento);
  await expect(page.locator(".cand .nm", { hasText: nome }).first()).toBeVisible();
});

test("cada candidata tem link para a página dela no TSE", async ({ page }) => {
  await escolherEstado(page, "AC");
  const href = await page.locator(".know").first().getAttribute("href");
  expect(href).toMatch(/^https:\/\/divulgacandcontas\.tse\.jus\.br\/divulga\/#\/candidato\/NORTE\/AC\/20322002026\/\d+\/2026\/AC$/);
});

test("cargo sem mulheres mostra aviso e deixa seguir", async ({ page }) => {
  // no Espírito Santo, nenhuma mulher concorre a governadora em 2026
  await escolherEstado(page, "ES");
  for (let i = 0; i < 4; i++) await page.locator("#skip").click();
  await expect(page.locator(".step-title")).toHaveText("Governadora");
  await expect(page.locator(".empty")).toHaveText(/Nenhuma mulher concorre a governadora no Espírito Santo/);
  await expect(page.locator("#next")).toBeDisabled();
  await expect(page.locator("#skip")).toHaveText("Próximo cargo");
  await page.locator("#skip").click();
  await expect(page.locator(".step-title")).toHaveText("Presidenta");
});

test("falha ao carregar os dados mostra opção de tentar de novo", async ({ page }) => {
  let falhar = true;
  errosEsperados.push("503");
  // depois da falha, os dados vêm direto do disco, sem depender do servidor de testes
  await page.route("**/dados/*.json", (r) =>
    falhar ? r.fulfill({ status: 503 }) : r.fulfill({ path: `site${new URL(r.request().url()).pathname}` })
  );
  await escolherEstado(page, "SP");
  await expect(page.locator("#loading")).toContainText("Não foi possível carregar");
  falhar = false;
  await page.locator("#retry").click();
  await expect(page.locator(".cand").first()).toBeVisible();
});

test("no dia da eleição o envio e as assinaturas ficam pausados", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-10-04T10:00:00-03:00"));
  await page.goto("/");
  await expect(page.locator("#share")).toBeHidden();
  await expect(page.locator("#pledge-btn")).toBeHidden();
  await expect(page.locator("#pledge-note")).toContainText("dia de eleição");
});

test("assinar o manifesto troca o botão pela confirmação", async ({ page }) => {
  await page.goto("/#compromisso");
  await page.locator("#pledge-uf").selectOption("BA");
  await page.locator("#pledge-btn").click();
  await expect(page.locator("#pledge-btn")).toBeHidden();
  await expect(page.locator("#pledge-done")).toBeVisible();
});

test("voto em branco aparece na colinha e cargo pulado fica de fora", async ({ page, context }) => {
  await escolherEstado(page, "SP");
  const fed = await escolherPrimeira(page);
  // estadual: pula
  await page.locator("#skip").click();
  // senado 1: branco, que não tira ninguém da lista do 2º voto
  await expect(page.locator(".step-title")).toHaveText("Senadora (1º voto)");
  const senadoras = await page.locator(".cand").count();
  await page.locator("#branco").click();
  await expect(page.locator("#branco")).toHaveAttribute("aria-pressed", "true");
  await page.locator("#next").click();
  await expect(page.locator(".step-title")).toHaveText("Senadora (2º voto)");
  await expect(page.locator(".cand")).toHaveCount(senadoras);
  await page.locator("#skip").click();
  await page.locator("#skip").click();
  // presidenta: branco
  await expect(page.locator(".step-title")).toHaveText("Presidenta");
  await page.locator("#branco").click();
  await page.locator("#next").click();

  await expect(page.locator(".step-title")).toHaveText("Sua urna tem 1 mulher.");
  await expect(page.locator(".step-help", { hasText: "tecla BRANCO" })).toBeVisible();
  await expect(page.locator('#slots .digits[aria-label="voto em branco"]')).toHaveCount(2);

  const [whatsapp] = await Promise.all([context.waitForEvent("page"), page.locator("#share").click()]);
  const texto = new URL(whatsapp.url()).searchParams.get("text") || "";
  expect(texto).toContain(`*${fed}*`);
  expect(texto).toContain("Presidenta: *BRANCO*");
  expect(texto).toContain("Senadora (1º voto): *BRANCO*");
  expect(texto).not.toContain("Deputada estadual");
  expect(texto).toContain("Minha urna tem 1 mulher");
});

test("só votos em branco viram convite, não colinha", async ({ page, context }) => {
  await escolherEstado(page, "AC");
  for (let i = 0; i < 6; i++) {
    await page.locator("#branco").click();
    await page.locator("#next").click();
  }
  await expect(page.locator(".step-title")).toHaveText("Sua urna tem 0 mulheres.");
  await expect(page.locator("#share")).toHaveText("Convidar amigas pelo WhatsApp");
  const [whatsapp] = await Promise.all([context.waitForEvent("page"), page.locator("#share").click()]);
  const texto = new URL(whatsapp.url()).searchParams.get("text") || "";
  expect(texto).toContain("Monte sua urna só com mulheres");
  expect(texto).not.toContain("BRANCO");
});

test("limpar escolhas pede confirmação e recomeça do mapa", async ({ page }) => {
  await escolherEstado(page, "SP");
  await expect(page.locator("#limpar")).toBeHidden();
  const fed = await escolherPrimeira(page);
  await expect(page.locator("#limpar")).toBeVisible();

  // cancelar mantém tudo como estava
  page.once("dialog", (d) => d.dismiss());
  await page.locator("#limpar").click();
  await expect(page.locator("#slots .digits").first()).toHaveAttribute("aria-label", `número ${fed}`);

  // confirmar apaga as escolhas e volta para o mapa com o estado marcado
  page.once("dialog", (d) => d.accept());
  await page.locator("#limpar").click();
  await expect(page.locator(".step-title")).toHaveText("Onde você vota?");
  await expect(page.locator("#uf-select")).toHaveValue("SP");
  await expect(page.locator("#slots .digits").first()).toHaveAttribute("aria-label", "sem escolha");
  await expect(page.locator("#limpar")).toBeHidden();
  await page.reload();
  await expect(page.locator("#slots .digits").first()).toHaveAttribute("aria-label", "sem escolha");
});

test("não mostra mais a faixa de protótipo", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Protótipo")).toHaveCount(0);
});
