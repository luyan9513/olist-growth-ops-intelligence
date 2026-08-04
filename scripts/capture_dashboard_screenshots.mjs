/** 使用 Chrome DevTools Protocol 截取已完全渲染的本地 Streamlit 页面。 */

import fs from "node:fs/promises";
import path from "node:path";

const DEBUG_BASE = process.env.OLIST_CHROME_DEBUG_URL || "http://127.0.0.1:9222";
const APP_BASE = process.env.OLIST_STREAMLIT_URL || "http://127.0.0.1:8767";
const OUTPUT_DIR = "docs/assets/portfolio";
const TARGETS = [
  ["/", "增长总览", "01_growth_overview.png"],
  ["/ops-actions", "商家运营行动", "02_seller_ops_actions.png"],
  ["/experiments", "实验设计", "03_experiment_design.png"],
  ["/quality", "数据质量", "04_data_quality.png"],
];

let nextId = 0;

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  return response.json();
}

async function openTarget(url) {
  return jsonRequest(`${DEBUG_BASE}/json/new?${encodeURIComponent(url)}`, {method: "PUT"});
}

async function closeTarget(id) {
  await fetch(`${DEBUG_BASE}/json/close/${id}`);
}

function connect(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl);
  const pending = new Map();
  const events = [];
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id) {
      if (message.method?.startsWith("Network.webSocket") || message.method === "Network.loadingFailed") {
        events.push({method: message.method, params: message.params});
        if (events.length > 20) events.shift();
      }
      return;
    }
    if (!pending.has(message.id)) return;
    const {resolve, reject} = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(JSON.stringify(message.error)));
    else resolve(message.result);
  };
  const ready = new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });
  return {
    ready,
    events,
    close: () => socket.close(),
    send: async (method, params = {}) => {
      await ready;
      const id = ++nextId;
      const result = new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
      socket.send(JSON.stringify({id, method, params}));
      return result;
    },
  };
}

async function waitForHeading(cdp, heading, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await cdp.send("Runtime.evaluate", {
      expression: `Array.from(document.querySelectorAll('h1')).some(node => node.textContent.includes(${JSON.stringify(heading)}))`,
      returnByValue: true,
    });
    if (result.result.value === true) return;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  const diagnostic = await cdp.send("Runtime.evaluate", {
    expression: "JSON.stringify({readyState: document.readyState, title: document.title, url: location.href, body: document.body.innerText.slice(0, 500)})",
    returnByValue: true,
  });
  throw new Error(`页面在 ${timeoutMs}ms 内未显示标题：${heading}；诊断=${diagnostic.result.value}；网络=${JSON.stringify(cdp.events)}`);
}

async function waitForStablePage(cdp, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let stableChecks = 0;
  while (Date.now() < deadline) {
    const result = await cdp.send("Runtime.evaluate", {
      expression: `(() => {
        const skeletons = document.querySelectorAll('[data-testid="stSkeleton"]').length;
        const running = document.querySelectorAll('[data-testid="stStatusWidget"]').length;
        return {skeletons, running, height: document.documentElement.scrollHeight};
      })()`,
      returnByValue: true,
    });
    const state = result.result.value;
    stableChecks = state.skeletons === 0 && state.running === 0 ? stableChecks + 1 : 0;
    if (stableChecks >= 2) {
      await cdp.send("Runtime.evaluate", {expression: "window.scrollTo(0, 0)"});
      await new Promise(resolve => setTimeout(resolve, 750));
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`页面组件在 ${timeoutMs}ms 内未稳定`);
}

async function capture(route, heading, filename) {
  const target = await openTarget(`${APP_BASE}${route}`);
  const cdp = connect(target.webSocketDebuggerUrl);
  try {
    await cdp.ready;
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false,
    });
    await waitForHeading(cdp, heading);
    await waitForStablePage(cdp);
    const layout = await cdp.send("Page.getLayoutMetrics");
    const contentSize = layout.cssContentSize || layout.contentSize;
    const screenshot = await cdp.send("Page.captureScreenshot", {
      format: "png", captureBeyondViewport: true,
      clip: {x: 0, y: 0, width: 1440, height: Math.max(1000, Math.ceil(contentSize.height)), scale: 1},
    });
    const output = path.join(OUTPUT_DIR, filename);
    await fs.writeFile(output, Buffer.from(screenshot.data, "base64"));
    return {file: output, heading, width: 1440, height: Math.max(1000, Math.ceil(contentSize.height))};
  } finally {
    cdp.close();
    await closeTarget(target.id);
  }
}

await fs.mkdir(OUTPUT_DIR, {recursive: true});
const results = [];
for (const target of TARGETS) results.push(await capture(...target));
console.log(JSON.stringify({status: "ok", screenshots: results}, null, 2));
