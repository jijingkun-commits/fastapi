# AI 出题智能体澄清设计（独立后台页 / 指定知识库 / PDF 交付）

> 设计目标：在**不耦合现有聊天 supervisor** 的前提下，新增一个独立的后台管理页能力，基于用户选择的知识库范围生成试卷与答案 PDF，并支持直接下载。

## 0. 结论先行（Final）
- 采用**独立后台页 + 独立出题工作流**，不接入现有 `chat/supervisor/multi_agent_graph` 主链。
- 采用**知识检索 + 结构化组卷 + HTML 排版 + PDF 导出** 的单一路径，不做“聊天里顺手生成 PDF”的双轨设计。
- 采用**用户可编辑初始组卷模板**：后台页先加载默认模板，用户可修改首期固定题型（单选/多选/判断/简答）的题量、难度、分值与标题后再生成。
- 采用**用户显式选择知识库范围**：至少支持多 `dataset_id` 选择；V1 先不做按段落/知识点树精细裁剪。多数据集按用户勾选顺序作为优先级，出现知识冲突时任务失败并提示缩小范围。
- 采用**作业化生成语义**：点击“生成并下载”后创建独立生成任务，完成后自动返回下载链接/触发下载，避免长请求直接回传大文件。
- 采用**试卷与答案同一份 PDF**：试卷正文在前，答案区在后，答案需附简短解析，并通过显式分页规则保证分页清晰、打印稳定。
- 采用**生成历史可回放**：每次成功生成都要登记历史记录，并将 PDF 作为 `export` 资产保存到现有 MinIO，支持后续重复下载。
- 采用**出题质量门禁**：题目生成完成后必须通过题型合法、答案合法、证据存在、去重、覆盖度检查，未通过不得进入 PDF。
- 采用**后台权限与限流约束**：仅后台管理员可访问；默认仅可查看本人历史记录；限制单次总题量和单用户并发生成任务数。
- 采用**低耦合边界**：只复用现有 `RAGFlow` 检索能力与资产存储能力；禁止改造现有 `supervisor` 来承接该场景。

```mermaid
flowchart LR
  UI["后台管理页"] --> FORM["组卷模板编辑"]
  FORM --> API["Exam Admin API"]
  API --> JOB["Exam Generation Job"]
  JOB --> RETRIEVE["RAGFlow 检索指定知识库"]
  RETRIEVE --> AGENT["Exam Generation Workflow"]
  AGENT --> CONTRACT["Paper Contract"]
  CONTRACT --> HTML["HTML Template Renderer"]
  HTML --> PDF["PDF Renderer"]
  PDF --> ASSET["Export Asset"]
  ASSET --> DOWNLOAD["直接下载"]
```

## 1. scope_contract

| 项目 | 冻结结论 |
|---|---|
| 目标 | 后台管理员在单独页面中，选择知识库范围、调整组卷模板，生成一份“试卷 + 答案”的 PDF 并直接下载 |
| 范围内 | 独立后台页、模板编辑、知识库范围选择、AI 生成题目、质量门禁、PDF 导出、导出任务结果展示/下载、历史记录查看与重复下载、权限控制与限流 |
| 范围外 | 不接入聊天页面；不复用现有聊天 supervisor；不做学生答题页；不做自动阅卷；不做题库运营后台；不做复杂模板市场 |
| 成功标准 | 管理员可在 1 个页面完成：选范围 → 调模板 → 点按钮 → 通过质量门禁 → 成功得到分页正确的 PDF |
| 发布边界 | V1 仅支持“基于知识生成题目”，不要求知识库中已有原题；V1 默认一份任务生成一份 PDF |

## 2. product_contract（PRD-Lite）

- target_users:
  - 后台管理员
  - 题库/培训运营人员
  - 内部教研/业务负责人
- core_scenarios:
  - 管理员进入独立后台页，选择 1~N 个知识库数据集
  - 管理员修改默认组卷模板并提交生成任务
  - 系统按多数据集优先级检索知识证据并生成题单
  - 题单通过质量门禁后导出为 PDF
  - 管理员可直接下载并在历史记录中重复下载
- business_goals:
  - 在不污染现有聊天主链的前提下落地可用的 AI 出题能力
  - 将知识到试题到 PDF 的链路收敛为后台可操作产品能力
  - 保证每道题可回溯到知识证据并降低幻觉出题风险
  - 让成功生成结果可打印、可归档、可重复下载
  - 将生成历史沉淀为可回放的后台资产记录
- non_goals:
  - 不做在线考试流程
  - 不做学生端页面
  - 不做题目人工审核流
  - 不做多租户模板中心
  - 不把该功能塞进现有对话智能体体系
