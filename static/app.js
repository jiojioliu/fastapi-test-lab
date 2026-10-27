const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const storageKeys = {
  token: "fastapi-lab-token",
  user: "fastapi-lab-user",
};

const restoredUser = readStoredUser();

const state = {
  token: localStorage.getItem(storageKeys.token) || "",
  user: restoredUser,
  products: [],
  cart: readStoredCart(restoredUser),
  lastTraffic: null,
  catalogLoaded: false,
  healthTimer: null,
  trafficTimer: null,
  currentOrderId: null,
};

const roleLabels = {
  customer: "普通用户",
  admin: "管理员",
  guest: "访客用户",
};

const roleDescriptions = {
  customer: "商城访问 · 独立购物车与个人订单",
  admin: "管理员测试账户 · 控制台 · 网络实验室 · 全部订单",
  guest: "目录只读访问 · 不可创建订单",
};

const paymentLabels = {
  alipay: "支付宝",
  wechat: "微信支付",
  bank_card: "银行卡",
};

const orderStatusLabels = {
  pending: "待处理",
  confirmed: "已确认",
  shipped: "配送中",
  completed: "已完成",
  cancelled: "已取消",
};

const viewMetadata = {
  overview: ["运行概览", "LOCAL SERVICE / LIVE"],
  console: ["API 控制台", "REQUEST BUILDER / RAW"],
  catalog: ["商品目录", "REST / PAGINATION / SEARCH"],
  orders: ["订单工作台", "AUTH / IDEMPOTENCY / OWNERSHIP"],
  "order-detail": ["订单详情", "ORDER DETAILS / SECURE"],
  lab: ["网络实验室", "FAILURE / LATENCY / OBSERVATION"],
  guides: ["工具指南", "WORKFLOW / ARTIFACTS / FILTERS"],
};

const requestPresets = {
  health: {
    method: "GET",
    path: "/api/health",
    body: "",
    headers: {},
  },
  products: {
    method: "GET",
    path: "/api/products?search=key&sort=rating&page_size=8",
    body: "",
    headers: {},
  },
  login: {
    method: "POST",
    path: "/api/auth/login",
    body: { username: "admin", password: "admin123" },
    headers: { "X-Training-Source": "interactive-console" },
  },
  orders: {
    method: "GET",
    path: "/api/orders?page=1&page_size=12",
    body: "",
    headers: {},
  },
  "create-order": {
    method: "POST",
    path: "/api/orders",
    body: {
      items: [{ product_id: 1, quantity: 1 }],
      note: "Created from the interactive console",
    },
    headers: { "Idempotency-Key": "console-order-demo-001" },
  },
  echo: {
    method: "POST",
    path: "/api/lab/echo?source=console&lesson=inspection",
    body: { message: "hello test lab", active: true },
    headers: { "X-Training-Mode": "postman" },
  },
  slow: {
    method: "GET",
    path: "/api/lab/slow?delay_ms=1200",
    body: "",
    headers: {},
  },
  status500: {
    method: "GET",
    path: "/api/lab/status/500",
    body: "",
    headers: {},
  },
  upload: {
    method: "POST",
    path: "/api/lab/upload",
    body: { note: "Use multipart upload in the Network Lab or Postman" },
    headers: {},
  },
};

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(storageKeys.user) || "null");
  } catch {
    return null;
  }
}

function cartStorageKey(user = state.user) {
  return user ? `fastapi-lab-cart:${user.id}:${user.username}` : "fastapi-lab-cart:guest";
}

