# DESIGN.md

> 像一张精密测试台：先验证身份，再让数据与操作按权限就位。

## 1. Visual Theme & Atmosphere

**Style**: Warm Technical Editorial（暖白技术编辑风）
**Keywords**: 纸感、精确、克制、可信、仪器化、清晰分区、暖色信号
**Tone**: 安静而专业，像实验室里的操作手册与仪表盘结合 — NOT 霓虹赛博、NOT 游戏化、NOT 装饰过载
**Feel**: 推开测试室的门之前，先在前台核验身份；进入后，每块数据都像被清楚标注的实验记录。

**Interaction Tier**: L1 精致静态
**Dependencies**: CSS only；无 GSAP、Lenis 或 WebGL

产品由登录门禁、角色化导航、数据概览、API 控制台、商品目录、订单工作台和网络实验室组成。登录门面使用 Northstar Goods 电商品牌，不暴露测试平台身份；普通用户进入商城工作区；管理员测试账户进入测试控制台；访客通过游客入口进入目录只读模式。工具指南和测试快捷链接只对管理员测试账户显示。

订单工作台不重复展示全局账户信息。结算由独立弹窗完成，用户可选择支付宝、微信支付或银行卡；订单记录支付方式与支付状态，并返回支付成功凭证。工具指南采用左侧工具索引、右侧分步任务、可复制命令与可持久化验收清单。

订单列表与订单详情使用独立路由：`/orders` 展示购物车和历史订单，`/orders/{id}` 展示商品明细、支付信息与配送进度。刷新详情页必须恢复当前订单，而不是退回默认首页。

## 2. Color Palette & Roles

```css
:root {
  /* Backgrounds */
  --bg: #f2eee4;
  --bg-rgb: 242, 238, 228;
  --surface: #fffdf8;
  --surface-rgb: 255, 253, 248;
  --surface-alt: #e8e2d5;
  --surface-hover: #f8f3e9;

  /* Navigation */
  --nav: #1d2723;
  --nav-rgb: 29, 39, 35;
  --nav-text: #f7f1e6;
  --nav-muted: #aab4ac;

  /* Borders */
  --border: #d9d1c1;
  --border-hover: #b7aa93;

  /* Text */
  --text: #1b2320;
  --text-rgb: 27, 35, 32;
  --text-secondary: #5c655f;
  --text-tertiary: #8a918b;

  /* Accent */
  --accent: #c9552f;
  --accent-hover: #ad4224;
  --accent-rgb: 201, 85, 47;
  --accent-soft: #f5d9cd;

  /* Semantic */
  --success: #2d715b;
  --success-rgb: 45, 113, 91;
  --success-soft: #dcebe3;
  --error: #b43a3a;
  --error-rgb: 180, 58, 58;
  --error-soft: #f4dcdc;
  --warning: #b77722;
  --warning-soft: #f4e4c9;
  --info: #3e698e;
  --info-soft: #dce7ef;

  /* Focus and effects */
  --focus: #176d76;
  --focus-rgb: 23, 109, 118;
  --overlay: rgba(29, 39, 35, 0.62);
}
```

**Color Rules:**

- 页面所有颜色必须通过以上 CSS 变量引用，禁止在组件规则中新增硬编码十六进制色值。
- 页面底色使用暖白；深色只用于侧栏、代码和认证页叙事区，杜绝全屏黑底。
- 朱橙是唯一主操作色；绿色、蓝色和红色只表示状态，不用于装饰。
- 同一区域最多出现一个主强调色；角色身份色只用于小型徽章与边界。

## 3. Typography Rules

**Font Stack:**

```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

:root {
  --font-sans: "Noto Sans SC", "DM Sans", "Microsoft YaHei UI", sans-serif;
  --font-mono: "IBM Plex Mono", "Cascadia Code", Consolas, monospace;
}
```

| Role | Font | Size | Weight | Line Height | Letter Spacing |
|------|------|------|--------|-------------|----------------|
| Auth Hero H1 | Noto Sans SC | 56-64px | 700 | 1.16 | -0.04em |
| Dashboard Page Title | Noto Sans SC | 24px | 700 | 1.35 | 0.01em |
| Section H2 | Noto Sans SC | 32px | 700 | 1.3 | -0.02em |
| Card H3 | Noto Sans SC | 16-18px | 600 | 1.55 | 0.01em |
| Body | Noto Sans SC | 15px | 400 | 1.75 | 0.02em |
| Dense UI Body | Noto Sans SC | 13-14px | 400 | 1.65 | 0.01em |
| Label | DM Sans / Noto Sans SC | 11-12px | 600 | 1.5 | 0.1em |
| Metric | IBM Plex Mono | 28-38px | 600 | 1.2 | -0.03em |
| Code | IBM Plex Mono | 12-14px | 400 | 1.7 | 0 |

**Typography Rules:**

