# FastAPI Test Lab

一个用于接口测试、性能测试和网络观察的本地拟真环境。项目包含可交互 Web 控制台、REST API、SQLite 示例数据、JWT 登录、订单幂等流程、文件上传、表单、限流、延迟和故障注入，并附带 Postman 集合与 JMeter 测试计划。

## 快速启动

在 Windows 下双击 `start.bat`，或在 PowerShell 中运行：

```powershell
Set-Location "D:\Documents\ChatGPT\fastapi-test-lab"
.\start.ps1
```

首次启动会自动准备 Python 3.12 和虚拟环境。启动后访问：

- 交互控制台：<http://127.0.0.1:8000>
- Swagger UI：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>

预置账号：

| 角色 | 用户名 | 密码 | 用途 |
| --- | --- | --- | --- |
| 普通用户 | `customer` | `customer123` | 商城、独立购物车、个人订单 |
| 管理员测试账户 | `admin` | `admin123` | 测试控制台、网络实验室、工具指南、全部订单 |
| 访客用户 | 登录页访客入口 | 不需要 | 商品目录只读访问 |

登录页支持普通用户注册。公开注册只会创建 `customer` 角色，不能自行申请管理员权限。管理员账号同时承担唯一测试账户角色。访客必须先从登录页创建访客会话，虽然无需输入密码，但未认证状态下不会显示商城或控制台页面。

服务默认只监听 `127.0.0.1`。如果确实需要在局域网中访问，可运行 `.\start.ps1 -Public`，但项目含演示密钥和重置能力，不应部署到公网。

### 账户隔离

- `customer` 创建和看到的订单只属于普通用户账号。
- `admin` 是唯一的测试账号，同时拥有管理员能力；流量指标、网络实验室与故障注入接口只允许 `admin` 角色。
- `guest` 是只读角色：可浏览目录，但不能创建订单或访问网络实验室。
- 各账号的浏览器购物车分别存储在独立命名空间，切换账号不会继承对方的购物车。
- 非管理员读取其他用户的订单会返回 `404`；管理员保留跨账号查看与状态管理能力。
- 普通用户直接访问 `/api/lab/*` 会收到 `403`，隔离不只依赖前端隐藏。
- 页面启动时只显示登录/注册入口；有效 JWT 校验通过后才加载业务界面和对应菜单。

## 网页里可以做什么

- **登录门禁**：未认证时只显示登录、注册与访客入口；成功校验 JWT 后才加载业务界面。
- **角色化首页**：普通用户进入商品目录，管理员测试账户进入运行概览，访客进入只读目录。
- **工具可见性**：工具指南、Swagger、ReDoc 和 Postman 快捷入口只对管理员测试账户显示。
- **运行概览**：实时请求数、req/s、P50/P95/P99、错误率、最近 60 秒流量曲线、状态码分布和请求日志。
- **API 控制台**：选择方法、路径、Headers、JSON Body 发请求，查看响应和 Request ID；登录后自动附带 Bearer JWT。
- **商品目录**：搜索、分类、排序，加入购物车并创建受保护订单。
- **购物车页面**：购物车使用独立路由 `/cart`，集中展示商品数量、税费、应付金额和结算流程。
- **我的订单页面**：订单列表使用独立路由 `/orders`；点击订单或按编号查询会进入 `/orders/{订单号}`，刷新后仍保持订单详情路由。
- **结算与支付**：结算弹窗支持支付宝、微信支付与银行卡，并将支付方式和支付状态写入订单；支付完成后的按钮返回购物车。
- **网络实验室**：生成慢响应、随机故障、连续限流、302 重定向、请求回显和 multipart 上传。
- **工具指南**：四类测试工具的具体操作入口和下载链接。

点击“重置全部数据”会恢复账号、商品和种子订单，并清空内存中的流量统计。

## 核心接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/auth/login` | JSON 登录并返回 JWT |
| `POST` | `/api/auth/guest` | 创建只读访客会话 |
| `POST` | `/api/auth/register` | 注册普通用户并返回 JWT |
| `POST` | `/api/auth/token` | Swagger 使用的 OAuth2 表单登录 |
| `GET` | `/api/auth/me` | 当前用户（需 JWT） |
| `GET` | `/api/products` | 搜索、排序、分类和分页 |
| `GET` | `/api/products/{id}` | 商品详情 |
| `POST` | `/api/orders` | 创建订单（需 JWT） |
| `GET` | `/api/orders` | 当前用户的订单（需 JWT） |
| `GET` | `/api/orders/{id}` | 查询当前用户的一笔订单（需 JWT） |
| `PATCH` | `/api/orders/{id}/status` | 修改状态（仅管理员） |
| `GET` | `/api/lab/slow?delay_ms=1000` | 可调延迟 |
| `GET` | `/api/lab/flaky?failure_rate=0.3&mode=500` | 随机失败 |
| `GET` | `/api/lab/rate-limit` | 10 秒内最多 5 次 |
| `GET` | `/api/lab/status/500` | 指定状态码 |
| `POST` | `/api/lab/form` | `x-www-form-urlencoded` |
| `POST` | `/api/lab/upload` | `multipart/form-data` |
| `ANY` | `/api/lab/echo` | 回显请求 |
| `GET` | `/api/traffic/summary` | 实时流量指标 |

