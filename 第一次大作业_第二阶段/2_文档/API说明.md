# 问序问卷系统第二阶段 API 说明

应用版本：2.0.2。

本文介绍接口怎样调用、需要哪些参数、返回什么，以及失败后怎样处理。API01～API50 是文档编号，不表示必须按编号依次调用。

完整机器定义见[接口静态定义](../3_测试用例/测试证据/接口静态定义.openapi.json)。部分接口没有声明完整响应模型，OpenAPI 中响应结构较简略，不代表实际没有返回数据。

## 一、调用前需要了解的规则

### 1.1 地址与身份认证

业务接口统一以 `/api` 开头。

注册或登录成功后，服务器设置会话 Cookie。浏览器随后携带 Cookie，后端据此识别当前账号，不能通过请求中的用户名或用户 ID 随意更换操作者。

健康检查、注册、登录和退出不要求预先登录，其余接口需要有效会话。路径中包含 `public` 也不代表免登录。

浏览器跨站写请求受来源检查约束，写请求还检查声明的请求大小。不能通过前端隐藏按钮代替后端权限检查。

### 1.2 参数放在哪里

| 参数位置 | 写法 | 示例 |
|---|---|---|
| 路径参数 | 放在 URL 对应位置 | `/api/surveys/{sid}` |
| 查询参数 | 放在 `?` 后 | `?page=2&search=年龄` |
| 请求体 | 使用 JSON 发送 | `{"revision":2}` |

本文中的 `{sid}`、`{qid}` 等是占位符，实际调用时替换为服务器返回的 ID。

### 1.3 几种 ID 不要混用

| 名称 | 含义 |
|---|---|
| `sid` | 问卷 ID |
| `share` | 问卷分享码 |
| `aid` | 可恢复填写过程 ID |
| `qid` | 由具体路径决定，可能是题目系列 ID，也可能是问卷实例 ID |
| `vid` | 独立题目版本 ID |
| `lid` | 题库 ID |
| `iid` | 题库成员 ID |
| `gid` | 授权记录 ID |
| `version_id` | 问卷发布快照 ID |
| `question_version_id` | 常用题确定版本 ID |

例如，`/api/questions/{qid}` 使用系列 ID，`/api/surveys/{sid}/questions/{qid}/values` 使用问卷实例 ID。

### 1.4 修订号怎样使用

`revision` 表示对象当前修订状态，必须使用服务器最近返回的值。

| 操作 | 使用哪个 revision |
|---|---|
| 保存、发布、关闭问卷 | 问卷 revision |
| 导入或升级问卷实例 | 问卷 revision |
| 创建、恢复或归档题目版本 | 题目系列 revision |
| 修改题库及成员 | 题库 revision |
| 撤销授权 | 授权记录 revision |
| 保存、放弃或提交填写过程 | 填写过程 revision |

收到 409 后，应重新读取并核对，不应盲目换成新编号强制覆盖。

`activity_seq` 是服务端并发协调字段，不代替用户编辑修订号，也不应由客户端自行维护。

## 二、成功与错误返回

创建接口通常返回 201，其他成功操作通常返回 200，具体以对应路由为准。

| 状态码 | 常见含义 | 客户端处理 |
|---|---|---|
| 200 | 查询或操作成功 | 使用实际返回内容更新状态 |
| 201 | 创建成功 | 保存新对象 ID 和 revision |
| 401 | 登录、会话或凭证失效 | 重新登录同一账号，妥善处理未同步输入 |
| 403 | 明确禁止、来源不一致或越权 | 核对权限，不通过拼接地址绕过 |
| 404 | 不存在，或隐藏无权资源的存在 | 核对 ID、归属和授权 |
| 409 | 修订冲突、重复记录或状态不允许 | 重新读取后由用户决定 |
| 413 | 请求内容过大 | 减少请求内容 |
| 422 | 字段、参数或业务配置不合法 | 根据具体问题修改 |
| 503 | 数据库操作失败或暂不可用 | 不提前显示保存成功，核对后重试 |