- acceptance_gates:
  - 独立后台页面入口存在
  - 用户必须显式选择知识库范围
  - 默认模板可编辑且题型固定为单选/多选/判断/简答
  - 每道题都存在证据且必须通过质量门禁
  - 单个 PDF 含试卷、答案、简短解析且分页正确
  - 任务成功后可直接下载
  - 历史记录可查看且可重复下载
  - 后台权限与限流策略生效

### 2.1 target_users
- 后台管理员
- 题库/培训运营人员
- 内部教研/业务负责人

### 2.2 core_scenarios
1. 管理员进入独立后台页，选择 1~N 个知识库数据集。
2. 系统加载默认组卷模板，管理员可改题型、题量、分值、标题、难度分布。
3. 管理员点击“生成并下载”，系统创建任务并执行出题。
4. 系统基于知识库内容检索证据，按用户勾选顺序混合多个数据集，并在冲突时直接失败。
5. 系统生成试题、答案与简短解析，并先通过质量门禁，再输出单份 PDF。
6. 生成完成后，页面显示任务状态并支持直接下载。
7. 管理员可在历史记录中查看既往生成任务，并重新下载保存在 MinIO 中的 PDF。

### 2.3 business_goals
- 在不污染现有聊天主链的前提下，落地一个可用的 AI 出题能力。
- 将“知识 → 试题 → PDF”链路收敛为后台可操作产品能力。
- 保证每道题可回溯到知识证据，降低幻觉与越界出题风险。
- 将“生成完成”定义为“题目通过质量门禁”，而不是模型先吐出结果就算成功。
- 确保生成结果可打印、可归档、可重复下载。
- 将成功生成记录沉淀为后台历史资产，避免“下完就丢”。

### 2.4 KPI
- 管理员完成一次从配置到下载的成功率 >= 90%。
- 生成结果中 100% 题目都带有结构化来源证据。
- 95% 以上生成任务在目标时限内完成（时限由部署后观测再定，V1 不先写死 SLA）。
- PDF 分页错误（题干/答案截断、页眉页脚错位）在验收样本中为 0 个 blocker。
- 题目质量门禁误放行率在验收样本中为 0 个 blocker。

### 2.5 non_goals
- 不做在线考试流程。
- 不做学生端页面。
- 不做题目人工审核流。
- 不做多租户模板中心。
- 不把该功能塞进现有对话智能体体系。

### 2.6 acceptance_gates
- 必须存在独立后台页面入口。
- 必须允许用户显式选择知识库范围。
- 必须提供可编辑初始模板，而不是写死题量。
- 必须产出“试卷 + 答案”单一 PDF，且有明确分页。
- 必须与现有 `supervisor/chat` 主链低耦合。
- 必须支持生成后直接下载。
- 必须存在历史记录列表，并支持重复下载。
- 必须存在题目质量门禁，且门禁失败时不得导出 PDF。
- 必须明确多数据集优先级和冲突语义。
- 必须存在后台权限控制与任务限流。

## 2.7 product_contract（机读）

```yaml
product_contract:
  target_users:
    - 后台管理员
    - 题库/培训运营人员
    - 内部教研/业务负责人
  core_scenarios:
    - 管理员进入独立后台页，选择 1~N 个知识库数据集
    - 管理员修改默认组卷模板并提交生成任务
    - 系统按多数据集优先级检索知识证据并生成题单
    - 题单通过质量门禁后导出为 PDF
    - 管理员可直接下载并在历史记录中重复下载
  business_goals:
    - 在不污染现有聊天主链的前提下落地可用的 AI 出题能力
    - 将知识到试题到 PDF 的链路收敛为后台可操作产品能力
    - 保证每道题可回溯到知识证据并降低幻觉出题风险
    - 让成功生成结果可打印、可归档、可重复下载
    - 将生成历史沉淀为可回放的后台资产记录
  non_goals:
    - 不做在线考试流程
    - 不做学生端页面
    - 不做题目人工审核流
    - 不做多租户模板中心
    - 不把该功能塞进现有对话智能体体系
  acceptance_gates:
    - 独立后台页面入口存在
    - 用户必须显式选择知识库范围
    - 默认模板可编辑且题型固定为单选/多选/判断/简答
    - 每道题都存在证据且必须通过质量门禁
    - 单个 PDF 含试卷、答案、简短解析且分页正确
    - 任务成功后可直接下载
    - 历史记录可查看且可重复下载
    - 后台权限与限流策略生效
```

## 3. architecture_contract

