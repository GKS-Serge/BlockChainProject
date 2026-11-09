const rows = document.querySelector("#transaction-rows");
const searchInput = document.querySelector("#search-input");
const graphStage = document.querySelector("#graph-stage");
const graphViewport = document.querySelector("#graph-viewport");
const inspectorContent = document.querySelector("#inspector-content");
const toast = document.querySelector("#toast");
const transactionDialog = document.querySelector("#transaction-dialog");
const transactionForm = document.querySelector("#transaction-form");

let chainState = null;
let selectedIndex = 0;
let activePanel = "details";
let activeView = "graph";
let zoom = 1;
let dataVisible = false;
let toastTimer;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function blocks() {
  return chainState?.chain ?? [];
}

function selectedBlock() {
  return blocks().find((block) => block.index === selectedIndex) ?? blocks()[0] ?? null;
}

function blockAlias(block) {
  return block.index === 0 ? "GENESIS" : `BLOC-${String(block.index).padStart(4, "0")}`;
}

function hashAlias(hash) {
  return hash ? `0x${hash.slice(0, 8).toUpperCase()}` : "—";
}

function shortDate(timestamp) {
  return new Date(timestamp * 1000).toLocaleString("fr-FR", {
    dateStyle: "short",
    timeStyle: "medium"
  });
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2800);
}

function formatValue(alias, raw = alias) {
  const displayed = dataVisible ? raw : alias;
  return `<span class="sensitive-value" data-alias="${escapeHtml(alias)}" data-raw="${escapeHtml(raw)}">${escapeHtml(displayed)}</span>`;
}

function detailRow(label, alias, raw = alias, copy = false) {
  const value = formatValue(alias, raw);
  const content = copy
    ? `<span class="copy-value">${value}<button type="button" data-copy-alias="${escapeHtml(alias)}" data-copy-raw="${escapeHtml(raw)}" aria-label="Copier ${escapeHtml(label)}"><img src="./assets/copy.svg" alt="" /></button></span>`
    : value;
  return `<div class="detail-row"><span>${escapeHtml(label)}</span><strong>${content}</strong></div>`;
}

function renderMetrics() {
  const allBlocks = blocks();
  const transactionBlocks = allBlocks.filter((block) => block.data?.type === "transaction");
  const timestamps = allBlocks.slice(1).map((block) => block.timestamp);
  const intervals = timestamps.slice(1).map((timestamp, index) => timestamp - timestamps[index]);
  const averageInterval = intervals.length
    ? `${(intervals.reduce((sum, interval) => sum + interval, 0) / intervals.length).toFixed(1)} s`
    : "—";

  document.querySelector("#metric-blocks").textContent = String(allBlocks.length);
  document.querySelector("#metric-blocks-note").textContent =
    `${allBlocks.length} bloc${allBlocks.length === 1 ? "" : "s"} dans le registre`;
  document.querySelector("#metric-transactions").textContent = String(transactionBlocks.length);
  document.querySelector("#metric-transactions-note").textContent = "Transactions confirmées dans la chaîne";
  document.querySelector("#metric-interval").textContent = averageInterval;
  document.querySelector("#metric-validity").textContent = chainState.valid ? "Valide" : "Invalide";
  document.querySelector("#metric-validity-note").textContent = chainState.valid
    ? `Travail cumulé · ${chainState.total_work}`
    : `${chainState.errors.length} anomalie${chainState.errors.length === 1 ? "" : "s"} détectée${chainState.errors.length === 1 ? "" : "s"}`;
  document.querySelector("#chain-count").textContent =
    `${allBlocks.length} bloc${allBlocks.length === 1 ? "" : "s"}`;
  document.querySelector("#validation-title").textContent =
    chainState.valid ? "Registre intègre" : "Registre invalide";
  document.querySelector("#validation-note").textContent = chainState.valid
    ? "Les empreintes SHA-256 et les liens entre tous les blocs ont été vérifiés."
    : chainState.errors.join(" ");
  document.querySelector("#integrity-summary").textContent = chainState.valid
    ? "Toutes les empreintes et liaisons sont cohérentes"
    : chainState.errors[0] ?? "La chaîne est invalide";

  const connection = document.querySelector("#connection-status");
  connection.classList.toggle("is-error", !chainState.valid);
  connection.innerHTML = `<i></i>${chainState.valid ? "Nœud local · connecté" : "Registre invalide"}`;
}