错误响应通常包含 `error`，可能附带 `details`。例如以下只是结构示意，不是新增抓包记录：

```json
{
  "error": "请检查填写内容",
  "details": {
    "q3": "此题必须回答"
  }
}
```

不同接口可能使用不同状态码保护资源存在性，不能将所有权限错误统一理解成 403。

## 三、先理解主要调用顺序

### 3.1 普通问卷与可恢复填写

```text
注册或登录
    → 创建问卷
    → 保存草稿
    → 发布
    → 获取或开始填写过程
    → 保存输入
    → 使用最新 revision 提交
    → 查看统计
```

当前页面的自动保存与恢复使用 `attempt` 接口。提交以服务端已保存草稿为准，不再附带第二套答案。

### 3.2 常用题复用

```text
创建常用题 v1
    → 可选：共享或加入题库
    → 导入问卷
    → 设置实例必答与跳转
    → 发布问卷
```

### 3.3 更新已有实例

```text
创建题目新版
    → 保存当前问卷草稿
    → 选择目标版本并预览
    → 核对预览上下文
    → 确认升级
    → 修复规则问题
    → 重新发布
```

预览不冻结授权，也不代表已经升级。确认时仍检查目标权限和问卷 revision。

可重复示例见[API调用链示例](../3_测试用例/测试证据/API调用链示例.py)，已有 22 步记录见[执行记录](../3_测试用例/测试证据/API调用链执行记录.json)。这些属于材料示例，不重复累计为新的业务测试。

## 四、账号与会话

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API01 | `GET /api/health` | 无 | `status`、`version`；检查数据库连接 |
| API02 | `POST /api/auth/register` | 用户名、密码 | 201，`id`、`username`，设置会话 Cookie |
| API03 | `POST /api/auth/login` | 用户名、密码 | `id`、`username`，设置会话 Cookie |
| API04 | `POST /api/auth/logout` | 无 | `ok=true`，删除当前会话及 Cookie |
| API05 | `GET /api/auth/me` | 有效会话 | 当前账号 `id`、`username` |

用户名为 3～40 字符，符合允许字符模式；密码为 8～128 字符。

注册重名返回 409，格式错误返回 422，登录凭证错误返回 401。登录成功可能创建新会话；退出可重复调用。

示意请求：

```json
{
  "username": "demo_user",
  "password": "ExamplePass123!"
}
```

以上仅展示格式，不代表项目预设账号。

## 五、问卷编辑与发布

以下操作面向问卷所有者，列表仅返回自己的问卷。

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API06 | `GET /api/surveys` | 查询 `page` | `items`、`total`、`page`，列表项含回答数量 |
| API07 | `POST /api/surveys` | `title` | 201，完整问卷，初始为空草稿 |
| API08 | `GET /api/surveys/{sid}` | 问卷 ID | 完整问卷及当前草稿 |
| API09 | `PUT /api/surveys/{sid}/draft` | `revision`、完整 `draft` | 更新后的问卷及 `draft_issues` |
| API10 | `POST /api/surveys/{sid}/publish` | `revision`、可选 `deadline` | 发布快照及问卷元数据 |
| API11 | `PATCH /api/surveys/{sid}/status` | `status="closed"`、可选 `revision` | `ok` 和问卷元数据，关闭问卷 |
| API12 | `GET /api/surveys/{sid}/versions` | 问卷 ID | 发布版本列表，不含完整 definition |
| API13 | `GET /api/surveys/{sid}/versions/{version}` | 问卷 ID、发布序号 | 指定完整发布快照 |

### 5.1 保存草稿

保存成功会增加 revision，但不改变已发布内容，也不使独立截止时间设置生效。

来源实例需带回原来源字段供核对，不能随意增删替换。旧 revision 通常返回 409，来源不一致可能返回 403，结构错误返回 422。

### 5.2 发布

发布重新检查题型、跳转、可作答性和来源。截止时间必须为空，或带时区且晚于当前时间。

成功发布生成新的问卷发布版本。网络结果不确定时应先查询，不能直接重复创建发布。

