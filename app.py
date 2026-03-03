import streamlit as st
import pandas as pd
from database import init_db, get_db, Report, TestMetric
from ai_engine import parse_pdf_with_gemini, parse_pdf_with_groq, refine_parse_with_gemini, get_mock_data
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

# 初始化資料庫與資料夾
init_db()
if not os.path.exists("reports"):
    os.makedirs("reports")

# 側邊欄導覽
st.sidebar.title("🚀 Smart TRMS")
ai_provider = st.sidebar.radio("選擇 AI 引擎", ["Gemini 3 Flash", "Groq (DeepSeek V3)"])
page = st.sidebar.selectbox(
    "導航選單",
    ["📊 數據看板 (Dashboard)", "📤 報告上傳 (Upload)", "📂 數位檔案庫 (Archive)", "⚙️ 系統設定 (Settings)"]
)

# --- 1. 數據看板 ---
if page == "📊 數據看板 (Dashboard)":
    st.header("數據看板")
    db_gen = get_db()
    db = next(db_gen)
    col_stat1, col_stat2 = st.columns([1, 2])
    with col_stat1:
        pie_fig = plot_pass_rate_pie(db)
        if pie_fig: st.plotly_chart(pie_fig, use_container_width=True)
        else: st.info("尚與資料。")
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
    st.header(f"報告上傳與 AI 智慧解析 ({ai_provider})")
    
    report_type = st.selectbox(
        "選擇報告領域 (幫助 AI 精準辨識)",
        ["通用 (General)", "電子零件 (Electronics)", "材料分析 (Materials)", "醫療器材 (Medical Devices)"]
    )
    
    uploaded_file = st.file_uploader("選擇 PDF 測試報告", type=["pdf"])
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        
        if 'ai_results' not in st.session_state or st.session_state.get('last_file') != uploaded_file.name or st.session_state.get('last_provider') != ai_provider:
            with st.status(f"AI 正在以 [{report_type}] 模式解析中...") as status:
                try:
                    if ai_provider == "Gemini 3 Flash":
                        res = parse_pdf_with_gemini(file_bytes)
                    else:
                        res = parse_pdf_with_groq(file_bytes)
                        
                    if "error" in res:
                        st.warning(res["error"])
                        res = get_mock_data()
                    
                    if isinstance(res, list) and len(res) > 0:
                        res = res[0]
                    elif not isinstance(res, dict):
                        res = get_mock_data()
                        
                    st.session_state.ai_results = res
                except:
                    st.session_state.ai_results = get_mock_data()
                st.session_state.last_file = uploaded_file.name
                st.session_state.last_provider = ai_provider
                status.update(label="解析完成！", state="complete")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📄 原始文件預覽")
            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        with col2:
            st.subheader("📝 AI 辨識結果與對話修正")
            
            user_msg = st.chat_input("對 AI 下達進階修正指令...")
            if user_msg:
                with st.spinner("AI 重新審查中..."):
                    # 對話修正目前僅實作 Gemini 版本，Groq 可後續擴充
                    refined = refine_parse_with_gemini(file_bytes, st.session_state.ai_results, user_msg)
                    if "error" not in refined:
                        st.session_state.ai_results = refined
                        st.success("數據已更新！")
                    else: st.error(refined["error"])

            with st.form("confirm_form"):
                data = st.session_state.ai_results
                r_no = st.text_input("報告編號", value=data.get("report_number", ""))
                model = st.text_input("產品型號/名稱", value=data.get("product_model", ""))
                lab = st.text_input("實驗室", value=data.get("laboratory", ""))
                try: t_date = datetime.datetime.strptime(data.get("test_date", "2023-01-01"), "%Y-%m-%d").date()
                except: t_date = datetime.date.today()
                test_date = st.date_input("測試日期", value=t_date)
                res = st.selectbox("整體判定", ["Pass", "Fail"], index=0 if data.get("overall_result") == "Pass" else 1)
                summ = st.text_area("結論摘要", value=data.get("ai_summary", ""))
                
                m_df = pd.DataFrame(data.get("metrics", []))
                edited_m = st.data_editor(m_df, num_rows="dynamic", key="m_editor_upload")
                
                if st.form_submit_button("確認入庫並儲存 PDF"):
                    db_gen = get_db()
                    db = next(db_gen)
                    try:
                        safe_r_no = r_no.replace("/", "-").replace("\\", "-").strip()
                        if not safe_r_no or safe_r_no == "N/A":
                            safe_r_no = f"UNNAMED_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        save_path = f"reports/{safe_r_no}.pdf"
                        with open(save_path, "wb") as f: f.write(file_bytes)
                        
                        new_r = Report(
                            report_number=r_no, product_model=model, laboratory=lab,
                            test_date=test_date, overall_result=res, ai_summary=summ,
                            file_path=save_path, status='已確認'
                        )
                        db.add(new_r)
                        db.flush()
                        for _, row in edited_m.iterrows():
                            db.add(TestMetric(
                                report_id=new_r.id, metric_name=row['metric_name'],
                                metric_value=row['metric_value'], unit=row['unit'], is_pass=row['is_pass']
                            ))
                        db.commit()
                        st.success(f"入庫成功！檔案：{save_path}")
                        st.balloons()
                    except Exception as e:
                        db.rollback()
                        st.error(f"錯誤: {e}")
                    finally: db.close()

# --- 3. 數位檔案庫 ---
elif page == "📂 數位檔案庫 (Archive)":
    st.header("數位檔案庫管理")
    db_gen = get_db()
    db = next(db_gen)
    reports = db.query(Report).all()
    
    if not reports:
        st.warning("暫無資料。")
    else:
        list_data = [{
            "ID": r.id, "報告編號": r.report_number, "型號": r.product_model,
            "結果": r.overall_result, "日期": r.test_date
        } for r in reports]
        df = pd.DataFrame(list_data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        col_sel, col_del = st.columns([3, 1])
        with col_sel:
            selected_id = st.selectbox("選擇報告進行檢視或刪除", df["ID"])
        
        if selected_id:
            curr = db.query(Report).filter(Report.id == selected_id).first()
            
            with col_del:
                st.write("")
                if st.button("🗑️ 刪除此報告", type="secondary"):
                    try:
                        if curr.file_path and os.path.exists(curr.file_path):
                            os.remove(curr.file_path)
                        db.delete(curr)
                        db.commit()
                        st.success(f"報告 {curr.report_number} 已刪除。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"刪除失敗: {e}")

            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader("📄 PDF 預覽")
                if curr.file_path and os.path.exists(curr.file_path):
                    with open(curr.file_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                    st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)
                else: st.error("PDF 檔案已遺失。")
            with c2:
                st.subheader("🔍 詳細指標")
                st.info(f"**AI 結論：** {curr.ai_summary}")
                m_list = db.query(TestMetric).filter(TestMetric.report_id == selected_id).all()
                st.table(pd.DataFrame([{ "指標名稱": m.metric_name, "數值": m.metric_value, "單位": m.unit, "判定": "✅" if m.is_pass else "❌" } for m in m_list]))
    db.close()

# --- 4. 系統設定 ---
elif page == "⚙️ 系統設定 (Settings)":
    st.header("系統設定")
    col1, col2 = st.columns(2)
    with col1:
        new_gemini_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    with col2:
        new_groq_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
        
    if st.button("儲存設定"):
        os.environ["GEMINI_API_KEY"] = new_gemini_key
        os.environ["GROQ_API_KEY"] = new_groq_key
        st.success("API 金鑰已更新！")
