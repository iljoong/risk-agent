# RCI Agent デモンストレーションマニュアル

Evidence desk presenter guide | 2026年10月28日

他の形式: [英語 Markdown](demonstration-manual.md), [英語 PDF](demonstration-manual.pdf), [韓国語 Markdown](demonstration-manual.ko.md), [韓国語 PDF](demonstration-manual.ko.pdf), [日本語 PDF](demonstration-manual.ja.pdf), [中国語 Markdown](demonstration-manual.zh.md), [中国語 PDF](demonstration-manual.zh.pdf)。

## 1. デモの概要

**対象者:** 実装済みの調査デモを確認するプレゼンター、アナリスト、関係者。セットアップ後、15～20分を見込んでください。本マニュアルは現在のアプリについて説明するものであり、構想段階のシナリオパックにあるすべての機能を扱うものではありません。

**冒頭のメッセージ:** "This is a fictional investigation workbench. The agent helps organize and challenge evidence; the analyst controls amendments and review. No bank, case-management system, or regulatory decision service is connected."

### 聴衆に見せる内容

| セグメント | 時間 | デモの内容 |
|---|---|---|
| 開始と準備 | 3分 | アラート一覧からアラートを開き、調べるべき問いを確認したうえで、同梱の架空の証拠を収集します。 |
| 確認と検証 | 4分 | ソースの制約を確認し、設定済みのエージェントに調査結果を検証させます。 |
| 修正と明確化 | 4分 | アナリストによる訂正を保存し、範囲を限定したスコープフォームを送信します。 |
| レビューと準備 | 4分 | 6つの成果物をレビューし、コピー可能なケースノートを準備します。 |
| 変更と再確認 | 3分 | レビューを無効化し、履歴を確認して、保存済みの作業を開き直します。 |

### 1分でわかるケース

Harbour Components Ltd は架空の産業用部品卸売業者です。**CASE-1041** に表示される既存のアラート **ALT-2041** は、元の AML 優先度が **High** です。3件の入金は合計 **GBP 48,000** で、その後 Meridian Supply へ **GBP 45,500** が送金されています。これは入金額の **94.79%** にあたり、最初の入金から **56 minutes** 後のことです。

受取人は、利用可能な90日間の履歴には見当たりません。これはシナリオ上の前提事実であり、表示された行から導かれる推論でも、新たな取引関係の証明でもありません。仕入先への支払いという説明も依然としてあり得ます。請求書は欠落しており、過去のケースは閲覧制限されています。

### プレゼンテーションのルートを選ぶ

**フルルート:** セクション2～8に従います。準備にはモデル推論を使いませんが、メッセージの送信とスコープフォームの送信では設定済みのモデルが呼び出され、料金が発生する場合があります。モデルの文言、所要時間、提案される更新内容は保証されません。

**推論なしルート:** 準備、ソースの確認、手動による修正、レビュー、履歴、再オープンを使います。エージェントへのプロンプト送信、ポリシー確認の依頼、スコープフォームの送信は省略します。フォームは、開いてキャンセルすることで見せます。このルートではエージェントによるライブ分析を実演しないことを、必ず明言してください。

**重要な区別:** 保存された修正は以降のエージェントのターンでコンテキストになりますが、他のすべてのステージの文章を自動的に書き換えたり、元のソースレコードを変更したりはしません。影響を受けるステージには再レビューが必要であることを示すマークが付きます。

## 2. 環境を準備する

### 聴衆が到着する前に

Windows PowerShell でリポジトリのルートを使用します。初回インストール、依存関係の復元、モデル設定、認証については **README.md** に従ってください。認証情報をプロンプトやデモ資料にコピーしないでください。

アップグレードする場合は、起動時のマイグレーションの前に、アプリの API とワーカーを停止し、設定済みのデータディレクトリ（既定では `.data`）をバックアップしてください。バックエンドとフロントエンドのロックファイルは、README の記載どおりに復元します。拡張機能や依存関係を変更した後は、API とワーカーの両方を再起動してください。両者の設定とデータディレクトリは一致している必要があります。

フルルートでは、推論へのアクセスが許可されたモデルを選択します。開始前に選択してください。アラートを開くと、そのアラートに紐づくケースが1件だけ作成され、再度開くとそのケースが再開されるため、リハーサルで重複が生じることはありません。一方、**New investigation** を使うたびに、同じタイトルでアラートに紐づかない別の CASE-1041 セッションが作成されるため、使用は控えめにしてください。