示意请求：

```json
{
  "revision": 3,
  "deadline": null
}
```

### 5.3 关闭

接口只接受 `closed`。建议携带当前 revision，避免关闭基于过期页面执行。

关闭不删除历史快照和正式答案。已有填写过程仍可只读恢复，但不允许新增保存或提交。

## 六、填写、恢复、提交与整卷统计

### 6.1 当前可恢复填写流程

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API14 | `GET /api/public/{share}` | 分享码 | 标题、说明、策略、题数、版本及截止时间 |
| API17 | `GET /api/public/{share}/attempt` | 分享码 | 当前账号的进行中过程；不存在时为 null |
| API18 | `POST /api/public/{share}/attempt` | `anonymous` | 新建或返回已有进行中过程 |
| API19 | `GET /api/attempts/{aid}` | 过程 ID | 原定义、答案、路径、问题、revision、只读状态等 |
| API20 | `PUT /api/attempts/{aid}` | `revision`、`answers`、可选位置 | 保存后的过程视图 |
| API21 | `POST /api/attempts/{aid}/abandon` | `revision` | `ok=true`，放弃过程并清除原始输入 |
| API22 | `POST /api/attempts/{aid}/submit` | `revision` | 正式答卷回执：`id`、`version`、`submitted_at` |

所有过程操作都检查账号归属，不允许通过他人的 aid 读取草稿。

同账号、同问卷最多一份进行中过程。开始接口可返回已有过程；问卷关闭后不能创建新过程，已有过程读取时会说明只读状态。

保存示例：

```json
{
  "revision": 1,
  "answers": {
    "q1": "yes",
    "q3": "25"
  },
  "current_question_id": "q3"
}
```

题目 ID 必须来自该过程的发布快照。草稿允许待修正输入，不代表提交会接受无效答案。

提交请求：

```json
{
  "revision": 2
}
```

提交前先确认最新输入已经保存，并使用保存返回的 revision。重复提交已完成的同一过程返回原回执；放弃后的过程不再接受保存或提交。

### 6.2 保留的旧兼容流程

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API15 | `POST /api/public/{share}/start` | `anonymous` | 签名 token、脱敏定义、版本和策略 |
| API16 | `POST /api/responses` | `token`、`answers` | 正式答卷回执 |
| API23 | `POST /api/evaluate` | `token`、`answers` | 清理后的答案和路径，不写答卷 |

旧流程通过签名 token 绑定账号、问卷和发布版本，仍检查状态、答案和重复策略。不能把旧 token 请求中的答案与可恢复过程草稿混成同一过程的两个答案来源。

同一凭证重复提交返回已有回执，但重复开始可能产生不同凭证。

### 6.3 原有整卷统计与答案明细

| 编号 | 方法与路径 | 查询参数 | 返回与权限 |
|---|---|---|---|
| API24 | `GET /api/surveys/{sid}/statistics` | `version`、`start`、`end` | 问卷所有者查询，返回份数、人数及各题统计 |
| API25 | `GET /api/surveys/{sid}/questions/{qid}/values` | `version`、`page`、`start`、`end` | 问卷所有者查询实例答案明细 |

这里的 qid 是问卷实例 ID，version 是问卷发布序号。

时间必须包含时区，开始不晚于结束。汇总授权接收者不能借 API25 读取他人的原始明细。

## 七、独立题目、版本与使用查询

| 编号 | 方法与路径 | 输入或筛选 | 成功返回与权限 |
|---|---|---|---|
| API26 | `GET /api/questions` | `page`、`search`、可选 `question_id` | 自有题或有效 use 版本列表 |
| API27 | `POST /api/questions` | `content`、可选 `change_note` | 201，`question` 与初始 `version` |
| API28 | `GET /api/questions/{qid}` | 系列 ID | 所有者读取系列及完整版本历史 |
| API29 | `GET /api/question-versions/{vid}` | 版本 ID | 所有者或该版本 use 接收者读取版本 |
| API30 | `GET /api/question-versions/{vid}/diff/{other}` | 两版本 ID | 同系列、均可读版本的差异数组 |
| API31 | `POST /api/questions/{qid}/versions` | 内容、revision、父版本 | `question`、新 `version`、`diff` |
| API32 | `POST /api/questions/{qid}/restore` | revision、父版本、恢复来源 | `question`、恢复产生的新版本及差异 |
| API33 | `POST /api/questions/{qid}/archive` | `revision` | 归档后的题目 |
| API34 | `GET /api/questions/{qid}/usage` | 系列 ID、`page` | 按权限返回分类数量及自有明细 |

