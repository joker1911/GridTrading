#%%
import pandas as pd

def grid_trading(data, total_amount, buy_decrease_percent, sell_increase_percent, buy_amount_limit, sell_amount_limit, daily_increase_percent, session_increase_percent, maxDayUse):
    """
    网格交易策略函数

    :param data: 交易数据，DataFrame格式，包含date, time, code, open, high, low, close, volume, amount, adjustflag列
    :param total_amount: 总金额，单位：人民币元
    :param buy_decrease_percent: 降价百分比，用于决定买入时机，例如0.05表示降价5%
    :param sell_increase_percent: 涨价百分比，用于决定卖出时机，例如0.05表示涨价5%
    :param buy_amount_limit: 每次买入的最大金额限制
    :param sell_amount_limit: 每次卖出的最大金额限制
    :param daily_increase_percent: 当日增幅低于设定比例，买入
    :param session_increase_percent: 当日增幅超过设定比例，卖出
    :return: 总收益
    """
    # 初始化变量
    cash = total_amount  # 现金
    positions = {}  # 持仓，格式为 {code: (数量, 成本价, 买入时间)}
    last_prices = {}  # 上一交易日的收盘价，格式为 {code: 收盘价}
    session_prices = {}  # 本次交易的开盘价，格式为 {code: 开盘价}

    data['datetime'] = pd.to_datetime((data['time'].astype(str).str[:12]), format='%Y%m%d%H%M')
    data['close'] = data['close']/10000
    data['open'] = data['open']/10000
    data.sort_values(by='datetime', inplace=True)  # 确保数据按时间排序

    date = data['date'][0]

    openDaily = data['open'][0]
    ableSold = 0

    percent = 0

    print(openDaily)

    todayUse = 0
    todayGet = 0

    # 遍历每五分钟的交易数据
    for index, row in data.iterrows():
        code = row['code']
        open_price = row['open']
        close = row['close']
        datetime = row['datetime']


        # 如果是第一天，初始化last_prices和session_prices
        if code not in last_prices:
            last_prices[code] = close
            session_prices[code] = open_price
            continue

        # 计算降价和涨价的阈值
        buy_threshold = last_prices[code] * (1 + buy_decrease_percent)
        sell_threshold = last_prices[code] * (1 + sell_increase_percent)

        # 计算当日增幅和本次涨幅
        daily_increase = (close - openDaily) / openDaily
        session_increase = (close - session_prices[code]) / session_prices[code]
        percent += session_increase

        # print(f"现金：{cash}; ", end='')
        # print(f"目前价格：{close}; ", end='')
        # print(f"买入价格：{buy_threshold}; ", end='')
        # print(f"卖出价格：{sell_threshold}; ", end='')
        # print(f"当日增幅：{daily_increase:.4f}; ", end='')
        # print(f"本次涨幅：{session_increase:.4f}; ")

        # 检查是否满足买入条件
        if (close <= buy_threshold or daily_increase < daily_increase_percent)and cash > 0 and maxDayUse > todayUse:
            # print(daily_increase < daily_increase_percent)
            # print(f"满足买入条件 {daily_increase_percent} > {daily_increase} openDa: {openDaily}")
            # print(close <= buy_threshold)
            # print(f"or {close}  <= {buy_threshold}  ")
            #
            # print()
            # print()
            # print()
            # print()
            # 确保每次买入的金额不超过buy_amount_limit
            buy_amount = min(cash, buy_amount_limit)  # 每次买入的最大金额限制
            buy_quantity = buy_amount // close  # 使用close作为买入价格计算买入数量
            if buy_quantity > 0:
                # 更新现金和持仓
                cash -= buy_quantity * close
                if code in positions:
                    old_quantity, old_cost, old_buy_time = positions[code]
                    new_cost = (old_cost * old_quantity + buy_quantity * close) / (old_quantity + buy_quantity)
                    positions[code] = (old_quantity + buy_quantity, new_cost, datetime)
                    todayUse += buy_quantity * close
                    # print("买入")
                else:
                    positions[code] = (buy_quantity, close, datetime)

        # 检查是否满足卖出条件
        if ableSold > 0:
            # print(f"{close} > {sell_threshold}", end="   ")
            # print(close >= sell_threshold)
            # 确保在T+1日才能卖出
            if close >= sell_threshold or daily_increase >= session_increase_percent:
                # print("符合卖出条件")
                # 确保每次卖出的金额不超过sell_amount_limit
                sell_amount = min(ableSold, sell_amount_limit/close)  # 每次卖出的最大金额限制
                sell_quantity_to_sell = sell_amount // close  # 计算需要卖出的股票数量
                if sell_quantity_to_sell > 0 and ableSold - sell_quantity_to_sell > 0:
                    # 更新现金和持仓
                    cash += sell_quantity_to_sell * close
                    todayGet += sell_quantity_to_sell * close
                    ableSold -= sell_quantity_to_sell

                    # print("卖出")

        # 更新上一交易日的收盘价和本次交易的开盘价
        last_prices[code] = close
        if row['date'] != date:
            print(f"{date}今日 {ableSold * row['close'] + cash}; 本次涨幅 {session_increase}")
            # if todayUse != 0:
            #     print(f"今日使用{todayUse}; ", end='')
            # if todayGet != 0:
            #     print(f"今日卖出{todayGet}; ", end='')
            # if todayUse != 0 or todayGet != 0:
            #     print()
            ableSold += todayUse
            openDaily = row['close']
            todayUse = 0
            todayGet = 0
            date = row['date']
        session_prices[code] = row['close']

    # 计算最终的总收益
    total_value = cash
    for code, (quantity, cost, buy_time) in positions.items():
        total_value += quantity * data[data['code'] == code]['close'].iloc[-1]

    total_profit = total_value - total_amount
    print(f"\n最终总收益：{total_profit} 元")
    print(f"\n最终现金：{cash} 元")
    return total_profit


# 调用函数
#%%
# data = pd.read_csv("D:/sz.399310(2023-01-01^2024-12-31).csv")
data = pd.read_csv("D:/history_A_stock_k_data.csv")

total_amount = 10000  # 总金额
buy_decrease_percent = -0.01  # 降价2%
sell_increase_percent = 0.01  # 涨价2%
maxDayUse = 500
total_profit = grid_trading(data, total_amount, buy_decrease_percent, sell_increase_percent, 1000, 1000, buy_decrease_percent, sell_increase_percent, maxDayUse)
print(total_profit / total_amount)