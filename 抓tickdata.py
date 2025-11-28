import pandas as pd
import sqlite3
import shioaji as sj
import time
from datetime import datetime, timedelta, time as dt_time
import os
import sys

# ==========================================
# 1. 設定與初始化 (Configuration)
# ==========================================

BASE_DIR = r"D:\我才不要走量化"
csv_path = os.path.join(BASE_DIR, "法說會", "TMBA_Events_Master.csv")
db_path = os.path.join(BASE_DIR, "Data_Warehouse", "event01.db") 

# 確保資料夾存在
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# 🛑 流量限制設定 (4.5 GB)
LIMIT_GB = 0.5
BYTES_LIMIT = LIMIT_GB * 1024 * 1024 * 1024 

api = sj.Shioaji()
# ⚠️ 請填入你的 API Key
api.login(
    api_key="C9S9Vrcw1jiCkXj3QRR6rJYwfg5MQXBoTzYBprqXFvj7",      
    secret_key="BpauMtipDtzCFWPHnmpjdzk99ansWrapyhUrc2xrAv7F"   
)

print(f"🚀 API 登入成功 | 資料庫路徑: {db_path}")

# ==========================================
# 2. 流量監控函數 (Risk Control)
# ==========================================
def check_usage_limit():
    """
    檢查 API 流量使用狀況，如果超過限制則回傳 True
    """
    try:
        usage = api.usage()
        if usage is None: return False
        
        current_bytes = usage.bytes
        current_gb = current_bytes / (1024**3)
        
        # 顯示當前用量
        print(f"📊 目前流量使用: {current_gb:.4f} GB / {LIMIT_GB} GB")
        
        if current_bytes >= BYTES_LIMIT:
            print(f"🛑 流量警報：已達到 {LIMIT_GB} GB 上限，啟動熔斷機制停止下載。")
            return True
        return False
        
    except Exception as e:
        print(f"⚠️ 無法取得流量資訊: {e}")
        return False

