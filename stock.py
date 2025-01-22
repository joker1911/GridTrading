#%%
from app import app, db
from models import InStock, TodayStock
from datetime import datetime

def buy(code, quantity, time, price, cash, ableSold):
    """记录买入操作"""
    with app.app_context():
        # 创建一个新的 InStock 实例
        in_stock = InStock(
            code=code,
            buyQuantity=quantity,
            buyPrice=price,
            buyDate=time,
            cash=cash,
            total=cash+(ableSold * price)+(quantity * price)
        )
        try:
            db.session.add(in_stock)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

def sell(code, quantity, time, price, cash, ableSold):
    """记录卖出操作"""
    with app.app_context():
        # 查询库存中是否有对应的股票
        in_stock = InStock(
            code=code,
            soldQuantity=quantity,
            sellPrice=price,
            sellDate=time,
            cash=cash + (quantity * price),
            total=cash + (ableSold * price)
        )


        try:
            db.session.add(in_stock)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False







# 示例：测试买入和卖出操作
if __name__ == "__main__":
    buy(code="AAPL", quantity=100, time=datetime.utcnow(), price=150.0, cash=10000, ableSold=100)
    sell(code="AAPL", quantity=50, time=datetime.utcnow(), price=160.0, cash=10000, ableSold=100)
