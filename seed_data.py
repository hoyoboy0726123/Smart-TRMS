import random
import datetime
from database import SessionLocal, init_db, Report, TestMetric

def seed_data():
    # 初始化資料庫結構
    init_db()
    db = SessionLocal()
    
    # 清除舊資料（選用，確保展示效果）
    db.query(TestMetric).delete()
    db.query(Report).delete()
    
    product_models = ["iPhone 15 Pro", "Samsung S24", "Pixel 8"]
    labs = ["SGS Taiwan", "TUV Rheinland", "Intertek"]
    metrics_info = [
        {"name": "電壓穩定性", "unit": "V", "base": 5.0, "range": 0.5},
        {"name": "抗壓強度", "unit": "MPa", "base": 150.0, "range": 20.0}
    ]

    print("正在產生 10 筆展示資料...")

    for i in range(10):
        # 產生過去 10 天的日期
        test_date = datetime.date.today() - datetime.timedelta(days=(10 - i))
        report_no = f"TR-2026-{100 + i}"
        model = product_models[i % len(product_models)]
        lab = labs[i % len(labs)]
        
        # 模擬 80% 的合格率
        overall_result = "Pass" if random.random() > 0.2 else "Fail"
        
        report = Report(
            report_number=report_no,
            product_model=model,
            laboratory=lab,
            test_date=test_date,
            overall_result=overall_result,
            ai_summary=f"這是關於 {model} 在 {lab} 進行的第 {i+1} 次測試自動生成的摘要。",
            status="已確認"
        )
        db.add(report)
        db.flush() # 取得 report.id

        # 為每份報告產生指標數據
        for m in metrics_info:
            # 隨機產生數值
            val = m["base"] + (random.random() - 0.5) * m["range"]
            # 如果整體失敗，隨機讓某個指標數值異常
            is_pass = True
            if overall_result == "Fail" and random.random() > 0.5:
                val = m["base"] * 1.5 if random.random() > 0.5 else m["base"] * 0.5
                is_pass = False
            
            metric = TestMetric(
                report_id=report.id,
                metric_name=m["name"],
                metric_value=round(val, 2),
                unit=m["unit"],
                is_pass=is_pass
            )
            db.add(metric)

    db.commit()
    db.close()
    print("✅ 成功產生 10 筆展示資料！現在您可以啟動系統查看看板了。")

if __name__ == "__main__":
    seed_data()
