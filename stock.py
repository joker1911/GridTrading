from app import db
from app import TodayStock



def sell(code, quantity, time):
    tStock = db.session.query(TodayStock).filter_by(code=code).filter_by(time=time).first()
    if tStock:
        if tStock.quantity >= quantity:
            tStock.quantity -= quantity
            db.session.commit()
        else:
            return False
    else:
        return False


def buy(code, quantity, time):
    tStock = db.session.query(TodayStock).filter_by(code=code).filter_by(time=time).first()
    if tStock:
        tStock.quantity += quantity
        db.session.commit()
        return True
    else:
        tStock = TodayStock(code=code, time=time, quantity=quantity)
        db.session.add(tStock)
        db.session.commit()
        return True