import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database import Report, TestMetric

def plot_metric_trend(db, metric_name):
    """
    針對特定測試指標繪製趨勢圖。
    """
    results = db.query(
        Report.test_date, 
        TestMetric.metric_value, 
        Report.report_number
    ).join(TestMetric).filter(TestMetric.metric_name == metric_name).order_by(Report.test_date).all()
    
    if not results:
        return None
    
    df = pd.DataFrame(results, columns=['日期', '數值', '報告編號'])
    
    # [優化] 將數值從 String 轉為 Float，無法轉換的 (如 16 to 3000) 會變為 NaN
    df['數值'] = pd.to_numeric(df['數值'], errors='coerce')
    
    # 過濾掉 NaN (無法轉換為數值的項目)
    df = df.dropna(subset=['數值'])
    
    if df.empty:
        return None
        
    fig = px.line(
        df, x='日期', y='數值', 
        title=f'指標趨勢分析: {metric_name}',
        markers=True,
        hover_data=['報告編號']
    )
    return fig

def plot_pass_rate_pie(db):
    """
    繪製整體合格率圓餅圖。
    """
    results = db.query(Report.overall_result).all()
    if not results:
        return None
        
    df = pd.DataFrame(results, columns=['結果'])
    counts = df['結果'].value_counts().reset_index()
    counts.columns = ['判定', '數量']
    
    fig = px.pie(
        counts, values='數量', names='判定', 
        title='累積報告合格率統計',
        color='判定',
        color_discrete_map={'Pass': '#2ECC71', 'Fail': '#E74C3C'}
    )
    return fig
