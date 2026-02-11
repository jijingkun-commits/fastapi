---
description: 🔒 安全审计：检查依赖漏洞、代码安全、敏感信息泄露
---

# 🔒 安全审计 (Security Audit)

全面的安全审查，识别并修复代码库中的安全漏洞。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 审计步骤

### 1. 依赖审计
```bash
# Python
pip-audit
safety check

# Node.js
npm audit
yarn audit
```

- 检查已知漏洞
- 更新过时的包
- 审查第三方依赖的安全性

### 2. 代码安全审查

#### 常见漏洞检查

| 漏洞类型 | 检查项 |
|----------|--------|
| **SQL 注入** | 是否使用参数化查询？ |
| **XSS** | 用户输入是否转义？ |
| **CSRF** | 是否有 CSRF token？ |
| **认证** | 密码是否加密存储？ |
| **授权** | 权限检查是否完整？ |
| **敏感数据** | 日志是否泄露敏感信息？ |

#### Python/FastAPI 检查点
```python
# ❌ SQL 注入风险
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全写法
query = select(User).where(User.id == user_id)

# ❌ 敏感信息泄露
logger.info(f"User login: {username}, password: {password}")

# ✅ 安全写法
logger.info(f"User login: {username}")
```

#### 前端检查点
```typescript
// ❌ XSS 风险
element.innerHTML = userInput;

// ✅ 安全写法
element.textContent = userInput;

// ❌ 敏感信息暴露
console.log('API Key:', process.env.API_KEY);
```

### 3. 环境与配置审计

- [ ] `.env` 文件已加入 `.gitignore`
- [ ] 无硬编码的密钥、密码
- [ ] 生产环境配置与开发环境分离
- [ ] API 密钥有适当的权限范围

### 4. 基础设施安全

- [ ] HTTPS 强制使用
- [ ] CORS 配置正确
- [ ] Rate limiting 已启用
- [ ] 错误信息不暴露内部细节

## 安全检查清单

### 认证与授权
- [ ] 密码使用 bcrypt/argon2 加密
- [ ] JWT 有过期时间
- [ ] 敏感操作有二次验证
- [ ] 权限检查在每个端点执行

### 数据保护
- [ ] 敏感数据传输加密
- [ ] 数据库连接使用 SSL
- [ ] 日志不包含敏感信息
- [ ] 备份数据已加密

### 输入验证
- [ ] 所有用户输入已验证
- [ ] 文件上传有类型和大小限制
- [ ] API 参数有 schema 验证

### 依赖管理
- [ ] 依赖版本已锁定
- [ ] 无已知漏洞的依赖
- [ ] 定期更新依赖

## 输出格式

```markdown
## 安全审计报告

### 发现的问题
1. **高风险**: [问题描述] - [位置]
2. **中风险**: [问题描述] - [位置]
3. **低风险**: [问题描述] - [位置]

### 修复建议
- [具体修复步骤]

### 通过的检查项
- [列出安全的部分]
```

---
*提示：使用 `/security-audit` 触发此工作流。建议在每次发布前执行。*
