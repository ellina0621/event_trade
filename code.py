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



# 匯入 Shioaji 套件
import pandas as pd
import time
import sqlite3
import numpy as np
import shioaji as sj
import statsmodels.api as sm
import matplotlib.pyplot as plt
import os
import yfinance as yf
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import chardet
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import statsmodels.api as sm
from numpy.linalg import lstsq
from dateutil.relativedelta import relativedelta
import mplfinance as mpf
import seaborn as sns
from scipy.stats import pearsonr
from scipy.stats import ttest_1samp
from arch import arch_model
import statsmodels.formula.api as smf

####用database資料去計算以每半小時為單位的lambda跟oib####
##change 內外
db_path = "event01.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

#（1）確認 side 欄位是否已存在，沒有就新增
cursor.execute("""
PRAGMA table_info(ticks);
""")
cols = [row[1] for row in cursor.fetchall()]

if "side" not in cols:
    cursor.execute("ALTER TABLE ticks ADD COLUMN side TEXT;")
    print("✓ 已新增 side 欄位")
else:
    print("✓ side 欄位已存在，直接更新")

#（2）將 tick_type → side（b/s）
cursor.execute("UPDATE ticks SET side = 'b' WHERE tick_type = 1;")
cursor.execute("UPDATE ticks SET side = 's' WHERE tick_type = 2;")

conn.commit()
conn.close()

#print("✓ 已完成 side 填寫（b/s）")

########計算oib#########
db_path = "event01.db"
conn = sqlite3.connect(db_path)
# 讀取需要的欄位
df = pd.read_sql("SELECT code, ts, close, volume, side FROM ticks", conn)
conn.close()

df["ts"] = pd.to_datetime(df["ts"], format="mixed")
df["date"] = df["ts"].dt.date
df["half_hour"] = df["ts"].dt.floor("30T")

# ***** 修正 OIB: 使用 volume 替代 amount *****
# 買方量 (使用 volume)
buy = (
    df[df["side"] == "b"]
    .groupby(["code", "date", "half_hour"])["volume"] # *** 修正點：用 volume ***
    .sum()
    .rename("buy_volume")
)

# 賣方量 (使用 volume)
sell = (
    df[df["side"] == "s"]
    .groupby(["code", "date", "half_hour"])["volume"] # *** 修正點：用 volume ***
    .sum()
    .rename("sell_volume")
)

# OIB 應該是淨買/賣量，不需要取絕對值，保留方向，才能反映壓力方向
oib = pd.concat([buy, sell], axis=1).fillna(0)
# ***** 修正 OIB: 移除 abs，反映方向性 *****
oib["OIB"] = oib["buy_volume"] - oib["sell_volume"]


######算lambda#####
results = []
for (code, hh), g in df.groupby(["code", "half_hour"]):
    g = g.sort_values("ts").reset_index(drop=True)
    
    if len(g) < 3: continue

    g["dP"] = g["close"].diff()
    # ***** 修正 lambda X 變數: 使用 volume 替代 amount (dAmt) *****
    g["dVol"] = g["volume"].diff() 

    g = g.dropna(subset=["dP", "dVol"])

    if g["dVol"].abs().sum() == 0: continue # 避免成交量變化總和為零

    X = sm.add_constant(g["dVol"])
    y = g["dP"]

    model = sm.OLS(y, X).fit()

    # lambda_hat 現在代表價格衝擊對 (成交量變化) 的敏感度
    lambda_hat = model.params["dVol"] 
    # ***** 修正 lambda: 移除絕對值，保留 lambda 原始數值 *****
    results.append({
        "code": code,
        "half_hour": hh,
        "lambda_30m": lambda_hat, 
        "n_ticks": len(g)
    })

lambda_df = pd.DataFrame(results)

#####合併######
merged = pd.merge(
    lambda_df,
    oib,
    on=["code", "half_hour"],
    how="inner"
)

# ***** 修正 info_pressure: OIB * Lambda 應該是 Pressure * Sensitivity *****
# 注意：lambda_30m 已經有正負號 (價格衝擊方向)，OIB 也有正負號 (買賣壓力方向)
# Pressure = 價格衝擊方向 * 壓力大小
merged["info_pressure"] = merged["OIB"] * merged["lambda_30m"]

print(merged.head())