每个请求响应都包含：

- `X-Request-ID`：可用于在 Burp/Wireshark 中进行请求对照。
- `X-Process-Time-Ms`：服务端处理耗时。
- `X-Lab-Node`：模拟节点名。

## Postman

下载集合：

<http://127.0.0.1:8000/downloads/postman-collection>

也可以直接导入 [FastAPI_Test_Lab.postman_collection.json](postman/FastAPI_Test_Lab.postman_collection.json)。集合变量 `baseUrl` 默认是 `http://127.0.0.1:8000`。

建议使用 Collection Runner 按顺序执行。第一步“Login and capture JWT”会把 token 保存到 `{{access_token}}`，后续请求使用 Bearer Auth。multipart 上传请求需要把 `sample-upload.txt` 替换为项目 `downloads` 目录中的实际文件。

## JMeter

下载测试计划：

<http://127.0.0.1:8000/downloads/jmeter-plan>

或导入 [FastAPI_Test_Lab.jmx](jmeter/FastAPI_Test_Lab.jmx)。计划包含：

1. 登录并提取 `access_token`
2. 商品搜索
3. 250 ms 慢响应接口
4. 带 Bearer JWT 与唯一幂等键的订单创建

默认配置为 8 线程、5 秒 Ramp-up、每线程 10 次循环。第一次练习建议改成 1 线程 1 循环做冒烟测试，再逐级加压。JMeter 运行期间刷新网页“运行概览”，可直接看到流量曲线和延迟统计。

订单负载会扣减库存。连续高压测试后可在网页中点击“重置全部数据”，或在 PowerShell 中执行：

```powershell
$login = Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}' `
  http://127.0.0.1:8000/api/auth/login
Invoke-RestMethod -Method Post `
  -Headers @{ Authorization = "Bearer $($login.access_token)" } `
  http://127.0.0.1:8000/api/lab/reset
```

## Burp Suite

1. 在 Burp 中启用 Proxy listener：`127.0.0.1:8080`。
2. 用 Burp 内置浏览器打开 <http://127.0.0.1:8000>。
3. 在 Proxy HTTP history 中观察登录 JSON、Bearer JWT 和订单请求。
4. 把请求发送到 Repeater，可修改 Headers、查询参数和 Body 观察服务端校验。

本环境使用明文 HTTP，不要求为本站配置 HTTPS 证书。Burp 的 Proxy history 是标准模式下更清晰的请求捕获工具。

## Wireshark

Windows 回环流量捕获通常需要安装 Npcap。服务启动后：

1. 在 Npcap Loopback Adapter 或 Adapter for loopback traffic capture 上开始捕获。
2. 在网页“网络实验室”执行一次“请求回显”。
3. 使用显示过滤器 `tcp.port == 8000 && http`。
4. 对照响应中的 `X-Request-ID`、HTTP 路径和 JSON Body。

还可以抓取限流场景并观察 `429`、`Retry-After`、`X-RateLimit-*` 响应头。

## 本地测试

```powershell
Set-Location "D:\Documents\ChatGPT\fastapi-test-lab"
.\test.ps1
```

当前测试覆盖健康检查、登录失败/成功、JWT 访问、商品查询、订单鉴权、幂等重放、管理员状态修改、表单、上传、回显、状态码模拟、限流和流量统计。

## 项目结构

```text
app/             FastAPI 应用、路由、SQLite 数据层
static/          网页控制台、登录门禁与暖白技术编辑主题
DESIGN.md        9 章节视觉与交互规范
tests/           pytest 接口测试
postman/         Postman Collection v2.1
jmeter/          JMeter 5.6+ Test Plan
downloads/       网页可下载的测试样例
data/            SQLite 数据库（运行后生成）
```

此项目是测试练习环境，不是生产模板。演示账号、固定签名密钥、重置能力和内存流量统计均为实验用途设计。
