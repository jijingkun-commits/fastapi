# SQL 查询指南

> 本参考文档供 AI Agent 按需加载，遵循渐进披露原则

## 可用表结构

### t_user (用户表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| username | VARCHAR | 用户名 |
| email | VARCHAR | 邮箱 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### t_todo (待办表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| title | VARCHAR | 标题 |
| description | TEXT | 描述 |
| priority | INT | 优先级 (1-5) |
| status | VARCHAR | 状态 |
| due_date | DATETIME | 截止时间 |

## 常用查询模式

### 分页查询
```sql
SELECT * FROM t_user LIMIT 10 OFFSET 0;
```

### 聚合统计
```sql
SELECT status, COUNT(*) as count 
FROM t_todo 
GROUP BY status;
```

### 日期过滤
```sql
SELECT * FROM t_todo 
WHERE due_date BETWEEN '2026-01-01' AND '2026-01-31';
```

## 安全约束

⚠️ **禁止操作**：
- `DROP TABLE` - 删除表
- `DELETE FROM` (无 WHERE) - 全表删除
- `UPDATE` (无 WHERE) - 全表更新
- `TRUNCATE` - 清空表

✅ **推荐做法**：
- 始终使用 `LIMIT` 限制结果数量
- 复杂查询先用 `EXPLAIN` 分析
