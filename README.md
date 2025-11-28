# event_trade
以資訊指標預測法說會所帶來的超額報酬，以資訊指標作為濾網篩選交易標的

#文獻回顧
ongaerts, D., Rösch, D., & van Dijk, M. (2025). Cross-Sectional Identification of Private Information. The Review of Asset Pricing Studies, raaf010.

作者以內部人交易與併購作為事件日，發現OIB*Lambda確實能捕捉到informed trading，且相較於過去傳統PIN、ITI等資訊指標更好計算

#策略發想
以法說會為事件日，並假設在法說會前已有 informed trader 知道法說會是否符合市場預期，提前布局。

根據 ongaerts, D., Rösch, D., & van Dijk, M. (2025) 的研究，OIB*Lambda為資訊指標是否能在法說會前預測法說會帶來的超額報酬？先知道法說會是好or法會？

#DATA與指標

1.投資標的：台灣上市公司

2.法說會日期參考：公開資訊觀測站

3.daily data：TEJ PRO ➞ 計算異常報酬率

4.tick data：永豐API ➞ 計算資訊指標及實際回測

5.日期：2021/01/01～2025/06/30

6.本金：單日交易皆投入 $1,000,000

7.成本：0.1425%  (buy)、0.4425% (sell)

![result](https://meee.com.tw/um4mnky)

#回歸檢定

![result](https://meee.com.tw/hqBDCPU)

![result](https://meee.com.tw/hwJ8mAk)

![result](https://meee.com.tw/yQhY8wd)

![result](https://meee.com.tw/v7ufdNd)

#因子檢定－五爪圖分析

(1) t-1 _11:00～11:30的資訊指標 < 0 (不是指沒資訊，而是指賣壓強且價格衝擊力大）並根據t= 0當日 9:00～9:30資訊指標(all sample)分五組

(2) 累積CAR：假設每一筆交易總報酬率為CAR[0,+2]，逐筆累積

![result](https://meee.com.tw/DHVLLdC)

#簡單回測
法說會公告規定：至遲應於召開日前一日或參加日前一日公告其時間、地點

以下回測皆使用tick data

回測日期：2021/01/01～2021/12/31

每一天資金投入：$1,000,000，若當天有數檔股票交易則以等權方式分配資金

#交易邏輯

(1) 第一層濾網：每天收盤回測隔天要開法說會的股票，篩選其當日11:00~11:30資訊指標 < 0的股票作為隔天(t =0)的觀察股票

(2) 第二層濾網：法說會當日（t = 0）9:30:00~9:34:59抓股池內的tick data，並計算9:00:00～9:30:00的資訊指標，根據前面研究，選擇9:00指標最高的兩檔進行交易（不為負），若當天9:00指標皆為負則不交易（０<= x <=2）

(3) 進場時間與價格：t=0的9:35:00～9:35:59進場，以這段區間的平均成交價作為進場價

(4) 出場時間與價格：t+2(交易日)的10:00:00～10:00:59出場，以這段區間的平均成交價作為出場價








