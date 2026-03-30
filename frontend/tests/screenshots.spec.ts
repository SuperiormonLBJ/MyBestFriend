import { test } from "@playwright/test";
import path from "path";

const outDir = path.join(__dirname, "..", "docs", "screenshots");

const shots: { route: string; name: string }[] = [
  { route: "/chat", name: "chat.png" },
  { route: "/job-preparation", name: "job-preparation.png" },
  { route: "/admin", name: "admin.png" },
  { route: "/admin/knowledge", name: "admin-knowledge.png" },
  { route: "/admin/settings", name: "admin-settings.png" },
  { route: "/admin/prompts", name: "admin-prompts.png" },
  { route: "/admin/eval", name: "admin-eval.png" },
];

for (const { route, name } of shots) {
  test(`screenshot ${name}`, async ({ page }) => {
    await page.goto(route, { waitUntil: "load", timeout: 60_000 });
    await page.waitForTimeout(800);
    await page.screenshot({
      path: path.join(outDir, name),
      fullPage: true,
    });
  });
}
