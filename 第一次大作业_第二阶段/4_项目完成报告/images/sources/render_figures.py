from pathlib import Path
import json, re, math, html, hashlib
from PIL import Image, ImageDraw, ImageFont

R=Path(__file__).resolve().parent; OUT=R.parent
for folder in ['svg','png','sources']:(OUT/folder).mkdir(parents=True,exist_ok=True)
FIG=[]
def add(ch,title,kind,data,anchor,intro,after,basis):
    FIG.append(dict(id=len(FIG)+1,chapter=ch,title=title,kind=kind,data=data,anchor=anchor,intro=intro,explanation=after,basis=basis))
def flow(ch,title,items,anchor,intro,after,basis):add(ch,title,'flow',items,anchor,intro,after,basis)
def table(ch,title,headers,rows,anchor,intro,after,basis):add(ch,title,'table',dict(headers=headers,rows=rows),anchor,intro,after,basis)
flow(1,'系统功能全景图',[
['账号与会话','登录后按所有者和授权访问','old'],['问卷管理','创建、编辑、发布与关闭','old'],['填写与恢复','跳转、保存、续填和提交','old'],['整卷统计','份数、人数和各题结果','old'],['常用题与版本','独立保存、比较、分支和恢复','new'],['题库与共享','整理固定版本，按用途授权','new']],
'### 1.2','系统同时服务问卷创建者和填写者。图 1 将功能按使用任务归组，便于先了解整体范围。','灰色部分承接第一阶段，蓝色部分是第二阶段扩展。账号、问卷和填写仍走原有流程；新增能力主要用于管理可复用题目。','报告1.2；services/surveys.py、attempts.py、questions.py')
table(1,'八项新需求对应关系图',['需求','设计与模块','验证入口'],[
['R01 保存常用题','题目系列＋固定版本；question_instances','T090、T106'],['R02 共享题目','精确版本授权；sharing','T091～T097'],['R03 修改隔离','实例内容＋完整发布快照','T075、T100'],['R04 历史与恢复','父版本、恢复来源；questions','T075、T218'],['R05 版本并存','按确定版本引用和查询','T101、T102'],['R06 使用追踪','问卷去重与可见范围；question_usage','T105、T128'],['R07 题库管理','独立成员、排序与分页；libraries','T101、T129～T131'],['R08 跨问卷统计','先限权再聚合；question_statistics','T102～T104、T116']],
'## 二、系统设计','八项需求分别落到哪些设计和测试上，可以对照图 2 阅读后续章节。','同一项设计可以服务多个需求，例如固定版本既支持并存，也保护历史解释。T 编号对应提交材料中的逐项测试索引，不是新增测试次数。','需求设计实现验证对照.json；逐项测试索引.json')
for phase,title in [(1,'第一阶段系统结构图'),(2,'第二阶段系统结构图')]:
 table(2,title,['层次','原有核心','本阶段变化'],[
 ['Vue 前端','工作台、编辑器、填写页、统计页','原有交互与页面' if phase==1 else '新增题目、历史、题库、共享页；调整编辑器'],
 ['FastAPI 后端','会话、题型、规则、问卷、填写、统计','原有服务与校验' if phase==1 else '新增题目版本、来源操作、授权与单题统计'],
 ['MongoDB 副本集','users / sessions / surveys\nsurvey_versions / attempts / responses','六集合与索引、事务' if phase==1 else '保留六集合；新增五集合；显式升级约束'],
 ['历史保护','草稿与发布分离；填写绑定快照','第一阶段已有基础' if phase==1 else '继续沿用；题目更新不会替换旧快照']],
 '### 2.2' if phase==1 else '### 2.3',
 '图 3 从相同的三层结构出发，说明第一阶段已经具备哪些能力。' if phase==1 else '对照图 3，图 4 标明第二阶段在各层增加和调整的内容。',
 '前端通过后端访问数据库。发布快照、恢复填写和事务提交是后续扩展的基础。' if phase==1 else '第二阶段保留 Vue、FastAPI 和 MongoDB 核心结构，新增工作集中在题目管理与授权。原填写、规则和整卷统计继续复用。',
 '报告2.1、2.6；第一阶段至第二阶段文件变化.json')