### 3つのプロセスを起動する

**ターミナル1 - API**

```powershell
.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

**ターミナル2 - 永続ワーカー**

```powershell
.\.venv\Scripts\python.exe -m skill_chat.tasks.worker
```

**ターミナル3 - フロントエンド**

```powershell
npm --prefix .\web run dev -- --host 127.0.0.1 --port 5173
```

**http://127.0.0.1:5173** を開きます。設定されているフロントエンドのオリジンを正確に使用してください。ポートがすでに使用されている場合は、正体不明のプロセスを停止せず、README の代替ポートの手順に従ってください。

### 準備状況を確認する

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Readiness（準備完了）には、ワーカーの最近のハートビートが必要です。クラウドの権限やモデルの品質は検証しません。フルルートで発表する前に、短いモデルリクエストを1回別途リハーサルしてください。課金対象となる場合があります。

**プレゼンター用チェックリスト:** 架空のデータのみを使用する。聴衆向けにブラウザを拡大する。モデルピッカーの位置を確認する。API とワーカーのターミナルは、ログやシークレットを投影せずに、問題の診断用として手元に置いておく。上記の通常のアプリ URL を使用し、`?prototype=centered-chat` のメモリ内レイアウト比較は使用しない。通常のアプリの代わりに、自動テスト用の分離されたサーバーを使用しない。

## 3. デスクを開いて証拠を確認する

### アラートを開く

1. サイドバーの **Alerts (fictional demo)** 一覧で、4件のアラートを確認します。各行には、アラート ID、優先度、対象、トリガー、そして **No case yet. Review by** に続く日付、または **Case open at** に続くステージのいずれかが表示されます。review-by の日付はリマインダーであり、規制上の助言ではありません。
2. **Open alert ALT-2041, Harbour Components Ltd** を選択します。これにより、そのアラートに紐づくケースが1件作成されます。後で同じアラートを選択すると（ボタンは **Resume alert** と表示されます）、重複して作成されることなく、そのケースが再び開きます。
3. **CASE-1041 evidence desk**、**Demo connector / fictional records** のラベル、元の **High** のアラート優先度を確認します。まだ何も準備されていません。デスクには開始時の **Question to answer** が表示され、証拠がまだ収集されていないことが示されます。
4. 6つのステージ（Detect、Investigate、Gather evidence、Analyze、Human review、Decision）を示します。ケースは **Investigate** で開きます。**Detect** をクリックすると **Read-only** であることを示せます。Detect は元のアラートと優先度を記録し、承認済みの状態で始まり、後の変更によって無効化されず、修正もできません。**Continue to Investigate** で作業用のステージに戻ります。
5. 証拠を準備する前に、必要に応じて **Clarify investigation scope** を使用できます（セクション5）。
6. **Prepare investigation** をクリックします。準備タスクが成功し、**Refresh demo evidence** が有効になるまで待ちます。

**期待される結果:** ステージの成果物が更新されます。中央の **Evidence** タブを選択すると、入力済みのトランザクションタイムラインと証拠レジスターが表示されます。準備では、モデル推論を使わずに、バックエンドワーカー経由で同梱のフィクスチャレコードを取得します。これは実際の金融システムへの照会ではありません。

**証拠のないアラート（任意、2分）:** 別のアラート（たとえば **ALT-2038**）を開き、**Prepare investigation** をクリックします。同梱のデモ用証拠があるのは ALT-2041 のみのため、準備では欠落しているソース（**SRC-00**）1件とギャップ **GAP-01** が記録されます。Analyze には、調査結果を導き出せないと表示されます。これにより、デスクが証拠を創作せず、ギャップとして報告することを示せます。

**紹介経路:** **New investigation** はアラート一覧の下に残っており、紹介案件や手動で得た手がかりに使います。どのアラートにも紐づかない独立した CASE-1041 セッションが作成され、その Detect ステージは編集可能なままです。

### ナビゲーションを説明する

実装済みの **A layout** では、左に **Investigation sessions**、中央にワークフローとステージのワークスペース、右に会話とコンポーザーを備えた **Investigation assistant** が配置されています。

| エリアまたはコントロール | プレゼンターの操作 |
|---|---|
| **Output** タブ | 確認中のステージを編集し、共有ファクトを修正し、リビジョン履歴を開きます。 |
| **Evidence** タブ | トランザクションタイムライン、証拠レジスター、ソースレコードを確認します。 |
| **Review** タブ | アナリストの根拠を入力し、ノートをレビューして、準備またはコピーします。**Review & record** もこのタブを開きます。 |
| サイドバーの区切り線 | デスクトップでは、どちらの区切り線もドラッグできます。キーボード操作では、フォーカスして左右の矢印キーを使い、Home/End で最小幅/最大幅を選択します。 |
| **Chat** | 右側の会話サイドバーを開閉します。閉じるアイコンを押すと、メッセージの下書きを破棄せずにワークスペースへ戻ります。 |
| 太陽/月ボタン | ライト/ダークモードを切り替えます。初回はシステムの設定に従い、明示的に選択した場合は、ブラウザのストレージが使用できればその選択が保存されます。 |

幅が1,000ピクセル以下の画面では、履歴とチャットは同時に並ぶ列ではなくドロワーになり、サイズ変更ハンドルは非表示になります。セッションを開くには **Toggle history**、アシスタントを開くには **Chat** を使用します。中央のエリアで作業する前に、チャットドロワーを閉じてください。

**Analyze** をクリックして、その **Output** タブを確認します。どのステージをクリックしても Output に戻るだけで、ワークフローは進みません。**Make current stage** は、現在のワークフローのステージを意図的に変更する場合にのみ使用します。後でノートをレビューすると Human review に設定され、ノートを準備すると Decision に設定されます。

### 基となるレコードを確認する

**Evidence** を選択し、関連する証拠項目から **Inspect SRC-01** を開きます。選択された台帳レコード、フィクスチャのスナップショット、バージョン、取得タイムスタンプ、カバレッジを読み上げます。次に進む前に **Close source** を使用します。

| レコード | UTC | 金額 | 取引先 |
|---|---|---|---|
| TX-781 | 09:12 | +GBP 18,000 | Alder Industrial |
| TX-782 | 09:31 | +GBP 16,000 | Beacon Assembly |
| TX-783 | 09:54 | +GBP 14,000 | Cedar Parts |
| TX-784 | 10:08 | -GBP 45,500 | Meridian Supply |

**Analyze** を選択してその **Output** タブに戻り、94.79% の比較と56分の時間枠を指し示します。選択されたレコードには残高が含まれず、資金の系譜や意図を立証するものでもないことを説明します。

**Evidence** に戻ります。**SRC-04** を確認して閲覧制限のある過去のケースを示し、**SRC-07** を確認して欠落している請求書を示します。**All sources (7)** からも、各ソースを開くことができます。

**期待される結果:** SRC-04 は閲覧制限されたまま、SRC-07 は欠落したままです。どちらも不利な調査結果や、完了した裏付け確認を意味しません。証拠を更新すると取得時の観測は変わりますが、利用できないレコードが閲覧可能になることも、古いフィクスチャの内容が新たに最新になることもありません。

**トークトラック:** "Source freshness and retrieval time are different. We can see what was supplied, what was not supplied, and why the conclusion remains limited."

## 4. 解釈を検証して修正する

### 設定済みのエージェントに尋ねる

フルルートでは、中央で **Analyze** を選択します。右側の **Investigation assistant** サイドバーで **Draft a challenge** をクリックします。アシスタントが閉じている場合は、先に **Chat** で開いてください。これはコンポーザーに入力するだけです。プロンプトを読んでから **Send message** をクリックします。

この新しいタスクが完了するまで待ってください。直前に成功したタスクを新しい結果と取り違えないようにします。固定の回答を約束せず、応答とステージの成果物を確認します。

**フォローアッププロンプトの例:**

> What evidence challenges the concern? Separate observed facts, calculated comparisons, alternative explanations, and gaps. Propose a revised Analyze output with evidence references. Do not infer wrongdoing, fund lineage, or the contents of the restricted case.

**期待される動作:** エージェントは現在保存されている調査コンテキストを受け取り、スコープを限定した成果物の更新を提案できます。提案は、タスクが正常に完了して初めて正式なものになります。応答があっても、成果物が変更されたという証拠にはなりません。ステージのテキストとバージョンを確認してください。更新が提案されなかった場合は、明示的に依頼するか、以下の手動による修正を使用します。

### アナリストの訂正を保存する

**Analyze** を選択し、**Stage output** を以下の例に置き換えて、理由を入力します。

> Selected records show GBP 48,000 incoming and GBP 45,500 outgoing within 56 minutes [E-01]. Timing alone does not establish intent or fund lineage. Supplier payments fit the business profile [E-03], but the invoice remains unverified [E-04, GAP-01]. Restricted case contents are not adverse evidence [GAP-02].

**Reason for stage amendment:**

> Preserve the alternative explanation and distinguish observed facts from interpretation.

保存する前に、**Detect** をクリックしてから **Analyze** に戻ります。次に **Evidence** に切り替えて **Output** に戻ります。未保存の出力と理由は、どちらの移動でも保持されるはずです。**Apply stage amendment** をクリックして永続化します。

**期待される結果:** リビジョンと出力バージョンが増加し、Analyze と下流の出力は再レビューが必要になり、準備済みのノートはクリアされます。以前のステージの文章と元のソースレコードは上書きされません。

### 永続化の範囲を正確に説明する

保存された編集は、以降のエージェントのコンテキストに入ります。未保存のステージ編集、理由、レビューの根拠は、マウントされたデスク内でタブを切り替えても保持されます。ステージ編集は、ステージを確認する操作でも保持されます。メッセージの下書きは、アシスタントを閉じて開き直しても保持されます。これらの未保存の下書きはいずれも保存済みレコードではないため、再読み込みやセッションの切り替えをまたいで頼らないでください。

**Output** で **Revision history** を開き、修正内容、理由、利用可能な場合は **Previous text** と **Saved text** を確認します。表示されている場合は **Load older revisions** を使用します。これはアプリケーションのリビジョン履歴であり、外部のコンプライアンス監査システムの証明ではありません。

## 5. スコープを明確化し、架空のポリシーを確認する

### 範囲を限定した A2UI フォームを実演する

1. アクティブなタスクがない状態で、アクティブな中央タブの内容の下にある **Clarify investigation scope** をクリックします。必要に応じてスクロールしてください。モバイルでは、先にチャットドロワーを閉じます。
2. **Investigation scope** に、以下の例を入力します。
3. フルルートでは、**Apply scope and ask agent** をクリックします。
4. **Scope clarification resolved.** が表示され、新しく作成されたタスクが成功するまで待ってから続行します。

> Assess the permitted supplier-payment evidence. Keep the missing invoice and restricted prior case explicit. Do not infer a new commercial relationship from absence in the available 90-day history.

**期待される動作:** 回答は永続化され、通常の永続的なエージェント継続が1件キューに入ります。アナリストが入力している間、ワーカーは待機しません。保留中、解決済み、キャンセル済みのステータスは、開き直しても保持されます。

推論なしルートでは、送信しないでください。代わりに **Cancel scope clarification** をクリックします。固定フォームを開く、またはキャンセルするだけでは、エージェントによる分析のデモにはなりません。

公式のレンダラーがフォームを表示できない場合は、アクセシブルな **Plain form fallback** が表示されることがあります。同じ範囲限定の回答と送信に対応しますが、エージェントが生成した任意の HTML や画面を読み込む許可を意味するものではありません。

### 任意のポリシー依頼

**Evidence** で **All sources (7)** を開き、**SRC-05** と **SRC-06** を確認します。これらには、架空の **G-AML-07 v3** と **L-01 v2** の該当箇所が含まれています。

右側のアシスタントサイドバーで **Draft a policy check** をクリックし、用意されたコンポーザーのテキストを確認して、フルルートの場合にのみ送信します。または、次のプロンプトを使用します。

> Using the supplied fictional G-AML-07 v3 and L-01 v2 passages, identify the checks and gaps that remain before a human could recommend closure or escalation. Cite the passage locators. Distinguish this demo policy from law and do not claim the invoice has been corroborated.

**期待される議論:** 裏付ける証拠と矛盾する証拠の両方を考慮する必要があること、調査担当者による検証と根拠が引き続き必要であること、請求書の欠落とアクセスできないケースが依然として制約であること。生成される文言はモデルに依存するため、ソースの該当箇所と照合して確認する必要があります。

### 任意の AML スキル

6つのワークフローステージで6つのスキルが自動的に実行されるわけではありません。インストール済みの AML スキルをフルルートで実演する場合は、先に証拠を準備し、アシスタントのコンポーザーの **Skills** から1つ選ぶか、そのスラッシュコマンドを入力します。ポップアップには名前のみが表示されます。

| スキル | デモの焦点 |
|---|---|
| `/aml-case-context` | 記録されたアラート、顧客のコンテキスト、情報のギャップを説明します。 |
| `/aml-transaction-behaviour` | 検証済みのトランザクション指標を、期待値や履歴と照らして評価します。 |
| `/aml-hypothesis-review` | 懸念事項を、正当な説明や反証と照らして検証します。 |
| `/aml-policy-applicability` | 適用される提供済みの手順と、人による承認の要件を特定します。 |
| `/aml-investigation-readiness` | 未完了の確認事項を特定します。必要な証拠が欠けている場合は、準備完了の結果をブロックしなければなりません。 |
| `/aml-case-narrative` | アナリストのレビュー用に、出典付きで編集可能なケースノートを起草します。 |

これらは任意の指示であり、検証済みのリスクモデル、承認された実在の銀行ポリシーパック、計算エンジン、ライブのケース連携ではありません。計算は、検証済みの準備メトリクスまたは特定された承認済みツールから得る必要があり、言語モデルの算術に頼ってはいけません。スキルを選択しただけでは推論は実行されず、そのプロンプトを送信して初めて実行されます。選択したスキルはフォローアップでも有効なままです。通常のプロンプトに戻すには、コンポーザーのチップにある **Clear skill** を使用します。

### AG-UI を過大評価せずに説明する

**AG-UI** は、再生可能な調査スナップショットと明確化のアクティビティを、固定の React ワークスペースに配信します。ユーザーの操作はサーバー側で検証されるコマンドであり、会話テキストは従来どおり別のストリームを使用します。

**A2UI** は、制限されたスコープフォームのみを描画します。これは、エージェントが任意にワークフローを設計するものでも、AG-UI のテキスト/ツールのライフサイクルを完全に実装したものでも、人の入力を待つワーカーの SDK チェックポイント/再開でもありません。

## 6. レビューしてケースノートを準備する

このセグメントの前に、エージェントのターンと修正をすべて完了させてください。以降に重要な変更を加えるたびに、レビューが無効になる可能性があります。

### 人が担当する成果物を入力する

準備では証拠と分析が入力されますが、完全な人による判断は入力されません。すべてのステージを確認してください。"Awaiting investigation preparation and human assessment" という汎用的なテキストを、完了した評価として承認してはいけません。

**Human review** については、デモに合わせて成果物を適宜修正します。

> Analyst checked the selected transaction comparison and considered the plausible supplier explanation. The invoice is unavailable [GAP-01]; prior case contents remain restricted [GAP-02]. No conclusion about intent or fund lineage is established.

**Decision** には、実行済みの決定ではなく、提案する処理方針を記録します。

> Proposed next action: obtain invoice corroboration and request authorized access to the prior case before considering closure. No closure, escalation approval, regulatory filing, or account restriction has been executed.

変更ごとに意味のある **Reason for stage amendment** を入力し、**Apply stage amendment** をクリックします。これらの例はプレゼンターが用意した判断であり、エージェントによる自動的な調査結果ではありません。

### 承認とレビュー

1. 最後の修正の後で、編集可能な5つのステージの出力をそれぞれ確認します。Detect は読み取り専用で、アラートから開いたケースではすでに承認済みです。
2. 各出力とその証拠参照を検証します。納得できた場合にのみ **Acknowledge this output** をクリックします。
3. 編集可能な各ステージに **Acknowledged** と表示されるまで待ちます。リクエストの実行中にボタンが無効になっているだけでは不十分です。
4. 中央の **Review** タブを選択するか、**Review & record** をクリックします。**Analyst rationale** に、以下の例を実際の出力に合わせて調整して入力します。
5. **Mark note reviewed** をクリックし、続けて **Prepare case note** をクリックします。

> I checked the selected records and alternative supplier explanation. The invoice gap and restricted prior case remain unresolved. Further authorized evidence collection is proposed; no external decision or approval is confirmed.

**期待される結果:** 準備がすでに成功していること、影響を受けるすべての出力が承認済みであること、根拠が空でないことが必要です。準備されたノートには、共有された調査結果、ステージの出力、根拠、証拠に由来する参照とギャップ、そして **External saving / approval: unconfirmed** が表示されます。

### コピーするが、外部での完了を主張しない

**Copy case note** をクリックするか、クリップボードにアクセスできない場合は、表示されたノートを手動で選択してコピーします。コピー先には、実在のケースシステムではなく、使い捨てのデモ用ドキュメントを使用してください。

**トークトラック:** "This prepares a record for the existing human workflow. Copying is not saving to another system, approving a disposition, or closing a case."

## 7. 変更によってレビューが無効になることを示す

### 共有ファクトを修正する

ノートを準備した後、**Output** を選択し、**Shared fact across all stages** を開きます。**Shared beneficiary description** を次のように変更します。

> Meridian Supply was not observed in the available 90-day history; the age of the commercial relationship is unknown.

**Reason for shared fact amendment** に、次のように入力します。

> Avoid equating absence from available history with a new commercial relationship.

**Apply shared fact amendment** をクリックします。

**期待される結果:** 共有された調査結果が変更され、編集可能な5つの出力は再レビューが必要になり（アラートから開いたケースでは Detect は承認済みのまま）、レビュー済みフラグと準備済みのノートはクリアされます。**Review** に戻ると、**Copy case note** はもう利用できず、必要な承認が再度行われるまでノートのレビューはブロックされます。Output に切り替えただけではノートが非表示になるだけで、ノートを無効にするのは修正そのものです。

共有された文言は、以降のすべてのエージェントのターンで利用できるようになります。各ステージのテキストが自動的に置き換わることも、変更不可のソースコンテンツが変更されることもありません。エージェントへの反映を実演する場合は、修正後の共有ファクトを説明し、必要な出力の訂正を提案するよう求める短いリクエストを送信します。これはモデル呼び出しです。

### レコードを確認して開き直す

**Output** に戻り、**Revision history** を開きます。修正について、実行者、操作、リビジョン、理由、変更前後のテキストを示します。利用可能な場合は、古いリビジョンを読み込みます。

再読み込みの前に、残っている下書きを保存します。ページを再読み込みし、アラート一覧で **Resume alert ALT-2041** を選択するか、**Investigation sessions** から選択して、ケースを開き直します。同じタイトルのセッションが複数ある場合は、直前に使用したものを選択します。保存した修正、証拠、明確化のステータスが保持されていることを確認します。

再読み込みそのものでは、証拠の準備やエージェントの分析は再実行されません。ブラウザの接続が切れても、永続的なバックグラウンド作業はキャンセルされません。

### 通常の会話は別のものとして扱う

**New conversation** を選択すると、通常のチャット、PDF レビュー、任意のスキル、保存済みの HTML アーティファクトが引き続き利用できることを示せます。廃止された過去の RFP スキルを、現在の製品機能として紹介しないでください。

**プレゼンテーションの締めくくり:** "We have a persistent, editable evidence desk with traceable revisions. The analyst can challenge and correct the agent. Source limitations stay visible, and the app does not execute consequential financial or regulatory decisions."

### 次のデモに向けてリセットする

別のアラート（たとえば ALT-2036）を開くか、**New investigation** で新しい架空のセッションを使用します。ALT-2041 を再び開くと既存のケースが再開されるだけで、リセットはされません。ALT-2041 を最初からやり直すには、**Investigation sessions** からそのセッションを削除します（これによりアラートが解放され、新しいケースを作成できます）。デモをリセットするために `.data` を削除しないでください。**Refresh demo evidence** をリセットボタンとして使うのも避けてください。新しい準備ターンが作成され、以前のレビューが無効になる場合があります。

## 8. トラブルシューティングと制約

| 症状 | プレゼンターの対応 |
|---|---|
| タスクがキューに入ったまま進まない | ワーカーの準備状況と、API とワーカーの設定が一致していることを確認します。重複して送信しないでください。 |
| コントロールが無効になっている | アクティブなターンまたは更新処理が完了するまで待ちます。レビューには、準備済みの証拠、承認、根拠も必要です。 |
| リビジョンの競合 | ローカルの下書きを保持します。保存済みの出力と比較し、表示される場合は **Keep draft and use latest revision** を使用してから、理由を付けて意図的に再適用します。他のリビジョンを不用意に上書きしないでください。 |
| モデルが失敗する、または認可されていない | 失敗を隠さず表示したままにします。プレゼンテーションの外でプロバイダーの設定を確認するか、推論なしルートに切り替えます。フィクスチャの応答をライブ推論と呼ばないでください。 |
| コンテキストが上限を超える | 保存済みの過大な出力を短くするか、適切に設定されたモデルの上限を選択します。再試行しても、古い分析が黙ってリベースされることはありません。 |
| ソースが利用できないまま | SRC-04 は閲覧制限され、SRC-07 は設計上欠落していることを説明します。アクセスの回避や請求書の取得成功を示唆しないでください。 |
| ノートを準備できない | 準備を完了し、プレースホルダーを修正し、影響を受けるすべてのステージを承認し、根拠を入力して、ノートをレビュー済みにします。 |
| スコープのレンダラーが失敗する | 表示される場合は、プレーンなフォールバックを使用します。画面が無効な場合は、セッションを開き直して再読み込みします。 |
| コピーに失敗する | 表示されたノートを手動で選択してコピーします。外部への保存は未確認のままです。 |
| セッションまたはアシスタントが非表示 | セッションには **Toggle history**、アシスタントには **Chat** を使用します。狭い画面では、ワークスペースを編集する前にチャットドロワーを閉じます。 |
| タイムライン、レビュー、履歴が見当たらない | ソースは **Evidence**、ノートは **Review**、共有ファクトとリビジョン履歴は **Output** を選択します。ステージを選択すると Output に戻ります。 |

### 正確に伝えるべき運用上の制限

このアプリはローカルの単一ユーザー向けです。API プロセス1つ、ワーカー1つ、全体で実行中のタスク1つ、セッションごとにアクティブなターン1つという構成です。ローカルスコープはマルチユーザー認証ではありません。聴衆向けにデプロイする場合でも、ループバックやオリジンの保護を緩めないでください。

**Stop** は協調的なキャンセル要求です。最終的な結果が出るまで待ってください。**Retry** は明示的な操作であり、リンクされた新しいタスクを作成します。失敗、キャンセル、または古くなった提案を、公開済みの出力として提示してはいけません。ブラウザを閉じてもキャンセルにはなりません。

このデモは、ライブの異常検知、検証済みのリスクスコアの算出、規制遵守の証明、実在の銀行/ケースシステムへの接続を行いません。そのリビジョン履歴は、規制対象の監査統制を完全に実装したものではありません。アラート一覧は、同梱の架空のアラート4件のみです。ライブフィード、担当割り当て、トリアージの書き込み、「ケース不要」という処理方針はなく、review-by の日付はリマインダーにすぎません。高度なフィルターや完全な運用モデルなど、その他のシナリオ機能は実装されていません。

対応する公式の A2UI パッケージには、上流の Zod 依存関係に関するアドバイザリ **GHSA-mrhx-c7xc-m3w5** が残っています。固定テンプレートの検証とサイズ/深さの制限は安全策であり、このアドバイザリが解決済みであるという主張ではありません。依存関係の開示については README を参照してください。

### 参照資料とメンテナンス

**README.md** は、インストール、設定、コマンド、制限事項、検証に関する運用上の基準資料です。英語版のペアは `demonstration-manual.md` / `demonstration-manual.pdf` で、韓国語、日本語、中国語のペアには、それぞれ `.ko`、`.ja`、`.zh` の接尾辞が付きます。各 PDF には、対応する Markdown 版のデモ内容が含まれています。翻訳版のガイドでは、プレゼンターが実際のコントロールを見つけられるよう、UI ラベルを英語のまま残しています。これはアプリがローカライズされていることを意味するものではありません。

- シナリオの説明と想定プロセス: `docs\scenario\scenario.md` と `docs\scenario\process.md`。
- 実装済みの設計: `docs\superpowers\specs\2026-10-28-investigation-evidence-desk-design.md` と `docs\superpowers\specs\2026-10-29-alert-first-investigation-start-design.md`。
- プロトコル設計の背景: `docs\research\ag-ui-a2ui-integration.md`。
- 実行可能なブラウザー受け入れテスト: `web\e2e\investigation-workflow.spec.ts`。

アプリが変更された場合は、UI ラベルと動作を再確認してください。自動化されたフィクスチャの実行で検証されるのはアプリケーションの動作であり、ライブ推論の品質、金融面の正確性、実システムの権限ではありません。