function readStoredCart(user = null) {
  try {
    const value = JSON.parse(localStorage.getItem(cartStorageKey(user)) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function canUseTestLab(user = state.user) {
  return !user || user.role === "admin";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function formatMoney(value) {
  return `¥${Number(value || 0).toFixed(2)}`;
}

function statusClass(statusCode) {
  if (statusCode >= 500) return "server-error";
  if (statusCode >= 400) return "client-error";
  if (statusCode >= 300) return "redirect";
  if (statusCode >= 200) return "success";
  return "idle";
}

function statusDigitClass(statusCode) {
  return `s${String(statusCode).charAt(0)}`;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  if (
    options.body &&
    typeof options.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  const started = performance.now();
  const response = await fetch(path, { ...options, headers });
  const elapsed = performance.now() - started;
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (
    response.status === 401 &&
    state.token &&
    !path.startsWith("/api/auth/")
  ) {
    clearSession(false);
  }
  return { response, data, text, elapsed };
}

function toast(message, type = "success") {
  const region = $("#toast-region");
  const node = document.createElement("div");
  node.className = `toast ${type === "error" ? "error" : ""}`;
  node.textContent = message;
  region.append(node);
  window.setTimeout(() => {
    node.style.opacity = "0";
    node.style.transform = "translateY(5px)";
    window.setTimeout(() => node.remove(), 200);
  }, 3200);
}

function showView(viewName, updateHash = true) {
  let nextView = viewMetadata[viewName] ? viewName : "overview";
  if (
    ["overview", "console", "lab"].includes(nextView) &&
    state.user &&
    !canUseTestLab()
  ) {
    nextView = state.user.role === "guest" ? "catalog" : "orders";
    toast("测试控制台与流量数据仅对管理员测试账户开放", "error");
  }
  if (
    ["orders", "order-detail"].includes(nextView) &&
    state.user?.role === "guest"
  ) {
    nextView = "catalog";
    toast("访客账户仅可浏览商品目录", "error");
  }
  if (nextView === "guides" && state.user?.role !== "admin") {
    nextView = canUseTestLab() ? "overview" : "catalog";
    toast("工具指南仅对管理员测试账户开放", "error");
  }
  $$(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${nextView}`);
  });
  const activeNavView =
    nextView === "order-detail" ? "orders" : nextView;
  $$(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === activeNavView);
  });
  const [title, eyebrow] = viewMetadata[nextView];
  $("#page-title").textContent = title;
  $("#page-eyebrow").textContent = eyebrow;
  $("#sidebar").classList.remove("open");
  if (updateHash) {
    if (nextView === "orders") {
      const target = "/orders";
      if (window.location.pathname !== target) {
        history.pushState({ view: nextView }, "", target);
      }
    } else if (nextView !== "order-detail") {
      const target = `/#${nextView}`;
      if (window.location.pathname !== "/" || window.location.hash !== `#${nextView}`) {
        history.pushState({ view: nextView }, "", target);
      }
    }
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (nextView === "catalog" && !state.catalogLoaded) loadCatalog();
  if (nextView === "orders" && state.user) loadOrders();
}

function defaultViewForRole() {
  return canUseTestLab() ? "overview" : "catalog";
}

function showAuthGate() {
  stopPolling();
  $("#app-shell").hidden = true;
  $("#auth-shell").hidden = false;
  document.body.classList.remove("is-authenticated");
  document.title = "Northstar Goods · 账户登录";
  setAuthMode("login");
  $("#auth-login-error").hidden = true;
  $("#guest-entry-error").hidden = true;
}

async function enterApplication(preferredView = null) {
  if (!state.user || !state.token) {
    showAuthGate();
    return;
  }
  $("#auth-shell").hidden = true;
  $("#app-shell").hidden = false;
  document.body.classList.add("is-authenticated");
  applyRoleBranding();
  showView(preferredView || defaultViewForRole(), false);
  await Promise.all([
    refreshHealth(),
    loadCatalog(),
    state.user.role === "guest" ? Promise.resolve() : loadOrders(),
  ]);
  if (canUseTestLab()) {
    await refreshTraffic();
    if (state.user.role === "admin") syncGuideChecklist();
  }
  startPolling();
}

function startPolling() {
  stopPolling();
  state.healthTimer = window.setInterval(refreshHealth, 15000);
  if (canUseTestLab()) {
    state.trafficTimer = window.setInterval(refreshTraffic, 2500);
  }
}

function stopPolling() {
  if (state.healthTimer) window.clearInterval(state.healthTimer);
  if (state.trafficTimer) window.clearInterval(state.trafficTimer);
  state.healthTimer = null;
  state.trafficTimer = null;
}

function bindNavigation() {
  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => showView(item.dataset.view));
  });
  $$("[data-go]").forEach((item) => {
    item.addEventListener("click", () => showView(item.dataset.go));
  });
  $("#menu-button").addEventListener("click", () => {
    $("#sidebar").classList.toggle("open");
  });
  document.addEventListener("click", (event) => {
    if (
      window.innerWidth <= 720 &&
      $("#sidebar").classList.contains("open") &&
      !$("#sidebar").contains(event.target) &&
      !$("#menu-button").contains(event.target)
    ) {
      $("#sidebar").classList.remove("open");
    }
  });
  window.addEventListener("popstate", () => {
    applyLocationRoute(false);
  });
}

function routeFromLocation() {
  const detailMatch = window.location.pathname.match(/^\/orders\/([^/]+)\/?$/);
  if (detailMatch) {
    return {
      view: "order-detail",
      orderId: decodeURIComponent(detailMatch[1]),
    };
  }
  if (window.location.pathname === "/orders" || window.location.pathname === "/orders/") {
    return { view: "orders" };
  }
  const hashView = window.location.hash.slice(1);
  return {
    view: viewMetadata[hashView] ? hashView : "overview",
  };
}

async function applyLocationRoute(updateUrl = false) {
  const route = routeFromLocation();
  if (route.view === "order-detail") {
    await showOrderDetail(route.orderId, updateUrl);
    return;
  }
  showView(route.view, updateUrl);
}

async function enterRequestedRoute() {
  const route = routeFromLocation();
  await enterApplication(
    route.view === "order-detail" ? "orders" : route.view,
  );
  if (route.view === "order-detail" && state.user?.role !== "guest") {
    await showOrderDetail(route.orderId, false);
  }
}

async function refreshHealth() {
  try {
    const { response, data } = await request("/api/health");
    if (!response.ok) throw new Error("Health check failed");
    $("#sidebar-status").textContent = "服务在线";
    $("#sidebar-status-dot").classList.remove("offline");
    $("#live-label").textContent = `v${data.version || "1.0"} LIVE`;
  } catch {
    $("#sidebar-status").textContent = "服务离线";
    $("#sidebar-status-dot").classList.add("offline");
    $("#live-label").textContent = "OFFLINE";
    $(".live-chip .pulse-dot").classList.add("offline");
  }
}

async function refreshTraffic() {
  try {
    const { response, data } = await request("/api/traffic/summary?recent_limit=40");
    if (!response.ok) throw new Error("Traffic request failed");
    state.lastTraffic = data;
    renderTraffic(data);
  } catch {
    $("#sidebar-status").textContent = "模板连接中断";
    $("#sidebar-status-dot").classList.add("offline");
  }
}

function renderTraffic(data) {
  const summary = data.summary;
  $("#metric-total").textContent = formatNumber(summary.total_requests);
  $("#metric-rpm").textContent = formatNumber(summary.requests_last_minute);
  $("#metric-rps").textContent = Number(summary.requests_per_second).toFixed(2);
  $("#metric-p95").textContent = Number(summary.p95_latency_ms).toFixed(0);
  $("#metric-p99").textContent = Number(summary.p99_latency_ms).toFixed(0);
  $("#metric-errors").textContent = Number(summary.error_rate).toFixed(2);
  $("#metric-active").textContent = formatNumber(summary.active_requests);

  const timeline = data.timeline || [];
  const total = timeline.reduce((sum, item) => sum + item.count, 0);
  $("#chart-empty").hidden = total > 0;
  drawTrafficChart(timeline);

  const distribution = data.status_distribution || {};
  const groups = { ok: 0, redirect: 0, client: 0, server: 0 };
  Object.entries(distribution).forEach(([code, count]) => {
    const digit = Number(code.charAt(0));
    if (digit === 2) groups.ok += count;
    else if (digit === 3) groups.redirect += count;
    else if (digit === 4) groups.client += count;
    else if (digit === 5) groups.server += count;
  });
  const totalStatus = Object.values(groups).reduce((sum, count) => sum + count, 0);
  $("#status-total").textContent = formatNumber(totalStatus);
  $("#status-legend").innerHTML = `
    <span><i class="legend-dot ok"></i>2xx <b>${formatNumber(groups.ok)}</b></span>
    <span><i class="legend-dot redirect"></i>3xx <b>${formatNumber(groups.redirect)}</b></span>
    <span><i class="legend-dot client"></i>4xx <b>${formatNumber(groups.client)}</b></span>
    <span><i class="legend-dot server"></i>5xx <b>${formatNumber(groups.server)}</b></span>
  `;
  drawStatusChart(groups);
  renderRecentRequests(data.recent || []);
}

function prepareCanvas(canvas) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.round(width * ratio));
  canvas.height = Math.max(1, Math.round(height * ratio));
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function cssVariable(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function drawTrafficChart(timeline) {
  const canvas = $("#traffic-chart");
  if (!canvas.clientWidth) return;
  const { context: ctx, width, height } = prepareCanvas(canvas);
  ctx.clearRect(0, 0, width, height);
  const padding = { top: 17, right: 9, bottom: 23, left: 30 };
  const chartWidth = Math.max(1, width - padding.left - padding.right);
  const chartHeight = Math.max(1, height - padding.top - padding.bottom);
  const maxValue = Math.max(5, ...timeline.map((item) => item.count));

  ctx.font = '8px "Cascadia Code", Consolas, monospace';
  ctx.fillStyle = cssVariable("--text-tertiary");
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  for (let row = 0; row <= 4; row += 1) {
    const value = Math.round((maxValue / 4) * (4 - row));
    const y = padding.top + (chartHeight / 4) * row;
    ctx.strokeStyle = cssVariable("--border");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(value), 1, y);
  }

  if (!timeline.length) {
    ctx.fillStyle = cssVariable("--text-tertiary");
    ctx.textAlign = "center";
    ctx.fillText("Waiting for traffic", width / 2, height / 2);
    return;
  }

  const pointX = (index) =>
    padding.left + (index / Math.max(1, timeline.length - 1)) * chartWidth;
  const pointY = (value) =>
    padding.top + chartHeight - (value / maxValue) * chartHeight;

  const gradient = ctx.createLinearGradient(0, padding.top, 0, height);
  gradient.addColorStop(0, `rgba(${cssVariable("--accent-rgb")}, 0.2)`);
  gradient.addColorStop(1, `rgba(${cssVariable("--accent-rgb")}, 0)`);
  ctx.beginPath();
  timeline.forEach((item, index) => {
    const x = pointX(index);
    const y = pointY(item.count);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(pointX(timeline.length - 1), padding.top + chartHeight);
  ctx.lineTo(pointX(0), padding.top + chartHeight);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  timeline.forEach((item, index) => {
    const x = pointX(index);
    const y = pointY(item.count);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = cssVariable("--accent");
  ctx.lineWidth = 1.7;
  ctx.stroke();

  timeline.forEach((item, index) => {
    if (item.count === 0) return;
    const x = pointX(index);
    const y = pointY(item.count);
    ctx.beginPath();
    ctx.arc(x, y, 2.1, 0, Math.PI * 2);
    ctx.fillStyle = cssVariable("--accent");
    ctx.fill();
    if (item.errors > 0) {
      ctx.beginPath();
      ctx.arc(x, y, 3.8, 0, Math.PI * 2);
      ctx.strokeStyle = cssVariable("--error");
      ctx.lineWidth = 1.3;
      ctx.stroke();
    }
  });

  ctx.fillStyle = cssVariable("--text-tertiary");
  ctx.textAlign = "center";
  [0, Math.floor(timeline.length / 2), timeline.length - 1].forEach((index) => {
    ctx.fillText(timeline[index].label, pointX(index), height - 6);
  });
}

function drawStatusChart(groups) {
  const canvas = $("#status-chart");
  if (!canvas.clientWidth) return;
  const { context: ctx, width, height } = prepareCanvas(canvas);
  ctx.clearRect(0, 0, width, height);
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2 - 8;
  const values = [
    { value: groups.ok, color: cssVariable("--success") },
    { value: groups.redirect, color: cssVariable("--warning") },
    { value: groups.client, color: cssVariable("--info") },
    { value: groups.server, color: cssVariable("--error") },
  ];
  const total = values.reduce((sum, item) => sum + item.value, 0);
  ctx.lineWidth = 9;
  ctx.lineCap = "butt";
  if (!total) {
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.strokeStyle = cssVariable("--border");
    ctx.stroke();
    return;
  }
  let start = -Math.PI / 2;
  values.forEach((item) => {
    if (!item.value) return;
    const end = start + (item.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, start + 0.025, end - 0.025);
    ctx.strokeStyle = item.color;
    ctx.stroke();
    start = end;
  });
}

function renderRecentRequests(entries) {
  const body = $("#recent-requests");
  if (!entries.length) {
    body.innerHTML = `
      <tr class="empty-row">
        <td colspan="6">还没有请求记录。打开 API 控制台开始测试。</td>
      </tr>
    `;
    return;
  }
  body.innerHTML = entries
    .map(
      (entry) => `
        <tr>
          <td>${formatTime(entry.timestamp)}</td>
          <td><span class="method ${escapeHtml(entry.method.toLowerCase())}">${escapeHtml(entry.method)}</span></td>
          <td>${escapeHtml(entry.path)}</td>
          <td><span class="status-code ${statusDigitClass(entry.status)}">${entry.status}</span></td>
          <td>${Number(entry.duration_ms).toFixed(1)} ms</td>
          <td>${escapeHtml(entry.request_id)}</td>
        </tr>
      `,
    )
    .join("");
}

async function clearTraffic() {
  try {
    const { response } = await request("/api/traffic/clear", { method: "DELETE" });
    if (!response.ok) throw new Error();
    await refreshTraffic();
    toast("流量统计已清空");
  } catch {
    toast("清空流量失败", "error");
  }
}

async function loadCatalog() {
  const search = $("#catalog-search").value.trim();
  const category = $("#catalog-category").value;
  const sort = $("#catalog-sort").value;
  const params = new URLSearchParams({
    sort,
    page: "1",
    page_size: "24",
  });
  if (search) params.set("search", search);
  if (category) params.set("category", category);
  try {
    const { response, data } = await request(`/api/products?${params}`);
    if (!response.ok) throw new Error(data?.detail || "商品加载失败");
    state.products = data.items;
    state.catalogLoaded = true;
    renderCategories(data.categories || []);
    renderCatalog(data.items);
  } catch (error) {
    $("#catalog-grid").innerHTML = `
      <div class="empty-block" style="grid-column:1/-1">
        <strong>商品加载失败</strong><span>${escapeHtml(error.message)}</span>
      </div>
    `;
  }
}

function renderCategories(categories) {
  const select = $("#catalog-category");
  const selected = select.value;
  select.innerHTML =
    '<option value="">全部分类</option>' +
    categories
      .map(
        (category) =>
          `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`,
      )
      .join("");
  if (categories.includes(selected)) select.value = selected;
}

function renderCatalog(products) {
  const grid = $("#catalog-grid");
  const canPurchase = state.user?.role !== "guest";
  if (!products.length) {
    grid.innerHTML = `
      <div class="empty-block" style="grid-column:1/-1">
        <strong>没有匹配的商品</strong><span>调整搜索词或分类后重试</span>
      </div>
    `;
    return;
  }
  grid.innerHTML = products
    .map(
      (product) => `
        <article class="product-card" style="--accent:${escapeHtml(product.accent)}">
          <div class="product-topline">
            <span class="sku">${escapeHtml(product.sku)}</span>
            <span class="rating">★ ${Number(product.rating).toFixed(1)}</span>
          </div>
          <div class="product-visual"><span class="product-glyph"></span></div>
          <span class="product-category">${escapeHtml(product.category)}</span>
          <h3>${escapeHtml(product.name)}</h3>
          <p>${escapeHtml(product.description)}</p>
          <div class="product-bottom">
            <div class="product-price">${formatMoney(product.price)}<small>库存 ${product.stock}</small></div>
            ${
              canPurchase
                ? `<button class="add-cart" data-product-id="${product.id}" title="加入购物车" aria-label="将 ${escapeHtml(product.name)} 加入购物车">＋</button>`
                : '<span class="read-only-note">访客只读</span>'
            }
          </div>
        </article>
      `,
    )
    .join("");
  $$(".add-cart", grid).forEach((button) => {
    button.addEventListener("click", () => addToCart(Number(button.dataset.productId)));
  });
}

function addToCart(productId) {
  if (!state.user || state.user.role === "guest") {
    toast("访客账户为只读模式", "error");
    return;
  }
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;
  const line = state.cart.find((item) => item.product_id === productId);
  if (line) {
    line.quantity = Math.min(20, line.quantity + 1);
  } else {
    state.cart.push({
      product_id: productId,
      name: product.name,
      price: product.price,
      quantity: 1,
    });
  }
  persistCart();
  renderCart();
  toast(`${product.name} 已加入购物车`);
}

function persistCart() {
  localStorage.setItem(cartStorageKey(), JSON.stringify(state.cart));
}

function renderCart() {
  const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  const navCount = $("#cart-nav-count");
  navCount.hidden = count === 0;
  navCount.textContent = String(count);
  $("#cart-count-label").textContent = `${count} 件商品`;
  const items = $("#cart-items");
  if (!state.cart.length) {
    items.innerHTML = `
      <div class="cart-empty">
        <span>◇</span><p>购物车为空</p><a href="#catalog" data-go-cart>去商品目录看看</a>
      </div>
    `;
    $("#cart-total-row").hidden = true;
    $("#checkout-button").disabled = true;
    $("[data-go-cart]")?.addEventListener("click", (event) => {
      event.preventDefault();
      showView("catalog");
    });
    return;
  }
  items.innerHTML = state.cart
    .map(
      (item) => `
        <div class="cart-line">
          <div><strong>${escapeHtml(item.name)}</strong><small>${formatMoney(item.price)} / 件</small></div>
          <div class="quantity-control">
            <button data-cart-action="minus" data-product-id="${item.product_id}">−</button>
            <span>${item.quantity}</span>
            <button data-cart-action="plus" data-product-id="${item.product_id}">＋</button>
          </div>
          <span class="cart-price">${formatMoney(item.price * item.quantity)}</span>
        </div>
      `,
    )
    .join("");
  const subtotal = state.cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0,
  );
  const tax = Math.round(subtotal * 0.06 * 100) / 100;
  $("#cart-subtotal").textContent = formatMoney(subtotal);
  $("#cart-tax").textContent = formatMoney(tax);
  $("#cart-total").textContent = formatMoney(subtotal + tax);
  $("#cart-total-row").hidden = false;
  $("#checkout-button").disabled = false;
  $("#checkout-button").textContent = "去结算";
  $$("[data-cart-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const productId = Number(button.dataset.productId);
      const line = state.cart.find((item) => item.product_id === productId);
      if (!line) return;
      if (button.dataset.cartAction === "plus") {
        line.quantity = Math.min(20, line.quantity + 1);
      } else {
        line.quantity -= 1;
        if (line.quantity <= 0) {
          state.cart = state.cart.filter((item) => item.product_id !== productId);
        }
      }
      persistCart();
      renderCart();
    });
  });
}

async function login(username, password, errorNode) {
  if (errorNode) {
    errorNode.hidden = true;
    errorNode.textContent = "";
  }
  try {
    const { response, data } = await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) throw new Error(data?.detail || "登录失败");
    saveSession(data);
    await enterRequestedRoute();
    toast(`已登录为 ${data.user.display_name}`);
    return true;
  } catch (error) {
    if (errorNode) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } else {
      toast(error.message, "error");
    }
    return false;
  }
}