flow(2,'问卷完整业务流程图',[
['创建和编辑','添加题目，保存草稿','old'],['发布检查','题型、跳转、来源均需合法','changed'],['生成发布快照','保存当时的完整 definition','old'],['开始并持续填写','绑定快照，按路径保存输入','old'],['正式提交','完整校验后原子生成答卷','old'],['查看统计或关闭','关闭后停止新提交，草稿可只读','old']],
'### 2.4','图 5 沿实际使用顺序串起一份问卷的完整过程。','编辑草稿和发布是两件事。修改草稿不会立即改变正在填写的内容，提交后的统计只读取正式答卷。','services/surveys.py、attempts.py；报告2.7')
flow(2,'从问卷保存为常用题流程图',[
['选择自有实例','先核对问卷归属和来源权限','changed'],['提取可复用内容','题干、题型、选项、校验','new'],['事务创建系列与 v1','保存固定内容，设置版本指针','new'],['关联当前草稿实例','来源由服务端生成并绑定实例','new']],
'#### 2.8.2','保存常用题需要把题目内容与问卷专属配置分开，过程见图 6。','原问卷的必答与跳转不成为常用题内容；旧答卷也不自动归入新系列。来自他人的共享实例不能借此另存成自有题。','services/question_instances.py；T090、T106')
add(2,'常用题导入多份问卷示例图','branch',dict(root=['年龄题 v1','确定题目版本'],children=[['问卷 A 的实例 a','必答；按 A 的规则跳转','changed'],['问卷 B 的实例 b','可选；按 B 的规则跳转','changed'],['问卷 A 的实例 c','同版本再次使用，实例 ID 不同','changed']]),
'#### 2.8.3','同一常用题版本可以有多次使用，图 7 以年龄题说明它们如何保持独立。','每次导入都有新的实例 ID，并保存当时内容。必答和 routing 属于实例；相同来源不意味着实例配置必须相同。','services/question_instances.py；T090、T102')
table(3,'十一集合总体关系图',['集合／区域','主要关联方向','作用'],[
['users → sessions','sessions.user_id → users._id','账号与服务端会话'],['users → surveys','surveys.owner_id → users._id','问卷归属与可编辑草稿'],['surveys → survey_versions','survey_id → surveys._id','完整发布快照'],['attempts / responses → survey_versions','version_id → survey_versions._id','恢复与正式答案绑定原定义'],['questions → question_versions','question_id → questions._id；latest_version_id 指向版本','系列与固定版本'],['question_libraries → question_library_items','library_id → question_libraries._id','题库与独立成员'],['question_library_items → question_versions','question_version_id → question_versions._id','收录确定版本'],['resource_grants → 版本／问卷／用户','question_version_id、survey_id、grantee_id','use 与 aggregate 分开'],['问卷内 source → question_versions','source.question_version_id → question_versions._id','快照内保留实例内容和来源']],
'### 3.2','图 8 按业务区域列出十一集合之间的主要关联。箭头表示应用维护的引用方向，不表示数据库外键。','前四行覆盖原有六集合，后续关系由第二阶段补充。MongoDB 的结构校验不自动检查所有跨集合关系，因此后端仍要核对归属、版本与授权。','database/collection_validators.json；报告2.1、3.1')
table(3,'集合职责与生命周期图',['数据组','允许怎样变化','为什么分开'],[
['users / sessions','账号维护；会话产生、过期和退出','会话生命周期短，不嵌入所有历史'],['surveys','草稿、状态和 revision 可更新','编辑聚合根'],['survey_versions / question_versions','创建新版本；应用无原地内容修改入口','历史内容可追溯'],['attempts','进行中可保存；提交或放弃后终态','半成品不混入正式统计'],['responses','正式提交后保存结果','独立增长，按快照解释'],['questions / question_libraries','管理元信息、归档或整理','管理对象与内容历史分离'],['question_library_items / resource_grants','成员增删排序；授权生效或撤销','独立查询、分页和权限生命周期']],
'### 3.2','集合不只是存放位置，也承担不同的变化规则，见图 9。','把可变管理信息、不可变内容版本和持续增长的作答记录分开，能够减少一次修改牵动其他数据的范围。这里的不可变由应用入口约束，不宣称管理员无法直接改库。','collection_validators.json；services/questions.py、attempts.py')
add(3,'问卷文档内部结构图','tree',dict(root=['surveys 文档','归属、状态、revision 与 draft'],children=[['draft 基本信息','标题、说明、填写配置','old'],['draft.questions[]','每个元素是问卷内实例','changed'],['实例内容','id、type、title、options、validation','old'],['实例配置与来源','required、routing；可选 source','changed']]),
'### 3.2','图 10 展开一份问卷内部的层次，帮助对照字段表阅读。','questions[] 嵌入 draft，实例中继续嵌入选项、校验和跳转。source 是第二阶段的可选来源，不是另一个替代题目内容的远程链接。','collection_validators.json：surveys；详细数据库设计字段表')
table(3,'嵌入与引用选择图',['对象','组织方式','选择理由'],[
['一份问卷的题目、选项与规则','嵌入完整定义','通常一起读取、校验和发布；问卷题数有上限'],['独立题目与内容历史','questions 引用 question_versions','不同问卷复用，旧内容不可被新版覆盖'],['填写过程与正式答卷','独立集合，通过 version_id 引用','数量持续增长，避免问卷文档无限膨胀'],['题库成员与授权','独立集合并建立索引','独立排序、分页、撤销和范围查询']],
'### 3.3','图 11 从读取方式和数据增长出发，说明哪些内容放在一起，哪些独立保存。','完整定义读取适合嵌套文档，独立增长和独立管理适合引用。全关系式拆分或关系库加 JSON 也可实现；本项目选择该组合以延续原代码并匹配完整版本访问。','报告3.1～3.3；题目最多100题的服务端限制')
add(3,'独立题目与题目版本关系图','branch',dict(root=['questions：年龄题','所有者、序号、最近版本指针'],children=[['question_versions：v1','固定题干、题型和校验','new'],['question_versions：v2','创建新文档，不覆盖 v1','new'],['question_versions：v3','编号表示创建顺序','new']]),
'### 3.4','图 12 区分“同一道题”和“这道题的某次内容”。','question_id 识别系列，question_version_id 识别确定版本。latest_version_id 用于管理和提示，问卷不会因此自动改用最新版。','services/questions.py；T075～T077')
flow(3,'题库与成员关系图',[
['question_libraries','名称、所有者、revision','new'],['question_library_items','library_id、排序、版本引用','new'],['question_versions','固定内容；同系列可收录多版','new']],
'### 3.4','图 13 展示题库、成员和版本三者的关联。','唯一索引约束同库同确定版本不重复；同系列不同版本可以并存。管理题库不等于拥有库中所有题目的转授权能力。','database/indexes.json；services/libraries.py；T101')
flow(3,'题目来源追溯图',[
['responses 正式答卷','version_id 指向问卷发布版本','old'],['survey_versions 发布快照','definition.questions[] 保存实例','changed'],['实例及 source','按 answers.question_id 找实例，再读来源','changed'],['question_versions 固定版本','source.question_version_id 指向此处','new']],
'### 3.5','正式答卷没有重复增加题目来源字段，但仍可沿图 14 追溯内容。','答案中的 question_id 是问卷实例 ID。通过它在对应发布快照中找到 source，才知道属于哪个独立题目版本；没有来源的旧实例不强行关联。','services/question_statistics.py；domain/question_sources.py')
flow(3,'草稿、发布快照与答卷关系图',[
['surveys.draft','编辑中，可以修改','old'],['survey_versions.definition','发布复制完整定义，固定内容','old'],['attempts.version_id','开始填写时绑定该快照','old'],['responses.version_id','提交后仍引用同一发布版本','old']],
'### 3.5','图 15 说明编辑内容如何变成可稳定解释的正式答案。','填写过程中即使发布了新版，原 attempt 也不会切换 version_id。草稿、快照和答案分别保存各自职责所需的数据，避免运行时追随最新题目。','services/surveys.py、attempts.py；T100')
table(3,'两阶段数据结构变化图',['区域','第一阶段','第二阶段调整'],[
['六个原集合','账号、问卷、快照、过程、答卷','继续保留；attempts、responses 约束不变'],['问卷题目实例','内容、required、routing','增加可选 source；旧题允许没有来源'],['surveys','原状态与修订信息','增加 draft_issues、activity_seq 等扩展字段'],['题目资源','没有独立题目版本管理','新增 questions、question_versions'],['题库与权限','没有对应集合','新增 question_libraries、question_library_items、resource_grants'],['历史答案','按 version_id 解释','不改写旧答案，不自动并入新系列统计']],
'### 3.8','图 16 将结构变化按对象对齐，具体字段类型仍以 Schema 和详细设计为准。','第二阶段扩展原问卷实例，同时增加独立管理集合。保持正式答卷结构，减少迁移范围；这并不等于所有集合约束都没有变化。','报告3.7；collection_validators.json；live-compatibility 历史证据')
table(3,'Schema、索引与事务分工图',['手段','负责什么','不能替代什么'],[
['Schema 校验','必需字段、类型、嵌套结构、枚举及范围','不自动核对跨集合授权和版本归属'],['唯一与查询索引','重复提交、进行中草稿、题库成员唯一性；查询加速','不判断题意、规则可达性和所有权限'],['事务与条件更新','版本序号/插入/指针；提交；revision 冲突','事务读不同对象仍需共同写入边界'],['后端业务校验','合法答案、跳转、来源、授权和状态','前端提示不能替代后端拒绝']],
'### 3.8','数据正确性由几层约束共同保证，图 17 列出各自职责。','例如，题库唯一索引防重复，后端确认目标版本可用，事务保证关联写入完整。三者解决不同问题，不能只靠 Schema 或前端禁用按钮。','collection_validators.json；indexes.json；database.py、question_sources.py')
add(4,'条件跳转路径图','routing',{},
'### 4.2','用四题示意问卷说明跳转：Q1 选“是”进入 Q2，选“否”跳到 Q3；Q2 默认继续 Q3，Q3 再到 Q4。图 18 中最后一项表示两条路径的共同后段。','这是解释规则的示意定义，不冒充新执行的问卷测试。只允许向后或结束，可以避免循环；必答检查只针对实际路径。','domain/rules.py；报告4.1；示意题目非新增测试数据')
table(4,'路径变化后的答案清理图',['时点','有效路径','保存与提交处理'],[
['初次 Q1＝是','Q1 → Q2 → Q3 → Q4','Q2 工具答案参与原路径'],['把 Q1 改为否','Q1 → Q3 → Q4','重算路径，Q2 不再有效'],['保存／正式提交','只认可当前路径上的有效答案','移除失效路径答案；Q2 不参与跳转与统计']],
'### 4.3','沿用图 18 的四题问卷，图 19 只改变 Q1 的答案，观察 Q2 的变化。','跳过不等于可把旧 Q2 答案继续算入提交。服务端根据当前有效答案重算路径，清除已不属于路径的内容；不能只信任页面传来的路径。','domain/rules.py；services/attempts.py')
flow(5,'发布校验流程图',[
['核对所有者与 revision','过期请求拒绝，避免覆盖','old'],['检查题目定义','字段、类型、选项和安全数值','old'],['检查可作答性与跳转','必答有合法答案；目标与条件有效','old'],['检查 source 与版本内容','来源真实，内容一致，禁止伪造','changed'],['全部通过才发布','保存完整快照；失败返回明确问题','old']],
'### 5.2','图 20 说明发布检查覆盖哪些方面。各检查相互配合，图示不代表内部函数逐条调用的唯一顺序。','上下界顺序正确还不够，必答题必须存在合法答案。升级后可以保存待修复草稿，但发布不能省略完整检查。','services/surveys.py；domain/questions.py、question_sources.py')
add(5,'自动保存与恢复时序图','sequence',dict(actors=['填写者／页面','后端服务','MongoDB'],events=[
[0,0,'输入立即留在页面：此时还不能称为已同步'],[0,1,'停顿、最长等待或切题触发保存，携带 revision'],[1,2,'检查状态与 revision，保存原始输入并增加修订号'],[1,0,'数据库确认后返回；仅最新修改获确认才显示“已保存”'],[0,1,'退出后同账号恢复：请求已有进行中过程'],[1,0,'按原快照与有效答案重算路径，返回合理位置'],[0,1,'若 revision 冲突则提示处理，不能直接覆盖']]),
'### 5.4','图 21 区分本地输入、保存请求和服务端确认三个时点。','已获服务端确认的内容可以跨设备恢复。未完成输入允许保存在草稿中，但无效输入不决定分支；冲突或登录失效时应保留输入并明确反馈。','services/attempts.py；前端填写保存逻辑；报告7.4')
flow(5,'正式提交事务图',[
['请求携带 attempt 与 revision','先检查登录、归属和终态','old'],['读取服务端草稿与原快照','不接收第二套独立提交答案','old'],['重算路径并完整校验','有效路径必答、题型与状态均合法','old'],['事务写正式答卷并完成过程','关联 response_id，按实现清理答案副本','old'],['返回提交回执','失败回滚；重复请求遵循提交去重规则','old']],
'## 六、AI使用过程','正式提交与自动保存的严格程度不同，提交步骤见图 22。','只有完整校验通过才产生正式答卷。答卷插入和填写过程进入终态属于同一事务，避免只完成一半；晚到的保存不能重新修改终态过程。','services/attempts.py；原事务、终态与提交去重测试')
table(6,'三处交互问题的发现与修复对照图',['审阅发现','原因与调整','验证与边界'],[
['预览 A 后确认却升级 B','确认读取当前选中题 → 绑定实例、来源、目标、revision 和草稿上下文','T198、T201～T208、T219、T221'],['v2 迟到结果覆盖 v1','缺请求上下文 → 仅最新结果与筛选快照一起更新','T199、T209～T213、T220'],['旧成员不可用便无法更新','按钮依赖旧版本 → 允许选目标，提交重新核权','T114、T115、T200、T214～T217']],
'## 七、测试结果','图 23 用实际问题说明 AI 辅助编程仍需要审阅、复现和修正。','用户提出问题及约束，Codex 辅助修改代码、测试和材料。自动测试通过并不等于所有页面已经人工验收；2.0.2 原生弹窗等浏览器复核仍待完成。','AI使用日志：实例13、32～38；逐项测试索引')
add(7,'测试构成与验收状态图','bars',dict(values=[['后端测试',154],['前端组件',90],['前端逻辑',16]],notes=['260 项不同用例，均有通过记录；不是代码覆盖率','初次完整记录：2026-10-25；独立复测：2026-10-26','类型检查、生产构建及隔离启动：有通过记录','2.0.2 真实浏览器人工验收：待完成','2026-10-29 本轮：图文与归档核对，不重跑业务测试']),
'### 7.3','图 24 只展示已有测试数量和验收状态，不表示本次制作图表又运行了一轮测试。','三类测试合计 260 项，重复执行不增加数量。组件模拟与接口测试有各自作用，但不能代替真实浏览器人工操作，更不能推导出容量或性能结论。','逐项测试索引.json；自动测试结果/20261026独立解压复测')
flow(7,'提交包复核流程图',[
['整理源码与原始证据','保留历史失败和当前通过记录','old'],['生成清单并打包','源码、材料、图片使用相对路径','changed'],['独立目录解压','检查包内版本、引用和哈希','old'],['区分两类复核','历史：测试/构建/启动；本轮：图文/归档','changed'],['记录范围与限制','依赖复用条件和人工待办如实保留','old']],
'### 7.4','图 25 将交付复核拆成可以核查的步骤。','2026-10-26 的独立解压执行过全量测试、构建和隔离启动；本次报告插图完成后只重新检查图片、文件和压缩包一致性。两种记录分别保留。','材料核对记录.json；20261026独立解压复测；本轮可视化核对记录')
flow(8,'旧数据继续运行示例图',[
['第一阶段旧问卷','实例没有 source，仍有原题目内容','old'],['按原完整快照恢复','attempt.version_id 继续有效','old'],['原规则与题型检查','填写、路径、提交逻辑继续复用','old'],['正式答卷与整卷统计','按原 definition 解释答案','old']],
'### 8.2','旧数据没有独立题目来源，仍应能完成原流程，见图 26。','source 为可选字段，因此兼容旧问卷不需要猜测它属于哪个常用题。把旧题另存为常用题，也不意味着历史答案自动获得关联。解决机制见图 14、16。','T100、T106～T108；报告7.4')
table(8,'问卷升级前后的隔离效果图',['对象','题目产生 v2 后','A 主动升级并发布后'],[
['题目系列','新增 v2；v1 不变','两个版本继续存在'],['问卷 A 草稿','仍使用 v1','确认后改用 v2，可先修复规则'],['问卷 B','仍使用 v1','保持 v1，不受 A 的操作影响'],['A 的旧发布快照','仍保存原 v1 内容','旧快照继续保留'],['已经开始的旧填写过程','绑定旧 version_id','按旧快照提交；新过程按当前发布开始']],
'### 8.2','图 27 把“修改不影响已有问卷”拆成几个具体对象。','若只让问卷读取常用题最新版，历史解释就可能被改变。因此保留实例内容和发布快照，更新由创建者明确选择；版本创建和确认机制见图 30～32。','T075、T099、T100；services/question_instances.py')
table(8,'统计计数示例图',['输入示例','计算方式','结果'],[
['问卷 A 的答卷 r1：两个实例分别答 20、40','按 response ID 去重；按实例计作答','1 份答卷，2 条作答'],['问卷 B 的答卷 r2：一个实例答 60','同一确定版本、在权限范围内','1 份答卷，1 条作答'],['合计','均值＝(20＋40＋60)÷3','2 份答卷、3 条作答，均值 40'],['另一个多选示例：[a,b] 与 [b,c]','分母是 2 条有效作答','a 50%、b 100%、c 50%']],
'### 8.2','图 28 用已有测试数据说明为什么要区分答卷数和作答条数。','展开答案项以后，一份答卷可能出现多行，不能将行数直接当成人数或份数。跨问卷统计本轮不提供去重人数，多选比例相加可以超过 100%。统计处理见图 35。','T102、T103；报告7.3')
add(8,'导入与撤销并发时序图','sequence',dict(actors=['导入事务','共同协调记录','撤销操作'],events=[
[0,1,'情形一：核权并条件写 activity_seq，导入事务先提交'],[2,1,'随后撤销提交：阻止后续新增导入'],[1,0,'已合法导入的原实例保留'],[2,1,'情形二：撤销先提交，授权变为无效'],[0,1,'在途导入若冲突重试，必须重新检查授权'],[1,0,'授权无效则拒绝导入，不产生合法实例']]),
'## 九、如何解决','图 29 分两种情形说明撤销与导入的生效先后，情形之间不是同一次请求的连续步骤。','单纯读取授权再写问卷不一定与撤销冲突，所以操作需要触及共同协调记录，并以成功提交顺序判定。保留既有使用与阻止新增使用的规则见图 34。','services/questions.py：authorize_use；T094～T097')
add(9,'题目版本演进与分支图','versions',dict(nodes=[['v1','初始内容',90,165],['v2','基于 v1',430,165],['v3','基于 v2',770,165],['v4','从 v1 分支',430,365]],edges=[[0,1,'父版本'],[1,2,'父版本'],[0,3,'从旧版派生']]),
'### 9.2','图 30 中，v4 创建得最晚，但它可以基于 v1 分支，而不是沿用 v3 的内容。','版本号表达创建先后，不能作为自动推荐升级的充分依据。升级必须由用户选择确定目标，版本序号、插入和指针更新在事务中完成。','services/questions.py；T075～T077')
add(9,'历史恢复关系图','versions',dict(nodes=[['v1','要恢复的历史内容',90,165],['v2','后续修改',430,165],['v3','恢复前的最近版本',770,165],['v4','恢复 v1 的内容',770,365]],edges=[[0,1,'演进'],[1,2,'演进'],[2,3,'parent → v3'],[0,3,'restored_from → v1']]),
'### 9.2','图 31 是另一种 v4 的产生方式：在最近版本为 v3 时恢复 v1 的内容。','这里的 v4 与图 30 的分支场景是两个独立示例。parent_version_id 记录直接演进关系，restored_from_version_id 记录恢复来源，旧版本均不覆盖。','services/questions.py：new_version；T075、T218')
flow(9,'升级预览与确认流程图',[
['保存并选定目标版本','发起新预览时作废旧确认','changed'],['绑定预览上下文','问卷、实例、来源、目标、revision、草稿','changed'],['展示差异与规则问题','待修复项保留，不静默删除','new'],['确认前再次核对','上下文变化则重新预览；禁止自动保存','changed'],['后端事务升级','核权、同系列、revision；不改旧快照','new'],['保存待修复草稿／发布','失败旧预览失效，修复后再完整发布','changed']],
'### 9.2','图 32 将升级拆成预览和确认两个动作，防止看到 A 的预览却更新 B。','切题、切目标、草稿变化、关闭或卸载都使旧上下文失效。确认阶段不能先自动保存来替换 revision，否则会绕过预览约束；发布仍需完整校验。','Editor.vue、useSurveyEditor.ts；T198～T208、T219、T221')
table(9,'使用授权与统计授权关系图',['谁授权','资源与能力','明确边界'],[
['题目所有者','use：指定题目版本 → 接收者','允许新增导入；未来版本不自动授权'],['问卷所有者','aggregate：指定问卷＋题目版本 → 接收者','允许指定范围汇总；不提供原始答卷或文本明细'],['题目作者查看他人数据','必须获得相应问卷的统计授权','不能因为拥有题目就给自己授权他人答案'],['共享接收者管理题库','可整理自己可用的版本','题库管理权不等于派生和转授权']],
'### 9.3','图 33 按授权人和资源区分两类权限。','use 回答“能不能把题用进问卷”，aggregate 回答“能不能读取指定问卷的汇总”。当前没有通用的他人问卷详情授权，也不因统计授权开放原始答卷。','services/sharing.py；T091、T104、T127')
table(9,'撤销授权前后行为图',['操作或对象','撤销前','撤销后'],[
['已合法导入的原草稿实例','按原来源保存、修复和发布','保留原版本，可继续保存和发布'],['已发布快照／旧填写过程','固定内容、绑定发布版本','继续可用，不追随授权删除内容'],['新增导入／升级为其他版本','检查目标当前授权','原授权不可复用；目标须有有效授权'],['汇总统计授权','按指定范围查询','新请求排除已撤销的问卷范围'],['再次另存或转授共享题','不默认允许','撤销不会使它变成自己的题']],
'### 9.3','图 34 区分撤销使用授权与撤销统计授权的不同影响。','既有合法来源只证明原问卷内原实例的使用，不是可以复制的永久通行证。统计授权撤销后也不能借“原来能看”继续查询该范围。','T092～T097、T104；question_sources.py、question_statistics.py')
flow(9,'跨问卷统计处理流程图',[
['选择确定题目版本','不同版本分别统计，不自动合并','new'],['先确定可见问卷范围','自有＋有效 aggregate 授权','new'],['寻找发布快照中的来源实例','按 source.question_version_id 匹配','new'],['匹配正式答卷和实例答案','时间依据 submitted_at，边界含端点','new'],['分开聚合并返回汇总','覆盖问卷、答卷、作答与选项/数值分布','new']],
'### 9.3','图 35 展示权限检查如何进入统计计算，不能聚合全部数据后再隐藏标题。','覆盖问卷数包含授权范围内发布引用该版本但零作答的问卷；有作答问卷数还需实际匹配有效答案。答卷按 ID 去重，作答按实例计数，结果不包含跨问卷去重人数或文本原文列表。','services/question_statistics.py；T102～T104、T116～T127')
flow(9,'数据库显式升级与恢复流程图',[
['普通启动与显式升级分开','启动检查一致性；不覆盖旧 validator','old'],['维护前备份并执行 --check','识别已知约束，全量预检旧文档','changed'],['--apply 保存恢复日志','数据库名、原约束、目标、应用进度','changed'],['逐集合应用并记录','完成置 complete；失败尝试恢复','changed'],['恢复前检查保护条件','日志匹配、约束未被他人改变','changed'],['出现新业务数据则拒绝降级','不能只恢复旧约束；按维护前完整备份恢复','changed']],
'__END__','图 36 将普通启动、显式升级和受保护的恢复放在一起说明。','新增缺失集合由初始化负责，升级流程处理已有集合约束。DDL 恢复不是业务数据备份；已有第二阶段题目或来源数据时，程序会阻止仅恢复旧约束，不承诺任意时刻无条件回退。','database.py、migration.py；T107、T108')