function renderGraph() {
  const allBlocks = blocks();
  graphStage.querySelectorAll(".block-node, .chain-edge, .edge, .signal").forEach((item) => item.remove());
  graphStage.style.width = `${Math.max(1080, 220 + allBlocks.length * 190)}px`;
  graphStage.style.height = "440px";
  document.querySelector("#graph-filter-count").textContent =
    `${allBlocks.length} bloc${allBlocks.length === 1 ? "" : "s"} · données réelles`;
  graphStage.querySelector(".reading-area").style.display = "none";
  graphStage.querySelector(".selection-field").style.display = "none";
  document.querySelector("#link-proof-title").textContent = "CHAÎNE SHA-256";
  document.querySelector("#link-proof-copy").textContent = `${allBlocks.length} bloc${allBlocks.length === 1 ? "" : "s"} relié${allBlocks.length === 1 ? "" : "s"} par leurs empreintes`;

  allBlocks.forEach((block, position) => {
    const left = 55 + position * 190;
    const isSelected = block.index === selectedIndex;
    if (position > 0) {
      const edge = document.createElement("span");
      edge.className = "chain-edge";
      edge.style.left = `${left - 48}px`;
      edge.style.top = "264px";
      edge.setAttribute("aria-hidden", "true");
      graphStage.append(edge);
    }

    const node = document.createElement("button");
    node.type = "button";
    node.className = `block-node${isSelected ? " is-current" : ""}`;
    node.dataset.blockIndex = String(block.index);
    node.style.left = `${left}px`;
    node.style.top = "190px";
    node.setAttribute("aria-label", `Sélectionner le bloc ${blockAlias(block)}`);
    node.setAttribute("aria-pressed", String(isSelected));
    node.innerHTML = `
      <span class="block-parent">${block.index === 0 ? "BLOC INITIAL" : `BLOC ${block.index}`}</span>
      <span class="block-body">
        <span class="block-top"><b>${escapeHtml(blockAlias(block))}</b><img src="./assets/${chainState.valid ? "etatDuBloc.svg" : "indicateur.svg"}" alt="${chainState.valid ? "Intègre" : "À vérifier"}" /></span>
        <span class="block-alias">${escapeHtml(hashAlias(block.hash))}</span>
        <span class="block-summary">${block.data?.type === "transaction" ? "1 transaction" : "genesis"} <img src="./assets/link.svg" alt="" /></span>
      </span>
      <span class="block-previous">${block.index === 0 ? "origine de la chaîne" : `préc. ${escapeHtml(blockAlias(allBlocks[position - 1]))}`}</span>`;
    node.addEventListener("click", () => selectBlock(block.index));
    graphStage.append(node);
  });

  const current = selectedBlock();
  document.querySelector("#link-proof-value").innerHTML =
    `<i></i>${escapeHtml(current ? blockAlias(current) : "—")}`;
  document.querySelector("#integrity-selected").innerHTML =
    `<i></i>${escapeHtml(current ? blockAlias(current) : "—")}`;
  setZoom(zoom);
  renderAlternateView();
}