function saveSession(payload) {
  state.token = payload.access_token;
  state.user = payload.user;
  state.cart = readStoredCart(state.user);
  localStorage.setItem(storageKeys.token, state.token);
  localStorage.setItem(storageKeys.user, JSON.stringify(state.user));
  renderCart();
  updateAuthUI();
}

async function restoreSession() {
  updateAuthUI();
  if (!state.token) return false;
  try {
    const { response, data } = await request("/api/auth/me");
    if (!response.ok) throw new Error();
    state.user = data;
    state.cart = readStoredCart(state.user);
    localStorage.setItem(storageKeys.user, JSON.stringify(data));
    renderCart();
    updateAuthUI();
    return true;
  } catch {
    clearSession(false);
    return false;
  }
}

function clearSession(notify = true) {
  if ($("#account-dialog")?.open) $("#account-dialog").close();
  if ($("#payment-dialog")?.open) $("#payment-dialog").close();
  state.token = "";
  state.user = null;
  state.cart = readStoredCart(null);
  localStorage.removeItem(storageKeys.token);
  localStorage.removeItem(storageKeys.user);
  renderCart();
  updateAuthUI();
  renderOrders(null);
  showAuthGate();
  if (notify) toast("已退出登录");
}

function updateAuthUI() {
  const loggedIn = Boolean(state.user);
  $("#account-label").textContent = loggedIn ? state.user.display_name : "未登录";
  $("#account-avatar").textContent = loggedIn
    ? (state.user.display_name || state.user.username).charAt(0).toUpperCase()
    : "G";
  $("#console-auth-state").textContent = loggedIn
    ? `已登录 · ${state.user.username} · Bearer JWT`
    : "未登录 · 公开接口可用";
  $("#orders-auth-state").textContent = loggedIn
    ? `会话有效 · ${roleLabels[state.user.role] || state.user.role}`
    : "需要登录";
  const hideTestTools = loggedIn && !canUseTestLab();
  const hideCommerce = loggedIn && state.user.role === "guest";
  const hideGuides = loggedIn && state.user.role !== "admin";
  $$("[data-test-only]").forEach((element) => {
    element.hidden = hideTestTools;
  });
  $$("[data-commerce-only]").forEach((element) => {
    element.hidden = hideCommerce;
  });
  $$("[data-guide-only]").forEach((element) => {
    element.hidden = hideGuides;
  });
  const role = loggedIn ? state.user.role : "guest";
  const badge = $("#account-role");
  badge.textContent = loggedIn ? role.toUpperCase() : "SIGNED OUT";
  badge.className = `role-badge ${role}`;
  if (loggedIn) {
    $("#dialog-profile-avatar").textContent = (
      state.user.display_name || state.user.username
    ).charAt(0).toUpperCase();
    $("#dialog-profile-name").textContent = state.user.display_name;
    $("#dialog-profile-username").textContent =
      `@${state.user.username} · ID ${state.user.id}`;
    $("#dialog-profile-role").textContent = state.user.role.toUpperCase();
    $("#dialog-profile-role").className = `role-badge ${state.user.role}`;
    $("#dialog-profile-permission").textContent =
      roleDescriptions[state.user.role] || "受限访问";
  }
  const appIsVisible = !$("#app-shell").hidden;
  if (
    appIsVisible &&
    hideTestTools &&
    ["overview", "console", "lab"].some((view) =>
      $(`#view-${view}`).classList.contains("active"),
    )
  ) {
    showView(state.user.role === "guest" ? "catalog" : "orders");
  }
  if (
    appIsVisible &&
    hideCommerce &&
    $("#view-orders").classList.contains("active")
  ) {
    showView("catalog");
  }
  if (
    appIsVisible &&
    hideGuides &&
    $("#view-guides").classList.contains("active")
  ) {
    showView(canUseTestLab() ? "overview" : "catalog");
  }
  applyRoleBranding();
}

