# 认证 API

用户登录和认证相关接口。

## 登录

### POST /api/v1/auth/login

用户登录获取 Token。

**请求体**:

```json
{
  "username": "admin",
  "password": "secret"
}
```

**响应**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误码**:

| 状态码 | 说明 |
|--------|------|
| 401 | 用户名或密码错误 |

---

## 获取当前用户

### GET /api/v1/auth/me

获取当前登录用户信息。

**请求头**:

```
Authorization: Bearer <token>
```

**响应**:

```json
{
  "id": 1,
  "username": "admin",
  "mobile": null
}
```