function renderTransactions(query = "") {
  const block = selectedBlock();
  const selectedTransactions = block?.data?.type === "transaction"
    ? [{ block, data: block.data }]
    : [];
  const normalized = query.trim().toLocaleLowerCase("fr");
  const visible = selectedTransactions.filter(({ block: itemBlock, data }) =>
    [blockAlias(itemBlock), itemBlock.hash, data.sender, data.receiver, data.amount, data.currency]
      .some((value) => String(value ?? "").toLocaleLowerCase("fr").includes(normalized))
  );
  rows.innerHTML = visible.length
    ? visible.map(({ block: itemBlock, data }) => {
      const transactionId = `TX-${String(itemBlock.index).padStart(6, "0")}`;
      const amount = `${data.amount} ${data.currency}`;
      const size = `${new TextEncoder().encode(JSON.stringify(data)).length} B`;
      const ordinal = String(itemBlock.index).padStart(4, "0");
      return `
        <tr>
          <td>${escapeHtml(transactionId)}</td>
          <td>${formatValue(`EXP-${ordinal}`, data.sender)}</td>
          <td>${formatValue(`DEST-${ordinal}`, data.receiver)}</td>
          <td>${formatValue(`MONTANT-${ordinal}`, amount)}</td>
          <td>${formatValue(`${size} · données JSON`, size)}</td>
          <td><span class="transaction-status"><img src="./assets/indicateurDetat.svg" alt="" />Validée</span></td>
        </tr>`;
    }).join("")
    : `<tr><td class="empty-transactions" colspan="6">${normalized ? "Aucune transaction ne correspond à la recherche." : "Aucune transaction dans ce bloc."}</td></tr>`;

  const count = selectedTransactions.length;
  document.querySelector("#transaction-block").textContent = block ? blockAlias(block) : "—";
  document.querySelector("#block-transaction-count").textContent =
    `${count} transaction${count === 1 ? "" : "s"}`;
  document.querySelector("#transaction-count").textContent =
    `${visible.length} affichée${visible.length === 1 ? "" : "s"} · ${count} dans ce bloc`;
}

function renderInspector() {
  const block = selectedBlock();
  if (!block) {
    inspectorContent.textContent = "Aucun bloc à afficher.";
    return;
  }
  const allBlocks = blocks();
  const position = allBlocks.findIndex((item) => item.index === block.index);
  const parent = position > 0 ? allBlocks[position - 1] : null;
  const child = allBlocks[position + 1] ?? null;
  const alias = blockAlias(block);
  document.querySelector("#inspector-alias").textContent = alias;

  if (activePanel === "raw") {
    inspectorContent.innerHTML = `<pre class="raw-data">${escapeHtml(JSON.stringify(block, null, 2))}</pre>`;
    return;
  }

  const links = `
    <div class="detail-separator"></div>
    <div class="continuity-title">CONTINUITÉ DES EMPREINTES</div>
    <div class="continuity-cards">
      <div class="continuity-card"><span>Parent</span><strong>${escapeHtml(parent ? blockAlias(parent) : "Origine")}</strong><small>${escapeHtml(parent ? hashAlias(parent.hash) : "Aucun bloc précédent")}</small></div>
      <div class="continuity-card"><span>Enfant</span><strong>${escapeHtml(child ? blockAlias(child) : "Dernier bloc")}</strong><small>${escapeHtml(child ? hashAlias(child.hash) : "À jour")}</small></div>
    </div>
    <div class="consistency"><img src="./assets/checkCheck.svg" alt="" />${chainState.valid ? "Liaisons vérifiées par le nœud" : "La chaîne présente des anomalies"}</div>`;

  if (activePanel === "links") {
    inspectorContent.innerHTML = `
      <span class="eyebrow">LIENS DE LA CHAÎNE</span>
      ${detailRow("Bloc sélectionné", alias)}
      ${detailRow("Empreinte précédente", parent ? hashAlias(parent.hash) : "Aucune", parent?.hash ?? "Aucune", Boolean(parent))}
      ${links}`;
    return;
  }

  const transaction = block.data?.type === "transaction" ? block.data : null;
  inspectorContent.innerHTML = `
    ${detailRow("Index du bloc", alias)}
    ${detailRow("Empreinte SHA-256", hashAlias(block.hash), block.hash, true)}
    ${detailRow("Hash précédent", parent ? hashAlias(block.previous_hash) : "Aucune", block.previous_hash, Boolean(parent))}
    <div class="detail-separator"></div>
    ${detailRow("Horodatage", shortDate(block.timestamp))}
    ${detailRow("Nonce", String(block.nonce))}
    ${detailRow("Transactions", transaction ? "1" : "0")}
    ${transaction ? detailRow("Montant", `${transaction.amount} ${transaction.currency}`) : ""}
    ${links}`;
}

