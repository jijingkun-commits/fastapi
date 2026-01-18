# 图表绘制指南

> 本参考文档供 AI Agent 按需加载

## 支持的图表类型

### 数据可视化图表
| 类型 | 函数 | 适用场景 |
|------|------|----------|
| 折线图 | `plt.plot()` | 时间序列、趋势分析 |
| 柱状图 | `plt.bar()` | 分类比较 |
| 饼图 | `plt.pie()` | 比例展示 |
| 散点图 | `plt.scatter()` | 相关性分析 |
| 直方图 | `plt.hist()` | 分布分析 |

### 几何图形
| 类型 | 方法 | 示例 |
|------|------|------|
| 圆形 | `Circle()` | 绘制圆 |
| 矩形 | `Rectangle()` | 绘制矩形 |
| 多边形 | `Polygon()` | 绘制多边形 |

## 代码模板

### 折线图
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x_data, y_data, marker='o', label='数据')
ax.set_xlabel('X Axis')
ax.set_ylabel('Y Axis')
ax.set_title('Line Chart')
ax.legend()
ax.grid(True, alpha=0.3)
```

### 饼图
```python
fig, ax = plt.subplots(figsize=(8, 8))
ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
ax.set_title('Pie Chart')
```

### 圆形
```python
fig, ax = plt.subplots(figsize=(8, 8))
circle = plt.Circle((0.5, 0.5), 0.3, fill=False, color='blue', linewidth=2)
ax.add_patch(circle)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.set_title('Circle')
```

## 重要规则

1. **所有文本使用英文**（xlabel, ylabel, title, legend）
2. **使用 `fig` 作为图像对象变量名**
3. **设置合适的 figsize**，默认 (10, 6)
4. **添加 grid 提高可读性**