function applyRoleBranding() {
  if (!state.user) return;
  const name = $("#brand-name");
  const subtitle = $("#brand-subtitle");
  if (state.user.role === "admin") {
    name.textContent = "API TEST LAB";
    subtitle.textContent = "ADMIN TEST CONSOLE";
    document.title = "FastAPI Test Lab · 管理员测试控制台";
    return;
  }
  name.textContent = "NORTHSTAR";
  subtitle.textContent =
    state.user.role === "guest" ? "VISITOR ACCESS" : "ONLINE STORE";
  document.title =
    state.user.role === "guest"
      ? "Northstar Goods · 游客浏览"
      : "Northstar Goods · 商城";
}

async function logout() {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch {
    // The local session is cleared even if the logout request is interrupted.
  }
  clearSession();
}

function checkout() {
  if (!state.user) {
    showAuthGate();
    toast("请先登录再提交订单", "error");
    return;
  }
  if (state.user.role === "guest") {
    toast("访客账户为只读模式，不能提交订单", "error");
    return;
  }
  if (!state.cart.length) return;
  const itemCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = state.cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0,
  );
  const total = subtotal + Math.round(subtotal * 0.06 * 100) / 100;
  $("#payment-item-count").textContent = `${itemCount} 件`;
  $("#payment-total").textContent = formatMoney(total);
  $("#confirm-payment-button").textContent = `确认支付 ${formatMoney(total)}`;
  $("#payment-form-view").hidden = false;
  $("#payment-success-view").hidden = true;
  $$('input[name="payment_method"]').forEach((input) => {
    input.checked = input.value === "alipay";
    input.closest(".payment-option").classList.toggle("active", input.checked);
  });
  $("#payment-dialog").showModal();
}