### 3.1 模块边界
| 模块 | 职责 | 禁止负责 |
|---|---|---|
| `exam_admin_page` | 展示表单、提交任务、展示状态、触发下载 | 不直接写生成逻辑，不直接拼 PDF |
| `exam_admin_api` | 参数校验、任务创建、状态查询、下载入口 | 不直接调用底层检索细节 |
| `exam_generation_service` | 编排任务生命周期，调用检索/工作流/质量门禁/渲染/资产存储 | 不感知前端展示细节 |
| `exam_generation_workflow` | 根据模板与知识证据生成结构化题单 | 不负责 PDF 排版，不直接决定导出成功 |
| `pdf_render_service` | 根据标准 `Paper Contract` 渲染 HTML/PDF | 不做知识检索与题目生成 |
| `exam_job_repo` | 持久化任务状态、模板快照、结果 canonical、历史记录索引 | 不做业务推理 |
| `rag_retrieval_gateway` | 读取指定知识库内容与证据片段，并按多数据集优先级返回证据 | 不负责题目质量校验 |
| `asset_service` | 将 PDF 保存到现有 MinIO 并提供下载链接 | 不理解试卷语义 |
| `exam_quality_gate` | 校验题型合法性、答案合法性、证据存在、去重、覆盖度 | 不负责检索与 PDF 渲染 |
| `exam_access_policy` | 校验后台权限、历史可见范围、并发与题量上限 | 不负责出题本身 |

### 3.2 依赖方向
```text
Admin Page -> Exam Admin API -> Exam Generation Service
Exam Generation Service -> Exam Generation Workflow
Exam Generation Service -> RAG Retrieval Gateway
Exam Generation Service -> Exam Quality Gate
Exam Generation Service -> PDF Render Service
Exam Generation Service -> Asset Service
Exam Generation Service -> Exam Job Repo
Exam Admin API -> Exam Access Policy
```

冻结规则：
1. `exam_generation_*` 不能依赖现有 `app/services/chat_service.py`。
2. `exam_generation_*` 不能修改 `app/ai/workflow/multi_agent_graph.py` 才能工作。
3. 现有 `supervisor` 不得反向调用出题工作流。
4. 知识检索复用 `RAGFlow` 网关即可，不做新的知识引擎分叉。

### 3.3 端到端数据流
1. 后台页调用“获取默认模板”接口，拿到初始组卷模板。
2. 管理员选择知识库范围并修改模板。
3. 页面调用“创建生成任务”接口。
4. 后端将模板快照与知识库选择写入 `exam_generation_job`。
5. 任务执行时先按多数据集优先级检索知识证据，再生成结构化题单 `Paper Contract`。
6. 结构化题单必须先通过 `exam_quality_gate`；未通过则任务失败。
7. 通过质量门禁后，交给 `pdf_render_service` 输出 PDF。
8. PDF 保存为 `export` 资产到现有 MinIO，并把 `asset_id/object_key/download_url` 写回任务记录。
9. 页面轮询任务状态；成功后自动下载，失败后展示明确原因。
10. 历史记录列表通过任务表 canonical 结果 + MinIO 资产信息回放，不重新生成 PDF。

### 3.4 状态生命周期
| 状态 | 含义 | owner |
|---|---|---|
| `draft` | 仅模板已加载/未提交 | 前端表单态 |
| `queued` | 已提交待处理 | `exam_generation_job` |
| `running` | 正在检索/出题/质检/排版 | `exam_generation_job` |
| `succeeded` | PDF 已产出并登记资产 | `exam_generation_job` |
| `failed` | 任务失败并有错误原因 | `exam_generation_job` |

冻结规则：
- 页面刷新后的唯一真理源是 `exam_generation_job.result_payload`。
- 历史记录页的唯一真理源也是 `exam_generation_job.result_payload`，不是前端缓存。
- 前端只读任务状态，不拼接“隐式成功”。
- 模板提交后必须保存请求快照，后续下载与重试都使用同一快照回放。

### 3.5 异常语义
| 场景 | 冻结语义 |
|---|---|
| 知识库未选 | API 直接 400，禁止自动猜默认知识库 |
| 模板非法（题量 <=0、分值不闭合等） | API 直接 400，返回字段级错误 |
| 多数据集知识冲突 | 任务失败，提示用户缩小范围或调整优先级 |
| 检索结果不足 | 任务失败，返回“知识证据不足，无法按模板生成” |
| LLM 生成结果不合法 | 工作流内部最多有限次重试；仍失败则任务失败 |
| 质量门禁失败 | 任务失败，不导出 PDF |
| PDF 渲染失败 | 任务失败，不生成半成品下载 |
| 资产保存失败 | 任务失败，不返回伪下载链接 |
| 权限不足或超限 | API 直接拒绝，并返回明确错误码 |

### 3.6 低耦合硬约束
- 不新增现有聊天状态字段来支持本功能。
- 不在 `app/ai/workflow/multi_agent_graph.py` 增加出题分支。
- 不在 `app/api/v1/endpoints/chat_api.py` 增加出题入口。
- 不复用聊天线程/消息作为本功能的持久化真理源。
- 不把质量门禁逻辑塞进前端或 PDF 渲染层。
- 不把多数据集冲突处理交给 prompt 模糊决策。
- 只允许复用：`RAGFlow` 检索能力、通用资产存储能力、通用 LLM/配置能力。