# All vector and raster output share the same primitives and Chinese text metrics.
FONT='C:/Windows/Fonts/msyh.ttc';BOLD='C:/Windows/Fonts/msyhbd.ttc'
COL={'old':('#eef1f5','#64748b'),'new':('#eaf3ff','#2967ad'),'changed':('#fff3e5','#b96b13')}
W=1280
class Canvas:
 def __init__(self,h):
  self.h=h;self.im=Image.new('RGB',(W*2,h*2),'white');self.d=ImageDraw.Draw(self.im);self.svg=[];self.text_bounds=[]
 def font(self,s,b=False):return ImageFont.truetype(BOLD if b else FONT,s*2)
 def width(self,t,s,b=False):return self.d.textlength(t,font=self.font(s,b))/2
 def rect(self,x,y,w,h,fill='#ffffff',stroke='#d5dfe9',r=12):
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
  self.d.rounded_rectangle((x*2,y*2,(x+w)*2,(y+h)*2),radius=r*2,fill=fill,outline=stroke,width=3)
 def line(self,points,arrow=False,color='#8a9aad',dash=False):
  self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="6 5"' if dash else '')+'/>')
  self.d.line([(int(x*2),int(y*2)) for x,y in points],fill=color,width=4)
  if arrow:
   x,y=points[-1];px,py=points[-2];a=math.atan2(y-py,x-px)
   tri=[(x,y),(x-11*math.cos(a-.42),y-11*math.sin(a-.42)),(x-11*math.cos(a+.42),y-11*math.sin(a+.42))]
   self.svg.append('<polygon points="'+' '.join(f'{xx},{yy}' for xx,yy in tri)+f'" fill="{color}"/>');self.d.polygon([(int(xx*2),int(yy*2)) for xx,yy in tri],fill=color)
 def txt(self,x,y,t,s=23,b=False,color='#233448',width=None):
  lines=[]
  for para in t.split('\n'):
   cur=''
   for token in re.findall(r'[A-Za-z0-9_.]+|.',para):
    units=list(token) if width and self.width(token,s,b)>width else [token]
    for ch in units:
     if width and cur and self.width(cur+ch,s,b)>width:lines.append(cur);cur=''
     cur+=ch
   lines.append(cur)
  for i,line in enumerate(lines):
   yy=y+i*s*1.5;ww=self.width(line,s,b)
   assert x>=0 and x+ww<=W-12,(t,x,ww)
   assert yy+s*1.4<self.h,(t,yy,self.h)
   self.text_bounds.append([x,yy,ww,s*1.5,line])
   self.svg.append(f'<text x="{x}" y="{yy+s}" font-family="Microsoft YaHei, sans-serif" font-size="{s}" font-weight="{700 if b else 400}" fill="{color}">{html.escape(line)}</text>')
   self.d.text((int(x*2),int(yy*2)),line,font=self.font(s,b),fill=color,anchor='lt')
  return len(lines)*s*1.5
 def head(self,f):
  self.rect(0,0,W,8,'#2967ad','#2967ad',0)
  self.txt(44,28,f'图 {f["id"]}  {f["title"]}',31,True,width=1180)
  self.txt(46,85,f'第{f["chapter"]}章 · 问序问卷系统 · 应用 2.0.2',18,color='#607083')
 def foot(self):
  y=self.h-47;self.line([(44,y-12),(1236,y-12)])
  for x,k,label in [(46,'old','沿用结构'),(250,'new','新增能力'),(454,'changed','修改／扩展')]:
   fill,edge=COL[k];self.rect(x,y+2,18,18,fill,edge,3);self.txt(x+28,y,label,17,color='#607083')
  self.txt(840,y,'设计示意；依据见图后说明',17,color='#607083')
 def save(self,f):
  base=f'fig-{f["id"]:02d}'
  (OUT/'svg'/f'{base}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}" role="img"><title>{html.escape(f["title"])}</title><rect width="100%" height="100%" fill="white"/>'+''.join(self.svg)+'</svg>','utf-8')
  self.im.save(OUT/'png'/f'{base}.png',optimize=True)
  f['width']=W;f['height']=self.h;f['text_runs']=len(self.text_bounds)
  (OUT/'sources'/f'{base}.json').write_text(json.dumps(f,ensure_ascii=False,indent=2),'utf-8')
