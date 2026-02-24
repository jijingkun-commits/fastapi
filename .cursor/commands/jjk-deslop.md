---
description: 🧹 清理 AI 代码冗余：移除 AI 生成的多余注释、防御性代码和类型转换
---

# 🧹 清理 AI 代码冗余 (Deslop)

检查当前分支与 main 的差异，清理 AI 生成的冗余代码。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 清理目标

### 1. 多余的注释
```python
# ❌ AI 常添加的冗余注释
def get_user(user_id: int):
    # Get user by ID  <- 多余，函数名已说明
    # This function retrieves a user from the database  <- 过于啰嗦
    return db.query(User).filter(User.id == user_id).first()

# ✅ 清理后
def get_user(user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

### 2. 过度防御性代码
```python
# ❌ 在已验证的代码路径中添加不必要的检查
async def process_message(message: Message):
    if message is None:  # <- 上游已保证非空
        raise ValueError("Message cannot be None")
    if not isinstance(message, Message):  # <- 类型系统已保证
        raise TypeError("Expected Message type")
    ...

# ✅ 清理后（信任上游验证）
async def process_message(message: Message):
    ...
```

### 3. 滥用 try/catch
```python
# ❌ 不必要的异常捕获
try:
    result = 1 + 1  # <- 这不会抛异常
except Exception as e:
    logger.error(f"Error: {e}")
    raise

# ✅ 清理后
result = 1 + 1
```

### 4. TypeScript 中的 `any` 类型
```typescript
// ❌ 用 any 绕过类型问题
const data = response.data as any;
const result = (something as any).method();

// ✅ 正确处理类型
const data: ResponseType = response.data;
const result = (something as SomeInterface).method();
```

### 5. 风格不一致
- 命名风格与文件其他部分不一致
- 缩进或格式与项目规范不符
- 导入顺序混乱

## 执行步骤

1. **获取差异**
```bash
git diff main...HEAD
```

2. **逐文件审查**
   - 对比 AI 修改前后的代码
   - 识别上述冗余模式

3. **清理并报告**
   - 删除冗余代码
   - 保持功能不变
   - 最后用 1-3 句话总结清理内容

## 示例输出

> **清理报告**：
> 移除了 `chat_service.py` 中 3 处冗余注释和 1 处不必要的 None 检查；
> 修正了 `api.ts` 中 2 处 `as any` 类型转换为正确类型。

---
*提示：使用 `/jjk-deslop` 触发此工作流。在代码审查前运行可提高代码质量。*