## 4. 关键设计冻结

### 4.1 智能体形态冻结
- 该能力在产品上叫“AI 出题智能体”。
- 在工程上冻结为：**独立单任务工作流**，而不是接入通用聊天智能体体系。
- 推荐实现形态：`exam_generation_workflow`（可用独立 LangGraph，也可由服务层按固定步骤串联；V1 优先“固定步骤 + 结构化 contract”）。

### 4.2 知识来源冻结
- 知识库中存的是**知识**，不是原题。
- 因此出题策略冻结为：**基于知识证据生成新题**。
- 每道题必须带结构化证据：至少包含 `dataset_id/doc_id/chunk_id/excerpt` 中的可用子集。
- 每道题除了标准答案，还必须生成简短解析；解析默认只出现在答案区，不出现在试卷正文。
- V1 不做“已有题库抽题”与“知识生成题”混合策略。
- 多数据集默认按用户勾选顺序作为优先级；若高优先级与低优先级知识冲突，直接失败，不做静默覆盖。

### 4.3 模板编辑冻结
- 后台页必须先加载“默认组卷模板”。
- 用户可以修改，但 V1 不做“模板管理中心/模板版本库”。
- V1 题型固定为：**单选、多选、判断、简答**。
- 模板编辑采用**结构化表单**，不要求用户直接写 JSON。

建议模板字段冻结如下：
| 字段 | 说明 |
|---|---|
| `paper_title` | 试卷标题 |
| `single_choice_count` | 单选题数量 |
| `multiple_choice_count` | 多选题数量 |
| `judge_count` | 判断题数量 |
| `short_answer_count` | 简答题数量 |
| `difficulty_distribution` | 易/中/难占比 |
| `score_strategy` | 题型分值配置 |
| `answer_section_enabled` | 固定为 `true`，V1 不关闭 |
| `answer_page_break` | 固定为 `true`，答案区单独分页 |
| `answer_explanation_mode` | 固定为 `short`，答案区输出简短解析 |

### 4.4 题目质量门禁冻结
- 单选题：固定 4 个选项，且仅允许 1 个正确答案。
- 多选题：固定 4~6 个选项，且至少 2 个正确答案。
- 判断题：只允许“对/错”，并必须带一句依据。
- 简答题：必须输出“参考答案 + 3~5 个要点”。
- 每道题都必须存在来源证据。
- 高相似度重复题不得同时出现在同一份试卷。
- 若知识点覆盖明显偏斜，质量门禁必须失败而不是强行放行。

### 4.5 多数据集规则冻结
- 用户可选择多个 `dataset_id`。
- 用户勾选顺序即多数据集优先级顺序。
- 检索允许跨数据集召回，但每道题都必须记录实际证据来源数据集。
- 当不同数据集知识出现明显冲突时，任务失败并提示用户缩小范围；禁止静默择一。

### 4.6 PDF 输出冻结
- 输出物固定为**单个 PDF**。
- PDF 结构固定为：
  1. 封面/标题信息（可选简版）
  2. 试卷正文
  3. 手动分页
  4. 答案区（答案 + 简短解析）
- 分页规则冻结：
  - 每道大题不得在页底只剩标题；必要时整题换页。
  - 答案区必须从新页开始。
  - 简短解析紧跟对应答案输出，禁止解析跨到正文区。
  - 页眉/页脚使用 Paged Media 规则统一渲染。

### 4.7 PDF 技术选型冻结
- V1 采用 **HTML + CSS Paged Media -> WeasyPrint PDF**。
- 选择理由：
  - 对分页、页眉页脚、打印版式支持成熟。
  - 后端 Python 内可直接运行，减少浏览器驱动依赖。
  - 比“让 LLM 直接写二进制/富文本导出”更稳定、可测试。
- 不采用：
  - 把 PDF 生成塞进前端浏览器导出。
  - 直接从 Markdown 粗暴转 PDF。
  - 在 V1 引入复杂 headless browser 打印链路。

### 4.8 结果 canonical 冻结
- 任务结果唯一真理源：`exam_generation_job.result_payload`。
- 其中至少包含：
  - `request_snapshot`
  - `paper_contract`
  - `asset_id`
  - `minio_object_key`
  - `download_url`
  - `status`
  - `error_info`
- 页面刷新、重新进入列表、点击下载，全部只认该字段。

### 4.9 生成历史冻结
- 后台页必须提供历史记录列表。
- 每次成功生成都必须落一条历史记录，并指向 MinIO 中已保存的 `export` 资产。
- 历史记录必须至少展示：标题、数据集摘要、模板快照摘要、状态、生成时间、下载入口。
- 历史记录页只做查看与重复下载，不重新触发生成。
- 若 MinIO 资产缺失，历史记录必须展示“资产不可用”，不能伪装为可下载。

