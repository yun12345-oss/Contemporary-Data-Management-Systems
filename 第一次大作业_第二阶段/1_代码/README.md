# 问卷系统 配置与运行说明

应用版本：2.0.2。本目录为可运行源码，在第一阶段核心上扩展题目版本、共享、题库与跨问卷统计，后端、前端、MongoDB定义及测试均随包提供。启动后，用浏览器访问网页即可，填写者不需要安装MongoDB。请整体解压材料，不能只拿backend文件夹或某个启动脚本。

## 一 目录与阅读顺序

```text
1_代码/
├─ backend/
│  ├─ app/                  接口、请求模型、服务、规则、统计和基础设施
│  ├─ tests/                领域及真实MongoDB集成测试
│  ├─ scripts/              演示数据、显式约束升级
│  ├─ pyproject.toml        Python包定义及测试配置
│  └─ requirements-lock.txt 锁定依赖
├─ frontend/
│  ├─ src/                  Vue页面、输入组件、规则和保存状态
│  ├─ tests/                普通单元及组件/路由测试
│  ├─ package.json          脚本与依赖
│  └─ pnpm-lock.yaml        前端锁定依赖
├─ database/                schema、索引、生成源、示例及旧约束
├─ scripts/                 安装、构建、启动、初始化及测试入口
├─ .env.example             配置模板
├─ compose.yaml / Dockerfile 可选容器配置，未实际验证
└─ 源码文件清单.sha256.json 交付内容哈希
```

第一次使用按本文件安装和启动；操作流程见[系统说明](../2_文档/系统说明.md)，设计见[数据库](../2_文档/数据库设计.md)、[API](../2_文档/API说明.md)、[关键逻辑](../2_文档/关键逻辑说明.md)。用例与原始结果在[测试材料](../3_测试用例/测试用例与结果.md)，完整报告和AI日志在第4部分。

## 二 环境与准备

| 项目 | 要求 | 用途与检查 |
| --- | --- | --- |
| 操作系统 | 已验证Windows本地路径 | PowerShell脚本为主要入口，其他系统需自行调整 |
| Python | 3.11或3.12 | `python --version`；需具备venv与pip能力 |
| Node.js | 22.12以上，当前环境使用24系列 | `node --version`；支持前端工具和TS测试 |
| pnpm | 11系列 | `pnpm --version`；使用已有锁定文件 |
| MongoDB | 8.x，启用副本集 | mongod.exe路径可显式传给脚本 |
| 网络 | 首次安装能访问依赖源 | 安装完成后本机使用不依赖云服务 |

发布和提交要同时修改几处数据，因此MongoDB需要以副本集方式运行，才能使用事务。课程演示用一个节点的survey-rs即可，但这不等于做过多节点容灾验证。不要将无关业务MongoDB实例当作本项目数据库启动，也不要随意删除数据目录。

## 三 首次安装与配置

以下命令均在本目录运行，路径中的MongoDB安装位置须替换为实际值。当前电脑示例位置为`D:\software\MongoDB\bin\mongod.exe`，不是所有电脑的固定路径。

```powershell
# 在“1_代码”目录打开PowerShell
.\scripts\install.ps1 -PythonExecutable python -PackageManager pnpm
.\scripts\start-local.ps1 -MongoExecutable 'D:\software\MongoDB\bin\mongod.exe' -SeedDemo
```

install.ps1的工作：建立.runtime虚拟环境，安装锁定的后端依赖与项目包，安装锁定前端依赖并构建，缺少.env时生成随机密钥。已有.env保持不动。若Python命令不是python，用-PythonExecutable传入实际命令或路径；pnpm也可通过-PackageManager显式指定。

start-local.ps1的工作：检查虚拟环境与前端产物，探测本机27019；需要时用.local/mongo-live启动mongod，初始化/检查副本集并等待主节点，按需导入演示数据，然后启动127.0.0.1:8000。当前脚本的MongoDB进程在后台运行，终端承担网页服务。

