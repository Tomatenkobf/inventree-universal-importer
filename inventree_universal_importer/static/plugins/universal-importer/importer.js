// src/importer.ts
function el(tag, text = "", cls = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function button(label, action, cls = "") {
  const b = el("button", label, cls);
  b.type = "button";
  b.onclick = action;
  return b;
}
function field(label, value = "", multiline = false) {
  const wrap = el("label", label);
  const input = multiline ? el("textarea") : el("input");
  input.value = value;
  wrap.append(input);
  return { wrap, input };
}
function check(label, checked = false) {
  const wrap = el("label", "", "upi-check");
  const input = el("input");
  input.type = "checkbox";
  input.checked = checked;
  wrap.append(input, document.createTextNode(label));
  return { wrap, input };
}
function details(label, data) {
  const d = el("details");
  d.append(el("summary", label), el("pre", JSON.stringify(data, null, 2)));
  return d;
}
function select(label, options) {
  const wrap = el("label", label);
  const input = el("select");
  for (const o of options) {
    const opt = el("option", o.label);
    opt.value = o.value;
    input.append(opt);
  }
  wrap.append(input);
  return { wrap, input };
}
function link(url, label) {
  const a = el("a", label);
  try {
    const u = new URL(url);
    if (u.protocol === "https:" && !u.username && !u.password) a.href = u.href;
  } catch {
  }
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}
var css = `
.upi{font:inherit;color:var(--mantine-color-text);padding:12px;max-width:1200px;margin:auto}.upi *{box-sizing:border-box}.upi h2{margin:0 0 8px}.upi p{line-height:1.5}.upi .muted{color:var(--mantine-color-dimmed)}.upi .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.upi label{display:flex;flex-direction:column;font-size:14px;gap:5px;margin:8px 0}.upi input,.upi textarea,.upi select{font:inherit;color:inherit;background:var(--mantine-color-body);border:1px solid var(--mantine-color-default-border,#aaa);border-radius:5px;padding:9px;min-width:0}.upi textarea{min-height:90px}.upi button{font:inherit;border:1px solid var(--mantine-color-default-border,#aaa);border-radius:5px;padding:8px 14px;margin:4px 6px 4px 0;background:var(--mantine-color-default);color:inherit;cursor:pointer}.upi button.primary{background:var(--mantine-primary-color-filled,#228be6);color:white}.upi button:disabled{opacity:.5;cursor:wait}.upi .card{border:1px solid var(--mantine-color-default-border,#aaa);border-radius:8px;padding:16px;margin:12px 0}.upi .upi-check{flex-direction:row;align-items:center}.upi .upi-check input{width:17px;height:17px}.upi .error{color:var(--mantine-color-red-6,#dc3545)}.upi pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto;font-size:12px}.upi img{max-width:120px;max-height:120px;object-fit:contain;float:right}.upi table{width:100%;border-collapse:collapse}.upi td,.upi th{padding:8px;text-align:left;border-bottom:1px solid var(--mantine-color-default-border,#aaa);overflow-wrap:anywhere}.upi .tag{font-size:12px;background:var(--mantine-color-blue-light);padding:4px 8px;border-radius:12px}.upi video{width:100%;max-width:400px}.upi a{color:var(--mantine-color-anchor,#228be6)}
`;
function renderPanel(target, context) {
  target.replaceChildren();
  const root = el("section", "", "upi");
  const style = el("style", css);
  root.append(style);
  target.append(root);
  root.append(
    el("h2", "Universal Product Importer"),
    el(
      "p",
      "Search worldwide product sources. Review every change before importing.",
      "muted"
    )
  );
  const status = el("p");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  const form = el("form");
  const grid = el("div", "", "grid");
  const inputs = {};
  for (const [key, label] of [
    ["gtin", "EAN / UPC / GTIN"],
    ["manufacturer", "Manufacturer"],
    ["mpn", "Manufacturer part number"],
    ["text", "Product search"],
    ["ipn", "Internal part number (existing search)"]
  ]) {
    const f = field(label);
    inputs[key] = f.input;
    grid.append(f.wrap);
  }
  const search = el("button", "Search", "primary");
  search.type = "submit";
  form.append(grid, search);
  root.append(form, status);
  const camera = el("div");
  root.append(camera);
  const results = el("div");
  const previewArea = el("div");
  root.append(results, previewArea);
  let config = { categories: [], parameter_map: {} };
  let allResults = [];
  let csvCurrent = null;
  const report = [];
  const pending = [];
  let lastJob = "";
  const api = async (action, data = {}) => (await context.api.post(
    (context.context?.endpoint || new URL(
      "plugin/universal-importer/api/",
      (context.host || window.location.origin).replace(/\/?$/, "/")
    ).href) + action + "/",
    data
  )).data;
  const error = (e) => {
    status.textContent = e?.response?.data?.error || e?.response?.data?.detail || e?.message || "Request failed";
    status.className = "error";
  };
  const run = async (action) => {
    status.className = "";
    status.textContent = "Working\u2026";
    search.disabled = true;
    try {
      await action();
    } catch (e) {
      error(e);
    } finally {
      search.disabled = false;
    }
  };
  void api("config").then((data) => {
    config = data;
    if (data.compatibility.warning) {
      status.textContent = data.compatibility.warning;
    }
  }).catch(error);
  form.onsubmit = (e) => {
    e.preventDefault();
    void lookup(
      Object.fromEntries(Object.entries(inputs).map(([k, v]) => [k, v.value]))
    );
  };
  async function lookup(query) {
    await run(async () => {
      previewArea.replaceChildren();
      const data = await api("search", query);
      allResults = data.results;
      status.textContent = `${data.results.length} result(s). ${data.errors.map((x) => x.provider + ": " + x.code).join("; ")}`;
      renderResults(data.existing);
    });
  }
  function renderResults(existing = []) {
    results.replaceChildren();
    if (existing.length)
      results.append(
        details("Existing InvenTree matches before external lookup", existing)
      );
    const controls = el("div", "", "grid");
    const filter = field("Filter name, manufacturer or source");
    const sort = select("Sort", [
      { value: "confidence", label: "Confidence" },
      { value: "name", label: "Product name" }
    ]);
    controls.append(filter.wrap, sort.wrap);
    results.append(controls);
    const cards = el("div");
    results.append(cards);
    let page = 0;
    function draw() {
      cards.replaceChildren();
      const needle = filter.input.value.toLowerCase();
      const rows = allResults.filter(
        (p) => [p.name, p.manufacturer, p.source].join(" ").toLowerCase().includes(needle)
      );
      rows.sort(
        (a, b) => sort.input.value === "name" ? a.name.localeCompare(b.name) : b.confidence - a.confidence
      );
      for (const p of rows.slice(page * 10, page * 10 + 10)) {
        const card = el("article", "", "card");
        if (p.image_urls[0]) {
          const img = el("img");
          img.src = p.image_urls[0];
          img.alt = p.name;
          img.loading = "lazy";
          img.referrerPolicy = "no-referrer";
          card.append(img);
        }
        card.append(
          el("h3", p.name || "Unnamed product"),
          el(
            "span",
            `${Math.round(p.confidence * 100)}% \u2022 ${p.records.map((r) => r.source).join(", ")}`,
            "tag"
          ),
          el(
            "p",
            [p.manufacturer, p.mpn, p.gtins.join(", ")].filter(Boolean).join(" \xB7 ")
          ),
          el("p", p.description.slice(0, 250)),
          el("p", p.explanation.join("; "), "muted")
        );
        if (p.existing.length)
          card.append(el("p", `${p.existing.length} existing part match(es)`));
        card.append(
          button("Review product", () => showPreview(p), "primary"),
          details("Individual source records, licenses and conflicts", {
            records: p.records,
            conflicts: p.conflicts
          })
        );
        cards.append(card);
      }
      cards.append(
        button("Previous", () => {
          page = Math.max(0, page - 1);
          draw();
        }),
        el(
          "span",
          `Page ${page + 1} / ${Math.max(1, Math.ceil(rows.length / 10))}`
        ),
        button("Next", () => {
          if ((page + 1) * 10 < rows.length) page++;
          draw();
        })
      );
    }
    filter.input.oninput = () => {
      page = 0;
      draw();
    };
    sort.input.onchange = draw;
    draw();
  }
  function showPreview(original) {
    previewArea.replaceChildren();
    const box = el("div", "", "card");
    previewArea.append(box);
    box.append(el("h3", "Edit and select fields"));
    const sourceRow = csvCurrent;
    const p = structuredClone(original);
    delete p.existing;
    const fg = el("div", "", "grid");
    box.append(fg);
    const selected = {};
    const editors = {};
    for (const [key, label, def] of [
      ["name", "Name (100 characters)", true],
      ["description", "Description (250 characters)", true],
      ["manufacturer", "Manufacturer + MPN", false],
      ["gtins", "GTIN identifiers", true],
      ["ipn", "Internal part number", false]
    ]) {
      const wrap = el("div");
      const cb = check("Import " + key, def);
      selected[key] = cb.input;
      wrap.append(cb.wrap);
      const f = field(
        label,
        key === "gtins" ? p.gtins.join(", ") : p[key] || "",
        key === "description"
      );
      editors[key] = f.input;
      wrap.append(f.wrap);
      fg.append(wrap);
    }
    const mpn = field("MPN", p.mpn);
    fg.append(mpn.wrap);
    const catcb = check("Import category");
    selected.category = catcb.input;
    box.append(catcb.wrap);
    const cat = select("Existing category", [
      { value: "", label: "Configured default / mapping" },
      ...config.categories.map((c) => ({
        value: String(c.id),
        label: c.name
      }))
    ]);
    box.append(cat.wrap);
    const specCb = check("Import selected specifications");
    selected.specifications = specCb.input;
    box.append(specCb.wrap);
    const specs = {};
    const specEdits = {};
    const specDetails = el("details");
    specDetails.append(
      el("summary", "Specifications (map templates in plugin settings)")
    );
    for (const [name, value] of Object.entries(p.specifications)) {
      const cb = check(name, !!config.parameter_map[name]);
      cb.input.disabled = !config.parameter_map[name];
      specs[name] = cb.input;
      const edit = field(name, String(value));
      specEdits[name] = edit.input;
      specDetails.append(cb.wrap, edit.wrap);
    }
    box.append(specDetails);
    const target2 = select("Import mode", [
      { value: "", label: "Create a new part" },
      ...original.existing.map((x) => ({
        value: String(x.id),
        label: `Enrich #${x.id} \u2014 ${x.name}`
      }))
    ]);
    box.append(target2.wrap);
    const manualTarget = field("Or enrich existing part ID");
    box.append(manualTarget.wrap);
    for (const x of original.existing) {
      const a = el("a", `View existing part #${x.id}`);
      a.href = `/web/part/${x.id}`;
      a.target = "_blank";
      a.rel = "noopener";
      box.append(a, el("br"));
    }
    const image = select("Download image (optional)", [
      { value: "", label: "Do not download" },
      ...p.image_urls.map((u) => ({ value: u, label: u }))
    ]);
    const sheet = select("Datasheet link (optional)", [
      { value: "", label: "Do not attach" },
      ...p.datasheet_urls.map((u) => ({ value: u, label: u }))
    ]);
    const pdf = check("Download selected PDF as attachment");
    const rights = check("I have verified usage rights for selected media");
    box.append(
      image.wrap,
      sheet.wrap,
      pdf.wrap,
      rights.wrap,
      details("Attribution and source references", {
        licenses: p.image_licenses,
        provenance: p.provenance,
        conflicts: p.conflicts
      })
    );
    for (const url of p.datasheet_urls)
      box.append(link(url, "Open datasheet"), el("br"));
    const overwrite = field(
      "Explicit overwrite fields, comma-separated (e.g. description)"
    );
    box.append(overwrite.wrap);
    const review = el("div");
    box.append(
      button(
        "Build final comparison",
        () => void run(async () => {
          for (const key of ["name", "description", "manufacturer"])
            p[key] = editors[key].value;
          p.mpn = mpn.input.value;
          p.gtins = editors.gtins.value.split(",").map((x) => x.trim()).filter(Boolean);
          for (const key in specEdits)
            p.specifications[key] = specEdits[key].value;
          const options = {
            fields: Object.keys(selected).filter((k) => selected[k].checked),
            ipn: editors.ipn.value,
            category_id: cat.input.value ? Number(cat.input.value) : null,
            target_id: Number(manualTarget.input.value || target2.input.value) || null,
            specifications: Object.keys(specs).filter(
              (k) => specs[k].checked
            ),
            overwrite: overwrite.input.value.split(",").map((x) => x.trim()).filter(Boolean),
            image_url: image.input.value,
            datasheet_url: sheet.input.value,
            download_pdf: pdf.input.checked,
            media_rights_confirmed: rights.input.checked
          };
          const data = await api("preview", { product: p, options });
          review.replaceChildren();
          review.append(
            el(
              "h3",
              "Final comparison \u2014 the signed snapshot below will be imported"
            )
          );
          const table = el("table");
          const header = el("tr");
          for (const title of ["Field", "Current", "Proposed"])
            header.append(el("th", title));
          table.append(header);
          for (const change of data.changes) {
            const row = el("tr");
            row.append(
              el("td", change.field),
              el(
                "td",
                typeof change.before === "object" ? JSON.stringify(change.before) : String(change.before ?? "\u2014")
              ),
              el(
                "td",
                typeof change.after === "object" ? JSON.stringify(change.after) : String(change.after ?? "\u2014")
              )
            );
            table.append(row);
          }
          review.append(table);
          review.append(
            details("Complete current values", data.current),
            details("All selected changes and identity", {
              options: data.options,
              product: data.product
            })
          );
          const separate = check(
            "Create a separate part despite the duplicates shown"
          );
          if (data.existing.length && !options.target_id)
            review.append(
              details("Duplicates", data.existing),
              separate.wrap
            );
          const confirm = check(
            "I reviewed these changes and approve this import"
          );
          review.append(confirm.wrap);
          const commitButton = button(
            "Confirm import",
            () => void run(async () => {
              if (!confirm.input.checked)
                throw Error("Confirm that you reviewed this snapshot");
              commitButton.disabled = true;
              try {
                const imported = await api("import", {
                  token: data.token,
                  confirm: true,
                  separate: separate.input.checked
                });
                status.textContent = `Imported part #${imported.part_id}`;
                review.replaceChildren(el("p", status.textContent));
                const a = el("a", "Open imported part");
                a.href = `/web/part/${imported.part_id}`;
                review.append(a);
                if (sourceRow) {
                  report.push({
                    row: sourceRow.row,
                    status: "imported",
                    part_id: imported.part_id
                  });
                  csvCurrent = null;
                }
              } catch (e) {
                if (sourceRow)
                  report.push({
                    row: sourceRow.row,
                    status: "failed",
                    error: e?.response?.data?.error || "Import failed"
                  });
                throw e;
              } finally {
                commitButton.disabled = false;
              }
            }),
            "primary"
          );
          review.append(
            commitButton,
            button("Add approved snapshot to batch", () => {
              if (!confirm.input.checked) {
                error(Error("Confirm review before adding to batch"));
                return;
              }
              pending.push({
                token: data.token,
                confirm: true,
                separate: separate.input.checked,
                row: sourceRow?.row || pending.length + 1
              });
              status.textContent = `${pending.length} reviewed snapshot(s) ready to queue`;
              review.replaceChildren(
                el(
                  "p",
                  "Added to reviewed batch. Continue with the next row."
                )
              );
            })
          );
          status.textContent = "Comparison ready. Review before confirming.";
        }),
        "primary"
      ),
      review
    );
    box.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }
  const scan = button(
    "Scan with camera",
    () => void run(async () => {
      const Detector = window.BarcodeDetector;
      if (!Detector || !navigator.mediaDevices)
        throw Error(
          "Camera barcode scanning is unavailable in this browser. Use a USB scanner or manual entry."
        );
      const supported = await Detector.getSupportedFormats();
      const formats = ["ean_13", "ean_8", "upc_a", "upc_e"].filter(
        (x) => supported.includes(x)
      );
      if (!formats.length)
        throw Error("This browser does not support retail barcode formats");
      const detector = new Detector({ formats });
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" }
      });
      const video = el("video");
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;
      let stopped = false;
      const stop = () => {
        stopped = true;
        stream.getTracks().forEach((t) => t.stop());
        camera.replaceChildren();
      };
      camera.replaceChildren(video, button("Stop camera", stop));
      await video.play();
      status.textContent = "Point the camera at the barcode";
      const timeout = window.setTimeout(stop, 6e4);
      const tick = async () => {
        if (stopped) return;
        if (!target.isConnected) {
          clearTimeout(timeout);
          stop();
          return;
        }
        try {
          const found = await detector.detect(video);
          if (found.length) {
            inputs.gtin.value = found[0].rawValue;
            clearTimeout(timeout);
            stop();
            status.textContent = "Barcode captured. Press Search.";
            return;
          }
        } catch {
          clearTimeout(timeout);
          stop();
          status.textContent = "Camera scan failed; use manual entry.";
          return;
        }
        window.setTimeout(() => void tick(), 250);
      };
      void tick();
    })
  );
  form.append(scan);
  const bulk = el("details");
  bulk.append(
    el("summary", "CSV batch review \u2014 up to 200 rows, no stock creation")
  );
  const file = el("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  const mapping = field(
    'Optional column mapping JSON, e.g. {"Item Code":"gtin"}',
    "{}"
  );
  const rowsArea = el("div");
  bulk.append(
    file,
    mapping.wrap,
    button(
      "Validate CSV",
      () => void run(async () => {
        if (!file.files?.[0]) throw Error("Select a CSV file");
        if (file.files[0].size > 1e6)
          throw Error("CSV is limited to 1 MB");
        const data = await api("csv", {
          csv: await file.files[0].text(),
          mapping: JSON.parse(mapping.input.value)
        });
        rowsArea.replaceChildren();
        for (const row of data.rows) {
          const line = el("div", "", "card");
          line.append(
            el(
              "span",
              `Row ${row.row}: ${row.error || JSON.stringify(row.query)}`
            )
          );
          if (!row.error)
            line.append(
              button("Search / retry this row", () => {
                csvCurrent = row;
                void lookup(row.query);
              }),
              button("Skip", () => {
                report.push({ row: row.row, status: "skipped" });
                line.append(el("span", "Skipped"));
              })
            );
          else
            report.push({
              row: row.row,
              status: "invalid",
              error: row.error
            });
          rowsArea.append(line);
        }
        status.textContent = "CSV validated. Search and review rows individually; quantity and location are informational only.";
      })
    ),
    button("Download session report", () => {
      const keys = ["row", "status", "part_id", "error"];
      const escape = (v) => {
        let s = String(v ?? "");
        if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
        return '"' + s.split('"').join('""') + '"';
      };
      const csv = [keys, ...report.map((r) => keys.map((k) => r[k]))].map((row) => row.map(escape).join(",")).join("\r\n");
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
      const a = el("a");
      a.href = url;
      a.download = "import-report.csv";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1e3);
    }),
    button(
      "Queue reviewed imports",
      () => void run(async () => {
        if (!pending.length)
          throw Error("Review products and add approved snapshots first");
        const job = await api("bulk", { rows: pending });
        lastJob = job.id;
        pending.length = 0;
        status.textContent = `Job ${job.id}: ${job.status}. Use Refresh job report to check progress.`;
      })
    ),
    button(
      "Refresh job report",
      () => void run(async () => {
        if (!lastJob) throw Error("No job queued in this session");
        const job = await api("job", { id: lastJob });
        for (const row of job.rows) {
          if (row.status !== "pending") report.push(row);
        }
        rowsArea.replaceChildren(details("Background job report", job));
        status.textContent = `Job ${job.status}`;
      })
    ),
    button(
      "Recover interrupted job",
      () => void run(async () => {
        if (!lastJob) throw Error("No job queued in this session");
        const job = await api("resume", { id: lastJob });
        status.textContent = `Job ${job.status}`;
      })
    ),
    rowsArea
  );
  root.append(bulk);
}
export {
  renderPanel
};
