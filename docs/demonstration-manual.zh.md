# RCI Agent 演示手册

证据工作台主讲人指南 | 2026 年 10 月 28 日

其他版本：[英文 PDF](demonstration-manual.pdf)、[韩文 Markdown](demonstration-manual.ko.md)、[韩文 PDF](demonstration-manual.ko.pdf)、[日文 Markdown](demonstration-manual.ja.md)、[日文 PDF](demonstration-manual.ja.pdf)、[中文 PDF](demonstration-manual.zh.pdf)、[英文 Markdown](demonstration-manual.md)。

## 1. 演示概览

**受众：** 主讲人、分析师，以及希望了解已实现的调查演示的相关方。准备完成后请预留 15-20 分钟。本手册描述的是当前应用，而不是设想场景包中的全部能力。

**开场白：** "这是一个虚构的调查工作台。智能体帮助整理并质疑证据；修订与复核由分析师掌控。系统未连接任何银行、案件管理系统或监管决策服务。"

### 观众将看到什么

| 环节 | 时间 | 演示内容 |
|---|---|---|
| 打开与准备 | 3 分钟 | 从告警列表中打开一条告警，确认待解答的问题，然后收集打包好的虚构证据。 |
| 检查与质疑 | 4 分钟 | 检查来源的局限性，并请已配置的智能体质疑相关结论。 |
| 修订与澄清 | 4 分钟 | 保存分析师的更正，并提交有界范围表单。 |
| 复核与准备 | 4 分钟 | 复核六项输出，并准备可复制的案件说明。 |
| 变更与回看 | 3 分钟 | 使复核失效，查看历史记录，并重新打开已保存的工作。 |

### 一分钟了解案件

Harbour Components Ltd 是一家虚构的工业零部件批发商。现有告警 **ALT-2041**（显示于 **CASE-1041**）的原始 AML 优先级为 **High**。三笔收款合计 **GBP 48,000**，随后向 Meridian Supply 付款 **GBP 45,500**：占收款的 **94.79%**，发生在首笔收款后 **56 分钟**。

在可用的 90 天历史记录中未观察到该受益人。这是场景设定的既定事实，并非根据所显示行数据推导的结论，也不能证明存在新的商业关系。供应商付款这一解释依然合理。发票缺失，且既往案件受限。

### 选择演示路线

**完整路线：** 按第 2-8 节进行。准备阶段不使用模型推理，但发送消息和提交范围表单会调用已配置的模型，并可能产生费用。模型的措辞、耗时和建议的更新均无法保证。

**无推理路线：** 使用准备、来源检查、手动修订、复核、历史记录和重新打开。跳过发送智能体提示、策略请求和提交范围表单。通过打开并取消表单来演示该表单。请明确说明此路线不演示智能体的实时分析。

**核心区别：** 已保存的修订会成为后续智能体轮次的上下文；它们不会自动改写其他阶段的文字，也不会修改原始来源记录。受影响的阶段会被标记为需要重新复核。

## 2. 准备环境

### 观众到场之前

在 Windows PowerShell 中使用仓库根目录。首次安装、依赖恢复、模型配置和身份验证请遵循 **README.md**。不要将凭据复制到提示词或演示材料中。

如需升级，请先停止应用的 API 和 worker，并在启动迁移之前备份已配置的数据目录（默认为 `.data`）。按 README 所述恢复后端和前端的锁定依赖。扩展或依赖变更后，请同时重启 API 和 worker；两者的配置和数据目录必须一致。

完整路线需选择具备推理访问授权的模型，并且要在开始之前选好。打开某条告警会创建其唯一关联的案件，再次打开则恢复该案件，因此排练不会产生重复项。每次 **New investigation** 都会创建另一个未关联的、标题相同的 CASE-1041 会话，请谨慎使用。

### 启动三个进程

**终端 1 - API**