- 中文正文保持不低于 15px，数据密集型表格可降至 13px，但行高不得低于 1.6。
- 英文标签与数字使用 DM Sans / IBM Plex Mono，保持仪器读数感。
- 标题使用 600-700 字重，正文不超过 500，避免所有信息同时抢注意力。
- **NEVER use**: Orbitron、Orbitron 类科幻字体、Comic Sans、纯英文无中文回退字体栈。

**Text Decoration:**

- Auth Hero H1：无渐变、无投影，以字号和留白形成视觉冲击。
- Dashboard H1/H2：无装饰，以深墨色与细横线区分层级。
- 正文：禁止文字阴影、渐变或描边。
- Eyebrow：使用单色标签和短横线，不使用发光滤镜。

## 4. Component Stylings

### Buttons

```css
.button {
  min-height: 44px;
  padding: 0 18px;
  border: 1px solid transparent;
  border-radius: 9px;
  font: 600 14px/1 var(--font-sans);
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease;
}
.button:hover { transform: translateY(-1px); }
.button:active { transform: translateY(0); }
.button:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
.button:disabled { opacity: .45; cursor: not-allowed; transform: none; }
.button.primary { background: var(--accent); color: var(--surface); }
.button.primary:hover { background: var(--accent-hover); }
.button.ghost { background: transparent; border-color: var(--border); color: var(--text); }
.button.ghost:hover { background: var(--surface-hover); border-color: var(--border-hover); }
```

### Cards and Panels

```css
.panel, .metric-card, .scenario-card, .guide-card, .product-card {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.panel:hover, .metric-card:hover, .scenario-card:hover, .product-card:hover {
  border-color: var(--border-hover);
}
.panel:focus-within, .product-card:focus-within {
  border-color: var(--focus);
  box-shadow: 0 0 0 3px rgba(var(--focus-rgb), .12);
}
```

### Navigation

```css
.sidebar { background: var(--nav); color: var(--nav-text); }
.nav-item {
  min-height: 44px;
  border-radius: 9px;
  color: var(--nav-muted);
  transition: background 150ms ease, color 150ms ease;
}
.nav-item:hover { color: var(--nav-text); background: rgba(var(--surface-rgb), .06); }
.nav-item:active { background: rgba(var(--surface-rgb), .1); }
.nav-item:focus-visible { outline: 2px solid var(--nav-text); outline-offset: 2px; }
.nav-item.active { color: var(--nav-text); background: rgba(var(--surface-rgb), .1); }
```

### Links

```css
a, .text-button {
  color: var(--accent);
  text-decoration: none;
  transition: color 150ms ease;
}
a:hover, .text-button:hover { color: var(--accent-hover); text-decoration: underline; text-underline-offset: 3px; }
a:active, .text-button:active { color: var(--text); }
a:focus-visible, .text-button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.text-button:disabled { color: var(--text-tertiary); cursor: not-allowed; text-decoration: none; }
```

### Tags and Role Badges

```css
.mini-tag, .role-badge {
  min-height: 26px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font: 600 10px/1.4 var(--font-mono);
}
.role-badge.customer { color: var(--info); background: var(--info-soft); }
.role-badge.guest { color: var(--text-secondary); background: var(--surface-alt); }
.role-badge.admin { color: var(--success); background: var(--success-soft); }
```

### Inputs and Forms

```css
input, select, textarea {
  min-height: 44px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
input:hover, select:hover, textarea:hover { border-color: var(--border-hover); }
input:focus, select:focus, textarea:focus {
  border-color: var(--focus);
  box-shadow: 0 0 0 3px rgba(var(--focus-rgb), .1);
  outline: none;
}
input:disabled, select:disabled, textarea:disabled {
  background: var(--surface-alt);
  color: var(--text-tertiary);
  cursor: not-allowed;
}
input[aria-invalid="true"] { border-color: var(--error); }
```

### Authentication Gate

```css
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(380px, .85fr);
  background: var(--bg);
}
.auth-story {
  position: relative;
  padding: clamp(36px, 6vw, 88px);
  overflow: hidden;
  background: var(--nav);
  color: var(--nav-text);
}
.auth-workbench { display: grid; place-items: center; padding: 32px; }
.auth-card {
  width: min(100%, 470px);
  padding: clamp(26px, 4vw, 42px);
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 0 24px 70px rgba(var(--text-rgb), .1);
}
.auth-tab {
  min-height: 44px;
  border-bottom: 2px solid transparent;
  color: var(--text-tertiary);
}
.auth-tab:hover { color: var(--text); }
.auth-tab:active { color: var(--accent); }
.auth-tab:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.auth-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
```

## 5. Layout Principles

**Container:**

- Main dashboard uses full width with a 256px sidebar and a maximum 1480px content canvas.
- Authentication page uses a split 58/42 layout on desktop.
- Text-heavy guidance content uses a 760px reading width.
- Main padding: 28-44px desktop, 18-24px tablet, 16px mobile.

**Spacing Scale:**

- Section spacing: 28-44px.
- Component gap: 12-16px.
- Card internal padding: 18-24px.
- Form field gap: 14px.
- Label to input gap: 7px.

**Grid:**