# ==========================================
# 3. 資料庫準備
# ==========================================
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ticks (
    event_id TEXT,       
    code TEXT,
    event_date TEXT,
    event_time TEXT,
    real_date TEXT,      
    relative_day INTEGER,
    ts TEXT,
    close REAL,
    volume REAL,
    bid_price REAL,
    ask_price REAL,
    side TEXT,
    tick_type TEXT
)
""")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_id ON ticks (event_id)")
conn.commit()

# 讀取進度
print("🔍 檢查資料庫已存在的進度...")
try:
    cursor.execute("SELECT DISTINCT event_id FROM ticks")
    existing_ids = set(row[0] for row in cursor.fetchall())
    print(f"✅ 資料庫中已有 {len(existing_ids)} 場法說會資料，將自動跳過。")
except Exception as e:
    print("⚠️ 讀取現有進度失敗，將從頭開始。")
    existing_ids = set()

# ==========================================
# 4. 核心功能函數
# ==========================================

def get_ticks_df(contract, date_str):
    # 🔥 流量檢查 🔥
    if check_usage_limit():
        raise InterruptedError("TRAFFIC_LIMIT_REACHED")

    try:
        ticks = api.ticks(contract, date=date_str)
        df = pd.DataFrame({**ticks})
        if df.empty: return None
        df['ts'] = pd.to_datetime(df['ts'])
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except InterruptedError:
        raise 
    except:
        return None

def save_to_db(df, event_id, code, event_date, event_time, real_date, rel_day):
    try:
        df['event_id'] = event_id
        df['code'] = str(code)
        df['event_date'] = event_date
        df['event_time'] = event_time 
        df['real_date'] = real_date
        df['relative_day'] = rel_day
        df['ts'] = df['ts'].astype(str)
        
        cols = ['event_id', 'code', 'event_date', 'event_time', 'real_date', 'relative_day', 
                'ts', 'close', 'volume', 'bid_price', 'ask_price', 'tick_type']
        
        for c in cols:
            if c not in df.columns: df[c] = None
        
        # 建立連線
        local_conn = sqlite3.connect(db_path)
        
        # 寫入資料
        df[cols].to_sql("ticks", local_conn, if_exists="append", index=False)
        
        # 🔥【關鍵修正】顯式提交，確保資料落地 🔥
        local_conn.commit()
        
        # 關閉連線
        local_conn.close()
        
    except Exception as e:
        print(f"⚠️ 寫入 DB 失敗: {e}")

def process_single_event(stock_code, event_date_str, event_time_str):
    try:
        event_date_obj = datetime.strptime(event_date_str, '%Y-%m-%d')
    except:
        try:
            event_date_obj = datetime.strptime(event_date_str, '%Y/%m/%d')
        except:
            return

    event_id = f"{stock_code}_{event_date_obj.strftime('%Y%m%d')}"

    if event_id in existing_ids:
        return "SKIPPED"

    contract = api.Contracts.Stocks[str(stock_code)]
    if not contract: return "ERROR"

    print(f"🔄 正在抓取: {stock_code} ({event_date_str}) EventID: {event_id}")

    # === T=0 ===
    center_date = event_date_obj
    t0_df = None
    real_t0_date_obj = None
    
    for i in range(5):
        check_date = center_date + timedelta(days=i)
        d_str = check_date.strftime('%Y-%m-%d')
        df = get_ticks_df(contract, d_str)
        if df is not None:
            t0_df = df
            real_t0_date_obj = check_date
            save_to_db(df, event_id, stock_code, event_date_str, event_time_str, d_str, 0)
            break
    
    if t0_df is None:
        print(f"    放棄：找不到 T=0 交易日")
        return "FAILED"

    # === T-1 ~ T-2 (修正為抓2天) ===
    search_date = real_t0_date_obj - timedelta(days=1)
    found_count = 0
    while found_count < 2:
        if (real_t0_date_obj - search_date).days > 20: break
        d_str = search_date.strftime('%Y-%m-%d')
        df = get_ticks_df(contract, d_str)
        if df is not None:
            rel_day = -(found_count + 1)
            save_to_db(df, event_id, stock_code, event_date_str, event_time_str, d_str, rel_day)
            found_count += 1
        search_date -= timedelta(days=1)

    search_date = real_t0_date_obj + timedelta(days=1)
    found_count = 0
    while found_count < 2:
        if (search_date - real_t0_date_obj).days > 20: break
        d_str = search_date.strftime('%Y-%m-%d')
        df = get_ticks_df(contract, d_str)
        if df is not None:
            rel_day = (found_count + 1)
            save_to_db(df, event_id, stock_code, event_date_str, event_time_str, d_str, rel_day)
            found_count += 1
        search_date += timedelta(days=1)
    
    return "SUCCESS"

# ==========================================
# 5. 主執行邏輯
# ==========================================

def is_afternoon_session(time_val):
    try:
        t_str = str(time_val).strip()
        if ':' in t_str:
            parts = t_str.split(':')
            h, m = int(parts[0]), int(parts[1])
            return dt_time(h, m) >= dt_time(13, 30)
        return False
    except:
        return False

print("📂 讀取並篩選事件表...")
try:
    df_events = pd.read_csv(csv_path)
    df_events.columns = [c.strip() for c in df_events.columns]
    stock_col = 'StockCode' if 'StockCode' in df_events.columns else 'Code'
    mask = df_events['Time'].apply(is_afternoon_session)
    df_target = df_events[mask].copy()
    
    print(f"📊 待處理任務數: {len(df_target)}")
    
    processed_count = 0
    skipped_count = 0

    for idx, row in df_target.iterrows():
        code = str(row[stock_col]).replace('.0', '')
        e_date = str(row['Date'])
        e_time = str(row['Time'])
        
        try:
            status = process_single_event(code, e_date, e_time)
            
            if status == "SKIPPED":
                skipped_count += 1
                if skipped_count % 100 == 0: print(f"⏭️ 已跳過 {skipped_count} 筆...")
            elif status == "SUCCESS":
                processed_count += 1
                time.sleep(1.2) # 保持禮貌
                
        except InterruptedError:
            print("\n🚨🚨🚨 系統強制停止：流量已達上限 🚨🚨🚨")
            print("請更換帳號或等待下個月額度重置。")
            break 
            
        if processed_count > 0 and processed_count % 10 == 0:
            print(f"⚡ 進度更新：新抓取 {processed_count} 筆... (檢查流量中)")

except Exception as e:
    print(f"❌ 發生未預期錯誤: {e}")

finally:
    conn.close()
    api.logout()
    print(f"👋 任務結束。共跳過 {skipped_count} 筆，新抓取 {processed_count} 筆。")