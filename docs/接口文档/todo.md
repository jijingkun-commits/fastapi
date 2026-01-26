# 待办 API

待办事项管理接口。

## 获取待办列表

### GET /api/v1/todo

获取当前用户的待办列表。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 状态过滤: todo/in_progress/done/cancelled |

**响应**:

```json
[
  {
    "id": 1,
    "title": "开会",
    "description": "项目周会",
    "status": "todo",
    "priority": 2,
    "category": "工作",
    "due_date": "2024-01-15T14:00:00",
    "progress": 0,
    "created_at": "2024-01-10T10:00:00"
  }
]
```

---

## 获取待办详情

### GET /api/v1/todo/{todo_id}

获取单个待办详情。

**响应**:

```json
{
  "id": 1,
  "title": "开会",
  "description": "项目周会",
  "status": "todo",
  "priority": 2,
  "category": "工作",
  "tags": ["重要"],
  "due_date": "2024-01-15T14:00:00",
  "start_time": null,
  "completed_at": null,
  "progress": 0,
  "progress_notes": null,
  "is_recurring": false,
  "recurrence_pattern": null,
  "created_at": "2024-01-10T10:00:00",
  "updated_at": "2024-01-10T10:00:00"
}
```

---

## 更新待办

### PUT /api/v1/todo/{todo_id}

更新待办事项（支持部分更新）。

**请求体**:

```json
{
  "title": "新标题",
  "status": "in_progress",
  "progress": 50
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | string | 标题 |
| `description` | string | 描述 |
| `status` | string | 状态 |
| `priority` | int | 优先级 (1=高, 2=中, 3=低) |
| `due_date` | string | 截止时间 (ISO 8601) |
| `progress` | int | 进度 (0-100) |
| `category` | string | 分类 |
| `tags` | array | 标签列表 |

---

## 完成待办

### POST /api/v1/todo/{todo_id}/complete

标记待办为已完成。

**响应**:

```json
{
  "message": "待办已完成",
  "todo_id": 1
}
```

---

## 删除待办

### DELETE /api/v1/todo/{todo_id}

删除待办事项（软删除）。

**响应**:

```json
{
  "message": "待办已删除",
  "todo_id": 1
}
```

---

## 设置重复任务

### POST /api/v1/todo/{todo_id}/recurring

设置待办为重复任务。

**请求体**:

```json
{
  "pattern": "weekly",
  "interval": 1,
  "days": [1, 3, 5],
  "end_date": "2024-12-31T00:00:00"
}
```

| pattern | 说明 |
|---------|------|
| `daily` | 每天 |
| `weekly` | 每周 |
| `monthly` | 每月 |

---

## 取消重复

### DELETE /api/v1/todo/{todo_id}/recurring

取消待办的重复设置。

---

## 跳过一次

### POST /api/v1/todo/{todo_id}/skip

跳过一次重复任务实例。

---

## 生成未来任务

### POST /api/v1/todo/generate-upcoming

批量生成未来 N 天的重复任务实例。

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `days` | int | 7 | 生成天数 |
