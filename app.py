import streamlit as st
import pandas as pd
from database import get_db_session, Report, TestMetric
from ai_engine import (
    parse_pdf_with_gemini, parse_pdf_with_groq, 
    refine_parse_with_gemini, get_mock_data,
    validate_gemini_key, validate_groq_key
)
from viz_engine import plot_metric_trend, plot_pass_rate_pie
import os
import datetime
import base64
import shutil

# 設定頁面配置
st.set_page_config(
    page_title="智慧測試報告管理系統 (Smart TRMS)",
    page_icon="📊",
    layout="wide"
)

# --- 簡易登入機制 ---
if "user_name" not in st.session_state:
    st.title("🚀 智慧測試報告管理系統")
    st.subheader("歡迎使用！請輸入您的帳號進行登入或註冊")
    
    with st.form("login_form"):
        u_name = st.text_input("使用者名稱 (帳號唯一，若不存在則會自動註冊)", placeholder="例如: User01")
        login_btn = st.form_submit_button("進入系統")
        
        if login_btn:
            if u_name.strip():
                st.session_state.user_name = u_name.strip()
                st.rerun()
            else:
                st.error("請輸入有效的使用者名稱")
    
    st.info("💡 說明：本系統採帳號隔離機制，不同帳號將擁有獨立的資料庫與 PDF 儲存空間。")
    st.stop() # 阻斷後續程式碼執行

# --- 登入後的變數設定 ---
current_user = st.session_state.user_name
user_report_dir = f"reports/{current_user}"
if not os.path.exists(user_report_dir):
    os.makedirs(user_report_dir)

# --- 側邊欄：BYOK 金鑰驗證與引擎選擇 ---
st.sidebar.title(f"👤 您好, {current_user}")
if st.sidebar.button("登出"):
    del st.session_state.user_name
    st.rerun()

st.sidebar.divider()
st.sidebar.info("🧪 **BYOK 隱私模式**：金鑰僅存於本次 Session。")

ai_provider = st.sidebar.radio("選擇 AI 引擎", ["Gemini 3 Flash", "Groq (Llama-3.1 8B)"])

if "gemini_valid" not in st.session_state: st.session_state.gemini_valid = False
if "groq_valid" not in st.session_state: st.session_state.groq_valid = False

if ai_provider == "Gemini 3 Flash":
    user_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")
    if user_key:
        valid, msg = validate_gemini_key(user_key)
        if valid:
            st.sidebar.success("✅ 金鑰驗證成功")
            st.session_state.gemini_api_key = user_key
            st.session_state.gemini_valid = True
        else:
            st.sidebar.error(f"❌ 驗證失敗: {msg}")
            st.session_state.gemini_valid = False
else:
    user_key = st.sidebar.text_input("輸入 Groq API Key", type="password")
    if user_key:
        valid, msg = validate_groq_key(user_key)
        if valid:
            st.sidebar.success("✅ 金鑰驗證成功")
            st.session_state.groq_api_key = user_key
            st.session_state.groq_valid = True
        else:
            st.sidebar.error(f"❌ 驗證失敗: {msg}")
            st.session_state.groq_valid = False

page = st.sidebar.selectbox("導航選單", ["📊 數據看板 (Dashboard)", "📤 報告上傳 (Upload)", "📂 數位檔案庫 (Archive)"])

def is_ready():
    return st.session_state.gemini_valid if ai_provider == "Gemini 3 Flash" else st.session_state.groq_valid

# --- 1. 數據看板 ---
if page == "📊 數據看板 (Dashboard)":
    st.header(f"📊 {current_user} 的數據看板")
    db = get_db_session(current_user)
    col_stat1, col_stat2 = st.columns([1, 2])
    with col_stat1:
        pie_fig = plot_pass_rate_pie(db)
        if pie_fig: st.plotly_chart(pie_fig, use_container_width=True)
        else: st.info("尚無數據。")
    with col_stat2:
        all_metrics = db.query(TestMetric.metric_name).distinct().all()
        metric_names = [m[0] for m in all_metrics]
        if metric_names:
            selected_metric = st.selectbox("選擇分析指標", metric_names)
            trend_fig = plot_metric_trend(db, selected_metric)
            if trend_fig: st.plotly_chart(trend_fig, use_container_width=True)
        else: st.info("尚無指標數據。")
    db.close()

