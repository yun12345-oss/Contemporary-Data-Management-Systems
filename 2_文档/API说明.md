# API说明

## 一 协议 身份与示例约定

基础地址为http://127.0.0.1:8000，所有下列路径已经包含/api。请求与响应为JSON；登录使用HttpOnly Cookie survey_session。浏览器同源携带Cookie，脚本需使用可保留Cookie的会话客户端。直接访问数据库不是填写方式。

除健康检查、注册、登录和退出本身外，业务端点要求有效登录。问卷管理/统计检查owner_id，填写草稿按问卷范围HMAC关联键检查本人。服务端不信任客户端user_id或path。写请求有Origin时必须在允许列表；缺少Origin的脚本调用仍需通过身份与业务检查。

所有JSON数值必须有限且绝对值不超过10¹⁵。Pydantic模型拒绝额外字段并限制基础形状；草稿允许业务内容未完成，不表示任意嵌套输入都接受。单次Content-Length声明超过1000000时拒绝413，这不替代部署入口的流式大小限制。

下列成功响应是根据代码整理的完整结构示例，ID和时间为脱敏固定值，不是本次真实网络响应；实际值由服务生成。完整definition会在多个接口重复，以免把必要字段用“...”省略。错误示例同样是约定示意；原始已执行结果以测试证据为准。

## 二 数据对象与字段字典

### 2.1 管理对象与元数据

Survey返回_id、owner_id、share_code、status、draft、deadline、revision、current_version、created_at、updated_at、activity_seq、schema_version。列表另外增加response_count，为所有版本累计正式份数。

PublishedVersion返回_id、survey_id、version、definition、published_at、schema_version、rule_engine_version。发布响应另外有survey元数据，包含revision/status/current_version/deadline/updated_at；该嵌套字段不写入版本集合。历史摘要排除definition。

### 2.2 填写对象

AttemptView返回_id、revision、status、anonymous、updated_at、definition、version、answers、path、issues、current_question_id、read_only、read_only_reason、deadline；已提交可增加receipt。answers是原始输入，不一定是合法正式答案；issues按题目ID给出当前路径错误，path可能止于无效题。没有进行中草稿返回null。

Receipt为id、version、submitted_at。Stats为version/title/total/respondent_count/questions；单题有id/title/type/answered/respondent_count，选择题另有options（id/label/count/respondent_count），数字题有average/min/max，文本无额外聚合字段。Values有items/total/page/page_size。

### 2.3 共享请求模型

下表逐项来自当前静态OpenAPI。对象引用的完整嵌套字段在后续模型中列出；默认值来自模型，不表示数据库自动填充。新AttemptRevision严格要求JSON整数；其他类型的实际转换由当前Pydantic配置决定，不把所有字段描述为严格无转换。


#### Credentials
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| username | string；minLength=3；maxLength=40；pattern="^[\\w\\-]+$" | 是 | 无显式默认 |
| password | string；minLength=8；maxLength=128 | 是 | 无显式默认 |

#### CreateSurvey
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| title | string；minLength=1；maxLength=200 | 否 | "未命名问卷" |

#### SaveDraft
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| revision | integer；minimum=1.0 | 是 | 无显式默认 |
| draft | Definition | 是 | 无显式默认 |

#### Definition
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| title | string；minLength=1；maxLength=200 | 是 | 无显式默认 |
| description | string；maxLength=5000 | 否 | "" |
| allow_anonymous | boolean | 否 | false |
| allow_repeat | boolean | 否 | false |
| questions | array[Question]；maxItems=100 | 否 | 无显式默认 |

#### Question
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| id | string；pattern="^[A-Za-z0-9_-]{1,64}$" | 是 | 无显式默认 |
| type | string；minLength=1；maxLength=40 | 是 | 无显式默认 |
| title | string；minLength=1；maxLength=500 | 是 | 无显式默认 |
| required | boolean | 否 | false |
| options | array[Option]；maxItems=100 | 否 | 无显式默认 |
| validation | object | 否 | 无显式默认 |
| routing | Routing | 否 | 无显式默认 |

#### Option
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| id | string；pattern="^[A-Za-z0-9_-]{1,64}$" | 是 | 无显式默认 |
| label | string；minLength=1；maxLength=200 | 是 | 无显式默认 |

#### Routing
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| rules | array[RoutingRule]；maxItems=20 | 否 | 无显式默认 |
| default_target | string；maxLength=64 或 null | 否 | 无显式默认 |

#### RoutingRule
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| condition | object | 是 | 无显式默认 |
| target | string；minLength=1；maxLength=64 | 是 | 无显式默认 |

#### Publish
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| revision | integer；minimum=1.0 | 是 | 无显式默认 |
| deadline | string 或 null | 否 | 无显式默认 |

#### StatusChange
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| status | string；const="closed" | 是 | 无显式默认 |
| revision | integer；minimum=1.0 或 null | 否 | 无显式默认 |

#### StartAttempt
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| anonymous | boolean | 否 | false |

