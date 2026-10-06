# Agent 应用开发练习

基于 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents)
教程进行的个人实践，包含智能体推理模式、工具调用、记忆、RAG 和上下文工程等示例。

## 开发环境

使用 Python 3.13+ 和 uv 管理依赖。在项目根目录执行：

```powershell
uv sync
Copy-Item .env.example .env
```

复制配置模板仅用于首次配置；已有 `.env` 时直接编辑它。按使用的服务填写密钥、
数据库地址和模型参数，再运行相应的练习脚本。各脚本可能需要不同的外部服务。

Git 跟踪源码、`pyproject.toml`、`uv.lock` 和 `.env.example`。
真实 `.env`、虚拟环境、本地记忆数据库、导入文档和生成报告由 `.gitignore` 排除。

## LLM 服务

当前 `.env` 使用 CLIProxy 的 Codex 通道：

- `LLM_MODEL_ID`：`gpt-6.1-sol`
- `LLM_BASE_URL`：`http://127.0.0.1:8317/v1`
- `LLM_API_KEY`：本机 CLIProxy 的客户端访问密钥。
- `OPENAI_API_KEY`、`LLM_MODEL`：通过 dotenv 变量引用跟随上面对应的参数。
  OpenAI 密钥别名确保 HelloAgents 自动检测时使用当前 OpenAI 兼容服务。

原来的本地 Ollama 三项参数已注释保存在 `.env` 中，模型为 `gemma4:12b`，
地址为 `http://127.0.0.1:11434/v1`。需要切回时，注释当前 CLIProxy 的三项
`LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`，取消本地 Ollama 三项参数的注释，
然后重新启动 Python 程序。两个配置只保留一组生效；兼容别名会自动跟随。

CLIProxy 调用需要 CLIProxy 核心及 `127.0.0.1:6789` 上的网络代理正在运行。
`main.py` 等在代码中明确指定模型和地址的练习脚本，仍以代码参数为准。

## 本地 Neo4j

Neo4j 使用 `compose.neo4j.yaml` 管理，只运行一个名为 `neo4j` 的容器。

- 网页管理界面：http://localhost:7474/browser/
- Python 连接地址：`bolt://localhost:7687`
- 用户名和密码：使用本地 `.env` 中的 `NEO4J_USERNAME`、`NEO4J_PASSWORD`。
- 镜像固定为本机已有的 Neo4j Community 2026.08.1 镜像摘要。
- 数据和日志继续使用原来的 `neo4j_data`、`neo4j_logs` 数据卷。
  两个卷声明为 `external`，Compose 不会创建空卷来替换已有数据。
- 端口只绑定到本机 `127.0.0.1`。

在项目目录执行：

```powershell
# 本机 Docker CLI 暂未加入 PATH，使用完整路径。
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
& $docker compose -f compose.neo4j.yaml up -d --pull never
& $docker compose -f compose.neo4j.yaml ps
& $docker compose -f compose.neo4j.yaml logs --tail 50 neo4j
```

停止和重新启动已有容器：

```powershell
& $docker compose -f compose.neo4j.yaml stop
& $docker compose -f compose.neo4j.yaml start
```

`up -d` 会按这份配置创建或启动服务；`start` 启动已有容器。
不要另外运行一条 `docker run` 并挂载同一个 `neo4j_data`，否则两个进程会争用数据库文件锁。
容器名称包含 `backup` 并不代表它有独立备份；备份必须另行创建。

### 2026-10-02 端口修复记录

Windows 的 IPv4/IPv6 TCP 动态端口范围此前是 `1024–15000`，
自动排除范围 `7681–7780` 包含了 Neo4j 的默认端口 `7687`，实际绑定返回权限错误。
已恢复 Windows 默认动态范围 `49152–65535` 并重启 WinNAT。
修复后 `7474`、`7687` 均可绑定，数据库查询和 Bolt 握手成功。

`scripts/repair-neo4j-port.ps1` 保存了本次修复步骤，仅用于再次确认相同系统问题后的管理员修复，
不是日常启动命令。它会短暂重启 WinNAT，可能影响 Docker/WSL 网络。
正常使用无需运行该脚本，也不需要重启 Windows。

参考：[Microsoft TCP 动态端口说明](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting)。