# --- 2. 報告上傳 ---
elif page == "📤 報告上傳 (Upload)":
    st.header(f"📤 報告上傳 ({ai_provider})")
    if not is_ready():
        st.error(f"❌ 請先在左側輸入並驗證 {ai_provider} API Key。")
    else:
        uploaded_file = st.file_uploader("選擇 PDF 測試報告", type=["pdf"])
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            current_key = st.session_state.gemini_api_key if ai_provider == "Gemini 3 Flash" else st.session_state.groq_api_key
            if 'ai_results' not in st.session_state or st.session_state.get('last_file') != uploaded_file.name:
                with st.status("AI 解析中...") as status:
                    try:
                        if ai_provider == "Gemini 3 Flash": res = parse_pdf_with_gemini(file_bytes, current_key)
                        else: res = parse_pdf_with_groq(file_bytes, current_key)
                        if "error" in res: res = get_mock_data()
                        if isinstance(res, list): res = res[0]
                        st.session_state.ai_results = res
                    except: st.session_state.ai_results = get_mock_data()
                    st.session_state.last_file = uploaded_file.name
                    status.update(label="解析完成！", state="complete")

            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("📄 PDF 預覽")
                base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
                st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf">', unsafe_allow_html=True)
            with col2:
                with st.form("confirm_form"):
                    d = st.session_state.ai_results
                    r_no = st.text_input("報告編號", value=d.get("report_number", ""))
                    model = st.text_input("產品型號", value=d.get("product_model", ""))
                    lab = st.text_input("實驗室", value=d.get("laboratory", ""))
                    try: t_date = datetime.datetime.strptime(d.get("test_date", "2023-01-01"), "%Y-%m-%d").date()
                    except: t_date = datetime.date.today()
                    test_date = st.date_input("測試日期", value=t_date)
                    res = st.selectbox("判定", ["Pass", "Fail"], index=0 if d.get("overall_result") == "Pass" else 1)
                    summ = st.text_area("摘要", value=d.get("ai_summary", ""))
                    m_df = pd.DataFrame(d.get("metrics", []))
                    edited_m = st.data_editor(m_df, num_rows="dynamic")
                    
                    if st.form_submit_button("確認入庫"):
                        db = get_db_session(current_user)
                        try:
                            safe_no = r_no.replace("/", "-")
                            save_path = f"{user_report_dir}/{safe_no}.pdf"
                            with open(save_path, "wb") as f: f.write(file_bytes)
                            new_r = Report(report_number=r_no, product_model=model, laboratory=lab, test_date=test_date, overall_result=res, ai_summary=summ, file_path=save_path)
                            db.add(new_r)
                            db.flush()
                            for _, row in edited_m.iterrows():
                                db.add(TestMetric(report_id=new_r.id, metric_name=row['metric_name'], metric_value=str(row['metric_value']), unit=row['unit'], is_pass=row['is_pass']))
                            db.commit()
                            st.success(f"已存入 {current_user} 的資料庫。")
                            st.balloons()
                        except Exception as e: st.error(f"錯誤: {e}")
                        finally: db.close()

# --- 3. 數位檔案庫 ---
elif page == "📂 數位檔案庫 (Archive)":
    st.header(f"📂 {current_user} 的檔案庫")
    db = get_db_session(current_user)
    reports = db.query(Report).all()
    if not reports: st.warning("暫無資料。")
    else:
        df = pd.DataFrame([{"ID": r.id, "報告編號": r.report_number, "日期": r.test_date} for r in reports])
        st.dataframe(df, use_container_width=True)
        sel_id = st.selectbox("選擇報告", df["ID"])
        if sel_id:
            curr = db.query(Report).filter(Report.id == sel_id).first()
            if st.button("🗑️ 刪除"):
                if curr.file_path and os.path.exists(curr.file_path): os.remove(curr.file_path)
                db.delete(curr); db.commit()
                st.rerun()
            c1, c2 = st.columns([1, 1])
            with c1:
                if curr.file_path and os.path.exists(curr.file_path):
                    with open(curr.file_path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
                    st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)
            with c2:
                m_list = db.query(TestMetric).filter(TestMetric.report_id == sel_id).all()
                st.table(pd.DataFrame([{"指標": m.metric_name, "數值": m.metric_value, "單位": m.unit} for m in m_list]))
    db.close()