#### SaveAttempt
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| revision | integer；minimum=1.0 | 是 | 无显式默认 |
| answers | object；maxProperties=100 | 是 | 无显式默认 |
| current_question_id | string；maxLength=64 或 null | 否 | 无显式默认 |

#### AttemptRevision
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| revision | integer；minimum=1.0 | 是 | 无显式默认 |

#### Submit
| 字段 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- |
| token | string；maxLength=4096 | 是 | 无显式默认 |
| answers | object；maxProperties=100 | 是 | 无显式默认 |

## 三 接口总表

| 编号 | 方法 | 完整路径 | 用途 |
| --- | --- | --- | --- |
| API01 | GET | `/api/health` | 健康检查 |
| API02 | POST | `/api/auth/register` | 注册并登录 |
| API03 | POST | `/api/auth/login` | 登录 |
| API04 | POST | `/api/auth/logout` | 退出当前会话 |
| API05 | GET | `/api/auth/me` | 当前用户 |
| API06 | GET | `/api/surveys` | 本人问卷列表 |
| API07 | POST | `/api/surveys` | 创建问卷 |
| API08 | GET | `/api/surveys/{sid}` | 读取本人问卷 |
| API09 | PUT | `/api/surveys/{sid}/draft` | 保存创建者草稿 |
| API10 | POST | `/api/surveys/{sid}/publish` | 发布新快照 |
| API11 | PATCH | `/api/surveys/{sid}/status` | 关闭问卷 |
| API12 | GET | `/api/surveys/{sid}/versions` | 历史版本摘要 |
| API13 | GET | `/api/surveys/{sid}/versions/{version}` | 历史完整版本 |
| API14 | GET | `/api/public/{share}` | 当前填写摘要 |
| API15 | GET | `/api/public/{share}/attempt` | 查询本人进行中草稿 |
| API16 | POST | `/api/public/{share}/attempt` | 开始或恢复填写 |
| API17 | GET | `/api/attempts/{aid}` | 读取本人填写过程 |
| API18 | PUT | `/api/attempts/{aid}` | 保存填写原始输入 |
| API19 | POST | `/api/attempts/{aid}/abandon` | 明确放弃草稿 |
| API20 | POST | `/api/attempts/{aid}/submit` | 提交已保存草稿 |
| API21 | GET | `/api/surveys/{sid}/statistics` | 整卷及每题统计 |
| API22 | GET | `/api/surveys/{sid}/questions/{qid}/values` | 某题内容分页 |
| API23 | POST | `/api/public/{share}/start` | 旧凭证式开始（兼容） |
| API24 | POST | `/api/evaluate` | 旧凭证路径校验（兼容） |
| API25 | POST | `/api/responses` | 旧凭证正式提交（兼容） |

## API01 健康检查

**方法和路径：** `GET /api/health`

**认证与权限：** 不要求登录。

### 参数

无路径或查询参数。

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "status": "ok",
  "version": "1.1.0"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 读取数据库ping，无业务写入。

**幂等、冲突与事务：** 只读，可重复调用。

**失败场景：** 数据库不可用503。

**补充约定：** 只能证明请求时数据库可响应，不是备份、容灾或全功能检查。


## API02 注册并登录

**方法和路径：** `POST /api/auth/register`

**认证与权限：** 不要求已有登录。

### 参数

无路径或查询参数。

### 请求示例

```json
{
  "username": "Student_A",
  "password": "ExamplePass123!"
}
```

### 成功响应示例 HTTP 201