function renderAlternateView() {
  const alternate = document.querySelector("#alternate-view");
  const allBlocks = blocks();
  if (activeView === "graph") {
    alternate.hidden = true;
    graphStage.hidden = false;
    graphViewport.hidden = false;
    return;
  }

  graphStage.hidden = true;
  graphViewport.hidden = true;
  alternate.hidden = false;
  const items = allBlocks.map((block) => {
    const alias = blockAlias(block);
    const label = `${block.data?.type === "transaction" ? "1 transaction" : "Bloc initial"} · ${shortDate(block.timestamp)}`;
    return activeView === "list"
      ? `<button type="button" data-block-index="${block.index}"><span>${escapeHtml(alias)}</span><span>${escapeHtml(label)}</span></button>`
      : `<button type="button" data-block-index="${block.index}"><span>${escapeHtml(alias)}</span><br /><small>${escapeHtml(shortDate(block.timestamp))}</small></button>`;
  }).join("");
  alternate.innerHTML = activeView === "list"
    ? `<div class="list-view">${items}</div>`
    : `<div class="timeline-view">${items}</div>`;
}

function render() {
  if (!chainState) return;
  if (!blocks().some((block) => block.index === selectedIndex)) {
    selectedIndex = blocks().at(-1)?.index ?? 0;
  }
  renderMetrics();
  renderGraph();
  renderTransactions(searchInput.value);
  renderInspector();
}

function selectBlock(index) {
  if (!blocks().some((block) => block.index === index)) return;
  selectedIndex = index;
  render();
}

function setZoom(nextZoom) {
  zoom = Math.max(0.65, Math.min(1.25, nextZoom));
  graphStage.style.transform = `scale(${zoom})`;
  graphViewport.style.height = `${440 * zoom}px`;
  graphViewport.style.overflow = "auto";
  document.querySelector("#scale-label").textContent = `ÉCHELLE LIBRE · ${Math.round(zoom * 100)} %`;
}

function setView(view) {
  activeView = view;
  document.querySelectorAll(".view-tab").forEach((tab) => {
    const active = tab.dataset.view === view;
    tab.classList.toggle("is-selected", active);
    tab.setAttribute("aria-selected", String(active));
  });
  renderAlternateView();
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`Le nœud a répondu avec le statut ${response.status}.`);
  const nextState = await response.json();
  if (!Array.isArray(nextState.chain) || nextState.chain.length === 0) {
    throw new Error("Le nœud a retourné une chaîne vide ou invalide.");
  }
  chainState = nextState;
  render();
}

document.querySelectorAll(".view-tab").forEach((tab) => {
  tab.addEventListener("click", () => setView(tab.dataset.view));
});

document.querySelectorAll(".inspector-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    activePanel = tab.dataset.panel;
    document.querySelectorAll(".inspector-tab").forEach((item) => {
      const active = item === tab;
      item.classList.toggle("is-active", active);
      item.setAttribute("aria-selected", String(active));
    });
    renderInspector();
  });
});

document.querySelector("#alternate-view").addEventListener("click", (event) => {
  const item = event.target.closest("[data-block-index]");
  if (item) selectBlock(Number(item.dataset.blockIndex));
});

searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLocaleLowerCase("fr");
  document.querySelectorAll(".block-node").forEach((node) => {
    node.hidden = Boolean(query) && !node.textContent.toLocaleLowerCase("fr").includes(query);
  });
  renderTransactions(query);
});

document.querySelector("#visibility-toggle").addEventListener("click", () => {
  dataVisible = !dataVisible;
  const button = document.querySelector("#visibility-toggle");
  button.setAttribute("aria-pressed", String(dataVisible));
  button.querySelector(".visibility-state").textContent =
    dataVisible ? "Données visibles" : "Données masquées";
  button.querySelector("span:first-of-type").textContent =
    dataVisible ? "Masquer les données" : "Afficher les données";
  renderTransactions(searchInput.value);
  renderInspector();
});