async function confirmPayment() {
  if (!state.cart.length) return;
  const button = $("#confirm-payment-button");
  const method = $('input[name="payment_method"]:checked')?.value || "alipay";
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "正在确认支付…";
  try {
    const idempotencyKey =
      typeof crypto.randomUUID === "function"
        ? `ui-${crypto.randomUUID()}`
        : `ui-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const payload = {
      items: state.cart.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
      })),
      note: "Northstar Goods online checkout",
      payment_method: method,
    };
    const { response, data } = await request("/api/orders", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(data?.detail || "订单创建失败");
    state.cart = [];
    persistCart();
    renderCart();
    $("#payment-success-order").textContent = data.id;
    $("#payment-success-method").textContent =
      paymentLabels[data.payment_method] || data.payment_method;
    $("#payment-success-total").textContent = formatMoney(data.total);
    $("#payment-form-view").hidden = true;
    $("#payment-success-view").hidden = false;
    await Promise.all([loadOrders(), loadCatalog()]);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function loadOrders() {
  if (!state.user || state.user.role === "guest") {
    renderOrders(null);
    return;
  }
  try {
    const { response, data } = await request("/api/orders?page=1&page_size=20");
    if (!response.ok) throw new Error(data?.detail || "订单加载失败");
    renderOrders(data.items);
  } catch (error) {
    if (error.message.includes("Authentication") || error.message.includes("token")) {
      clearSession(false);
    }
    $("#orders-list").innerHTML = `
      <div class="empty-block"><strong>订单加载失败</strong><span>${escapeHtml(error.message)}</span></div>
    `;
  }
}

function renderOrders(orders) {
  const container = $("#orders-list");
  if (!orders) {
    container.innerHTML = `
      <div class="empty-block"><strong>登录后查看订单</strong><span>普通用户与管理员测试账户各自拥有独立订单数据</span></div>
    `;
    return;
  }
  if (!orders.length) {
    container.innerHTML = `
      <div class="empty-block"><strong>暂无历史订单</strong><span>从商品目录加入商品并提交第一个订单</span></div>
    `;
    return;
  }
  container.innerHTML = orders
    .map((order) => {
      const itemSummary = order.items
        .map((item) => `${item.product_name} × ${item.quantity}`)
        .join("、");
      return `
        <div class="order-row">
          <div class="order-id"><strong>${escapeHtml(order.id)}</strong><small>${formatTime(order.created_at)}</small></div>
          <div class="order-items-preview"><strong>${escapeHtml(itemSummary)}</strong><small>${order.items.length} 种商品</small></div>
          <span class="order-payment-method">${escapeHtml(paymentLabels[order.payment_method] || order.payment_method)}</span>
          <span class="order-status">${escapeHtml(orderStatusLabels[order.status] || order.status)}</span>
          <span class="order-total">${formatMoney(order.total)}</span>
          <button class="order-view-button" data-order-id="${escapeHtml(order.id)}">查看详情</button>
        </div>
      `;
    })
    .join("");
  $$(".order-view-button", container).forEach((button) => {
    button.addEventListener("click", () =>
      showOrderDetail(button.dataset.orderId),
    );
  });
}

async function showOrderDetail(orderId, updateUrl = true) {
  if (!state.user || state.user.role === "guest") {
    showView("orders");
    return;
  }
  const normalizedId = String(orderId || "").trim().toUpperCase();
  if (!normalizedId) {
    $("#order-query-error").textContent = "请输入订单编号";
    $("#order-query-error").hidden = false;
    return;
  }
  state.currentOrderId = normalizedId;
  showView("order-detail", false);
  $("#order-detail-error").hidden = true;
  $("#order-detail-content").hidden = true;
  $("#order-detail-title").textContent = "订单详情";
  $("#order-detail-subtitle").textContent = "正在读取订单信息…";
  if (updateUrl) {
    history.pushState(
      { view: "order-detail", orderId: normalizedId },
      "",
      `/orders/${encodeURIComponent(normalizedId)}`,
    );
  }
  try {
    const { response, data } = await request(
      `/api/orders/${encodeURIComponent(normalizedId)}`,
    );
    if (!response.ok) throw new Error(data?.detail || "订单查询失败");
    renderOrderDetail(data);
  } catch (error) {
    $("#order-detail-error").hidden = false;
    $("#order-detail-subtitle").textContent = "无法读取订单";
    toast(error.message, "error");
  }
}

function renderOrderDetail(order) {
  state.currentOrderId = order.id;
  $("#order-query-error").hidden = true;
  $("#order-detail-content").hidden = false;
  $("#order-detail-error").hidden = true;
  $("#order-detail-title").textContent = order.id;
  $("#order-detail-subtitle").textContent = "订单记录与支付信息";
  $("#order-detail-id").textContent = order.id;
  $("#order-detail-id-label").textContent = order.id;
  $("#order-detail-status").textContent =
    orderStatusLabels[order.status] || order.status;
  $("#order-detail-created").textContent = new Date(order.created_at).toLocaleString(
    "zh-CN",
    { hour12: false },
  );
  $("#order-detail-payment").textContent =
    paymentLabels[order.payment_method] || order.payment_method;
  $("#order-detail-payment-status").textContent =
    order.payment_status === "paid" ? "已支付" : "待支付";
  $("#order-detail-items").innerHTML = order.items
    .map(
      (item) => `
        <tr>
          <td><strong>${escapeHtml(item.product_name)}</strong></td>
          <td>${formatMoney(item.unit_price)}</td>
          <td>${item.quantity}</td>
          <td>${formatMoney(item.line_total)}</td>
        </tr>
      `,
    )
    .join("");
  $("#order-detail-subtotal").textContent = formatMoney(order.subtotal);
  $("#order-detail-tax").textContent = formatMoney(order.tax);
  $("#order-detail-total").textContent = formatMoney(order.total);
  const stage = {
    pending: 0,
    confirmed: 1,
    shipped: 2,
    completed: 3,
    cancelled: 0,
  }[order.status] ?? 1;
  $$(".order-timeline li").forEach((item, index) => {
    item.classList.toggle("complete", index < stage);
    item.classList.toggle("current", index === stage);
  });
}

async function queryOrder(event) {
  event.preventDefault();
  const input = $("#order-search-input");
  const error = $("#order-query-error");
  error.hidden = true;
  if (!input.value.trim()) {
    error.textContent = "请输入订单编号";
    error.hidden = false;
    input.focus();
    return;
  }
  await showOrderDetail(input.value.trim(), true);
}

function setAuthMode(mode) {
  const isRegister = mode === "register";
  $$(".auth-tab").forEach((tab) => {
    const active = tab.dataset.authTab === mode;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  $("#auth-login-form").hidden = isRegister;
  $("#auth-register-form").hidden = !isRegister;
  $("#auth-card-title").textContent = isRegister ? "创建账户" : "登录账户";
  $("#auth-login-error").hidden = true;
  $("#auth-register-error").hidden = true;
}

async function registerCustomer(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const errorNode = $("#auth-register-error");
  errorNode.hidden = true;
  if (values.get("password") !== values.get("confirm_password")) {
    errorNode.textContent = "两次输入的密码不一致";
    errorNode.hidden = false;
    return;
  }
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = "正在创建账户…";
  try {
    const { response, data } = await request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username: values.get("username"),
        password: values.get("password"),
        display_name: values.get("display_name") || null,
      }),
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : detail?.[0]?.msg || "注册失败，请检查输入",
      );
    }
    saveSession(data);
    await enterRequestedRoute();
    toast(`账户 ${data.user.username} 已创建`);
  } catch (error) {
    errorNode.textContent = error.message;
    errorNode.hidden = false;
  } finally {
    submit.disabled = false;
    submit.textContent = "创建账户";
  }
}

async function loginAsGuest() {
  const errorNode = $("#guest-entry-error");
  errorNode.hidden = true;
  try {
    const { response, data } = await request("/api/auth/guest", {
      method: "POST",
    });
    if (!response.ok) throw new Error(data?.detail || "访客入口暂不可用");
    saveSession(data);
    await enterApplication("catalog");
    toast("已进入游客浏览模式");
  } catch (error) {
    errorNode.textContent = error.message;
    errorNode.hidden = false;
  }
}

function openAccountDialog() {
  if (!state.user) {
    showAuthGate();
    return;
  }
  $("#account-dialog").showModal();
}

function bindAuth() {
  $("#account-button").addEventListener("click", openAccountDialog);
  $("#close-account-dialog").addEventListener("click", () =>
    $("#account-dialog").close(),
  );
  $("#account-dialog").addEventListener("click", (event) => {
    if (event.target === $("#account-dialog")) $("#account-dialog").close();
  });
  $$(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => setAuthMode(tab.dataset.authTab));
  });
  $("#auth-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const submit = event.currentTarget.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "正在验证…";
    await login(
      form.get("username"),
      form.get("password"),
      $("#auth-login-error"),
    );
    submit.disabled = false;
    submit.textContent = "登录";
  });
  $("#auth-register-form").addEventListener("submit", registerCustomer);
  $("#guest-entry-button").addEventListener("click", loginAsGuest);
  $$("[data-demo-user]").forEach((button) => {
    button.addEventListener("click", () => {
      setAuthMode("login");
      $("#auth-login-form").elements.username.value = button.dataset.demoUser;
      $("#auth-login-form").elements.password.value =
        button.dataset.demoPassword;
      $("#auth-login-form").requestSubmit();
    });
  });
  $("#dialog-logout-button").addEventListener("click", logout);
  $("#checkout-button").addEventListener("click", checkout);
  $("#refresh-orders").addEventListener("click", loadOrders);
  $("#order-search-form").addEventListener("submit", queryOrder);
  $("#order-detail-back").addEventListener("click", () => showView("orders"));
  $("#close-payment-dialog").addEventListener("click", () =>
    $("#payment-dialog").close(),
  );
  $("#payment-dialog").addEventListener("click", (event) => {
    if (event.target === $("#payment-dialog")) $("#payment-dialog").close();
  });
  $("#confirm-payment-button").addEventListener("click", confirmPayment);
  $("#payment-done-button").addEventListener("click", () => {
    $("#payment-dialog").close();
    showView("orders");
  });
  $$('input[name="payment_method"]').forEach((input) => {
    input.addEventListener("change", () => {
      $$(".payment-option").forEach((option) => {
        option.classList.toggle("active", option.contains(input));
      });
    });
  });
}

function guideStorageKey() {
  return `fastapi-lab-guide-checks:${state.user?.id || "unknown"}`;
}

function readGuideChecks() {
  try {
    const value = JSON.parse(localStorage.getItem(guideStorageKey()) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function syncGuideChecklist() {
  const checks = readGuideChecks();
  $$("[data-guide-check]").forEach((input) => {
    input.checked = Boolean(checks[input.dataset.guideCheck]);
  });
  renderGuideProgress(checks);
}

function renderGuideProgress(checks = readGuideChecks()) {
  const inputs = $$("[data-guide-check]");
  const complete = inputs.filter((input) => input.checked).length;
  $("#guide-checklist-count").textContent = `${complete} / ${inputs.length} 已完成`;
  $("#guide-progress-value").textContent = `${complete} / ${inputs.length}`;
  $("#guide-progress-fill").style.width = `${(complete / inputs.length) * 100}%`;
  $$("[data-guide-progress]").forEach((node) => {
    node.classList.toggle("complete", Boolean(checks[node.dataset.guideProgress]));
  });
}

function selectGuideTool(tool) {
  $$("[data-guide-tool]").forEach((button) => {
    button.classList.toggle("active", button.dataset.guideTool === tool);
  });
  $$("[data-guide-panel]").forEach((panel) => {
    const active = panel.dataset.guidePanel === tool;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });
}

function bindGuides() {
  $$("[data-guide-tool]").forEach((button) => {
    button.addEventListener("click", () =>
      selectGuideTool(button.dataset.guideTool),
    );
  });
  $$("[data-guide-check]").forEach((input) => {
    input.addEventListener("change", () => {
      const checks = readGuideChecks();
      checks[input.dataset.guideCheck] = input.checked;
      localStorage.setItem(guideStorageKey(), JSON.stringify(checks));
      renderGuideProgress(checks);
    });
  });
  $$("[data-copy-text]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copyText);
        toast("命令已复制");
      } catch {
        toast("复制失败，请手动选择命令", "error");
      }
    });
  });
  selectGuideTool("postman");
}

function bindCatalog() {
  let timer;
  $("#catalog-search").addEventListener("input", () => {
    clearTimeout(timer);
    timer = window.setTimeout(loadCatalog, 260);
  });
  $("#catalog-category").addEventListener("change", loadCatalog);
  $("#catalog-sort").addEventListener("change", loadCatalog);
}

function setConsoleBody(body) {
  const text =
    typeof body === "string" ? body : body == null ? "" : JSON.stringify(body, null, 2);
  $("#request-body").value = text;
  $("#body-size").textContent = `${new Blob([text]).size} bytes`;
}

function updateConsoleStatus(statusCode, elapsed, info) {
  const pill = $("#response-status");
  pill.className = `status-pill ${statusClass(statusCode)}`;
  pill.textContent = statusCode ? String(statusCode) : "ERROR";
  $("#response-time").textContent = `${elapsed.toFixed(1)} ms`;
  $("#response-info").innerHTML = info
    .map((value) => `<span>${escapeHtml(value)}</span>`)
    .join("");
}

async function sendConsoleRequest() {
  const button = $("#send-request");
  button.disabled = true;
  button.firstChild.textContent = "发送中 ";
  const method = $("#request-method").value;
  const path = $("#request-path").value.trim();
  const rawBody = $("#request-body").value.trim();
  const rawHeaders = $("#request-headers").value.trim();
  const headers = {};
  try {
    if (rawHeaders) Object.assign(headers, JSON.parse(rawHeaders));
  } catch {
    toast("Headers 必须是合法 JSON", "error");
    button.disabled = false;
    button.firstChild.textContent = "发送 ";
    return;
  }
  try {
    if (!path.startsWith("/")) throw new Error("请求路径需要以 / 开头");
    const options = { method, headers };
    if (!["GET", "HEAD"].includes(method) && rawBody) {
      options.body = rawBody;
      if (!Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) {
        headers["Content-Type"] = "application/json";
      }
    }
    const result = await request(path, options);
    const isJson = typeof result.data === "object";
    const shownText = isJson
      ? JSON.stringify(result.data, null, 2)
      : String(result.data || result.text || "").slice(0, 30000);
    const requestId = result.response.headers.get("X-Request-ID") || "—";
    updateConsoleStatus(result.response.status, result.elapsed, [
      `Request ID · ${requestId}`,
      `${result.response.headers.get("X-Process-Time-Ms") || result.elapsed.toFixed(1)} ms · local-api-01`,
    ]);
    $("#response-body").textContent =
      shownText || "(empty response body)";
    if (
      path === "/api/auth/login" &&
      result.response.ok &&
      result.data?.access_token
    ) {
      saveSession(result.data);
      toast("Token 已自动保存，后续控制台请求会携带 Authorization");
    }
  } catch (error) {
    updateConsoleStatus(0, 0, ["请求未完成", "检查服务状态或请求路径"]);
    $("#response-body").textContent = `${error.name}: ${error.message}`;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = "发送 ";
  }
}

function bindConsole() {
  $("#preset-select").addEventListener("change", (event) => {
    const preset = requestPresets[event.target.value];
    if (!preset) return;
    $("#request-method").value = preset.method;
    $("#request-path").value = preset.path;
    setConsoleBody(preset.body);
    $("#request-headers").value = JSON.stringify(preset.headers || {}, null, 2);
  });
  $("#request-body").addEventListener("input", () => {
    $("#body-size").textContent = `${new Blob([$("#request-body").value]).size} bytes`;
  });
  $$(".editor-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".editor-tab").forEach((item) => item.classList.toggle("active", item === tab));
      $$(".editor-pane").forEach((pane) => {
        pane.classList.toggle("active", pane.dataset.pane === tab.dataset.editor);
      });
    });
  });
  $("#send-request").addEventListener("click", sendConsoleRequest);
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      if ($("#view-console").classList.contains("active")) {
        event.preventDefault();
        sendConsoleRequest();
      }
    }
  });
  $("#copy-curl").addEventListener("click", async () => {
    const method = $("#request-method").value;
    const path = $("#request-path").value.trim();
    const body = $("#request-body").value.trim();
    let command = `curl -i -X ${method} "http://127.0.0.1:8000${path}"`;
    if (state.token) command += ` \\\n  -H "Authorization: Bearer ${state.token}"`;
    try {
      const headers = JSON.parse($("#request-headers").value || "{}");
      Object.entries(headers).forEach(([key, value]) => {
        command += ` \\\n  -H "${key}: ${value}"`;
      });
    } catch {
      // Ignore malformed optional headers while copying.
    }
    if (body && !["GET", "HEAD"].includes(method)) {
      command += ` \\\n  -H "Content-Type: application/json" \\\n  --data '${body.replaceAll("'", "'\\''")}'`;
    }
    try {
      await navigator.clipboard.writeText(command);
      toast("cURL 已复制到剪贴板");
    } catch {
      $("#response-body").textContent = command;
      toast("剪贴板不可用，cURL 已显示在响应区", "error");
    }
  });
}

function printLab(value) {
  $("#lab-output").textContent =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function runLabAction(action) {
  try {
    if (action === "slow") {
      const delay = $("#delay-range").value;
      const { response, data, elapsed } = await request(
        `/api/lab/slow?delay_ms=${delay}`,
      );
      printLab({ http_status: response.status, client_elapsed_ms: elapsed.toFixed(1), ...data });
      return;
    }
    if (action === "flaky") {
      const failureRate = Number($("#failure-range").value) / 100;
      const mode = $("#failure-mode").value;
      const { response, data } = await request(
        `/api/lab/flaky?failure_rate=${failureRate}&mode=${mode}`,
      );
      printLab({ http_status: response.status, ...data });
      return;
    }
    if (action === "burst") {
      const clientKey = `ui-burst-${Date.now()}`;
      const results = [];
      for (let index = 1; index <= 6; index += 1) {
        const { response, data } = await request("/api/lab/rate-limit", {
          headers: { "X-Lab-Client": clientKey },
        });
        results.push({
          attempt: index,
          status: response.status,
          remaining: data?.remaining,
          detail: data?.detail || "accepted",
        });
      }
      printLab({
        note: "The sixth request in a ten-second window should return 429.",
        results,
      });
      return;
    }
    if (action === "redirect") {
      const { response, elapsed } = await request("/api/lab/redirect", {
        redirect: "follow",
      });
      printLab({
        http_status: response.status,
        final_url: response.url,
        elapsed_ms: elapsed.toFixed(1),
        note: "The browser followed the 302 response to /docs.",
      });
      return;
    }
    if (action === "echo") {
      const { response, data } = await request(
        "/api/lab/echo?source=network-lab&course=wireshark",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Lab-Exercise": "echo-and-inspect",
          },
          body: JSON.stringify({
            message: "Inspect this request in Burp or Wireshark",
            client: "interactive-dashboard",
          }),
        },
      );
      printLab({ http_status: response.status, ...data });
    }
  } catch (error) {
    printLab({ error: error.message });
    toast("场景请求失败", "error");
  }
}

function bindLab() {
  $$("[data-lab-action]").forEach((button) => {
    button.addEventListener("click", () => runLabAction(button.dataset.labAction));
  });
  $("#delay-range").addEventListener("input", () => {
    $("#delay-output").textContent = `${$("#delay-range").value} ms`;
  });
  $("#failure-range").addEventListener("input", () => {
    $("#failure-output").textContent = `${$("#failure-range").value}%`;
  });
  $("#upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = $("#upload-file").files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const { response, data } = await request("/api/lab/upload", {
        method: "POST",
        body: form,
      });
      printLab({ http_status: response.status, ...data });
    } catch (error) {
      printLab({ error: error.message });
    }
  });
  $("#reset-lab").addEventListener("click", async () => {
    if (!window.confirm("这会重置账号、商品、订单和流量。确定继续吗？")) return;
    try {
      const { response, data } = await request("/api/lab/reset", { method: "POST" });
      clearSession(false);
      state.cart = [];
      persistCart();
      renderCart();
      await Promise.all([loadCatalog(), refreshTraffic()]);
      printLab(data);
      toast("测试环境已重置");
    } catch {
      toast("环境重置失败", "error");
    }
  });
  $("#clear-traffic-lab").addEventListener("click", clearTraffic);
}

function bindGlobal() {
  $("#clear-traffic").addEventListener("click", clearTraffic);
  window.addEventListener("resize", () => {
    if (state.lastTraffic) {
      drawTrafficChart(state.lastTraffic.timeline || []);
      const distribution = state.lastTraffic.status_distribution || {};
      const groups = { ok: 0, redirect: 0, client: 0, server: 0 };
      Object.entries(distribution).forEach(([code, count]) => {
        const digit = Number(code.charAt(0));
        if (digit === 2) groups.ok += count;
        else if (digit === 3) groups.redirect += count;
        else if (digit === 4) groups.client += count;
        else if (digit === 5) groups.server += count;
      });
      drawStatusChart(groups);
    }
  });
}

async function init() {
  bindNavigation();
  bindAuth();
  bindCatalog();
  bindConsole();
  bindLab();
  bindGuides();
  bindGlobal();
  renderCart();
  updateAuthUI();
  setAuthMode("login");
  const authenticated = await restoreSession();
  if (!authenticated) {
    showAuthGate();
    return;
  }
  await enterRequestedRoute();
}

init();