```json
{
  "id": "111111111111111111111111",
  "username": "Student_A"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 追加users及sessions，设置HttpOnly会话Cookie。

**幂等、冲突与事务：** 非幂等；同规范化用户名再次注册409。

**失败场景：** 用户名重复409，结构或数值错误422。

**补充约定：** 用户名按casefold唯一；返回id不是_id，不返回哈希。两个写入不是发布/提交那样的多文档业务事务，不宣称注册失败时会话和用户始终整体回滚。成功201。


## API03 登录

**方法和路径：** `POST /api/auth/login`

**认证与权限：** 不要求已有登录。

### 参数

无路径或查询参数。

### 请求示例

```json
{
  "username": "Student_A",
  "password": "ExamplePass123!"
}
```

### 成功响应示例 HTTP 200

```json
{
  "id": "111111111111111111111111",
  "username": "Student_A"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 查询用户并追加sessions，覆盖当前浏览器会话Cookie。

**幂等、冲突与事务：** 重复成功登录可新增会话，不是只保留单一会话。

**失败场景：** 错误账号/密码401，输入结构422。

**补充约定：** 会话有效期7天；已有其他设备会话不会因此全部撤销。


## API04 退出当前会话

**方法和路径：** `POST /api/auth/logout`

**认证与权限：** 路由本身不要求有效登录。

### 参数

无路径或查询参数。

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "ok": true
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 按Cookie摘要删除匹配会话，清除Cookie。

**幂等、冲突与事务：** 重复调用仍返回ok；只影响匹配会话。

**失败场景：** 数据库错误503。

**补充约定：** 前端填写页会先尝试保存；后端此接口不代替保存，也不主动删除草稿。


## API05 当前用户

**方法和路径：** `GET /api/auth/me`

**认证与权限：** 必须有效登录。

### 参数

无路径或查询参数。

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "id": "111111111111111111111111",
  "username": "Student_A"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 查询sessions与users，无业务写入。

**幂等、冲突与事务：** 只读。

**失败场景：** 失效或不存在会话401。

**补充约定：** 摘要和expires_at共同校验，TTL尚未删除也不代表会话有效。


## API06 本人问卷列表

**方法和路径：** `GET /api/surveys`

**认证与权限：** 有效登录，按当前owner_id过滤。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| page | query | integer；minimum=1 | 否 | 1 |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "items": [
    {
      "_id": "333333333333333333333333",
      "owner_id": "111111111111111111111111",
      "share_code": "abcdefabcdefabcdefabcdef",
      "status": "published",
      "draft": {
        "title": "课程学习与实践调查",
        "description": "用于说明文档结构与路径的脱敏示例",
        "allow_anonymous": true,
        "allow_repeat": true,
        "questions": [
          {
            "id": "q_role",
            "type": "single_choice",
            "title": "你的身份",
            "required": true,
            "options": [
              {
                "id": "student",
                "label": "学生"
              },
              {
                "id": "worker",
                "label": "已工作"
              }
            ],
            "validation": {},
            "routing": {
              "rules": [
                {
                  "condition": {
                    "question_id": "q_role",
                    "operator": "eq",
                    "value": "worker"
                  },
                  "target": "q_age"
                }
              ],
              "default_target": null
            }
          },
          {
            "id": "q_tools",
            "type": "multiple_choice",
            "title": "使用过哪些工具",
            "required": true,
            "options": [
              {
                "id": "mongo",
                "label": "MongoDB"
              },
              {
                "id": "python",
                "label": "Python"
              },
              {
                "id": "java",
                "label": "Java"
              }
            ],
            "validation": {
              "min_choices": 2,
              "max_choices": 2
            },
            "routing": {
              "rules": [
                {
                  "condition": {
                    "question_id": "q_tools",
                    "operator": "contains_all",
                    "value": [
                      "mongo",
                      "python"
                    ]
                  },
                  "target": "q_feedback"
                }
              ],
              "default_target": null
            }
          },
          {
            "id": "q_age",
            "type": "number",
            "title": "年龄",
            "required": true,
            "options": [],
            "validation": {
              "min": 0,
              "max": 120,
              "integer_only": true
            },
            "routing": {
              "rules": [
                {
                  "condition": {
                    "question_id": "q_age",
                    "operator": "between",
                    "value": [
                      60,
                      120
                    ]
                  },
                  "target": "END"
                }
              ],
              "default_target": null
            }
          },
          {
            "id": "q_feedback",
            "type": "text",
            "title": "建议",
            "required": false,
            "options": [],
            "validation": {
              "min_length": 2,
              "max_length": 100
            },
            "routing": {
              "rules": [],
              "default_target": "END"
            }
          }
        ]
      },
      "deadline": null,
      "revision": 3,
      "current_version": 1,
      "created_at": "2026-10-20T09:10:00",
      "updated_at": "2026-10-20T09:20:00Z",
      "activity_seq": 1,
      "schema_version": 1,
      "response_count": 1
    }
  ],
  "total": 1,
  "page": 1
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 查当前页surveys并聚合其正式答卷累计数。

**幂等、冲突与事务：** 只读，无统一全局快照。

**失败场景：** 未登录401，page<1或类型错误422。

**补充约定：** page默认1，每页20；按created_at倒序。response_count累计所有版本，非当前版本统计总数；不会列出其他人的问卷。


## API07 创建问卷

**方法和路径：** `POST /api/surveys`

**认证与权限：** 有效登录。

### 参数

无路径或查询参数。

### 请求示例

```json
{
  "title": "课程学习与实践调查"
}
```

### 成功响应示例 HTTP 201

```json
{
  "_id": "333333333333333333333333",
  "owner_id": "111111111111111111111111",
  "share_code": "abcdefabcdefabcdefabcdef",
  "status": "draft",
  "draft": {
    "title": "课程学习与实践调查",
    "description": "",
    "allow_anonymous": false,
    "allow_repeat": false,
    "questions": []
  },
  "deadline": null,
  "revision": 1,
  "current_version": 0,
  "created_at": "2026-10-20T09:10:00",
  "updated_at": "2026-10-20T09:10:00",
  "activity_seq": 0,
  "schema_version": 1
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 插入初始draft，revision=1，current_version=0，activity_seq=0。

**幂等、冲突与事务：** 非幂等，每次合法调用创建新ID。

**失败场景：** 未登录401，标题结构422。

**补充约定：** 成功201；此时没有可发布的完整题目，不能跳过定义配置直接发布。


## API08 读取本人问卷

**方法和路径：** `GET /api/surveys/{sid}`

**认证与权限：** 有效登录且owner_id匹配。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "_id": "333333333333333333333333",
  "owner_id": "111111111111111111111111",
  "share_code": "abcdefabcdefabcdefabcdef",
  "status": "published",
  "draft": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "deadline": null,
  "revision": 3,
  "current_version": 1,
  "created_at": "2026-10-20T09:10:00",
  "updated_at": "2026-10-20T09:20:00Z",
  "activity_seq": 1,
  "schema_version": 1
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 读取当前管理文档，无写入。

**幂等、冲突与事务：** 只读。

**失败场景：** 不存在或他人资源404，未登录401。

**补充约定：** 包含可变draft和管理元数据，不是发布快照。


## API09 保存创建者草稿

**方法和路径：** `PUT /api/surveys/{sid}/draft`

**认证与权限：** 有效登录且所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "revision": 1,
  "draft": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  }
}
```

### 成功响应示例 HTTP 200

```json
{
  "_id": "333333333333333333333333",
  "owner_id": "111111111111111111111111",
  "share_code": "abcdefabcdefabcdefabcdef",
  "status": "draft",
  "draft": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "deadline": null,
  "revision": 2,
  "current_version": 0,
  "created_at": "2026-10-20T09:10:00",
  "updated_at": "2026-10-20T09:19:00Z",
  "activity_seq": 0,
  "schema_version": 1
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 按_id/owner_id/revision条件替换draft，递增revision并更新管理时间。

**幂等、冲突与事务：** 单文档原子条件更新；旧revision重发409。

**失败场景：** 冲突409，非法结构422，他人404。

**补充约定：** 允许业务配置尚未完成；数值安全边界仍检查。只保存draft，不保存页面独立截止时间。


## API10 发布新快照

**方法和路径：** `POST /api/surveys/{sid}/publish`

**认证与权限：** 有效登录且所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "revision": 2,
  "deadline": null
}
```

### 成功响应示例 HTTP 200

```json
{
  "_id": "444444444444444444444444",
  "survey_id": "333333333333333333333333",
  "version": 1,
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "published_at": "2026-10-20T09:20:00",
  "schema_version": 1,
  "rule_engine_version": 1,
  "survey": {
    "revision": 3,
    "status": "published",
    "current_version": 1,
    "deadline": null,
    "updated_at": "2026-10-20T09:20:00Z"
  }
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 事务内校验、追加survey_versions、更新surveys版本指针/状态/截止/revision/activity_seq。

**幂等、冲突与事务：** 多文档事务；重复旧revision409，每次成功发布新增版本。

**失败场景：** 配置/时间非法422，revision冲突409，他人404。

**补充约定：** deadline必须含时区且晚于当前时间，null表示不限。省略deadline按模型默认null处理，调用方要保留旧时间必须明确提交旧值。返回survey元数据不写入版本文档。


## API11 关闭问卷

**方法和路径：** `PATCH /api/surveys/{sid}/status`

**认证与权限：** 有效登录且所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "status": "closed",
  "revision": 3
}
```

### 成功响应示例 HTTP 200

```json
{
  "ok": true,
  "survey": {
    "revision": 4,
    "status": "closed",
    "current_version": 1,
    "deadline": null,
    "updated_at": "2026-10-20T09:20:00Z"
  }
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 单文档设置closed，递增revision/activity_seq，更新管理时间。

**幂等、冲突与事务：** 新客户端携带revision；省略可兼容旧调用，不是幂等键。

**失败场景：** 旧revision409，其他status422，他人404。

**补充约定：** 不删除版本、草稿或答卷；已关闭再次调用也可能递增元数据，不写成完全无变化的幂等操作。


## API12 历史版本摘要

**方法和路径：** `GET /api/surveys/{sid}/versions`

**认证与权限：** 有效登录且所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
[
  {
    "_id": "444444444444444444444444",
    "survey_id": "333333333333333333333333",
    "version": 1,
    "published_at": "2026-10-20T09:20:00",
    "schema_version": 1,
    "rule_engine_version": 1
  }
]
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 按问卷读取版本，排除definition，按version倒序。

**幂等、冲突与事务：** 只读。

**失败场景：** 他人或问卷不存在404，未登录401。

**补充约定：** 返回数组，不是分页items对象。


## API13 历史完整版本

**方法和路径：** `GET /api/surveys/{sid}/versions/{version}`

**认证与权限：** 有效登录且所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |
| version | path | integer | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "_id": "444444444444444444444444",
  "survey_id": "333333333333333333333333",
  "version": 1,
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "published_at": "2026-10-20T09:20:00",
  "schema_version": 1,
  "rule_engine_version": 1
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 读取该问卷版本完整definition。

**幂等、冲突与事务：** 只读。

**失败场景：** 版本不存在404，未登录401。

**补充约定：** version路径参数是整数；当前实现仅按指定序号查询，不把此端点写成修改接口。


## API14 当前填写摘要

**方法和路径：** `GET /api/public/{share}`

**认证与权限：** 有效登录。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| share | path | string | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "title": "课程学习与实践调查",
  "description": "用于说明文档结构与路径的脱敏示例",
  "allow_anonymous": true,
  "allow_repeat": true,
  "question_count": 4,
  "version": 1,
  "deadline": null
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 按分享码查问卷，要求当前开放；读取当前版本摘要。

**幂等、冲突与事务：** 只读。

**失败场景：** 未发布/关闭/截止409，未知分享码404，未登录401。

**补充约定：** 公开是入口用途，不是无需登录。关闭后的草稿恢复应调用/attempt，不依赖本接口成功。


## API15 查询本人进行中草稿

**方法和路径：** `GET /api/public/{share}/attempt`

**认证与权限：** 有效登录，以问卷范围关联键识别本人。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| share | path | string | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "_id": "555555555555555555555555",
  "revision": 2,
  "status": "in_progress",
  "anonymous": true,
  "updated_at": "2026-10-20T10:01:00Z",
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "version": 1,
  "answers": {
    "q_role": "worker",
    "q_age": "-"
  },
  "path": [
    "q_role",
    "q_age"
  ],
  "issues": {
    "q_age": "请输入有效数字"
  },
  "current_question_id": "q_age",
  "read_only": false,
  "read_only_reason": null,
  "deadline": null
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 查询in_progress并读绑定版本，计算恢复位置和只读状态。

**幂等、冲突与事务：** 只读，多次读取不构成统一快照。

**失败场景：** 未知问卷404，未登录401，不支持格式版本409。

**补充约定：** 没有草稿返回JSON null。已关闭/截止仍可返回read_only=true，保留原始内容。


## API16 开始或恢复填写

**方法和路径：** `POST /api/public/{share}/attempt`

**认证与权限：** 有效登录。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| share | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "anonymous": true
}
```

### 成功响应示例 HTTP 200

```json
{
  "_id": "555555555555555555555555",
  "revision": 1,
  "status": "in_progress",
  "anonymous": true,
  "updated_at": "2026-10-20T10:00:00Z",
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "version": 1,
  "answers": {},
  "path": [
    "q_role"
  ],
  "issues": {
    "q_role": "此题必须回答"
  },
  "current_question_id": "q_role",
  "read_only": false,
  "read_only_reason": null,
  "deadline": null
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 事务中更新协调字段；已有过程则返回，缺少时检查开放/策略并创建。

**幂等、冲突与事务：** 部分唯一索引与事务协调，一账号一问卷一份进行中过程。

**失败场景：** 新建时关闭/截止/禁止重复409，匿名不允许422，未登录401。

**补充约定：** 已有过程忽略新默认匿名值，保留开始时版本和匿名；已有关闭过程可返回只读。


## API17 读取本人填写过程

**方法和路径：** `GET /api/attempts/{aid}`

**认证与权限：** 有效登录且关联键属于本人。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| aid | path | string | 是 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "_id": "555555555555555555555555",
  "revision": 2,
  "status": "in_progress",
  "anonymous": true,
  "updated_at": "2026-10-20T10:01:00Z",
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "version": 1,
  "answers": {
    "q_role": "worker",
    "q_age": "-"
  },
  "path": [
    "q_role",
    "q_age"
  ],
  "issues": {
    "q_age": "请输入有效数字"
  },
  "current_question_id": "q_age",
  "read_only": false,
  "read_only_reason": null,
  "deadline": null
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 读过程与原版本，重算路径/错误/位置。

**幂等、冲突与事务：** 只读。

**失败场景：** 他人/缺失过程404，未登录401，不支持版本409。

**补充约定：** submitted可含receipt；终态原始答案已清空。不是创建者查看他人草稿的接口。


## API18 保存填写原始输入

**方法和路径：** `PUT /api/attempts/{aid}`

**认证与权限：** 有效登录、本人、in_progress、当前开放。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| aid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "revision": 1,
  "answers": {
    "q_role": "worker",
    "q_age": "-"
  },
  "current_question_id": "q_age"
}
```

### 成功响应示例 HTTP 200

```json
{
  "_id": "555555555555555555555555",
  "revision": 2,
  "status": "in_progress",
  "anonymous": true,
  "updated_at": "2026-10-20T10:01:00Z",
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "version": 1,
  "answers": {
    "q_role": "worker",
    "q_age": "-"
  },
  "path": [
    "q_role",
    "q_age"
  ],
  "issues": {
    "q_age": "请输入有效数字"
  },
  "current_question_id": "q_age",
  "read_only": false,
  "read_only_reason": null,
  "deadline": null
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 事务内检查归属/状态/revision、开放；清除确定跳过内容，写草稿revision+1。

**幂等、冲突与事务：** 串行请求结合乐观并发；旧revision409；不是无条件覆盖。

**失败场景：** 未知题/非法结构/超限422，关闭或终态/冲突409，他人404。

**补充约定：** 允许不完整、超题目范围或中间数字字符串。raw单项字符串最多20000、最多100题；中间值不参与规则。位置仅提示，由服务器约束。


## API19 明确放弃草稿

**方法和路径：** `POST /api/attempts/{aid}/abandon`

**认证与权限：** 有效登录且本人，不要求问卷开放。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| aid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "revision": 2
}
```

### 成功响应示例 HTTP 200

```json
{
  "ok": true
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 按_id/revision/in_progress单文档原子条件更新，清空答案并转abandoned。

**幂等、冲突与事务：** 非成功回执幂等；终态重发409，不能恢复或接受迟到保存。

**失败场景：** 冲突/已结束409，他人404，未登录401。

**补充约定：** 前端确认后发送；成功即删除该过程答案副本，后续可按策略新建。


## API20 提交已保存草稿

**方法和路径：** `POST /api/attempts/{aid}/submit`

**认证与权限：** 有效登录且本人；新提交须进行中和开放。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| aid | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "revision": 3
}
```

### 成功响应示例 HTTP 200

```json
{
  "version": 1,
  "submitted_at": "2026-10-20T10:03:00",
  "id": "777777777777777777777777"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 事务读服务器草稿并完整校验，追加responses，关联回执并清空草稿内容。

**幂等、冲突与事务：** 同一已提交过程重试先返回原回执，不先拒绝旧revision。

**失败场景：** 逐题非法422，状态/重复/冲突409，他人404。

**补充约定：** 请求不含answers；客户端须先完成最新保存。已提交重试可返回旧回执，不重新创建答案。


## API21 整卷及每题统计

**方法和路径：** `GET /api/surveys/{sid}/statistics`

**认证与权限：** 有效登录且问卷所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |
| version | query | integer；minimum=1 或 null | 否 | "无显式默认" |
| start | query | string 或 null | 否 | "无显式默认" |
| end | query | string 或 null | 否 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "version": 1,
  "title": "课程学习与实践调查",
  "total": 1,
  "respondent_count": 1,
  "questions": [
    {
      "id": "q_role",
      "title": "你的身份",
      "type": "single_choice",
      "answered": 1,
      "respondent_count": 1,
      "options": [
        {
          "id": "student",
          "label": "学生",
          "count": 0,
          "respondent_count": 0
        },
        {
          "id": "worker",
          "label": "已工作",
          "count": 1,
          "respondent_count": 1
        }
      ]
    },
    {
      "id": "q_tools",
      "title": "使用过哪些工具",
      "type": "multiple_choice",
      "answered": 0,
      "respondent_count": 0,
      "options": [
        {
          "id": "mongo",
          "label": "MongoDB",
          "count": 0,
          "respondent_count": 0
        },
        {
          "id": "python",
          "label": "Python",
          "count": 0,
          "respondent_count": 0
        },
        {
          "id": "java",
          "label": "Java",
          "count": 0,
          "respondent_count": 0
        }
      ]
    },
    {
      "id": "q_age",
      "title": "年龄",
      "type": "number",
      "answered": 1,
      "respondent_count": 1,
      "average": 40,
      "min": 40,
      "max": 40
    },
    {
      "id": "q_feedback",
      "title": "建议",
      "type": "text",
      "answered": 0,
      "respondent_count": 0
    }
  ]
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 只读responses与指定版本，分别聚合人数、次数和题型结果。

**幂等、冲突与事务：** 多个聚合，不是同一时点快照。

**失败场景：** 无版本/他人404，反向或无时区时间422。

**补充约定：** version省略取当前；start/end含时区，边界包含。零回答数字统计为null，选项补0；不统计attempts。


## API22 某题内容分页

**方法和路径：** `GET /api/surveys/{sid}/questions/{qid}/values`

**认证与权限：** 有效登录且问卷所有者。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| sid | path | string | 是 | "无显式默认" |
| qid | path | string | 是 | "无显式默认" |
| version | query | integer；minimum=1 或 null | 否 | "无显式默认" |
| page | query | integer；minimum=1 | 否 | 1 |
| start | query | string 或 null | 否 | "无显式默认" |
| end | query | string 或 null | 否 | "无显式默认" |

### 请求示例

无JSON请求体。

### 成功响应示例 HTTP 200

```json
{
  "items": [
    {
      "value": 40,
      "submitted_at": "2026-10-20T10:03:00",
      "anonymous": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 筛选版本时间，展开题目非空答案并排序分页。

**幂等、冲突与事务：** 只读；持续新增时skip分页可能变化。

**失败场景：** 题目/版本/他人404，page或时间非法422。

**补充约定：** page默认1，每页20；按submitted_at倒序/_id升序。实名项可有user_id，匿名项没有；不返回内部去重键。


## API23 旧凭证式开始（兼容）

**方法和路径：** `POST /api/public/{share}/start`

**认证与权限：** 有效登录且开放。

### 参数

| 名称 | 位置 | 类型与限制 | 必需 | 默认 |
| --- | --- | --- | --- | --- |
| share | path | string | 是 | "无显式默认" |

### 请求示例

```json
{
  "anonymous": true
}
```

### 成功响应示例 HTTP 200

```json
{
  "token": "服务端签名字符串",
  "definition": {
    "title": "课程学习与实践调查",
    "description": "用于说明文档结构与路径的脱敏示例",
    "allow_anonymous": true,
    "allow_repeat": true,
    "questions": [
      {
        "id": "q_role",
        "type": "single_choice",
        "title": "你的身份",
        "required": true,
        "options": [
          {
            "id": "student",
            "label": "学生"
          },
          {
            "id": "worker",
            "label": "已工作"
          }
        ],
        "validation": {},
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_role",
                "operator": "eq",
                "value": "worker"
              },
              "target": "q_age"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_tools",
        "type": "multiple_choice",
        "title": "使用过哪些工具",
        "required": true,
        "options": [
          {
            "id": "mongo",
            "label": "MongoDB"
          },
          {
            "id": "python",
            "label": "Python"
          },
          {
            "id": "java",
            "label": "Java"
          }
        ],
        "validation": {
          "min_choices": 2,
          "max_choices": 2
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_tools",
                "operator": "contains_all",
                "value": [
                  "mongo",
                  "python"
                ]
              },
              "target": "q_feedback"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_age",
        "type": "number",
        "title": "年龄",
        "required": true,
        "options": [],
        "validation": {
          "min": 0,
          "max": 120,
          "integer_only": true
        },
        "routing": {
          "rules": [
            {
              "condition": {
                "question_id": "q_age",
                "operator": "between",
                "value": [
                  60,
                  120
                ]
              },
              "target": "END"
            }
          ],
          "default_target": null
        }
      },
      {
        "id": "q_feedback",
        "type": "text",
        "title": "建议",
        "required": false,
        "options": [],
        "validation": {
          "min_length": 2,
          "max_length": 100
        },
        "routing": {
          "rules": [],
          "default_target": "END"
        }
      }
    ]
  },
  "version": 1,
  "deadline": null,
  "anonymous": true
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 查状态、版本、重复策略，签发24小时token，不创建attempts。

**幂等、冲突与事务：** 每次调用生成新attempt_id，不自动恢复。

**失败场景：** 匿名非法422，关闭/截止/禁止重复409。

**补充约定：** 旧页面未提交输入不保存。新填写页不用此接口；保留是为了兼容，非第二份新草稿答案来源。


## API24 旧凭证路径校验（兼容）

**方法和路径：** `POST /api/evaluate`

**认证与权限：** 有效登录且token属于本人。

### 参数

无路径或查询参数。

### 请求示例

```json
{
  "token": "开始接口返回的签名字符串",
  "answers": {
    "q_role": "worker",
    "q_age": 40
  }
}
```

### 成功响应示例 HTTP 200

```json
{
  "answers": {
    "q_role": "worker",
    "q_age": 40,
    "q_feedback": null
  },
  "path": [
    "q_role",
    "q_age",
    "q_feedback"
  ]
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 读token绑定版本并evaluate，不保存。

**幂等、冲突与事务：** 只读，可重复；不是正式提交。

**失败场景：** token无效/过期401、他人token403、逐题422、版本缺失404。

**补充约定：** 此预览不执行最终提交的开放/截止事务检查；预览通过不代表之后提交必成功。


## API25 旧凭证正式提交（兼容）

**方法和路径：** `POST /api/responses`

**认证与权限：** 有效登录且token属于本人。

### 参数

无路径或查询参数。

### 请求示例

```json
{
  "token": "开始接口返回的签名字符串",
  "answers": {
    "q_role": "worker",
    "q_age": 40
  }
}
```

### 成功响应示例 HTTP 200

```json
{
  "version": 1,
  "submitted_at": "2026-10-20T10:03:00",
  "id": "777777777777777777777777"
}
```

**字段解释：** 见本接口用途与第二部分对象字典；definition结构完整列于响应或Definition模型，日期为ISO8601字符串。

**数据库变化：** 事务查同attempt回执，校验开放/版本/重复及路径，写正式答卷。

**幂等、冲突与事务：** 同token在有效期内重试返回原回执，即使重试答案改变也不覆盖。

**失败场景：** 无效token401、他人403、非法答案422、状态/重复409。

**补充约定：** 已有回执先返回；token过期时先解码失败，不能宣称无限期重试。此流程不创建或更新持久草稿。


## 四 错误协议与处理

业务错误：

```json
{"error":"请检查填写内容","details":{"q_age":"数字超出允许范围"}}
```

结构错误：

```json
{"error":"请求字段格式不正确：输入不合法","details":[{"field":"body.revision","message":"字段校验失败"}]}
```

| 状态码 | 用途 | 客户端处理 |
| --- | --- | --- |
| 401 | 未登录、会话失效或旧token无效 | 恢复登录，填写页保留本地未同步输入 |
| 403 | 不允许Origin或旧token属于他人 | 核对来源和账号，不绕过权限 |
| 404 | 不存在或不属于当前用户 | 不继续猜测资源，不显示他人内容 |
| 409 | revision/状态/重复限制冲突 | 读服务器状态，明确决定重载，不盲目重试覆盖 |
| 413 | 声明请求体过大 | 减少输入规模 |
| 422 | 模型、配置或答案不合法 | 显示字段或逐题错误，修改后重试 |
| 503 | 数据库不可用或写入失败 | 保留输入，排查服务后重试 |

基础结构错误的details是数组，逐题业务错误通常是对象，其余错误可能为null，客户端不能无条件按一种类型读取。并非任何异常都转换成以上错误，例如未覆盖的程序错误仍可能是500；文档不承诺捕获所有故障。

## 五 完整调用链与revision流转

以下Python脚本在服务已启动、依赖已安装后可自行运行，会创建独立测试账号和问卷。它是可执行调用示例，本轮仅作语法和字段核对，没有将其输出冒充为新验收结果。Cookie使用httpx.Client保持，ID与revision从响应取得。


```python
import json
from uuid import uuid4
import httpx

definition = json.loads(r'''{
  "title": "课程学习与实践调查",
  "description": "用于说明文档结构与路径的脱敏示例",
  "allow_anonymous": true,
  "allow_repeat": true,
  "questions": [
    {
      "id": "q_role",
      "type": "single_choice",
      "title": "你的身份",
      "required": true,
      "options": [
        {
          "id": "student",
          "label": "学生"
        },
        {
          "id": "worker",
          "label": "已工作"
        }
      ],
      "validation": {},
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_role",
              "operator": "eq",
              "value": "worker"
            },
            "target": "q_age"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_tools",
      "type": "multiple_choice",
      "title": "使用过哪些工具",
      "required": true,
      "options": [
        {
          "id": "mongo",
          "label": "MongoDB"
        },
        {
          "id": "python",
          "label": "Python"
        },
        {
          "id": "java",
          "label": "Java"
        }
      ],
      "validation": {
        "min_choices": 2,
        "max_choices": 2
      },
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_tools",
              "operator": "contains_all",
              "value": [
                "mongo",
                "python"
              ]
            },
            "target": "q_feedback"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_age",
      "type": "number",
      "title": "年龄",
      "required": true,
      "options": [],
      "validation": {
        "min": 0,
        "max": 120,
        "integer_only": true
      },
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_age",
              "operator": "between",
              "value": [
                60,
                120
              ]
            },
            "target": "END"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_feedback",
      "type": "text",
      "title": "建议",
      "required": false,
      "options": [],
      "validation": {
        "min_length": 2,
        "max_length": 100
      },
      "routing": {
        "rules": [],
        "default_target": "END"
      }
    }
  ]
}''')
password = "ExamplePass123!"
owner = "owner_" + uuid4().hex[:10]
filler = "filler_" + uuid4().hex[:10]
def result(response):
    response.raise_for_status()
    return response.json()

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as c:
    result(c.get("/api/health"))
    result(c.post("/api/auth/register", json={"username":owner,"password":password}))
    survey = result(c.post("/api/surveys", json={"title":definition["title"]}))
    sid, share = survey["_id"], survey["share_code"]
    survey = result(c.put(f"/api/surveys/{sid}/draft", json={"revision":survey["revision"],"draft":definition}))
    published = result(c.post(f"/api/surveys/{sid}/publish", json={"revision":survey["revision"],"deadline":None}))
    result(c.post("/api/auth/logout"))
    result(c.post("/api/auth/register", json={"username":filler,"password":password}))
    assert result(c.get(f"/api/public/{share}/attempt")) is None
    attempt = result(c.post(f"/api/public/{share}/attempt", json={"anonymous":True}))
    aid = attempt["_id"]
    attempt = result(c.put(f"/api/attempts/{aid}", json={"revision":attempt["revision"],"answers":{"q_role":"worker","q_age":"-"},"current_question_id":"q_age"}))
    restored = result(c.get(f"/api/public/{share}/attempt"))
    assert restored["_id"] == aid and restored["answers"]["q_age"] == "-"
    attempt = result(c.put(f"/api/attempts/{aid}", json={"revision":restored["revision"],"answers":{"q_role":"worker","q_age":"40","q_feedback":None},"current_question_id":"q_feedback"}))
    body = {"revision":attempt["revision"]}
    receipt = result(c.post(f"/api/attempts/{aid}/submit", json=body))
    assert result(c.post(f"/api/attempts/{aid}/submit", json=body)) == receipt
    result(c.post("/api/auth/logout"))
    result(c.post("/api/auth/login", json={"username":owner,"password":password}))
    stats = result(c.get(f"/api/surveys/{sid}/statistics", params={"version":published["version"]}))
    assert stats["total"] == stats["respondent_count"] == 1
    survey = result(c.get(f"/api/surveys/{sid}"))
    result(c.patch(f"/api/surveys/{sid}/status", json={"status":"closed","revision":survey["revision"]}))
    print({"survey_id":sid,"response_id":receipt["id"],"total":stats["total"]})
```

## 六 核对入口与验证限制

接口数量、路径、参数和请求模型已与当前create_app().openapi()静态定义逐项核对，静态JSON附于[证据目录](../3_测试用例/测试证据/接口静态定义.openapi.json)。完整调用脚本已作Python语法检查，不宣称本轮实际对服务执行。响应字段依据main.py和服务返回值整理，因当前多数接口未声明完整response_model，不能仅依赖自动OpenAPI推断全部响应。

事务、状态、匿名、人数、错误和历史兼容的已执行结果见[测试用例](../3_测试用例/测试用例与结果.md)。当前新填写页只使用attempts，旧start/evaluate/responses保持兼容，不将它们混用为两个草稿来源。