document.querySelector("#zoom-in").addEventListener("click", () => setZoom(zoom + 0.1));
document.querySelector("#zoom-out").addEventListener("click", () => setZoom(zoom - 0.1));
document.querySelector("#zoom-reset").addEventListener("click", () => setZoom(1));

document.querySelector("#export-transactions").addEventListener("click", () => {
  const block = selectedBlock();
  const transaction = block?.data?.type === "transaction" ? block.data : null;
  const headings = ["bloc", "empreinte", "expediteur", "destinataire", "montant", "devise"];
  const data = transaction
    ? [[block.index, block.hash, transaction.sender, transaction.receiver, transaction.amount, transaction.currency]]
    : [];
  const csv = [headings, ...data]
    .map((row) => row.map((field) => `"${String(field).replaceAll('"', '""')}"`).join(","))
    .join("\r\n");
  const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `transactions-${block ? block.index : "registre"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
  showToast("Export CSV téléchargé");
});

document.querySelector("#new-transaction").addEventListener("click", () => transactionDialog.showModal());
document.querySelector("#close-transaction-dialog").addEventListener("click", () => transactionDialog.close());
document.querySelector("#cancel-transaction").addEventListener("click", () => transactionDialog.close());

transactionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = transactionForm.querySelector('[type="submit"]');
  submitButton.disabled = true;
  try {
    const formData = new FormData(transactionForm);
    const response = await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender: formData.get("sender"),
        receiver: formData.get("receiver"),
        amount: Number(formData.get("amount")),
        currency: formData.get("currency")
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error ?? `Erreur HTTP ${response.status}`);
    transactionDialog.close();
    transactionForm.reset();
    await loadState();
    selectedIndex = result.block.index;
    render();
    showToast(`Transaction ajoutée dans le bloc ${blockAlias(result.block)}`);
  } catch (error) {
    showToast(error instanceof Error ? error.message : "Impossible d’ajouter la transaction.");
  } finally {
    submitButton.disabled = false;
  }
});

document.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-alias]");
  if (!copyButton) return;
  try {
    await navigator.clipboard.writeText(dataVisible ? copyButton.dataset.copyRaw : copyButton.dataset.copyAlias);
    showToast("Valeur copiée");
  } catch {
    showToast("Copie indisponible dans ce contexte");
  }
});

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => {
      const active = item === button;
      item.classList.toggle("is-active", active);
      if (active) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });
    if (button.dataset.nav === "Transactions") {
      document.querySelector(".transaction-card").scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (button.dataset.nav === "Structure") {
      document.querySelector(".graph-card").scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      document.querySelector(".metrics").scrollIntoView({ behavior: "smooth", block: "start" });
      if (button.dataset.nav === "Mesures") showToast("Indicateurs calculés à partir de la chaîne locale");
    }
  });
});

document.querySelectorAll("#status-filter, #state-filter, #links-filter, #transaction-filter, .lab-select, .settings-button, .help-button, .inspector-header .icon-button").forEach((button) => {
  button.addEventListener("click", () => showToast("Aucun filtre supplémentaire n’est configuré."));
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    searchInput.focus();
  }
  if (event.key === "Escape" && document.activeElement === searchInput) {
    searchInput.value = "";
    searchInput.dispatchEvent(new Event("input"));
    searchInput.blur();
  }
});

window.addEventListener("resize", () => setZoom(zoom));

loadState().catch((error) => {
  const connection = document.querySelector("#connection-status");
  connection.classList.add("is-error");
  connection.innerHTML = "<i></i>Nœud indisponible";
  document.querySelector("#metric-validity").textContent = "Hors ligne";
  document.querySelector("#metric-validity-note").textContent =
    error instanceof Error ? error.message : "Connexion impossible.";
  showToast("Impossible de charger le registre local.");
});

setInterval(() => {
  loadState().catch(() => {
    document.querySelector("#connection-status").classList.add("is-error");
    document.querySelector("#connection-status").innerHTML = "<i></i>Nœud indisponible";
  });
}, 5000);
