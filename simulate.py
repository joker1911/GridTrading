#%%
import pandas as pd
from stock import sell, buy


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
    data['close'] = data['close']
    data['open'] = data['open']
    data.sort_values(by='datetime', inplace=True)  # 确保数据按时间排序

    date = data['date'][0]

    openDaily = data['open'][0]
    ableSold = 0

    percent = 0


    todayUse = 0
    todayGet = 0
    todayBuyQuantity = 0

    cost = 0

    # 遍历每五分钟的交易数据
    for index, row in data.iterrows():
        code = row['code']
        open_price = row['open']
        close = row['close']
        datetime = row['datetime']

        if row['date'] != date:
            # print(f"{date}今日 {ableSold * row['close'] + cash}; 本次涨幅 {session_increase}")
            # if todayUse != 0:
            #     print(f"今日使用{todayUse}; ", end='')
            # if todayGet != 0:
            #     print(f"今日卖出{todayGet}; ", end='')
            # if todayUse != 0 or todayGet != 0:
            #     print()
            ableSold += todayBuyQuantity
            openDaily = row['close']
            todayUse = 0
            todayGet = 0
            todayBuyQuantity = 0
            date = row['date']



        # 如果是第一天，初始化last_prices和session_prices
        if code not in last_prices:
            last_prices[code] = close
            session_prices[code] = open_price
            continue

        # 计算降价和涨价的阈值
        buy_threshold = last_prices[code] * (1 + buy_decrease_percent)
        sell_threshold = last_prices[code] * (1 + sell_increase_percent)

        # 计算当日增幅和本次涨幅
        daily_increase = (close - openDaily) / openDaily * 100
        session_increase = (close - session_prices[code]) / session_prices[code] * 100
        percent += session_increase

        # print(f"现金：{cash}; ", end='')
        # print(f"目前价格：{close}; ", end='')
        # print(f"买入价格：{buy_threshold}; ", end='')
        # print(f"卖出价格：{sell_threshold}; ", end='')
        # print(f"当日增幅：{daily_increase:.4f}; ", end='')
        # print(f"本次涨幅：{session_increase:.4f}; ")

        if (ableSold + todayBuyQuantity) > 0:
            cost = (total_amount - cash) / (ableSold + todayBuyQuantity)

        current_flow = 0
        if cost != 0:
            current_flow = (close - cost) / cost * 100

        print(f"成本: {cost:.4f},  售价: {close:.4f}  当前流动：{current_flow:.4f}")



        # 检查是否满足买入条件
        if (current_flow < daily_increase_percent)and cash > 0 and maxDayUse > todayUse:
            # print(daily_increase < daily_increase_percent)
            # print(f"满足买入条件 {daily_increase_percent} > {daily_increase} openDa: {openDaily}")
            # print(close <= buy_threshold)
            # print(f"or {close}  <= {buy_threshold}  ")

            # 确保每次买入的金额不超过buy_amount_limit
            buy_amount = min(cash, buy_amount_limit)  # 每次买入的最大金额限制
            buy_quantity = buy_amount // close  # 使用close作为买入价格计算买入数量
            if buy_quantity > 0:
                # 更新现金和持仓
                print(f"买入{buy_quantity}股")
                cash -= buy_quantity * close
                cash -= buy_quantity * close * 0.0085
                todayUse += buy_quantity * close
                todayBuyQuantity += buy_quantity
                buy(code, buy_quantity, row['datetime'], close, cash, ableSold)
                if code in positions:
                    old_quantity, old_cost, old_buy_time = positions[code]
                    new_cost = (old_cost * old_quantity + buy_quantity * close) / (old_quantity + buy_quantity)
                    positions[code] = (old_quantity + buy_quantity, new_cost, datetime)
                else:
                    positions[code] = (buy_quantity, close, datetime)

        # 检查是否满足卖出条件
        if ableSold > 0:
            # print(f"{close} > {sell_threshold}", end="   ")
            # print(close >= sell_threshold)
            # 确保在T+1日才能卖出
            if current_flow >= sell_increase_percent or current_flow >= sell_increase_percent:
                # print("符合卖出条件")
                # 确保每次卖出的金额不超过sell_amount_limit
                sell_amount = min(ableSold, sell_amount_limit/close)  # 每次卖出的最大金额限制
                sell_quantity_to_sell = sell_amount // close  # 计算需要卖出的股票数量
                if sell_quantity_to_sell > 0 and ableSold - sell_quantity_to_sell > 0:
                    # 更新现金和持仓
                    cash += sell_quantity_to_sell * close
                    todayGet += sell_quantity_to_sell * close
                    ableSold -= sell_quantity_to_sell
                    cash -= sell_quantity_to_sell * close*0.0085

                    sell(code, sell_quantity_to_sell, row['datetime'], close, cash, ableSold)
                    # print("卖出")

        # 更新上一交易日的收盘价和本次交易的开盘价
        last_prices[code] = close

        session_prices[code] = row['close']

    # 计算最终的总收益
    total_value = cash + ((todayBuyQuantity + ableSold) * row['close'])

    total_profit = total_value - total_amount
    print(f"\n最终总收益：{total_profit} 元")
    # print(f"\n最终现金：{cash} 元")
    return total_profit

#%%
# 调用函数

# data = pd.read_csv("D:/sz.399310(2023-01-01^2024-12-31).csv")
# data = pd.read_csv("D:/sz.002031.csv")
data = pd.read_csv("D:/sz.399310.csv")

total_amount = 10000  # 总金额
buy_decrease_percent = -0.05  # 降价2%
sell_increase_percent = 0.01  # 涨价2%

buy_amount_limit = 1000
sell_amount_limit = 1000
maxDayUse = 100
print(f"{data["date"][0]} ---  {data['date'][data['date'].size - 1]}   ")
print(f"本金为：{total_amount}", end="")
data['close'] = data['close'] / 10000
data['open'] = data['open'] / 10000
total_profit = grid_trading(data, total_amount, buy_decrease_percent, sell_increase_percent, buy_amount_limit, sell_amount_limit, buy_decrease_percent, sell_increase_percent, maxDayUse)


print("收益率为 ", end="")

print(total_profit / total_amount * 100, end="%")
#%%
data['open']