### 4.10 权限与限流冻结
- 页面仅后台管理员可访问。
- 默认只允许查看本人创建的历史记录；V1 不做全局共享视图。
- 单次总题量必须有上限；建议 V1 默认 `<= 100`。
- 单用户同时运行中的生成任务必须有限制；建议 V1 默认 `<= 3`。
- 超时任务直接失败，不返回半成品 PDF。
- 读写语义：**只写新 canonical，不保留第二套并行结果字段**。

## 5. requirement_seeds

```yaml
requirement_seeds:
  - design_item: D-01
    fr_id: FR-EXAM-ADMIN-PAGE
    trigger: 管理员进入 AI 出题后台页
    input_contract:
      required_fields: []
      optional_fields: [last_template_snapshot]
      defaults: {}
    output_contract:
      required_fields: [template_form, dataset_selector, generate_button]
      optional_fields: [job_history]
    failure_semantics: 页面加载失败时展示错误态，不允许空白页
    observability_fields: [user_id, page_route]
    rollback_anchor: feature.enable_exam_generation_admin=false
    acceptance_gate: 后台存在独立页面入口

  - design_item: D-02
    fr_id: FR-EXAM-DATASET-SELECTION
    trigger: 用户提交生成任务
    input_contract:
      required_fields: [dataset_ids]
      optional_fields: [doc_filters]
      defaults: {}
    output_contract:
      required_fields: [validated_dataset_scope]
      optional_fields: []
    failure_semantics: dataset_ids 为空时直接拒绝提交
    observability_fields: [user_id, dataset_count, dataset_ids]
    rollback_anchor: feature.enable_exam_generation_admin=false
    acceptance_gate: 用户必须可选知识库范围

  - design_item: D-03
    fr_id: FR-EXAM-TEMPLATE-EDIT
    trigger: 用户修改默认模板并提交
    input_contract:
      required_fields: [paper_template]
      optional_fields: [paper_title, score_strategy, difficulty_distribution]
      defaults:
        answer_section_enabled: true
        answer_page_break: true
    output_contract:
      required_fields: [request_snapshot]
      optional_fields: []
    failure_semantics: 非法模板字段返回字段级错误
    observability_fields: [template_hash, total_question_count]
    rollback_anchor: feature.enable_exam_generation_template=false
    acceptance_gate: 初始模板可编辑而不是写死

  - design_item: D-04
    fr_id: FR-EXAM-KNOWLEDGE-TO-QUESTION
    trigger: 任务进入 running
    input_contract:
      required_fields: [dataset_ids, request_snapshot]
      optional_fields: [doc_filters, dataset_priority_order]
      defaults: {}
    output_contract:
      required_fields: [paper_contract.questions, paper_contract.answers, paper_contract.explanations]
      optional_fields: [evidence_map]
    failure_semantics: 检索不足、生成不合法或多数据集冲突时任务失败
    observability_fields: [job_id, retrieved_chunk_count, question_count, dataset_priority_order]
    rollback_anchor: feature.enable_exam_generation_workflow=false
    acceptance_gate: 题目基于知识生成而非假定已有原题

  - design_item: D-05A
    fr_id: FR-EXAM-QUALITY-GATE
    trigger: paper_contract 生成完成
    input_contract:
      required_fields: [paper_contract, evidence_map]
      optional_fields: [dataset_priority_order]
      defaults: {}
    output_contract:
      required_fields: [quality_gate_pass]
      optional_fields: [quality_report]
    failure_semantics: 任一门禁失败时直接阻断 PDF 导出
    observability_fields: [job_id, duplicate_count, coverage_score, evidence_missing_count]
    rollback_anchor: feature.enable_exam_generation_quality_gate=false
    acceptance_gate: 题目必须通过质量门禁后才可导出 PDF

  - design_item: D-05
    fr_id: FR-EXAM-PDF-WITH-ANSWERS
    trigger: paper_contract 校验通过
    input_contract:
      required_fields: [paper_contract]
      optional_fields: [render_options]
      defaults:
        answer_page_break: true
    output_contract:
      required_fields: [pdf_bytes, asset_id, minio_object_key, download_url]
      optional_fields: []
    failure_semantics: 渲染失败或保存失败则任务失败
    observability_fields: [job_id, page_count, pdf_size]
    rollback_anchor: feature.enable_exam_generation_pdf=false
    acceptance_gate: 单份 PDF 包含试卷与答案且分页正确

  - design_item: D-06
    fr_id: FR-EXAM-DIRECT-DOWNLOAD
    trigger: 任务成功
    input_contract:
      required_fields: [asset_id, download_url]
      optional_fields: []
      defaults: {}
    output_contract:
      required_fields: [downloadable_export]
      optional_fields: [file_name]
    failure_semantics: 禁止返回空链接或失效链接冒充成功
    observability_fields: [job_id, asset_id, download_started]
    rollback_anchor: feature.enable_exam_generation_download=false
    acceptance_gate: 点击生成后最终可直接下载

  - design_item: D-06A
    fr_id: FR-EXAM-ACCESS-POLICY
    trigger: 用户访问页面、提交任务或查看历史记录
    input_contract:
      required_fields: [user_id]
      optional_fields: [job_id, total_question_count, active_job_count]
      defaults: {}
    output_contract:
      required_fields: [access_decision]
      optional_fields: [reason_code]
    failure_semantics: 权限不足或超过限额时直接拒绝，不进入生成阶段
    observability_fields: [user_id, reason_code, total_question_count, active_job_count]
    rollback_anchor: feature.enable_exam_generation_access_policy=false
    acceptance_gate: 后台权限与限流策略生效

  - design_item: D-07
    fr_id: FR-EXAM-HISTORY-REPLAY
    trigger: 任务成功
    input_contract:
      required_fields: [asset_id, download_url]
      optional_fields: []
      defaults: {}
    output_contract:
      required_fields: [downloadable_export]
      optional_fields: [file_name]
    failure_semantics: 禁止返回空链接或失效链接冒充成功
    observability_fields: [job_id, asset_id, download_started]
    rollback_anchor: feature.enable_exam_generation_download=false
    acceptance_gate: 点击生成后最终可直接下载

  - design_item: D-07
    fr_id: FR-EXAM-HISTORY-REPLAY
    trigger: 用户进入历史记录页或点击历史下载
    input_contract:
      required_fields: [job_id]
      optional_fields: [page, page_size]
      defaults: {}
    output_contract:
      required_fields: [history_rows]
      optional_fields: [asset_id, minio_object_key, download_url]
    failure_semantics: 资产缺失时展示不可用状态，不重新生成
    observability_fields: [job_id, asset_id, minio_object_key, history_viewed]
    rollback_anchor: feature.enable_exam_generation_history=false
    acceptance_gate: 历史记录可查看且可重复下载
```

