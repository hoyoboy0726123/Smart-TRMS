import os
import json
import io
import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

# --- 基礎系統 Prompt ---
SYSTEM_PROMPT = """
你是一位具備跨領域知識的實驗室數據專家。請分析這份 PDF 文件，並根據以下原則提取結構化資訊：

1. **核心資訊**：自動辨識並提取報告編號(report_number)、產品名稱或型號(product_model)、核發實驗室(laboratory)、測試日期(test_date)。
2. **自動指標發現**：
   - 掃描所有表格與清單。
   - 提取所有測試項目(metric_name)、測得數值(metric_value)、單位(unit)及該項判定結果(is_pass)。
3. **專業摘要**：撰寫 150 字內的結論摘要。

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
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for i, page in enumerate(doc):
        if i >= max_pages: break
        text += page.get_text()
    return text

def validate_gemini_key(api_key):
    """驗證 Gemini 金鑰是否有效"""
    try:
        client = genai.Client(api_key=api_key)
        # 發送一個極小的請求測試
        client.models.generate_content(model="gemini-3-flash-preview", contents="hi", config=types.GenerateContentConfig(max_output_tokens=1))
        return True, "驗證成功"
    except Exception as e:
        return False, str(e)

def validate_groq_key(api_key):
    """驗證 Groq 金鑰是否有效"""
    try:
        client = Groq(api_key=api_key)
        # 列出模型來測試金鑰
        client.models.list()
        return True, "驗證成功"
    except Exception as e:
        return False, str(e)

def parse_pdf_with_gemini(file_bytes, api_key):
    """
    BYOK 版：傳入用戶自定義的 Gemini API Key。
    """
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"), SYSTEM_PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Gemini 驗證或辨識失敗: {str(e)}"}

def parse_pdf_with_groq(file_bytes, api_key):
    """
    BYOK 版：傳入用戶自定義的 Groq API Key。
    """
    try:
        client = Groq(api_key=api_key)
        pdf_text = extract_text_from_pdf(file_bytes, max_pages=5)
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"請解析以下報告內容：\n\n{pdf_text}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"Groq 驗證或辨識失敗: {str(e)}"}

def refine_parse_with_gemini(file_bytes, current_data, user_instruction, api_key):
    """
    BYOK 版對話修正。
    """
    try:
        client = genai.Client(api_key=api_key)
        refine_prompt = f"目前結果：\n{json.dumps(current_data, ensure_ascii=False)}\n指令：\"{user_instruction}\""
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"), refine_prompt, SYSTEM_PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"Gemini 修正失敗: {str(e)}"}

def get_mock_data():
    return {
        "report_number": "TR-MOCK-001",
        "product_model": "模擬產品",
        "laboratory": "模擬實驗室",
        "test_date": "2026-03-03",
        "overall_result": "Pass",
        "ai_summary": "這是模擬資料。",
        "metrics": [{"metric_name": "範例指標", "metric_value": "100", "unit": "V", "is_pass": True}]
    }