```powershell
.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

**终端 2 - 持久化 worker**

```powershell
.\.venv\Scripts\python.exe -m skill_chat.tasks.worker
```

**终端 3 - 前端**

```powershell
npm --prefix .\web run dev -- --host 127.0.0.1 --port 5173
```

打开 **http://127.0.0.1:5173**。请使用已配置的确切前端来源。如果端口已被占用，请按 README 中的备用端口说明操作，不要停止不明进程。

### 检查就绪状态

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

就绪状态要求 worker 最近有心跳。它不会验证云端权限或模型质量。完整路线演示之前，请另行排练一次简短的模型请求；该请求可能产生费用。

**主讲人检查清单：** 仅使用虚构数据；为观众放大浏览器；找到模型选择器；保持 API 和 worker 终端可用于诊断，但不要投屏显示日志或密钥。请使用上述常规应用 URL，而不是位于 `?prototype=centered-chat` 的内存布局对比页。不要用隔离的自动化测试服务器代替正常应用。

## 3. 打开工作台并检查证据

### 打开告警

1. 在侧边栏 **Alerts (fictional demo)** 列表中查看四条告警。每一行显示告警 ID、优先级、主体、触发原因，以及 **No case yet. Review by** 加日期，或 **Case open at** 加阶段。复核截止日期只是提醒，不是监管建议。
2. 选择 **Open alert ALT-2041, Harbour Components Ltd**。这会创建与该告警关联的唯一案件。之后再次选择同一告警（此时按钮显示为 **Resume alert**）会重新打开该案件，而不会创建重复项。
3. 确认 **CASE-1041 evidence desk**、**Demo connector / fictional records** 标签以及原始的 **High** 告警优先级。此时尚未准备任何内容：工作台显示起始的 **Question to answer**，并说明尚未收集证据。
4. 指出六个阶段：Detect、Investigate、Gather evidence、Analyze、Human review 和 Decision。案件在 **Investigate** 打开。点击 **Detect** 以说明它是 **Read-only**：它记录原始告警和优先级，初始即为已确认状态，不会因后续变更而失效，且不可修订。**Continue to Investigate** 可返回工作阶段。
5. 也可以在准备证据之前使用 **Clarify investigation scope**（见第 5 节）。
6. 点击 **Prepare investigation**。等待准备任务成功，且 **Refresh demo evidence** 变为可用。

**预期结果：** 各阶段输出已更新。选择中央的 **Evidence** 标签页，可看到已填充的交易时间线和证据登记表。准备过程通过后端 worker 检索打包好的固定数据记录，不使用模型推理，也不是对实时金融系统的查询。

**无证据的告警（可选，2 分钟）：** 打开另一条告警，例如 **ALT-2038**，点击 **Prepare investigation**。只有 ALT-2041 带有打包的演示证据，因此准备过程会记录一个缺失来源（**SRC-00**）和缺口 **GAP-01**。Analyze 会说明无法得出任何结论。借此说明工作台会报告缺口，而不是编造证据。

**转介路径：** **New investigation** 仍位于告警列表下方，用于转介或手动线索。它会创建一个不关联任何告警的独立 CASE-1041 会话，其 Detect 阶段保持可编辑。

### 讲解导航

已实现的 **A layout** 左侧为 **Investigation sessions**，中间为工作流和阶段工作区，右侧为带对话和输入框的 **Investigation assistant**。

| 区域或控件 | 主讲人操作 |
|---|---|
| **Output** 标签页 | 编辑所检查的阶段、修订共享事实并打开修订历史。 |
| **Evidence** 标签页 | 检查交易时间线、证据登记表和来源记录。 |
| **Review** 标签页 | 输入分析师理由、复核说明，并准备或复制说明。**Review & record** 同样会打开此标签页。 |
| 侧边栏分隔条 | 在桌面端可拖动任一分隔条。键盘用户可聚焦后使用左/右方向键；Home/End 分别选择最小/最大宽度。 |
| **Chat** | 打开或关闭右侧对话侧边栏。其关闭图标会返回工作区，且不会丢弃消息草稿。 |
| 太阳/月亮按钮 | 切换浅色/深色模式。首次访问跟随系统；若浏览器存储可用，则保存显式选择。 |

在宽度不超过 1,000 像素的屏幕上，历史记录和对话以抽屉形式呈现，而非同时显示的多列；调整大小的手柄会隐藏。使用 **Toggle history** 打开会话，使用 **Chat** 打开助手。在操作中间区域之前，请先关闭对话抽屉。

点击 **Analyze** 查看其 **Output** 标签页。点击任一阶段都会返回 Output，不会推进工作流。仅在有意更改当前工作流阶段时才使用 **Make current stage**。之后复核说明会将阶段设为 Human review；准备说明会将其设为 Decision。

### 检查底层记录

选择 **Evidence**，然后从相关证据项打开 **Inspect SRC-01**。阅读所选的账本记录、固定数据快照、版本、检索时间戳和覆盖范围。继续之前使用 **Close source**。

| 记录 | UTC | 金额 | 交易对手 |
|---|---|---|---|
| TX-781 | 09:12 | +GBP 18,000 | Alder Industrial |
| TX-782 | 09:31 | +GBP 16,000 | Beacon Assembly |
| TX-783 | 09:54 | +GBP 14,000 | Cedar Parts |
| TX-784 | 10:08 | -GBP 45,500 | Meridian Supply |

选择 **Analyze** 返回其 **Output** 标签页，指出 94.79% 的比较和 56 分钟的时间窗口。说明所选记录并未提供余额，也无法确定资金来源脉络或意图。

返回 **Evidence**。检查 **SRC-04** 以展示受限的既往案件，检查 **SRC-07** 以展示缺失的发票。**All sources (7)** 提供了另一种打开各来源的方式。

**预期结果：** SRC-04 仍然受限，SRC-07 仍然缺失。二者都不意味着不利结论，也不代表已完成佐证核查。刷新证据只会改变检索观察结果；不会让不可用的记录变得可访问，也不会使旧的固定数据内容变成最新内容。

**讲解词：** "来源的新鲜度与检索时间是两回事。我们能看到提供了什么、没有提供什么，以及为什么结论仍然受限。"

## 4. 质疑并修订解读

### 询问已配置的智能体

完整路线下，在中间选择 **Analyze**。在右侧 **Investigation assistant** 侧边栏中，点击 **Draft a challenge**。如果助手已关闭，请先用 **Chat** 打开。此操作只会填充输入框。阅读该提示词，然后点击 **Send message**。

等待这个新任务完成；不要把之前成功的任务误认为新的结果。检查回复和阶段输出，不要承诺固定的答案。

**建议的后续提示词：**

> What evidence challenges the concern? Separate observed facts, calculated comparisons, alternative explanations, and gaps. Propose a revised Analyze output with evidence references. Do not infer wrongdoing, fund lineage, or the contents of the restricted case.

**预期行为：** 智能体接收当前已保存的调查上下文，并可提出限定范围的输出更新。只有任务成功完成后，提议才会成为正式内容。回复并不证明输出已被更改：请检查该阶段的文本和版本。如果没有提出更新，请明确询问，或使用下面的手动修订。

### 保存分析师更正

选择 **Analyze**，将 **Stage output** 替换为以下示例，并填写理由。

> Selected records show GBP 48,000 incoming and GBP 45,500 outgoing within 56 minutes [E-01]. Timing alone does not establish intent or fund lineage. Supplier payments fit the business profile [E-03], but the invoice remains unverified [E-04, GAP-01]. Restricted case contents are not adverse evidence [GAP-02].

**Reason for stage amendment：**

> Preserve the alternative explanation and distinguish observed facts from interpretation.

保存之前，先点击 **Detect** 再返回 **Analyze**。然后切换到 **Evidence** 再切回 **Output**。未保存的输出和理由应在这两种导航中都保留。点击 **Apply stage amendment** 将其持久化。

**预期结果：** 修订号和输出版本增加；Analyze 及下游输出需要复核；已准备的说明被清除。较早阶段的文字和原始来源记录不会被覆盖。

### 准确说明持久化

已保存的编辑会进入后续的智能体上下文。未保存的阶段编辑、理由和复核理由在已挂载的工作台内切换标签页时会保留；阶段编辑在检查其他阶段时也会保留。消息草稿在关闭并重新打开助手后仍会保留。这些未保存的草稿都不是已保存的记录；不要指望它们在页面重新加载或会话切换后依然存在。

在 **Output** 中打开 **Revision history**，查看修订、理由，以及（如有）**Previous text** 和 **Saved text**。有提供时使用 **Load older revisions**。这是应用自身的修订历史，并不证明存在外部合规审计系统。

## 5. 澄清范围并检查虚构策略

### 演示有界的 A2UI 表单

1. 在没有活动任务时，点击当前中央标签页内容下方的 **Clarify investigation scope**；如有需要请向下滚动。在移动端，请先关闭对话抽屉。
2. 在 **Investigation scope** 中输入下面的示例。
3. 完整路线下，点击 **Apply scope and ask agent**。
4. 等待出现 **Scope clarification resolved.**，并等待新创建的任务成功后再继续。

> Assess the permitted supplier-payment evidence. Keep the missing invoice and restricted prior case explicit. Do not infer a new commercial relationship from absence in the available 90-day history.

**预期行为：** 答案被持久化，并排入一次普通的持久化智能体续接任务。worker 不会在分析师输入时等待。待处理、已解决和已取消的状态在重新打开后仍会保留。

无推理路线下，请不要提交，而是点击 **Cancel scope clarification**。打开或取消这个固定表单并不属于智能体分析演示。

如果官方渲染器无法显示该表单，可能会出现无障碍的 **Plain form fallback**。它支持相同的有界回答和提交；这并不意味着允许加载任意由智能体生成的 HTML 或界面。

### 可选的策略请求

在 **Evidence** 中打开 **All sources (7)**，检查 **SRC-05** 和 **SRC-06**。它们包含虚构的 **G-AML-07 v3** 和 **L-01 v2** 段落。

在右侧助手侧边栏中点击 **Draft a policy check**，检查已准备好的输入框文本，仅在完整路线下发送。也可以改用：

> Using the supplied fictional G-AML-07 v3 and L-01 v2 passages, identify the checks and gaps that remain before a human could recommend closure or escalation. Cite the passage locators. Distinguish this demo policy from law and do not claim the invoice has been corroborated.

**预期讨论：** 必须同时考虑支持与反驳的证据；调查人员的验证和理由仍然必要；缺失的发票和无法访问的案件仍是局限。生成的措辞取决于模型，必须对照来源段落核对。

### 可选的 AML 技能

六个工作流阶段不会自动运行六项技能。如果在完整路线上演示已安装的 AML 技能，请先准备证据，然后在助手输入框的 **Skills** 中选择其一，或输入其斜杠命令。弹出菜单只显示名称。

| 技能 | 演示重点 |
|---|---|
| `/aml-case-context` | 说明已记录的告警、客户背景和信息缺口。 |
| `/aml-transaction-behaviour` | 对照预期和历史评估已核实的交易指标。 |
| `/aml-hypothesis-review` | 用合理的正当解释和反面证据检验疑点。 |
| `/aml-policy-applicability` | 识别适用的已提供程序和人工批准要求。 |
| `/aml-investigation-readiness` | 识别未完成的核查；缺失必需证据时必须阻止"就绪"结果。 |
| `/aml-case-narrative` | 起草带引用、可编辑的案件说明，供分析师复核。 |

这些只是可选的指令，并非经过验证的风险模型、获批的真实银行策略包、计算引擎或实时案件集成。计算必须来自已核实的准备指标或明确的获批工具，而不是语言模型的算术。仅选择技能并不会运行推理；发送其提示词才会。所选技能在后续追问中保持有效；使用其输入框标签上的 **Clear skill** 可回到普通提示词。

### 讲解 AG-UI，不夸大

**AG-UI** 向固定的 React 工作区传递可重放的调查快照和澄清活动。用户操作是经服务端验证的命令；对话文本仍使用其原有的独立流。

**A2UI** 仅渲染受限的范围表单。它不是任意由智能体编写的工作流设计，不是完整的 AG-UI 文本/工具生命周期实现，也不是对等待人工输入的 worker 进行 SDK 检查点/恢复。

## 6. 复核并准备案件说明

在此环节之前完成各次智能体轮次和修订。之后每一次实质性变更都可能使复核失效。

### 填写由人负责的输出

准备过程填充的是证据和分析，而不是完整的人工判断。请检查每个阶段。不要将通用的 "Awaiting investigation preparation and human assessment" 文本当作已完成的评估予以确认。

对于 **Human review**，请根据演示情况修订输出，例如：

> Analyst checked the selected transaction comparison and considered the plausible supplier explanation. The invoice is unavailable [GAP-01]; prior case contents remain restricted [GAP-02]. No conclusion about intent or fund lineage is established.

对于 **Decision**，记录的是拟议处置，而非已执行的决定：

> Proposed next action: obtain invoice corroboration and request authorized access to the prior case before considering closure. No closure, escalation approval, regulatory filing, or account restriction has been executed.

为每项更改填写有意义的 **Reason for stage amendment**，并点击 **Apply stage amendment**。这些示例是主讲人提供的判断，而不是智能体自动得出的结论。

### 确认与复核

1. 在最后一次修订之后，依次访问五个可编辑的阶段输出。Detect 为只读，对于由告警打开的案件已处于确认状态。
2. 验证每项输出及其证据引用。只有在满意时才点击 **Acknowledge this output**。
3. 等待每个可编辑阶段显示 **Acknowledged**，而不是仅仅因请求正在运行而按钮被禁用。
4. 选择中央的 **Review** 标签页，或点击 **Review & record**。在 **Analyst rationale** 中输入下面的示例，并根据实际输出调整。
5. 点击 **Mark note reviewed**，然后点击 **Prepare case note**。

> I checked the selected records and alternative supplier explanation. The invoice gap and restricted prior case remain unresolved. Further authorized evidence collection is proposed; no external decision or approval is confirmed.

**预期结果：** 准备过程必须已成功；所有受影响的输出必须已确认；理由不得为空。已准备的说明会显示共享结论、各阶段输出、理由、源自证据的引用和缺口，以及 **External saving / approval: unconfirmed**。

### 复制，但不要声称外部已完成

点击 **Copy case note**；如果无法访问剪贴板，则手动选中并复制所显示的说明。请使用一次性的演示文档作为目的地，而不是真实的案件系统。

**讲解词：** "这是为现有的人工工作流准备一份记录。复制并不等于保存到其他系统、批准处置或关闭案件。"

## 7. 展示变更会使复核失效

### 修订共享事实

准备好说明后，选择 **Output** 并打开 **Shared fact across all stages**。将 **Shared beneficiary description** 改为：

> Meridian Supply was not observed in the available 90-day history; the age of the commercial relationship is unknown.

在 **Reason for shared fact amendment** 中输入：

> Avoid equating absence from available history with a new commercial relationship.

点击 **Apply shared fact amendment**。

**预期结果：** 共享结论发生变化；五个可编辑输出需要重新复核（由告警打开的案件中 Detect 保持已确认）；已复核标记和已准备的说明被清除。返回 **Review**：**Copy case note** 不再可用，且在重新完成所需确认之前，说明复核被阻止。仅切换到 Output 只是隐藏说明；真正使其失效的是该修订。

共享措辞现在可供所有后续智能体轮次使用。它不会自动替换各阶段的文本，也不会改变不可变的来源内容。如需演示智能体的传播效果，可发送一条简短请求，要求其解释修订后的共享事实并提出必要的输出更正；这是一次模型调用。

### 检查记录并重新打开

返回 **Output** 并打开 **Revision history**。展示某次修订的操作者、动作、修订号、理由以及前后文本。有提供时加载更早的修订。

重新加载之前请保存所有剩余草稿。重新加载页面，然后在告警列表中选择 **Resume alert ALT-2041** 重新打开案件，或从 **Investigation sessions** 中选择它。如果多个会话标题相同，请选择刚刚使用的那个。确认已保存的修订、证据和澄清状态仍然存在。

重新加载本身不会重新运行证据准备或智能体分析。浏览器断开连接不会取消持久化的后台工作。

### 保持普通对话的独立性

选择 **New conversation**，展示普通聊天、PDF 审阅、可选技能和已保存的 HTML 工件仍然可用。不要把已移除的历史 RFP 技能当作当前产品功能介绍。

**结束演示：** "我们拥有一个持久化、可编辑、修订可追溯的证据工作台。分析师可以质疑并纠正智能体。来源的局限性始终可见，且应用不会执行具有重大影响的金融或监管决策。"

### 为下一次演示重置

打开另一条告警（例如 ALT-2036），或使用 **New investigation** 创建全新的虚构会话；重新打开 ALT-2041 会恢复现有案件，而不是重置它。若要从头重复 ALT-2041，请在 **Investigation sessions** 中删除其会话（这会释放该告警以便创建新案件）。不要通过删除 `.data` 来重置演示。避免把 **Refresh demo evidence** 当作重置按钮：它会创建新的准备轮次，并可能使先前的复核失效。

## 8. 故障排查与边界

| 现象 | 主讲人操作 |
|---|---|
| 任务一直处于排队状态 | 检查 worker 就绪状态以及 API 与 worker 配置是否一致。不要重复提交。 |
| 控件被禁用 | 等待当前轮次或变更完成。复核还需要已准备的证据、确认和理由。 |
| 修订冲突 | 保留本地草稿。与已保存的输出比较；在提供时使用 **Keep draft and use latest revision**，然后带着理由有意识地重新应用。不要盲目覆盖他人的修订。 |
| 模型失败或未授权 | 保持失败信息可见。在演示之外检查提供方设置，或切换到无推理路线。不要把固定数据响应称为实时推理。 |
| 上下文超出预算 | 精简过长的已保存输出，或选择预算配置合适的模型。重试不会悄悄地对过时分析重新定基。 |
| 来源仍不可用 | 说明 SRC-04 受限、SRC-07 缺失是有意设计。不要暗示绕过访问限制或成功获取发票。 |
| 无法准备说明 | 完成准备；修订占位文本；确认每个受影响的阶段；填写理由；将说明标记为已复核。 |
| 范围渲染器失败 | 如有提供，使用纯表单回退。如果界面无效，重新打开会话以重新加载。 |
| 复制失败 | 手动选中并复制所显示的说明；外部保存仍未确认。 |
| 会话或助手被隐藏 | 使用 **Toggle history** 显示会话，使用 **Chat** 显示助手。在窄屏上，编辑工作区之前请先关闭对话抽屉。 |
| 时间线、复核或历史记录似乎缺失 | 选择 **Evidence** 查看来源，**Review** 查看说明，**Output** 查看共享事实和修订历史。选择阶段会返回 Output。 |

### 需准确说明的运行限制

该应用为本地单用户：一个 API 进程、一个 worker、全局同时只运行一个任务，每个会话同时只有一个活动轮次。本地范围不等同于多用户身份验证。面向观众部署时，不要放宽回环地址/来源保护。

**Stop** 是协作式取消请求；请等待其最终结果。**Retry** 需显式操作，并会创建一个关联的新任务。失败、已取消或过时的提议不得作为已发布的输出展示。关闭浏览器不等于取消。

本演示不检测实时异常，不计算经过验证的风险评分，不证明监管合规，也不连接实时银行/案件系统。其修订历史并非完整的受监管审计控制实现。告警列表为四条打包的虚构告警：没有实时数据源、分派、分流写入，也没有"无需立案"的处置，复核截止日期只是提醒。其他场景功能，例如高级筛选和完整运营模型，均未实现。

配套的官方 A2UI 软件包保留了上游 Zod 依赖的安全公告 **GHSA-mrhx-c7xc-m3w5**。固定模板验证以及大小/深度限制只是防护措施，并不表示该公告已被解决。依赖披露请参见 README。

### 资料来源与维护

**README.md** 是安装、配置、命令、限制和验证的运行依据。英文版为 `demonstration-manual.md` / `demonstration-manual.pdf`；韩文、日文和中文版分别使用 `.ko`、`.ja` 和 `.zh` 后缀。每个 PDF 包含其对应 Markdown 版本的演示内容。翻译版指南保留英文界面标签，以便主讲人找到实际的控件；这并不意味着应用已本地化。

- 场景叙述与预期流程：`docs\scenario\scenario.md` 和 `docs\scenario\process.md`。
- 已实现的设计：`docs\superpowers\specs\2026-10-28-investigation-evidence-desk-design.md` 和 `docs\superpowers\specs\2026-10-29-alert-first-investigation-start-design.md`。
- 协议设计背景：`docs\research\ag-ui-a2ui-integration.md`。
- 可执行的浏览器验收：`web\e2e\investigation-workflow.spec.ts`。

应用变更时请重新核对界面标签和行为。自动化固定数据运行验证的是应用行为，而不是实时推理质量、财务准确性或真实系统权限。