## 6. implementation_seeds

```yaml
implementation_seeds:
  - task_id: T01
    file_paths:
      - app/api/v1/endpoints/exam_admin_api.py
      - app/api/v1/router.py
      - docs/API文档/接口文档.md
    symbols: [exam_admin_router, create_job, get_job, download_export]
    change_type: new_feature

  - task_id: T02
    file_paths:
      - app/schemas/exam_generation.py
      - docs/开发文档/架构设计/AI模块设计.md
    symbols: [PaperTemplateRequest, PaperContract, ExamGenerationResult, ExamQualityReport]
    change_type: new_feature

  - task_id: T03
    file_paths:
      - app/models/exam_generation_job.py
      - app/repositories/exam_generation_job_repo.py
      - alembic/versions/<new_revision>.py
    symbols: [ExamGenerationJob, result_payload, request_snapshot]
    change_type: new_feature

  - task_id: T04
    file_paths:
      - app/services/exam_generation_service.py
      - app/services/exam_template_service.py
    symbols: [create_job, run_job, build_default_template]
    change_type: new_feature

  - task_id: T05
    file_paths:
      - app/ai/workflow/exam_generation_workflow.py
      - app/ai/tools/ragflow_tool.py
    symbols: [generate_paper_contract, retrieve_exam_evidence, resolve_dataset_priority]
    change_type: new_feature

  - task_id: T06
    file_paths:
      - app/services/pdf_render_service.py
      - app/templates/exam_pdf/base.html
      - app/templates/exam_pdf/styles.css
      - pyproject.toml
    symbols: [render_exam_pdf]
    change_type: new_feature

  - task_id: T07
    file_paths:
      - web/src/app/admin/exam-generation/page.tsx
      - web/src/components/admin/ExamGenerationPanel.tsx
      - web/src/lib/backend.ts
    symbols: [ExamGenerationPage, submitExamJob, downloadExamExport]
    change_type: new_feature

  - task_id: T08
    file_paths:
      - tests/unit/test_exam_generation_service.py
      - tests/unit/test_pdf_render_service.py
      - tests/unit/test_exam_admin_api.py
      - docs/开发文档/测试管理/<new_doc>.md
    symbols: [service_contract_tests, pagination_tests, api_tests]
    change_type: new_feature
```

## 7. execution_chain_seed

```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260311-ai-exam-generation-agent
  card_seed: [T01, T02, T03, T04, T05, T06, T07, T08]
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: per_task
    commit_policy: per_pr
    stop_boundary: per_pr
```

## 8. risk_rollback_contract