### 7.1 创建题目

```json
{
  "content": {
    "type": "number",
    "title": "你的年龄",
    "options": [],
    "validation": {
      "min": 0,
      "max": 120,
      "integer_only": true
    }
  },
  "change_note": "初版"
}
```

`content` 只含题型、题干、选项和校验，不保存问卷必答和跳转。

重复创建请求可能生成不同系列，不能在结果不确定时盲目重试。

### 7.2 创建与恢复版本

创建版本需要明确父版本，并检查题目归属、未归档和当前 revision。

恢复请求示意：

```json
{
  "revision": 3,
  "parent_version_id": "current_version_id",
  "restored_from_version_id": "historical_version_id",
  "change_note": "恢复历史内容"
}
```

恢复会新增版本，不覆盖旧文档。两种版本引用必须属于同一系列。旧修订请求返回冲突，不自动替用户选择其他父版本。

### 7.3 使用追踪

题目所有者可看自有明细及按权限提供的外部脱敏数量；有当前或历史使用关系的接收者只能看自己的使用。

草稿、当前发布和历史发布可能重叠，历史发布包含当前发布，总问卷数按 ID 并集去重。

## 八、使用授权与汇总授权

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API36 | `POST /api/grants` | 授权类型、版本、接收者及范围 | 创建或重新激活授权 |
| API37 | `GET /api/grants` | `page` | 自己发出或收到的授权列表 |
| API38 | `POST /api/grants/{gid}/revoke` | 授权当前 `revision` | 撤销后的授权记录 |

### 8.1 使用授权

由题目所有者授予，指向确定版本，survey_id 为 null：

```json
{
  "kind": "use",
  "question_version_id": "question_version_id",
  "username": "recipient_user",
  "survey_id": null
}
```

不会自动开放未来版本、修改、派生、转授或答卷读取。

### 8.2 汇总授权

由问卷所有者授予，必须指定问卷和该问卷发布使用过的版本：

```json
{
  "kind": "aggregate",
  "question_version_id": "question_version_id",
  "username": "recipient_user",
  "survey_id": "survey_id"
}
```

题目作者不能给自己开放他人的问卷数据。

### 8.3 撤销与重新授权

撤销要求授予者和 revision 正确。已有合法实例继续使用的规则，不表示撤销后仍能新增导入。

同资源、同接收者重新授权可以复用记录并增加 revision，因此不应理解成完全无副作用的重复请求。

## 九、题库与成员管理

| 编号 | 方法与路径 | 输入 | 成功返回与作用 |
|---|---|---|---|
| API39 | `GET /api/libraries` | `page` | 自有题库列表 |
| API40 | `POST /api/libraries` | `name`、可选 `description` | 201，完整题库 |
| API41 | `PUT /api/libraries/{lid}` | revision、名称、说明 | 更新后的题库 |
| API42 | `GET /api/libraries/{lid}/items` | `page`、`search`、可选 `question_id` | `library`、`items`、`total`、`page` |
| API43 | `POST /api/libraries/{lid}/items` | revision、版本、可选位置 | 201，`ok`、新 revision |
| API44 | `PUT /api/libraries/{lid}/items/{iid}` | revision、目标版本、可选位置 | `ok`、新 revision |
| API45 | `POST /api/libraries/{lid}/items/{iid}/remove` | `revision` | `ok`、新 revision |

成员操作使用题库 revision，不是题目系列 revision。