def card(c,x,y,w,h,title,body,k='new'):
 fill,edge=COL[k];c.rect(x,y,w,h,fill,edge);th=c.txt(x+20,y+15,title,24,True,width=w-40);bh=c.txt(x+20,y+22+th,body,21,width=w-40)
 assert 22+th+bh<=h+5,(title,body,h,th,bh)
def render(f):
 data=f['data'];kind=f['kind']
 if f['id']==1:
  c=Canvas(780);c.head(f)
  card(c,430,337,420,130,'问序问卷系统','创建者管理，填写者作答','old')
  pos=[(44,145),(464,145),(884,145),(44,530),(464,530),(884,530)]
  for (title,body,k),(x,y) in zip(data,pos):
   card(c,x,y,352,145,title,body,k)
   if y<300:c.line([(x+176,y+145),(x+176,312),(640,312),(640,337)])
   else:c.line([(640,467),(640,502),(x+176,502),(x+176,y)])
 elif f['id'] in [3,4]:
  c=Canvas(900);c.head(f)
  for i,(layer,core,change) in enumerate(data['rows'][:3]):
   y=145+i*199;k='old' if f['id']==3 else 'changed'
   card(c,44,y,1192,153,layer,core+'；'+change,k)
   if i<2:c.line([(640,y+153),(640,y+195)],True)
  c.txt(46,751,'历史保护：'+data['rows'][3][1]+'；'+data['rows'][3][2],20,width=1180)
 elif f['id']==8:
  c=Canvas(1125);c.head(f)
  nodes=[(44,145,'users','账号；owner_id / user_id 的引用目标','old'),(464,145,'questions','系列与最近版本指针','new'),(884,145,'question_libraries','个人题库名称、所有者','new'),(44,355,'sessions','user_id → users._id','old'),(464,355,'question_versions','question_id → questions._id','new'),(884,355,'question_library_items','library_id、question_version_id','new'),(44,565,'surveys','owner_id；draft.questions[].source','changed'),(464,565,'resource_grants','版本、问卷、授权人和接收者引用','new'),(44,775,'survey_versions','survey_id；definition 内嵌实例','changed'),(464,775,'attempts','version_id → 发布快照','old'),(884,775,'responses','version_id → 发布快照','old')]
  for x,y,title,body,k in nodes:card(c,x,y,352,150,title,body,k)
  for x in [220,640,1060]:c.line([(x,295),(x,355)],True)
  c.line([(44,220),(20,220),(20,640),(44,640)],True)
  c.line([(220,715),(220,775)],True)
  c.line([(884,430),(816,430)],True)
  c.line([(640,505),(640,565)],True)
  c.line([(396,850),(464,850)],True)
  c.line([(220,925),(220,970),(1060,970),(1060,925)],True)
  c.txt(48,1000,'箭头展示归属、成员或关联路径；框内字段说明实际引用。实例 source 另见图 14。',21,width=1180)
 elif f['id']==10:
  c=Canvas(845);c.head(f)
  card(c,44,145,1192,120,'surveys 文档','归属、状态与 revision；下列结构嵌入 draft','changed')
  c.rect(84,300,1152,440,'#f7faff','#2967ad');c.txt(108,318,'draft：基本信息与 questions[]',25,True)
  c.rect(124,380,1072,320,'#ffffff','#b96b13');c.txt(148,400,'questions[] 中的一个实例',24,True)
  card(c,164,463,476,190,'内容与实例 ID','id、type、title、options、validation','old')
  card(c,676,463,476,190,'实例配置与可选来源','required、routing、source','changed')
  c.line([(640,265),(640,300)],True)
 elif f['id']==36:
  c=Canvas(1070);c.head(f)
  nodes=[(44,145,'1. 维护前备份与 --check','已知约束、全量文档预检'),(464,145,'2. --apply 保存日志','数据库、原约束、目标与进度'),(884,145,'3. 逐集合应用','每次应用后记录进度'),(884,425,'完成','日志状态为 complete'),(464,425,'恢复前检查保护条件','日志匹配；约束未被他人改变'),(44,715,'允许按日志恢复','满足保护条件，恢复原约束'),(464,715,'拒绝仅恢复旧约束','已有新业务数据时需完整备份恢复')]
  for x,y,title,body in nodes:card(c,x,y,352,175,title,body,'changed')
  c.line([(396,232),(464,232)],True);c.line([(816,232),(884,232)],True)
  c.line([(1060,320),(1060,425)],True);c.txt(1080,351,'成功',21)
  c.line([(1060,320),(1060,369),(640,369),(640,425)],True);c.txt(666,334,'失败尝试恢复／显式 --rollback',20,width=370)
  c.line([(640,600),(640,715)],True);c.txt(660,645,'不满足条件',20)
  c.line([(640,600),(640,649),(220,649),(220,715)],True);c.txt(248,614,'满足条件',20)
  c.txt(46,942,'普通启动另走检查与缺失集合初始化；不会自动覆盖已有校验器。',22,width=1180)
 elif kind=='table':
  cols=len(data['headers']);widths=[280,480,432] if cols==3 else [596]*cols
  # Layout row height uses the exact renderer's measured character wrapping.
  probe=Canvas(4000);rowheights=[]
  for row in data['rows']:
   hs=[probe.txt(0,0,t,21,width=w-32) for t,w in zip(row,widths)];rowheights.append(max(hs)+32)
  h=int(145+58+sum(rowheights)+85);c=Canvas(h);c.head(f);y=139
  x=44
  for w,t in zip(widths,data['headers']):c.rect(x,y,w,58,'#233e60','#ffffff',0);c.txt(x+16,y+12,t,23,True,'#ffffff',w-32);x+=w
  y+=58
  for i,(row,rh) in enumerate(zip(data['rows'],rowheights)):
   x=44
   for j,(w,t) in enumerate(zip(widths,row)):
    c.rect(x,y,w,rh,'#edf4fc' if j==0 else ('#f6f8fb' if i%2==0 else '#ffffff'),'#d5dfe9',0);c.txt(x+16,y+15,t,21,j==0,width=w-32);x+=w
   y+=rh
 elif kind=='flow':
  n=len(data);cols=2 if n<=4 else 3;rows=math.ceil(n/cols);w=550 if cols==2 else 352;h=160+rows*250+80;c=Canvas(h);c.head(f)
  # Row-major reading; separate return arrows stay in a free gutter.
  for i,(title,body,k) in enumerate(data):
   row,col=divmod(i,cols);x=44+col*(w+68);y=145+row*250
   card(c,x,y,w,195,f'{i+1:02d}  {title}',body,k)
   if i<n-1:
    if col<cols-1:c.line([(x+w,y+97),(x+w+59,y+97)],True)
    else:
     yy=y+222;c.line([(x+w/2,y+195),(x+w/2,yy),(44+w/2,yy),(44+w/2,y+250)],True)
 elif kind in ['branch','tree']:
  children=data['children'];rows=len(children);h=170+rows*152+78;c=Canvas(h);c.head(f)
  rx,ry=44,170;card(c,rx,ry,380,160,*data['root'],'new' if f['chapter']>=3 else 'changed')
  for i,(title,body,k) in enumerate(children):
   yy=145+i*152;card(c,620,yy,616,122,title,body,k)
   c.line([(424,250),(510,250),(510,yy+61),(620,yy+61)],True)
 elif kind=='sequence':
  events=data['events'];h=215+len(events)*120+80;c=Canvas(h);c.head(f);xs=[185,640,1095]
  for x,t in zip(xs,data['actors']):c.rect(x-130,138,260,58,'#eaf3ff','#2967ad');c.txt(x-110,149,t,23,True,width=220);c.line([(x,202),(x,h-87)],dash=True)
  for i,(a,b,t) in enumerate(events):
   y=231+i*120
   if a==b:
    c.rect(50,y-5,1180,62,'#f4f7fa','#d5dfe9');c.txt(70,y+4,f'{i+1:02d}  {t}',21,width=1140)
   else:
    lo=min(xs[a],xs[b]);hi=max(xs[a],xs[b]);c.rect(lo-8,y-15,hi-lo+16,78,'#ffffff','#ffffff',0);c.txt(lo+6,y-13,f'{i+1:02d}  {t}',19,width=hi-lo-10);c.line([(xs[a],y+77),(xs[b],y+77)],True,'#2967ad')
 elif kind=='routing':
  c=Canvas(670);c.head(f)
  for x,y,title,body in [(44,165,'Q1 是否使用数据库','单选：是／否'),(456,165,'Q2 使用哪些工具','多选'),(868,165,'Q3 计划学习多久','数字：小时'),(868,420,'Q4 有什么建议','文本'),(456,420,'END','结束问卷')]:card(c,x,y,300,130,title,body,'old')
  c.line([(344,230),(456,230)],True);c.txt(371,190,'是',21)
  c.line([(756,230),(868,230)],True);c.txt(774,190,'默认',21)
  c.line([(194,295),(194,345),(1018,345),(1018,295)],True);c.txt(370,310,'否：跳过 Q2，直接进入 Q3',21)
  c.line([(1018,295),(1080,295),(1080,420)],True);c.txt(1095,368,'默认',21)
  c.line([(868,485),(756,485)],True);c.txt(773,448,'默认',21)
 elif kind=='versions':
  c=Canvas(650);c.head(f)
  for a,b,label in data['edges']:
   na,nb=data['nodes'][a],data['nodes'][b];xa,ya=na[2],na[3];xb,yb=nb[2],nb[3]
   if ya==yb:c.line([(xa+260,ya+55),(xb, yb+55)],True);c.txt(xa+262,ya+16,label,16,width=80)
   elif xa==xb:c.line([(xa+130,ya+110),(xb+130,yb)],True);c.txt(xa+145,ya+135,label,17,width=150)
   else:
    mid=ya+155;c.line([(xa+85,ya+110),(xa+85,mid),(xb+85,mid),(xb+85,yb)],True);c.txt((xa+xb)/2,mid-34,label,18,width=400)
  for title,body,x,y in data['nodes']:card(c,x,y,260,110,title,body,'new')
 else:
  c=Canvas(760);c.head(f)
  for i,(label,num) in enumerate(data['values']):
   y=150+i*90;c.txt(50,y,label,25,True);c.rect(245,y,850,43,'#eef1f5','#eef1f5',5);c.rect(245,y,850*num/154,43,'#2967ad','#2967ad',5);c.txt(1120,y,str(num),27,True)
  for i,t in enumerate(data['notes']):c.txt(50,445+i*44,'• '+t,22,width=1180)
 c.foot();c.save(f)

if __name__=='__main__':
 assert len(FIG)==36
 assert [sum(f['chapter']==c for f in FIG) for c in range(1,10)]==[2,5,10,2,3,1,2,4,7]
 for f in FIG:render(f)
 (OUT/'sources/figures.json').write_text(json.dumps(FIG,ensure_ascii=False,indent=2),'utf-8')
 print('已生成36张SVG、PNG和独立JSON源文件')
