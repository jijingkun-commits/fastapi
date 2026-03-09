# 前端性能优化方案

> 更新时间：2026-03-09
> 状态：待执行
> 目标：减少首屏加载时间 50%，优化手机端体验

## 问题诊断

### 当前状态
- 构建产物总大小：695MB
- ChatContainer chunk：16MB（未压缩）
- main-app.js：7MB
- react-vega 图表库：6.5MB
- 手机端加载慢，白屏时间长

### 根本原因
1. **重依赖未按需加载**：react-vega、katex、react-markdown 等在首屏就加载
2. **代码分割不足**：所有组件打包在一起
3. **字体策略不当**：preload: false 导致字体闪烁
4. **动画库开销大**：framer-motion 在低端手机性能差

---

## 优化方案（分 3 个阶段）

### 阶段 1：立即见效优化（预计减少 40% 加载时间）

#### 1.1 图表库按需加载
**文件**：`web/src/components/chat/messages/ai.tsx`

**改动**：
```typescript
// 在 AssistantMessage 组件中，将 SqlResultChart 改为条件动态加载
const SqlResultChart = useMemo(() => {
  if (!hasChartData) return null;
  return dynamic(() => import('./sql-result-chart').then(m => m.SqlResultChart), {
    ssr: false,
    loading: () => <div className="h-[300px] flex items-center justify-center text-gray-400">加载图表...</div>
  });
}, [hasChartData]);
```

**收益**：首屏减少 6.5MB

#### 1.2 Markdown 渲染器懒加载
**文件**：`web/src/components/chat/messages/ai.tsx`

**改动**：
```typescript
// 只在有 Markdown 内容时才加载
const MarkdownText = useMemo(() => {
  if (!hasMarkdownContent) return null;
  return dynamic(() => import('../markdown-text').then(m => m.MarkdownText), {
    ssr: false
  });
}, [hasMarkdownContent]);
```

**收益**：首屏减少 ~2MB（react-markdown + katex）

#### 1.3 语法高亮按需注册
**文件**：`web/src/components/chat/syntax-highlighter.tsx`

**改动**：
```typescript
// 改为动态注册语言
const loadLanguage = async (lang: string) => {
  switch(lang) {
    case 'python':
      const python = await import('react-syntax-highlighter/dist/esm/languages/prism/python');
      SyntaxHighlighterPrism.registerLanguage('python', python.default);
      break;
    case 'typescript':
    case 'tsx':
      const tsx = await import('react-syntax-highlighter/dist/esm/languages/prism/tsx');
      SyntaxHighlighterPrism.registerLanguage('tsx', tsx.default);
      break;
    // ... 其他语言
  }
};
```

**收益**：首屏减少 ~1MB

#### 1.4 字体预加载优化
**文件**：`web/src/app/layout.tsx`

**改动**：
```typescript
const notoSansSC = Noto_Sans_SC({
  weight: ["400", "500"], // 只保留常用字重，删除 600、700
  preload: true, // 改为 true
  display: "swap",
  fallback: ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "sans-serif"],
  variable: "--font-sans-cjk",
});
```

**收益**：减少字体闪烁，提升感知速度

---

### 阶段 2：构建优化（预计再减少 20% 加载时间）

#### 2.1 启用 Bundle Analyzer
**文件**：`web/next.config.mjs`

**改动**：
```javascript
import bundleAnalyzer from '@next/bundle-analyzer';

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

const nextConfig = {
  output: 'standalone',
  compress: true,
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn']
    } : false,
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  // ... 其余配置
};

export default withBundleAnalyzer(nextConfig);
```

**依赖**：
```bash
pnpm add -D @next/bundle-analyzer
```

**使用**：
```bash
ANALYZE=true pnpm build
```

#### 2.2 优化 Tailwind CSS
**文件**：`web/tailwind.config.js`

**改动**：
```javascript
module.exports = {
  content: [
    "./src/**/*.{ts,tsx,js,jsx}",
  ],
  safelist: [], // 移除未使用的类
  // ... 其余配置
};
```

#### 2.3 图片优化
**文件**：`web/next.config.mjs`

**改动**：
```javascript
const nextConfig = {
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
  },
  // ... 其余配置
};
```

---

### 阶段 3：运行时优化（提升交互体验）

#### 3.1 替换 framer-motion 为 CSS 动画
**文件**：`web/src/components/chat/index.tsx`

**改动**：
```typescript
// 将 motion.div 替换为普通 div + CSS transition
<div
  className={cn(
    "absolute z-20 h-full overflow-hidden border-r bg-white transition-transform duration-300 ease-out",
    chatHistoryOpen ? "translate-x-0" : "-translate-x-full"
  )}
  style={{ width: 300 }}
>
  {/* ... */}
</div>
```

**收益**：
- 减少 ~500KB bundle
- 提升低端手机性能
- 减少 JS 执行时间

#### 3.2 虚拟滚动（可选，针对长对话）
**文件**：`web/src/components/chat/index.tsx`

**改动**：使用 `react-window` 或 `@tanstack/react-virtual` 实现消息列表虚拟滚动

**收益**：长对话场景下内存占用减少 70%

#### 3.3 Service Worker 缓存（可选）
**文件**：`web/public/sw.js`

**改动**：缓存静态资源和 API 响应

**收益**：二次访问速度提升 80%

---

## 执行计划

### 第 1 周：阶段 1（核心优化）
- [ ] 1.1 图表库按需加载
- [ ] 1.2 Markdown 渲染器懒加载
- [ ] 1.3 语法高亮按需注册
- [ ] 1.4 字体预加载优化
- [ ] 验证：本地测试 + 手机端测试

### 第 2 周：阶段 2（构建优化）
- [ ] 2.1 启用 Bundle Analyzer
- [ ] 2.2 优化 Tailwind CSS
- [ ] 2.3 图片优化
- [ ] 验证：生产构建 + Lighthouse 评分

### 第 3 周：阶段 3（运行时优化）
- [ ] 3.1 替换 framer-motion
- [ ] 3.2 虚拟滚动（可选）
- [ ] 3.3 Service Worker（可选）
- [ ] 验证：性能监控 + 用户反馈

---

## 验证标准

### 性能指标
- **FCP (First Contentful Paint)**：< 1.5s（当前 ~3s）
- **LCP (Largest Contentful Paint)**：< 2.5s（当前 ~5s）
- **TTI (Time to Interactive)**：< 3s（当前 ~6s）
- **Bundle Size**：< 500KB gzipped（当前 ~2MB）

### 测试环境
- 桌面端：Chrome DevTools（Fast 3G）
- 手机端：真机测试（iPhone SE、小米 10）
- 工具：Lighthouse、WebPageTest

---

## 风险与回退

### 风险
1. 动态加载可能导致组件闪烁
2. CSS 动画可能不如 framer-motion 流畅
3. 语法高亮动态加载可能有延迟

### 回退策略
1. 保留原代码分支：`backup/before-perf-opt`
2. 分阶段上线，每阶段可独立回退
3. 灰度发布：先 10% 用户，观察 1 天再全量

---

## 附录：快速验证命令

```bash
# 1. 分析当前 bundle
cd web
ANALYZE=true pnpm build

# 2. 检查压缩后大小
pnpm build
find .next/static/chunks -name "*.js" -exec gzip -c {} \; | wc -c

# 3. Lighthouse 评分
pnpm build && pnpm start
# 然后在 Chrome DevTools 中运行 Lighthouse

# 4. 手机端测试
# 使用 Chrome Remote Debugging 连接真机
```
