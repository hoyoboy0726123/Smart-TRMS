# 智慧測試報告管理系統 (Smart TRMS) 系統設計文件 (SDD)

本文件旨在為「智慧測試報告管理系統 (Smart TRMS)」提供一份精簡且具備高度可執行性的系統設計架構。本設計專為初學者優化，採用 Python 生態系進行快速開發與在地化部署，並特別針對 AI 輔助開發（如 GitHub Copilot, ChatGPT）進行結構化配置。

---

## 1. 簡介

### 1.1 專案概述
本專案開發一套「智慧測試報告管理系統」，旨在解決傳統實驗室 PDF 報告數據難以檢索與分析的問題。系統將整合 AI 辨識技術，自動擷取非結構化 PDF 內容並轉化為 SQL 資料庫中的結構化數據，最後透過網頁介面提供趨勢分析與檔案管理功能。

### 1.2 系統目標
*   **自動化擷取**：利用 AI 技術減少 70% 以上的人工數據輸入時間。
*   **人機協作**：提供直觀的對照介面，確保 100% 的數據入庫準確率。
*   **數據可視化**：自動生成測試指標的趨勢圖，輔助品質預警。
*   **高效檢索**：支援多維度篩選與關鍵字搜尋，取代傳統資料夾查找。
*   **快速部署**：採用輕量化架構，可在一般筆記型電腦環境直接執行。

### 1.3 技術選型
*   **程式語言**：Python 3.9+ (穩定且具備豐富 AI 庫)
*   **Web UI 框架**：**Streamlit** (快速構建數據工具，無需撰寫傳統 HTML/CSS)
*   **資料處理**：Pandas (表格運算與統計)
*   **資料庫**：**SQLite** (單一檔案，免安裝伺服器)
*   **資料庫 ORM**：SQLAlchemy (簡化資料庫操作與後續擴展)
*   **AI 整合**：OpenAI API (GPT-4o Vision) 或 Azure Form Recognizer
*   **PDF 處理**：PyMuPDF 或 PDFPlumber

---

## 2. 系統架構與運作流程

### 2.1 整體架構
```
[ 使用者瀏覽器 ] 
       ↕ (HTTP)
[ Streamlit Web UI (app.py) ] <-----> [ AI 引擎 (ai_engine.py) ] 
       ↕ (ORM)                         ↕ (API Call)
[ SQLAlchemy 邏輯 (database.py) ] <---> [ OpenAI / Azure API ]
       ↕
[ SQLite 資料庫 (trms.db) ]
```

### 2.2 運作流程詳解
1.  **上傳與解析**：使用者於 Streamlit 介面上傳 PDF，系統呼叫 AI 引擎進行文字與表格辨識。
2.  **覆核驗證**：系統於介面展示「左側 PDF / 右側 AI 結果」，使用者手動修正後點擊「確認」。
3.  **持久化儲存**：資料經由 SQLAlchemy 寫入 SQLite 資料庫中。
4.  **查詢與分析**：使用者切換至「數位檔案庫」或「趨勢看板」，系統從資料庫抓取數據並由 Pandas 進行彙整繪圖。

---

## 3. 核心模組設計

| 模組名稱 | 檔案名稱 | 職責 | 核心功能 (函數) |
| :--- | :--- | :--- | :--- |
| **資料庫模組** | `database.py` | 定義數據模型與連線 | `init_db()`, `add_report()`, `get_filtered_reports()` |
| **AI 辨識模組** | `ai_engine.py` | 處理 PDF 並調用 AI API | `extract_pdf_text()`, `parse_with_ai()`, `summarize_report()` |
| **數據分析模組** | `viz_engine.py` | 生成統計數據與圖表 | `plot_trend_chart()`, `calculate_pass_rate()` |
| **主程式介面** | `app.py` | 負責 UI 呈現與流程控制 | `main_page()`, `upload_page()`, `dashboard_page()` |

---

## 4. 資料庫設計

### 4.1 資料庫選型
選用 **SQLite**。其優點為無需安裝複雜的資料庫伺服器，整個資料庫就是一個 `.db` 檔案，非常適合 MVP 階段與本機驗證，且 SQLAlchemy 支援平滑遷移至 PostgreSQL。

### 4.2 資料表設計

#### 表 A：`reports` (報告主檔)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| report_number | VARCHAR | 報告編號 | 唯一索引 |
| product_model | VARCHAR | 產品型號 | |
| laboratory | VARCHAR | 實驗室名稱 | |
| test_date | DATE | 測試日期 | |
| overall_result | VARCHAR | 判定結果 | Pass/Fail |
| ai_summary | TEXT | AI 生成的結論摘要 | |
| file_path | VARCHAR | 原始 PDF 儲存路徑 | |
| status | VARCHAR | 處理狀態 | 待審核/已確認/已作廢 |
| created_at | DATETIME | 建立時間 | |