同库同确定版本不能重复，更新目标需属于同系列且当前有权使用。旧版本失效不阻止选择有效新版，但提交时仍重新核权。

位置范围为 0～100000，省略时使用请求模型默认值。更新时需要明确目标版本，不能把 PUT 当成任意字段的局部 PATCH。

成员返回的 `available=false`、`version=null` 表示内容当前不可读，不应继续显示撤销后的版本内容。搜索针对可读固定版本，先筛选再分页。

## 十、问卷实例的来源操作

以下接口先检查问卷所有者，并使用当前问卷 revision。

| 编号 | 方法与路径 | 请求字段 | 返回与作用 |
|---|---|---|---|
| API46 | `POST /api/surveys/{sid}/questions/import` | revision、question_version_id | 更新后的问卷，生成新实例和来源 |
| API47 | `POST /api/surveys/{sid}/questions/upgrade-preview` | revision、instance_id、question_version_id | `diff`、`issues`、`definition`，不写问卷 |
| API48 | `POST /api/surveys/{sid}/questions/upgrade` | 同预览字段 | 更新后的问卷及草稿问题 |
| API49 | `POST /api/surveys/{sid}/questions/detach` | revision、instance_id | 移除允许解除的自有来源 |
| API50 | `POST /api/surveys/{sid}/questions/save-reusable` | revision、instance_id | 201，`survey`、`question`、`version` |

### 10.1 导入

后端读取确定版本、检查当前使用权，再生成新实例。初始必答，规则为空，不复制其他问卷的跳转目标。

重复合法导入会产生不同实例，不是无副作用重试。

### 10.2 升级预览与确认

```json
{
  "revision": 5,
  "instance_id": "instance_id",
  "question_version_id": "target_version_id"
}
```

预览不写草稿，也不授予最终使用权。确认仍检查目标当前授权和同系列关系。

前端需绑定预览时的实例、来源、目标、revision 和本地草稿状态。切题或编辑后重新预览，确认阶段不得隐式自动保存来替换预览修订号。

升级保留实例 ID、必答和跳转。规则失效时可保存待修复草稿，但修复前不能发布。

### 10.3 解除与另存

自有来源题可以通过专门接口解除关联。共享来源不能解除或另存成自己的系列，普通保存也不能删除来源绕过限制。

保存为常用题只提取内容，不复制问卷跳转，也不自动关联旧答案。

## 十一、同版本跨问卷统计

### API35

```text
GET /api/question-versions/{vid}/statistics
```

| 查询参数 | 要求 |
|---|---|
| `start` | 可选，带时区的开始时间 |
| `end` | 可选，带时区且不早于开始时间 |
| `survey_id` | 可选，进一步限定有权统计的问卷 |
| `boundaries` | 可选，2～30 个严格递增的安全数值边界 |

数组边界使用重复查询参数，例如：

```text
/api/question-versions/{vid}/statistics?boundaries=0&boundaries=18&boundaries=30
```

真实 URL 中，时间和其他参数应由客户端正确编码，尤其不要将时区中的 `+` 误当空格。

未传分组边界使用默认值；非法、非有限、超范围或倒序边界返回 422。显式空数组不等于未传参数。

### 11.1 返回内容

公共字段包括：

- `question_id`、`question_version_id`、`version`、`content`。
- `coverage_surveys`、`answered_surveys`。
- `valid_responses`、`valid_answers`、`notice`。
- 题型相关的选项结果，或数字均值、最小值、最大值和分布。

没有跨问卷 `respondent_count` 或原始文本答案列表。

### 11.2 权限与计数

先限定自有或有效 aggregate 授权问卷，再从正式答卷关联原快照，匹配来源版本和实例。

| 内容 | 口径 |
|---|---|
| 覆盖问卷 | 发布使用过该版本的授权问卷，包括零作答 |
| 有作答问卷 | 时间范围内有该版本有效作答 |
| 答卷数 | 正式答卷 ID 去重 |
| 作答条数 | 按匹配实例计数 |
| 多选比例 | 选项次数除以有效作答条数 |
| 时间 | 正式 `submitted_at`，包含起止端点 |

