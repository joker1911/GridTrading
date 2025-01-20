import pandas as pd
import logging

def grid_trading(data, total_amount, buy_decrease_percent, sell_increase_percent, buy_amount_limit, sell_amount_limit, daily_increase_percent, session_increase_percent, maxDayUse, transaction_fee=0.0085):
    """
    网格交易策略函数

    :param data: 交易数据，DataFrame格式，包含date, time, code, open, high, low, close, volume, amount, adjustflag列
    :param total_amount: 总金额，单位：人民币元
    :param buy_decrease_percent: 降价百分比，用于决定买入时机，例如-0.01表示降价1%
    :param sell_increase_percent: 涨价百分比，用于决定卖出时机，例如0.01表示涨价1%
    :param buy_amount_limit: 每次买入的最大金额限制
    :param sell_amount_limit: 每次卖出的最大金额限制
    :param daily_increase_percent: 当日增幅低于设定比例，买入
    :param session_increase_percent: 当日增幅超过设定比例，卖出
    :param maxDayUse: 每日最大使用金额
    :param transaction_fee: 交易手续费比例
    :return: 总收益
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 初始化变量
    cash = total_amount  # 现金
    positions = {}  # 持仓，格式为 {code: (数量, 成本价, 买入时间)}
    last_prices = {}  # 上一交易日的收盘价，格式为 {code: 收盘价}
    session_prices = {}  # 本次交易的开盘价，格式为 {code: 开盘价}

    # 数据预处理
    data['datetime'] = pd.to_datetime(data['time'].astype(str).str[:12], format='%Y%m%d%H%M')
    data['close'] = data['close'] / 10000
    data['open'] = data['open'] / 10000
    data.sort_values(by='datetime', inplace=True)  # 确保数据按时间排序

    date = data['date'].iloc[0]
    openDaily = data['open'].iloc[0]
    ableSold = 0
    todayUse = 0
    todayGet = 0
    todayBuyQuantity = 0

    # 遍历每五分钟的交易数据
    for index, row in data.iterrows():
        code = row['code']
        open_price = row['open']
        close = row['close']
        datetime = row['datetime']

        # 每日结束时的逻辑
        if row['date'] != date:
            ableSold += todayBuyQuantity  # 将当天买入的股票加入可卖出数量
            todayBuyQuantity = 0  # 重置当天买入数量
            openDaily = row['close']
            todayUse = 0
            todayGet = 0
            date = row['date']

        # 初始化 last_prices 和 session_prices
        if code not in last_prices:
            last_prices[code] = close
            session_prices[code] = open_price
            continue

        # 计算买入和卖出阈值
        buy_threshold = last_prices[code] * (1 + buy_decrease_percent)
        sell_threshold = last_prices[code] * (1 + sell_increase_percent)

        # 计算当日增幅和本次涨幅
        daily_increase = (close - openDaily) / openDaily
        session_increase = (close - session_prices[code]) / session_prices[code]

        # 检查是否满足买入条件
        if (close <= buy_threshold or daily_increase < daily_increase_percent) and cash > 0 and todayUse < maxDayUse:
            buy_amount = min(cash, buy_amount_limit)  # 每次买入的最大金额限制
            buy_quantity = buy_amount // close  # 计算买入数量
            if buy_quantity > 0:
                cash -= buy_quantity * close * (1 + transaction_fee)
                todayUse += buy_quantity * close
                todayBuyQuantity += buy_quantity

                if code in positions:
                    old_quantity, old_cost, old_buy_time = positions[code]
                    new_cost = (old_cost * old_quantity + buy_quantity * close) / (old_quantity + buy_quantity)
                    positions[code] = (old_quantity + buy_quantity, new_cost, datetime)
                else:
                    positions[code] = (buy_quantity, close, datetime)
                logging.info(f"买入 {buy_quantity} 股 {code}，价格 {close}，花费 {buy_quantity * close}")

        # 检查是否满足卖出条件
        if ableSold > 0 and (close >= sell_threshold or daily_increase >= session_increase_percent):
            sell_quantity_to_sell = min(ableSold, int(sell_amount_limit / close))
            if sell_quantity_to_sell > 0:
                cash += sell_quantity_to_sell * close * (1 - transaction_fee)
                todayGet += sell_quantity_to_sell * close
                ableSold -= sell_quantity_to_sell
                logging.info(f"卖出 {sell_quantity_to_sell} 股 {code}，价格 {close}，收入 {sell_quantity_to_sell * close}")

        # 更新上一交易日的收盘价和本次交易的开盘价
        last_prices[code] = close
        session_prices[code] = row['close']

    # 计算最终的总收益
    total_value = cash
    for code, (quantity, cost, buy_time) in positions.items():
        if code in data['code'].values:
            total_value += quantity * data[data['code'] == code]['close'].iloc[-1]

    total_profit = total_value - total_amount
    logging.info(f"最终总收益：{total_profit} 元")
    return total_profit

# 调用函数
#%%
# data = pd.read_csv("D:/sz.399310(2023-01-01^2024-12-31).csv")
data = pd.read_csv("D:/history_A_stock_k_data.csv")

total_amount = 1000  # 总金额
buy_decrease_percent = -0.01  # 降价2%
sell_increase_percent = 0.01  # 涨价2%
maxDayUse = 50
print(f"{data["date"][0]} ---  {data['date'][data['date'].size - 1]}   ")
print(f"本金为：{total_amount}", end="")
total_profit = grid_trading(data, total_amount, buy_decrease_percent, sell_increase_percent, 1000, 1000, buy_decrease_percent, sell_increase_percent, maxDayUse, 0.0085)


print("收益率为 ", end="")

print(total_profit / total_amount * 100, end="%")