若PowerShell执行策略拦截，仅对本次进程使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -PythonExecutable python -PackageManager pnpm
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -MongoExecutable 'D:\software\MongoDB\bin\mongod.exe' -SeedDemo
```

无需为了课程项目永久修改系统执行策略。

## 四 日常启动、停止与重建

已有.runtime和frontend/dist时：

```powershell
.\scripts\start-local.ps1 -MongoExecutable 'D:\software\MongoDB\bin\mongod.exe'
```

打开`http://127.0.0.1:8000`；接口文档为`http://127.0.0.1:8000/docs`；数据库健康检查为`http://127.0.0.1:8000/api/health`。使用网页期间保持这个终端运行。按Ctrl+C会停止网页，MongoDB后台进程通常仍在；这时网页打不开并不表示数据丢失。需要完全停止数据库时应使用MongoDB正常关闭方式；不要通过删除文件“停止数据库”。

修改前端后在本目录执行：

```powershell
.\scripts\build.ps1 -PackageManager pnpm
```

完成后重启后端，浏览器先保存未同步内容，再刷新加载新页面。后端直接启动仅适用于数据库已经运行：

```powershell
.\.runtime\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

前端开发可另开终端进入frontend执行`pnpm dev`，通过Vite代理访问后端。默认开发来源允许5173；若Vite自动换到其他端口，应核对ALLOWED_ORIGINS，端口变了可能导致写请求403，需要先核对配置。课程演示优先使用同源8000入口。

## 五 配置参数与修改影响

.env是本机配置，不随提交包提供；.env.example是可查看的模板。业务数据、会话和填写过程均在MongoDB，配置文件不是第二套业务数据库。

| 参数 | 类型与本项目示例 | 用途 | 修改影响 |
| --- | --- | --- | --- |
| MONGO_URI | 字符串：mongodb://127.0.0.1:27019/?replicaSet=survey-rs | 数据库连接与副本集发现 | 地址或副本集名不匹配会连接失败；启动脚本本地准备路径仍固定27019 |
| MONGO_DB | 字符串：survey_lab | 业务数据库名 | 改名会连接另一个库，不能认为旧数据消失 |
| SECRET_KEY | 至少32字符随机值，不能保留replace-模板 | 签名与问卷范围HMAC关联 | 重建会影响旧凭证、重复限制和草稿恢复，不可随意轮换 |
| COOKIE_SECURE | true/false；本机HTTP为false | Cookie是否仅HTTPS发送 | HTTP下设true可能导致登录后仍无法带会话 |
| ALLOWED_ORIGINS | 逗号分隔完整来源 | 浏览器写请求来源检查 | 协议、主机和端口需匹配，修改后重启；不是填写者白名单 |
| TEST_MONGO_URI | 测试进程环境变量 | 覆盖测试MongoDB地址 | 默认27019/survey-rs；不要使用不理解的真实业务环境 |

默认允许来源包含localhost与127.0.0.1的8000/5173。没有.env或环境变量时，底层配置的Mongo连接回退值是27017，但密钥仍未满足运行要求；应通过安装脚本正确生成配置，不依赖这一回退值完成启动。

本地脚本默认：网页127.0.0.1:8000，数据库127.0.0.1:27019，副本集survey-rs，数据.local/mongo-live，日志.local/mongo-live.log。.local和.env都不应删除后再声称原数据仍可恢复。第一阶段数据库升级必须按本文第二阶段升级补充执行migrate_phase2.py；本次从六集合扩展到十一集合，正式答卷格式保持不变。

## 六 演示数据与账号

首次带-SeedDemo启动后，示例账号demo，密码SurveyDemo2026!；也可自行注册。种子脚本查找已有demo用户和带campus-v1标识的问卷，存在时复用，不清空数据、不重复插入初始样例，也不重置已有账号密码。若同名账号原密码不同，请使用原密码或注册新账号，不以删除用户解决。

全新种子数据有3份构造答案，来自同一账号，数字6/8/4平均6；历史浏览器验收或个人填写会增加记录，因此本机当前数量不保证仍是3。演示数据不含真实个人资料。未完成草稿不计入正式统计。

## 七 更新与数据库升级

如果已经运行第二阶段，通常只需要更新程序、重新构建并重启。如果还在使用第一阶段数据库，则要先备份并停止旧程序写入，检查通过后再执行迁移。两种情况不要混用步骤。

### 7.1 已有第二阶段更新

停止旧网页服务，保留原配置及数据库，使用本目录完整源码并重新构建前端、启动2.0.2。本次不改数据库schema，无需重复运行迁移。浏览器刷新以获取新构建。不要更换原SECRET_KEY。

### 7.2 从第一阶段升级

先备份原业务数据和集合约束，停止所有旧程序写入。若使用新的代码目录，先复制原.env至代码根目录，再安装依赖；install.ps1不会覆盖已有.env。确保副本集已运行，在本目录执行：

```powershell
.\.runtime\Scripts\python.exe backend/scripts/migrate_phase2.py --check
.\.runtime\Scripts\python.exe backend/scripts/migrate_phase2.py --apply --journal artifacts/phase2/schema-upgrade.json
```

先检查预检结果，再显式应用。日志不能覆盖，DDL不是跨集合事务；失败时按日志核对。若已有第二阶段业务数据，不能只恢复旧validator继续运行旧代码，需要完整维护前备份。普通启动不会覆盖原约束。

## 八 测试、材料样例及结果位置

数据库启动后，从本目录执行：

```powershell
.\scripts\run-tests.ps1
cd frontend
pnpm test
pnpm run build
```

后端测试创建随机survey_lab_test_*数据库，只删除本次自行生成的测试库。原业务库survey_lab不被测试清空；测试需要对该本地测试环境具备创建、索引、事务和删除测试库权限。普通单元与组件两组由pnpm test依次执行，生产构建包含TypeScript检查。

运行后，后端JUnit写入本目录artifacts/test-results.xml，组件JUnit写入artifacts/component-tests.xml；普通单元默认只输出控制台。本次已保存结果统一放在[测试证据](../3_测试用例/测试证据)，这些是随包保存的既有记录；你自己运行后的输出会保存在代码目录。

### 8.1 可重复的材料API链

安装完成且MongoDB副本集运行后，在本目录执行：

```powershell
.\.runtime\Scripts\python.exe ..\3_测试用例\测试证据\API调用链示例.py
```

该脚本只创建随机临时库，自动验证题目v1/v2、导入、升级、发布及原过程提交，最后清理自己的临时库。默认重写相邻的示例与执行记录；需要保留原证据时，用`--output`指定新的输出目录。不增加既有260项测试计数。

### 8.2 验证状态

代码来源为已验证的2.0.2；仅重新组织材料及补充运行说明，不修改业务代码。保留安装、构建、启动、初始化、测试五个根脚本，显式迁移和演示脚本在backend/scripts。没有把依赖、dist、业务数据库或真实.env打包。

2026-10-25的260项记录见第3部分，2026-10-26材料样例及交付核对另记。Docker配置随源码保留但未实际验证。浏览器人工验收不能由组件测试替代。

## 九 故障排查

| 现象 | 可能原因 | 检查与处理 |
| --- | --- | --- |
| 提示Run install first | 未安装或只拷贝了部分文件 | 确认在完整1_代码内，运行install.ps1 |
| 缺少frontend/dist | 尚未构建 | 用build.ps1或安装脚本构建，成功后重启 |
| 找不到mongod.exe | 安装目录不同或未加入PATH | 用-MongoExecutable传入实际绝对路径 |
| 27019连接失败 | 数据库没启动、进程退出或目录权限问题 | 看.local/mongo-live.log，确认目录可写及端口配置 |
| 事务要求副本集 | 误连普通standalone实例 | 核对URI、survey-rs和启动方式，勿删除旧库重试 |
| 8000端口占用 | 同一服务已启动或其他程序占用 | 先打开网页核对，确认进程后停止旧服务，避免盲目结束无关进程 |
| 约束不一致拒绝启动 | 使用已存在但非目标约束的库 | 备份并停写，按显式--check/--apply流程，不手改校验器 |
| 登录反复失效 | Cookie协议、地址或浏览器会话不一致 | HTTP下检查COOKIE_SECURE，保持同一来源，查看/me结果 |
| 写请求403 | 当前Origin未允许 | 检查完整协议/主机/端口，配置后重启，不删除来源检查 |
| 保存409 | 其他页更新或过程已结束/问卷关闭 | 保留本页输入，读取服务器状态后明确决定，不自动覆盖 |
| 重进问卷找不到旧草稿 | 账号/链接/数据库/密钥不同，或已经提交/放弃 | 核对登录身份和配置；没有持久化过的旧页面输入不能事后恢复 |
| 首次安装下载失败 | 依赖源或网络问题 | 保留错误输出，检查访问；不要随意删除锁定文件改版本 |
