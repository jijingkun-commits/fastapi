---
description: ♻️ 代码重构：提升代码质量、可读性和性能
---

# ♻️ 代码重构 (Refactor)

重构选中的代码，在保持功能不变的前提下提升质量。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 重构维度

### 1. 代码质量改进

| 问题 | 解决方案 |
|------|----------|
| **重复代码** | 提取公共函数/组件 |
| **过长函数** | 拆分为多个小函数 |
| **过深嵌套** | 使用 early return、guard clause |
| **命名不清** | 使用描述性命名 |
| **魔法数字** | 提取为常量 |

### 2. 代码示例

#### Before: 过深嵌套
```python
def process_order(order):
    if order:
        if order.is_valid:
            if order.items:
                for item in order.items:
                    if item.in_stock:
                        # 处理逻辑
                        pass
```

#### After: Guard Clause
```python
def process_order(order):
    if not order or not order.is_valid:
        return
    
    if not order.items:
        return
    
    for item in order.items:
        if not item.in_stock:
            continue
        # 处理逻辑
```

#### Before: 重复代码
```python
def get_user_info(user_id):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

def get_user_orders(user_id):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user.orders
```

#### After: 提取公共逻辑
```python
def _get_user_or_404(user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

def get_user_info(user_id):
    return _get_user_or_404(user_id)

def get_user_orders(user_id):
    return _get_user_or_404(user_id).orders
```

### 3. 性能优化

- 识别 N+1 查询问题
- 使用适当的数据结构
- 减少不必要的计算
- 添加缓存（如适用）

### 4. 设计原则

| 原则 | 说明 |
|------|------|
| **SRP** | 单一职责：一个类/函数只做一件事 |
| **OCP** | 开闭原则：对扩展开放，对修改关闭 |
| **DRY** | 不重复自己 |
| **KISS** | 保持简单 |

## 重构检查清单

### 代码结构
- [ ] 提取了可复用的函数/组件
- [ ] 消除了代码重复
- [ ] 改进了变量和函数命名
- [ ] 简化了复杂逻辑和嵌套

### 性能
- [ ] 识别并修复了性能瓶颈
- [ ] 优化了算法和数据结构
- [ ] 减少了不必要的计算

### 可维护性
- [ ] 代码更加自文档化
- [ ] 遵循了 SOLID 原则
- [ ] 改进了错误处理和边界情况

## 输出格式

```markdown
## 重构报告

### 改进项
1. [改进描述] - [影响范围]

### 变更说明
- Before: [原代码问题]
- After: [改进后的优点]

### 未处理项（如有）
- [原因说明]
```

---
*提示：使用 `/jjk-refactor` 触发此工作流。可以选中特定代码后执行。*