| risk_id | 关键风险 | 触发信号 | 回退锚点 | 回退动作 |
|---|---|---|---|---|
| R01 | 出题功能侵入现有 supervisor/chat 主链 | 需要改 `multi_agent_graph/chat_api/chat_service` 才能工作 | `feature.enable_exam_generation_admin` | 立即回退聊天主链改动，恢复独立后台方案 |
| R02 | 基于知识生成的题目证据不足，产生幻觉题 | 题目没有来源片段或人工抽检明显越界 | `feature.enable_exam_generation_workflow` | 暂停生成能力，仅保留模板与范围配置页 |
| R03 | PDF 分页不稳定，试卷/答案跨页错乱 | 样本 PDF 出现截断、错页、答案区混排 | `feature.enable_exam_generation_pdf` | 回退 PDF 导出开关，先只保留结构化预览 |
| R04 | 任务结果只存在前端内存，刷新后丢失 | 刷新页面后看不到任务结果或下载链接失效 | `feature.enable_exam_generation_job_persist` | 强制恢复基于 job 表的结果持久化 |
| R05 | 多数据集冲突被静默吞掉，生成错误题目 | 不同数据集对同一知识点给出相反结论 | `feature.enable_exam_generation_quality_gate` | 回退到单数据集模式，禁用多数据集生成 |
| R06 | 权限或限流缺失导致后台滥用 | 非管理员访问或高并发生成拖垮服务 | `feature.enable_exam_generation_access_policy` | 回退页面入口并恢复仅内部白名单试用 |

## 9. 方案依据（最佳实践收口）
- 检索侧沿用现有 `RAGFlow` 指定知识库能力；本地已有 `dataset_id/dataset_ids` 检索契约，适合做“用户显式选范围”的唯一入口。
- PDF 侧采用 `HTML/CSS Paged Media -> WeasyPrint`，原因是分页、页眉页脚、打印版式能力更适合试卷场景。
- 工作流侧采用“固定步骤 + 结构化 contract”，避免为了“像智能体”而强行耦合到通用聊天编排。
- 结果侧采用 job canonical 持久化，避免直接长请求回传大文件带来的失败与不可回放。

## 10. design_freeze_summary

