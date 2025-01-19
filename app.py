#%%

import os
import sys

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from flask_sqlalchemy import SQLAlchemy  # 导入扩展类

app = Flask(__name__)
# 配置MySQL数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@127.0.0.1:3306/stock'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控


# 定义模型类

db = SQLAlchemy(app)
class InStock(db.Model):  # 表名将会是 user（自动生成，小写处理）
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(20), nullable=False)  # 名字
    code = db.Column(db.String(20), nullable=False)
    buyPrice = db.Column(db.Float, nullable=False)
    sellPrice = db.Column(db.Float, nullable=False)
    buyDate = db.Column(db.DateTime)
    sellDate = db.Column(db.DateTime)
    buyQuantity = db.Column(db.Float, nullable=False)
    soldQuantity = db.Column(db.Float, nullable=False)



class TodayStock(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(20), index=True, nullable=False)
    code = db.Column(db.String(20), index=True, nullable=False)
    date = db.Column(db.DateTime)
    ableToSellQuantity = db.Column(db.Float, nullable=False)
    soldQuantity = db.Column(db.Float, nullable=False)
    relateInStockId = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Float, nullable=False)


import click



@app.cli.command()  # 注册为命令，可以传入 name 参数来自定义命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息
