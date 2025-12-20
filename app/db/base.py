"""声明式基类：供所有ORM模型继承（中文注释）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有模型的基类。"""
    pass
