---
description: ⚡ 性能优化：分析瓶颈、优化算法、提升响应速度
---

# ⚡ 性能优化 (Optimize)

分析代码性能瓶颈，提供优化建议和实现。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 分析步骤

### 1. 性能分析

#### 识别常见问题
| 问题类型 | 表现 | 检查方法 |
|----------|------|----------|
| **N+1 查询** | 循环中执行数据库查询 | 检查 for 循环内的 DB 操作 |
| **内存泄漏** | 内存持续增长 | 检查未释放的资源 |
| **算法复杂度** | 大数据量时变慢 | 分析时间/空间复杂度 |
| **阻塞操作** | 响应延迟 | 检查同步 I/O 操作 |

#### Python 性能分析工具
```python
# 使用 cProfile
import cProfile
cProfile.run('your_function()')

# 使用 line_profiler
@profile
def slow_function():
    ...

# 使用 memory_profiler
@profile
def memory_hungry_function():
    ...
```

### 2. 优化策略

#### 数据库优化
```python
# ❌ N+1 查询
users = db.query(User).all()
for user in users:
    print(user.orders)  # 每次循环都查询

# ✅ 使用 joinedload
from sqlalchemy.orm import joinedload
users = db.query(User).options(joinedload(User.orders)).all()
for user in users:
    print(user.orders)  # 已预加载

# ✅ 使用 selectinload（多对多关系）
users = db.query(User).options(selectinload(User.roles)).all()
```

#### 缓存策略
```python
from functools import lru_cache
from cachetools import TTLCache

# 简单缓存
@lru_cache(maxsize=100)
def expensive_calculation(n):
    return sum(i ** 2 for i in range(n))

# 带过期时间的缓存
cache = TTLCache(maxsize=100, ttl=300)  # 5分钟过期

def get_user_data(user_id):
    if user_id in cache:
        return cache[user_id]
    data = fetch_from_db(user_id)
    cache[user_id] = data
    return data
```

#### 异步优化
```python
# ❌ 串行请求
results = []
for url in urls:
    result = await fetch(url)
    results.append(result)

# ✅ 并行请求
import asyncio
results = await asyncio.gather(*[fetch(url) for url in urls])
```

#### 分页和懒加载
```python
# ❌ 一次加载全部
all_items = db.query(Item).all()

# ✅ 分页加载
def get_items(page: int, page_size: int = 20):
    return db.query(Item).offset((page - 1) * page_size).limit(page_size).all()

# ✅ 流式处理大数据
def process_large_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:  # 逐行读取，不一次性加载
            yield process_line(line)
```

### 3. 前端优化

```typescript
// ❌ 不必要的重渲染
const Component = ({ data }) => {
  const processed = expensiveProcess(data);  // 每次渲染都计算
  return <div>{processed}</div>;
};

// ✅ 使用 useMemo
const Component = ({ data }) => {
  const processed = useMemo(() => expensiveProcess(data), [data]);
  return <div>{processed}</div>;
};

// ✅ 虚拟列表（大量数据）
import { FixedSizeList } from 'react-window';

const VirtualList = ({ items }) => (
  <FixedSizeList
    height={400}
    itemCount={items.length}
    itemSize={50}
  >
    {({ index, style }) => (
      <div style={style}>{items[index]}</div>
    )}
  </FixedSizeList>
);
```

## 优化检查清单

### 数据库
- [ ] 消除 N+1 查询
- [ ] 添加必要的索引
- [ ] 使用分页查询
- [ ] 优化复杂 SQL

### 缓存
- [ ] 热点数据已缓存
- [ ] 缓存有合理的过期策略
- [ ] 缓存穿透/雪崩已处理

### 算法
- [ ] 使用合适的数据结构
- [ ] 时间复杂度可接受
- [ ] 避免重复计算

### I/O
- [ ] 使用异步操作
- [ ] 批量处理代替循环
- [ ] 大文件流式处理

## 输出格式

```markdown
## 性能优化报告

### 发现的瓶颈
1. [位置] - [问题描述] - 预估影响

### 优化方案
1. [优化描述]
   - Before: [原代码/性能]
   - After: [优化后/预期提升]

### 性能对比
| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 响应时间 | 500ms | 50ms | 90% |
```

---
*提示：使用 `/optimize` 触发此工作流。可指定特定函数或模块进行分析。*