```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 6
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 8
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 11. clarify_handoff_contract

```yaml
clarify_handoff_contract:
  version: v2
  topic: "AI 出题智能体（独立后台页 / 指定知识库 / PDF 交付）"
  design_source: "workdocs/归档/正文/设计/2026-03-11-ai-exam-generation-agent-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - "后台管理员"
        - "教研/培训运营"
      core_scenarios:
        - "管理员进入独立后台页选择知识库范围"
        - "管理员修改默认组卷模板"
        - "系统基于知识生成试卷与答案"
        - "系统输出可直接下载的 PDF"
      business_goal_metrics:
        - "与现有 supervisor/chat 低耦合"
        - "知识->题目->PDF 链路可用"
        - "每道题都有证据来源"
        - "PDF 分页稳定"
        - "历史记录可回放并重复下载"
        - "质量门禁先于导出"
        - "多数据集冲突时明确失败"
        - "后台权限与限流有效"
      non_goals:
        - "不接入聊天页"
        - "不做学生作答系统"
        - "不做自动阅卷"
        - "不做模板中心"
      acceptance_gates:
        - "独立后台页面"
        - "知识库范围可选"
        - "默认模板可编辑"
        - "单个 PDF 含试卷+答案+简短解析"
        - "生成后可直接下载"
        - "历史记录可查看且可重复下载"
        - "质量门禁生效后才允许导出"
        - "多数据集优先级与冲突语义冻结"
        - "后台权限与限流策略生效"
        - "不依赖 supervisor"
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-EXAM-ADMIN-PAGE
      - design_item: D-02
        fr_id: FR-EXAM-DATASET-SELECTION
      - design_item: D-03
        fr_id: FR-EXAM-TEMPLATE-EDIT
      - design_item: D-04
        fr_id: FR-EXAM-KNOWLEDGE-TO-QUESTION
      - design_item: D-05
        fr_id: FR-EXAM-PDF-WITH-ANSWERS
      - design_item: D-05A
        fr_id: FR-EXAM-QUALITY-GATE
      - design_item: D-06
        fr_id: FR-EXAM-DIRECT-DOWNLOAD
      - design_item: D-06A
        fr_id: FR-EXAM-ACCESS-POLICY
      - design_item: D-07
        fr_id: FR-EXAM-HISTORY-REPLAY
    implementation_seeds:
      - task_id: T01
        file_paths: [app/api/v1/endpoints/exam_admin_api.py, app/api/v1/router.py, docs/API文档/接口文档.md]
        symbols: [exam_admin_router, create_job, get_job, list_jobs, download_export, access_policy]
        change_type: new_feature
      - task_id: T02
        file_paths: [app/schemas/exam_generation.py, docs/开发文档/架构设计/AI模块设计.md]
        symbols: [PaperTemplateRequest, PaperContract, ExamGenerationResult, ExamQualityReport]
        change_type: new_feature
      - task_id: T03
        file_paths: [app/models/exam_generation_job.py, app/repositories/exam_generation_job_repo.py, alembic/versions/<new_revision>.py]
        symbols: [ExamGenerationJob, result_payload, request_snapshot, minio_object_key]
        change_type: new_feature
      - task_id: T04
        file_paths: [app/services/exam_generation_service.py, app/services/exam_template_service.py]
        symbols: [create_job, run_job, list_jobs, build_default_template, enforce_access_policy]
        change_type: new_feature
      - task_id: T05
        file_paths: [app/ai/workflow/exam_generation_workflow.py, app/ai/tools/ragflow_tool.py]
        symbols: [generate_paper_contract, retrieve_exam_evidence, resolve_dataset_priority]
        change_type: new_feature
      - task_id: T06
        file_paths: [app/services/pdf_render_service.py, app/templates/exam_pdf/base.html, app/templates/exam_pdf/styles.css, pyproject.toml]
        symbols: [render_exam_pdf, quality_gate_before_render]
        change_type: new_feature
      - task_id: T07
        file_paths: [web/src/app/admin/exam-generation/page.tsx, web/src/components/admin/ExamGenerationPanel.tsx, web/src/lib/backend.ts]
        symbols: [ExamGenerationPage, ExamHistoryList, submitExamJob, downloadExamExport, questionLimitHint]
        change_type: new_feature
      - task_id: T08
        file_paths: [tests/unit/test_exam_generation_service.py, tests/unit/test_pdf_render_service.py, tests/unit/test_exam_admin_api.py, docs/开发文档/测试管理/<new_doc>.md]
        symbols: [service_contract_tests, pagination_tests, api_tests, quality_gate_tests, access_policy_tests]
        change_type: new_feature
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260311-ai-exam-generation-agent
      card_seed: [T01, T02, T03, T04, T05, T06, T07, T08]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_task
        commit_policy: per_pr
        stop_boundary: per_pr
    alignment_contract:
      strict_match: true
      requirement_seed_ids: [FR-EXAM-ADMIN-PAGE, FR-EXAM-DATASET-SELECTION, FR-EXAM-TEMPLATE-EDIT, FR-EXAM-KNOWLEDGE-TO-QUESTION, FR-EXAM-PDF-WITH-ANSWERS, FR-EXAM-QUALITY-GATE, FR-EXAM-DIRECT-DOWNLOAD, FR-EXAM-ACCESS-POLICY, FR-EXAM-HISTORY-REPLAY]
      implementation_task_ids: [T01, T02, T03, T04, T05, T06, T07, T08]
      card_seed_ids: [T01, T02, T03, T04, T05, T06, T07, T08]
  extended:
    observability_hints:
      - "记录 job_id/user_id/dataset_ids/template_hash/retrieved_chunk_count/question_count/page_count/asset_id/minio_object_key/quality_gate_pass"
      - "任务状态切换统一记录 queued/running/succeeded/failed"
    risk_counterexample_map:
      - risk_id: R01
        counterexample: "为了出题去改 multi_agent_graph 路由"
      - risk_id: R02
        counterexample: "题目生成成功但没有任何来源证据"
      - risk_id: R03
        counterexample: "答案区和试卷正文混在同一页"
      - risk_id: R04
        counterexample: "刷新页面后下载链接消失或历史记录里看不到 MinIO 资产"
      - risk_id: R05
        counterexample: "多数据集冲突时系统静默选择低优先级内容继续出题"
      - risk_id: R06
        counterexample: "普通用户也能访问后台页或单用户无限并发出题"
    assumptions:
      - "V1 管理员通过后台管理页触发，不进入聊天页。"
      - "V1 默认模板只提供单份可编辑模板，不做模板管理中心。"
      - "V1 至少支持多 dataset 选择，不强制按章节精细过滤。"
      - "V1 采用任务化生成体验：前端点按钮后等待完成并自动下载。"
      - "成功生成的 PDF 统一存放在现有 MinIO，并通过历史记录回放下载。"
      - "质量门禁失败不会产出 PDF 资产。"
      - "多数据集优先级由用户勾选顺序决定。"
      - "V1 默认只允许后台管理员访问，且只看自己历史记录。"
```

## 12. clarify_consistency_check

```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 4
  question_mode: package
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 13. execution_notes

```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: ".agents/skills/jjk-clarify/SKILL.md"
  question_mode: "package"
  degrade_reason: ""
  alternative_tool: ""
  verification: "已补充冻结：质量门禁、多数据集优先级与冲突语义、历史记录元数据、后台权限与限流；待用户审批后进入 jjk-plan。"
```


## 14. 审批记录

- design_approved: true
- approved_at: 2026-03-11 23:59 CST
- approved_round: round-4
- approval_evidence: "用户明确指令：[$jjk-plan]；将该指令视为对当前 AI 出题智能体单方案的正式确认。"
