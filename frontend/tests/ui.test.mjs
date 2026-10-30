import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { renderPanel } from "../../inventree_universal_importer/static/plugins/universal-importer/importer.js";
const wait = () => new Promise((resolve) => setTimeout(resolve, 20));
test("search renders safe text, preview requires explicit confirmation", async () => {
  const dom = new JSDOM('<div id="root"></div>', {
    url: "https://inventory.example/web/part/",
  });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const calls = [];
  const product = {
    name: "<img src=x onerror=alert(1)>",
    description: "Sensor",
    manufacturer: "Acme",
    mpn: "A1",
    gtins: ["04006381333931"],
    image_urls: [],
    datasheet_urls: [],
    specifications: {},
    records: [{ source: "demo" }],
    explanation: ["Exact GTIN"],
    confidence: 0.99,
    existing: [],
    source: "demo",
  };
  const api = {
    post: async (url, data) => {
      calls.push({ url, data });
      if (url.endsWith("config/"))
        return {
          data: {
            categories: [],
            parameter_map: {},
            compatibility: { warning: "" },
          },
        };
      if (url.endsWith("search/"))
        return { data: { results: [product], existing: [], errors: [] } };
      if (url.endsWith("preview/"))
        return {
          data: {
            token: "signed",
            changes: [{ field: "name", before: null, after: product.name }],
            existing: [],
            product,
            options: data.options,
            current: null,
          },
        };
      if (url.endsWith("import/")) return { data: { part_id: 7 } };
    },
  };
  const root = document.getElementById("root");
  renderPanel(root, {
    api,
    context: { endpoint: "/plugin/universal-importer/api/" },
  });
  await wait();
  root
    .querySelector("form")
    .dispatchEvent(new window.Event("submit", { cancelable: true }));
  await wait();
  assert.ok(root.textContent.includes(product.name));
  assert.equal(root.querySelectorAll("img").length, 0);
  const click = (text) =>
    [...root.querySelectorAll("button")]
      .find((b) => b.textContent === text)
      .click();
  click("Review product");
  click("Build final comparison");
  await wait();
  click("Confirm import");
  await wait();
  assert.equal(calls.filter((x) => x.url.endsWith("import/")).length, 0);
  const confirm = [...root.querySelectorAll("label")].find((x) =>
    x.textContent.includes("I reviewed these changes"),
  );
  confirm.querySelector("input").checked = true;
  click("Confirm import");
  await wait();
  assert.equal(calls.filter((x) => x.url.endsWith("import/")).length, 1);
  assert.ok(root.textContent.includes("Imported part #7"));
});
test("1.6 route context without feature context preserves a server subpath", async () => {
  const dom = new JSDOM('<div id="root"></div>', {
    url: "https://inventory.example/sub/web/plugin/universal-importer/import",
  });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const calls = [];
  const api = {
    post: async (url) => {
      calls.push(url);
      return {
        data: {
          categories: [],
          parameter_map: {},
          compatibility: { warning: "" },
        },
      };
    },
  };
  renderPanel(document.getElementById("root"), {
    api,
    host: "https://inventory.example/sub",
  });
  await wait();
  assert.equal(
    calls[0],
    "https://inventory.example/sub/plugin/universal-importer/api/config/",
  );
});
