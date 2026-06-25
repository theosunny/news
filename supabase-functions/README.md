# Supabase Edge Functions 部署说明

本目录记录乳业情报平台 Supabase Edge Functions 的部署步骤。
实际函数代码位于 `E:/claudpro/news/supabase/functions/`。

## daily-digest 函数

每日凌晨 6:00（北京时间）自动生成"今日速览"，汇总当日乳业动态。

### 函数代码位置

```
E:/claudpro/news/supabase/functions/daily-digest/index.ts
```

### 部署步骤

1. 确保已安装 Supabase CLI：

   ```bash
   npm install -g supabase
   ```

2. 登录并关联项目：

   ```bash
   supabase login
   supabase link --project-ref YOUR_PROJECT_REF
   ```

3. 部署函数：

   ```bash
   supabase functions deploy daily-digest
   ```

4. 设置所需 Secrets（见下方）

5. 在 Supabase SQL Editor 运行 pg_cron 脚本（见下方）

### 需要设置的 Secrets

在 Supabase Dashboard → Project Settings → Edge Functions → Secrets 中添加：

| Secret 名称 | 说明 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥，用于调用 Claude Haiku |
| `ANTHROPIC_BASE_URL` | （可选）自定义 Anthropic API 地址，默认 `https://api.anthropic.com` |

> 注意：`SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 由 Supabase Edge Functions 运行时自动注入，无需手动设置。

### pg_cron 定时触发

pg_cron SQL 文件位置：

```
E:/claudpro/news/supabase/migrations/20260626_pg_cron_digest.sql
```

在 Supabase SQL Editor 中运行该文件内容，**运行前请替换以下占位符**：

- `YOUR_PROJECT_REF`：替换为你的 Supabase 项目 Reference ID
- `YOUR_ANON_KEY`：替换为你的 Supabase 项目 anon key

定时规则：每日 UTC 22:00（= 北京时间次日 06:00）自动触发。

### 函数逻辑概述

1. 检查 `daily_digest` 表中今日是否已有记录，有则跳过
2. 查询 `articles` 表中当日文章（最多 50 条）
3. 调用 Claude Haiku，生成 5-8 条今日速览（JSON 数组）
4. 将结果写入 `daily_digest` 表的 `highlights` 字段
