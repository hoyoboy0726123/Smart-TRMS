import os
import json
import io
import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

load_dotenv()

# 初始化客戶端
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# 靈活化系統 Prompt：自動發現模式
SYSTEM_PROMPT = """
你是一位具備跨領域知識的實驗室數據專家。請分析這份報告內容，並根據以下原則提取結構化資訊：

1. **核心資訊**：自動辨識並提取報告編號(report_number)、產品名稱或型號(product_model)、核發實驗室(laboratory)、測試日期(test_date)。
2. **自動指標發現**：
   - 掃描所有數據。
   - 提取所有測試項目(metric_name)、測得數值(metric_value)、單位(unit)及該項判定結果(is_pass)。
   - **不要遺漏任何數據項目**，即便欄位名稱與上述不完全一致，請進行語義轉換。
3. **專業摘要**：撰寫 150 字內的結論摘要，若有異常（Fail）請特別標出。

請輸出一個單一的 JSON 物件 (Object)，不要輸出陣列 (Array)。
確保格式如下：
{
  "report_number": "...",
  "product_model": "...",
  "laboratory": "...",
  "test_date": "YYYY-MM-DD",
  "overall_result": "Pass/Fail",
  "ai_summary": "...",
  "metrics": [{"metric_name": "...", "metric_value": "...", "unit": "...", "is_pass": true}]
}
"""

def extract_text_from_pdf(file_bytes, max_pages=5):
    """
    從 PDF 中提取純文字，限制前 5 頁以符合免費層級 TPM 限制。
    大部分關鍵數據 (編號、型號、結論、指標) 都會在前 5 頁。
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        text += page.get_text()
    return text

def parse_pdf_with_gemini(file_bytes):
    if not gemini_client:
        return {"error": "請先在 .env 中設定 GEMINI_API_KEY"}

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                SYSTEM_PROMPT
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Gemini 辨識發生錯誤: {str(e)}"}

def parse_pdf_with_groq(file_bytes):
    """
    使用 Groq API 進行辨識。
    切換至 llama-3.1-8b-instant 以獲取更高的 TPM 限額與穩定性。
    """
    if not groq_client:
        return {"error": "請先在 .env 中設定 GROQ_API_KEY"}

    try:
        # 限制解析前 5 頁，避免 Token 超過 8000 TPM
        pdf_text = extract_text_from_pdf(file_bytes, max_pages=5)
        
        # 使用免費層級中配額最穩定的 8B 模型
        model_name = "llama-3.1-8b-instant"
        
        response = groq_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"請解析以下報告內容：\n\n{pdf_text}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"Groq 辨識發生錯誤: {str(e)}"}

def refine_parse_with_gemini(file_bytes, current_data, user_instruction):
    if not gemini_client:
        return {"error": "請先在 .env 中設定 GEMINI_API_KEY"}

    refine_prompt = f"""
    目前的辨識結果如下：
    {json.dumps(current_data, ensure_ascii=False)}

    使用者提出了以下修正或補充要求：
    "{user_instruction}"

    請重新審視 PDF 文件，並根據要求更新 JSON 資訊。
    """

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                refine_prompt,
                SYSTEM_PROMPT
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Gemini 重新辨識發生錯誤: {str(e)}"}

def get_mock_data():
    return {
        "report_number": "TR-2023-001",
        "product_model": "iPhone 15 Pro",
        "laboratory": "SGS Taiwan",
        "test_date": "2023-10-27",
        "overall_result": "Pass",
        "ai_summary": "本報告顯示產品在電壓穩定性與抗壓測試中皆符合國際標準。",
        "metrics": [
            {"metric_name": "電壓穩定性", "metric_value": "5.0", "unit": "V", "is_pass": True},
            {"metric_name": "抗壓強度", "metric_value": "150.5", "unit": "MPa", "is_pass": True}
        ]
    }
