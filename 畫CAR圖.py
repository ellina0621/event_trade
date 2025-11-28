import pandas as pd
import matplotlib.pyplot as plt
import os
import platform
from datetime import datetime

# --- 1. 設定路徑 ---
base_path = r"D:\我才不要走量化\法說會"
path_model = os.path.join(base_path, "final_model_complete.csv")
path_events = os.path.join(base_path, "TMBA_Events_Master.csv")
output_folder = os.path.join(base_path, "CAR_Charts_After1330") # 改個資料夾名區隔

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# --- 2. 畫圖設定 (修復中文) ---
def set_chinese_font():
    system = platform.system()
    if system == 'Windows':
        font_list = ['Microsoft JhengHei', 'SimHei', 'Arial']
        plt.rcParams['font.sans-serif'] = font_list
    elif system == 'Darwin': 
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    plt.rcParams['axes.unicode_minus'] = False 

set_chinese_font()

# --- 輔助函數：判斷時間是否晚於 13:30 ---
def is_after_market_close(time_str):
    try:
        # 將字串 (如 "14:30") 轉為時間物件
        t = datetime.strptime(str(time_str).strip(), '%H:%M').time()
        cutoff = datetime.strptime('13:30', '%H:%M').time()
        return t >= cutoff # 大於等於 13:30 回傳 True
    except:
        return False # 格式錯誤或空值就略過

def generate_car_plots_all_after_1330():
    print("🚀 載入資料中...")
    df_model = pd.read_csv(path_model)
    df_events = pd.read_csv(path_events)

    # --- 格式清洗 ---
    print("📅 格式化日期與代碼...")
    df_model['Date'] = pd.to_datetime(df_model['Date'], format='%Y%m%d')
    df_events['Date'] = pd.to_datetime(df_events['Date'])

    if 'StockCode' in df_events.columns:
        df_events.rename(columns={'StockCode': 'Code'}, inplace=True)
    if 'StockCode' in df_model.columns:
        df_model.rename(columns={'StockCode': 'Code'}, inplace=True)

    # --- 關鍵修改：篩選 13:30 (含) 以後的所有事件 ---
    print("🔍 正在篩選 13:30 後的法說會...")
    # 使用 apply 搭配上面的輔助函數
    mask = df_events['Time'].apply(is_after_market_close)
    df_events_filtered = df_events[mask].copy()
    
    print(f"👉 原始事件數：{len(df_events)}")
    print(f"👉 篩選後 (>=13:30) 事件數：{len(df_events_filtered)}")

    # --- 準備 CAR 計算 ---
    df_model.sort_values(by=['Code', 'Date'], inplace=True)
    df_model.set_index(['Code', 'Date'], inplace=True)

    window = 5 
    count = 0
    print(f"🎨 開始繪製 CAR 圖表 (輸出至 {output_folder})...")

    # --- 迴圈處理 ---
    for idx, row in df_events_filtered.iterrows():
        ticker = row['Code']
        event_date = row['Date']
        event_time = row['Time']
        raw_name = row.get('StockName')
        name = str(raw_name) if pd.notna(raw_name) else str(ticker)

        try:
            # 檢查是否有該股票資料
            if ticker not in df_model.index.levels[0]:
                continue
                
            stock_data = df_model.loc[ticker]
            
            # 檢查日期是否存在
            if event_date in stock_data.index:
                loc_idx = stock_data.index.get_loc(event_date)
                start_loc = loc_idx - window
                end_loc = loc_idx + window
                
                # 確保窗口在資料範圍內
                if start_loc >= 0 and end_loc < len(stock_data):
                    subset = stock_data.iloc[start_loc : end_loc+1].copy()
                    
                    # 計算 CAR
                    subset['CAR'] = subset['Abnormal_Return'].cumsum()
                    subset['Relative_Day'] = range(-window, window + 1)

                    # 繪圖
                    plt.figure(figsize=(10, 6))
                    plt.plot(subset['Relative_Day'], subset['CAR'], marker='o', color='#1f77b4', linewidth=2)
                    
                    # 標記線
                    plt.axvline(x=0, color='red', linestyle='--', alpha=0.8, label=f'法說會 ({event_time})')
                    plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
                    
                    # 標題
                    plt.title(f"{name} ({ticker}) - 法說會 CAR 走勢\n日期: {event_date.strftime('%Y-%m-%d')} 時間: {event_time}", fontsize=16)
                    plt.xlabel('相對天數', fontsize=12)
                    plt.ylabel('累積異常報酬 (CAR)', fontsize=12)
                    plt.legend(loc='best')
                    plt.grid(True, alpha=0.3)
                    
                    # 存檔 (檔名加上時間以防重複)
                    time_clean = str(event_time).replace(':', '')
                    filename = f"{ticker}_{event_date.strftime('%Y%m%d')}_{time_clean}.png"
                    save_path = os.path.join(output_folder, filename)
                    plt.savefig(save_path)
                    plt.close()
                    
                    count += 1
                    if count % 100 == 0:
                        print(f"✅ 已完成 {count} 張圖...")

        except Exception as e:
            # print(f"❌ Error: {e}") # 錯誤太多時可以註解掉
            continue

    print("-" * 30)
    print(f"🎉 全部完成！共產生 {count} 張圖表")
    print(f"📂 請查看資料夾：{output_folder}")

if __name__ == "__main__":
    generate_car_plots_all_after_1330()