```css
.metrics-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .75fr); gap: 14px; }
.catalog-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.auth-shell { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(380px, .85fr); }
```

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat | No shadow | Dense tables, navigation, inline controls |
| Subtle | `0 1px 2px rgba(var(--text-rgb), .05)` | Panels and cards |
| Elevated | `0 14px 36px rgba(var(--text-rgb), .08)` | Dialogs and floating menus |
| Auth | `0 24px 70px rgba(var(--text-rgb), .1)` | Login workbench card |

No colored glow or neon shadow. Borders and spacing provide structure before shadows do.

## 7. Animation & Interaction

**Motion Philosophy**: 信息立即出现，动效只确认状态变化，不延迟任务。
**Tier**: L1

### Dependencies

```html
<!-- None: CSS transitions and one-time CSS entrance animations only. -->
```

### Base Setup

```js
// One-time enter classes are added after the authenticated shell becomes visible.
document.querySelectorAll(".reveal").forEach((element, index) => {
  window.setTimeout(() => element.classList.add("in-view"), index * 70);
});
```

### Entrance Animation

```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.reveal {
  opacity: 0;
  transform: translateY(16px);
}
.reveal.in-view {
  opacity: 1;
  transform: translateY(0);
  transition: opacity .5s cubic-bezier(.16,1,.3,1), transform .5s cubic-bezier(.16,1,.3,1);
}
.auth-card { animation: fadeInUp .55s cubic-bezier(.16,1,.3,1) both; }
```

### Scroll Behavior

```css
html { scroll-behavior: smooth; }
[id] { scroll-margin-top: 84px; }
```

Dashboard data must remain immediately visible. Do not add scroll reveal to tables, charts, forms, or critical metrics.

### Hover & Focus States

```css
:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
.metric-card:hover { border-color: var(--border-hover); }
.product-card:hover { transform: translateY(-2px); border-color: var(--border-hover); }
tr:hover td { background: var(--surface-hover); }
.add-cart:hover { background: var(--accent); color: var(--surface); }
```

### Special Effects

- Authentication role diagram uses static line connectors and a restrained CSS `scaleIn` entrance.
- Metric values update in place; no odometer or continuous background animation.
- Toast notifications slide up 8px and fade out.
- Navigation view changes use a 220ms opacity/translate transition.

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## 8. Do's and Don'ts

### Do

- Keep the authentication gate visible until `/api/auth/me` validates an existing session.
- Present the logged-out experience as a normal e-commerce account page; reveal testing-specific language only after the administrator test account logs in.
- Restrict the tool guide and test quick links to the administrator test account.
- Separate checkout payment selection from the cart so the final action remains explicit and reversible.
- Keep account identity in the global header and account dialog only; do not repeat it inside the order workspace.
- Make role differences explicit through labels, navigation, and backend authorization.
- Keep data surfaces light, bordered, and readable during long test sessions.
- Make all form errors visible next to the action that failed.
- Preserve keyboard focus and 44px touch targets on every interactive element.
- Use inlined Lucide-style SVG icons from the existing project.

### Don't

- ❌ Never render the sidebar, dashboard, catalog, or lab before authentication succeeds.
- ❌ Never assign the administrator role through public registration.
- ❌ Never let a guest create orders, modify data, or access test-lab endpoints.
- ❌ Never rely only on hidden navigation for authorization; every restricted API must validate role.
- ❌ Never use neon glow, purple-blue tech gradients, or glassmorphism as the main visual language.
- ❌ Never place animation on critical tables or chart data.
- ❌ Never use color alone to communicate role or account state.
- ❌ Never show errors as an anonymous toast if the form itself failed.
- ❌ Never add a custom cursor or scroll hijacking to this dashboard.
- ❌ Never mix a second accent color into primary actions.

## 9. Responsive Behavior

**Breakpoints:**

| Name | Width | Key Changes |
|------|-------|-------------|
| Desktop | > 1180px | Split auth page; four metric columns; expanded sidebar |
| Tablet | 721-1180px | Auth page becomes stacked; metrics two columns; sidebar can collapse |
| Mobile | ≤ 720px | Auth card fills viewport; sidebar becomes drawer; all grids one or two columns |
| Narrow | ≤ 460px | Metrics two columns with smaller numeric type; tables scroll horizontally |

**Touch Targets:** minimum 44×44px
**Collapsing Strategy:** use an explicit menu button; never hide navigation without an alternate opener. Auth tabs remain horizontally visible and registration fields stack in one column.

```css
@media (max-width: 1180px) {
  .catalog-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 960px) {
  .auth-shell { grid-template-columns: 1fr; }
  .auth-story { min-height: 38vh; }
  .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dashboard-grid, .console-layout, .order-layout { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .sidebar { transform: translateX(-105%); }
  .sidebar.open { transform: translateX(0); }
  .workspace { margin-left: 0; }
  .catalog-grid { grid-template-columns: 1fr; }
  .auth-story { display: none; }
  .auth-workbench { min-height: 100vh; padding: 16px; }
}
```