题目作者不自动获得他人数据。不同版本不自动合并，明确指定无权问卷会被拒绝。

## 十二、常用请求模型与字段约束

请求模型通常禁止未知字段，并执行统一安全数值检查。以下为调用时最常用的字段组合，完整定义以 [schemas.py](../1_代码/backend/app/schemas.py) 和 OpenAPI 为准。

| 模型 | 必需字段 | 可选字段或说明 |
|---|---|---|
| Credentials | username、password | 用户名 3～40，密码 8～128 |
| CreateSurvey | 使用标题或默认标题 | 标题最多 200 |
| SaveDraft | revision、draft | draft 是完整定义 |
| Publish | revision | deadline 可为 null，非空需带时区 |
| StatusChange | status | 仅 closed；revision 可选，建议携带 |
| StartAttempt | — | anonymous 默认 false |
| SaveAttempt | revision、answers | current_question_id 可选 |
| AttemptRevision | revision | 用于放弃和过程提交 |
| Submit | token、answers | 旧兼容提交及 evaluate |
| NewQuestion | content | change_note 默认创建说明 |
| NewQuestionVersion | content、revision、parent_version_id | change_note 可选 |
| RestoreQuestion | revision、parent_version_id、restored_from_version_id | change_note 可选 |
| Revision | revision | 相关专门操作 |
| ImportQuestion | revision、question_version_id | — |
| InstanceOperation | revision、instance_id | — |
| UpgradeQuestion | revision、instance_id、question_version_id | — |
| GrantRequest | kind、question_version_id、username | survey_id 由用途决定 |
| LibraryRequest | name | description 默认空字符串 |
| EditLibrary | name、revision | description 默认空字符串 |
| LibraryItemRequest | revision、question_version_id | position 默认 0 |
| UpdateLibraryItem | revision、question_version_id | position 默认 0 |

`draft` 主要包括标题、说明、匿名和重复策略、题目数组。题目包含实例 ID、类型、题干、必答、选项、校验、跳转及可选来源。

`content` 只包括题型、题干、选项和校验。来源由服务器维护，不能通过 NewQuestion 自行伪造。

时间在 HTTP JSON 中使用日期时间字符串；数据库示例中的 Extended JSON `$date` 不应直接当成普通接口时间字段。

## 十三、重试、分页与验收边界

### 13.1 网络不确定时怎样重试

| 操作 | 重试注意事项 |
|---|---|
| GET 查询 | 可以重新查询，页面注意迟到响应 |
| 创建问卷、题目或题库 | 可能创建多个对象，先确认前次结果 |
| 导入题目 | 可能生成多个实例，不盲目重复 |
| 创建版本、恢复、发布 | 使用当前 revision，不能悄悄重放用户意图 |
| 保存草稿 | 旧 revision 不强制覆盖 |
| 正式提交 | 同一次过程或凭证返回原回执 |
| 授权 | 同资源接收者可能复用并更新记录，不是无副作用操作 |
| 撤销 | 使用授权当前 revision |

### 13.2 分页与搜索

有分页参数的列表通常每页 20 项，page 从 1 开始。要访问后续题库，需要继续请求后续页，不能只读取第一页。

题库搜索先检查可读固定版本、再分页。版本历史在系列内返回，不应将所有接口都当成相同分页结构。

### 13.3 实现与验证范围

新路由在网页兜底之前注册，未知 `/api` 路径不能被当作网页成功响应。

本说明结合路由、请求模型和服务实现编写；示意 JSON 只解释格式，不冒充真实完整响应。实际调用记录、自动测试和人工验收范围分别保留。

当前仍有 2.0.2 真实浏览器人工复核待办。接口和组件通过不能证明所有页面、网络条件和部署环境都已验证。

相关材料：

- [系统说明](系统说明.md)
- [数据库设计](数据库设计.md)
- [关键逻辑说明](关键逻辑说明.md)
- [测试步骤、输入输出与结果](../3_测试用例/测试用例与结果.md)