#### 表 B：`test_metrics` (測試指標數據)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| report_id | INTEGER | 關聯報告 ID | 外鍵 (Reports.id) |
| metric_name | VARCHAR | 指標名稱 | 如：電壓, 雜質含量 |
| metric_value | FLOAT | 測試數值 | |
| unit | VARCHAR | 單位 | |
| is_pass | BOOLEAN | 是否合格 | |

---

## 5. 使用者介面與互動規劃

### 5.1 頁面結構 (Sidebar 導覽)
1.  **📊 數據看板 (Dashboard)**：顯示合格率圓餅圖、關鍵指標趨勢線。
2.  **📤 報告上傳 (Upload)**：拖放 PDF 區域、AI 解析進度條、雙欄對照修正區。
3.  **📂 數位檔案庫 (Archive)**：具備篩選器（日期、型號）的數據表格。
4.  **⚙️ 系統設定 (Settings)**：API Key 設定、實驗室模板配置。

### 5.2 核心互動流程
*   **上傳路徑**：`st.file_uploader` 接收檔案 -> `ai_engine` 返回 JSON -> `st.data_editor` (Streamlit 的可編輯表格) 顯示數據供用戶手動修正 -> 點擊「提交入庫」按鈕。
*   **分析路徑**：從 SQLite 讀取數據 -> 轉換為 Pandas DataFrame -> `st.line_chart` 呈現趨勢。

---

## 6. API 設計 / 功能函數

### 6.1 `ai_engine.parse_with_ai(file_bytes)`
*   **輸入**：PDF 二進位串流。
*   **內部邏輯**：將 PDF 轉為圖片或文字，發送 Prompt 給 GPT-4o 請求回傳特定格式的 JSON（例如：`{"report_no": "TR123", "metrics": [...]}`）。
*   **輸出**：結構化字典 (Dictionary)。

### 6.2 `database.save_verified_data(report_meta, metrics_list)`
*   **輸入**：經人工核對後的元數據與指標列表。
*   **內部邏輯**：開啟 SQLAlchemy Session，同時寫入 `reports` 與 `test_metrics` 表，確保原子性。

---

## 7. 錯誤處理策略

| 錯誤情境 | 處理策略 | UI 呈現 |
| :--- | :--- | :--- |
| **AI 辨識失敗** | 若 API 回傳非 JSON 格式或超時，重試一次。 | `st.error` 提示「辨識失敗，請手動輸入關鍵欄位」。 |
| **檔案格式錯誤** | 檢查副檔名是否為 `.pdf`。 | `st.warning` 提示「僅支援 PDF 檔案」。 |
| **資料庫衝突** | 若報告編號重複。 | 彈出對話框詢問「是否覆蓋現有數據？」。 |

---

## 8. 實作路徑 (Implementation Roadmap)

### 8.1 環境建置與依賴安裝
```bash
# 建立專案資料夾
mkdir smart_trms
cd smart_trms

# 建立並啟動虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 建立 requirements.txt
cat <<EOT > requirements.txt
streamlit
pandas
sqlalchemy
plotly
openai
pdfplumber
python-dotenv
EOT

# 安裝套件
pip install -r requirements.txt
```

### 8.2 資料庫模組開發 (`database.py`)
1.  使用 SQLAlchemy `declarative_base` 定義 `Report` 與 `TestMetric` 類別。
2.  實作 `get_engine()` 函數連接 `sqlite:///trms.db`。

### 8.3 核心業務邏輯開發 (`ai_engine.py`)
1.  實作 PDF 文字提取邏輯。
2.  撰寫 Prompt Template，要求 LLM 擷取特定欄位並以 JSON 輸出。
3.  實作 API 調用邏輯（需包含 `try-except`）。

### 8.4 使用者介面開發 (`app.py`)
1.  配置 `st.set_page_config`。
2.  使用 `st.sidebar.selectbox` 進行頁面導覽切換。
3.  **上傳頁面核心代碼片段**：
    ```python
    uploaded_file = st.file_uploader("上傳 PDF 報告")
    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("原始文件預覽")
            # 顯示 PDF...
        with col2:
            st.subheader("AI 辨識結果 (可修正)")
            edited_data = st.data_editor(ai_json_result)
            if st.button("確認入庫"):
                save_to_db(edited_data)
    ```

### 8.5 測試與驗證
*   **功能測試**：確保不同實驗室模板的 PDF 都能正確被 LLM 解析。
*   **壓力測試**：連續上傳 10 份報告，觀察 SQLite 寫入速度。
*   **邊界測試**：上傳空白 PDF 或掃描畫質極差的 PDF。

### 8.6 部署與運行說明
1.  於專案根目錄建立 `.env` 檔案並填入 `OPENAI_API_KEY`。
2.  啟動指令：
    ```bash
    streamlit run app.py
    ```
3.  預設瀏覽器將自動開啟 `http://localhost:8501`。

---
*End of Design Document*