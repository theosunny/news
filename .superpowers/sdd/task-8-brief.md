# Task 8: Supabase Edge Function - 每日速览生成

## Context
乳业情报平台，Tasks 5-7 完成了爬虫部分。
Task 8 创建 Supabase Edge Function（Deno/TypeScript），每日凌晨 6:00 北京时间自动生成"今日速览"。
文件放在爬虫仓库的 supabase/ 目录下，但实际部署在 Supabase 平台。

## Global Constraints
- Deno/TypeScript（Edge Functions 运行时）
- 使用 Claude Haiku 生成速览（通过 Anthropic API）
- ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL 从 Deno.env 读取
- SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 从 Deno.env 读取（Edge Functions 自动注入）
- 如果今天已生成过，返回 {"message": "Already generated today"} 不重复生成
- highlights 是 JSON 数组，每项 {"title": str, "summary": str, "is_premium": bool}
- pg_cron 触发时间：UTC 22:00（= 北京时间 06:00）

## File to Create
- `E:/claudpro/news/supabase/functions/daily-digest/index.ts`

## Implementation

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

serve(async (_req) => {
  const today = new Date().toISOString().split("T")[0];

  // 检查今天是否已生成
  const { data: existing } = await supabase
    .from("daily_digest")
    .select("id")
    .eq("date", today)
    .single();

  if (existing) {
    return new Response(JSON.stringify({ message: "Already generated today" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 获取今日所有文章（UTC 00:00 起）
  const since = new Date();
  since.setUTCHours(0, 0, 0, 0);

  const { data: articles } = await supabase
    .from("articles")
    .select("title, summary, category, tags, sentiment_score, is_premium")
    .gte("created_at", since.toISOString())
    .order("created_at", { ascending: false })
    .limit(50);

  if (!articles || articles.length === 0) {
    return new Response(JSON.stringify({ message: "No articles today" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 构建发给 Claude 的文章列表
  const articlesText = articles
    .map((a, i) => `${i + 1}. [${a.category}] ${a.title}: ${a.summary ?? ""}`)
    .join("\n");

  // 调用 Claude Haiku
  const anthropicRes = await fetch(
    `${Deno.env.get("ANTHROPIC_BASE_URL") ?? "https://api.anthropic.com"}/v1/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": Deno.env.get("ANTHROPIC_API_KEY")!,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        messages: [{
          role: "user",
          content: `你是乳业分析师。从以下今日文章中选出5-8条最重要的动态，生成今日速览。
每条格式：{"title": "一句话标题", "summary": "一句话摘要", "is_premium": false}
重大行情、政策、安全事件标 is_premium: false，深度分析标 is_premium: true。
只返回 JSON 数组，不要其他文字。

今日文章：
${articlesText}`,
        }],
      }),
    }
  );

  const anthropicData = await anthropicRes.json();
  const rawText = anthropicData.content?.[0]?.text ?? "[]";

  // 解析 JSON（Claude 可能返回 markdown 代码块，需要去掉）
  let highlights: Array<{ title: string; summary: string; is_premium: boolean }> = [];
  try {
    const cleaned = rawText.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
    highlights = JSON.parse(cleaned);
    if (!Array.isArray(highlights)) highlights = [];
  } catch {
    highlights = [];
  }

  // 写入 daily_digest
  await supabase.from("daily_digest").insert({
    date: today,
    highlights,
  });

  return new Response(
    JSON.stringify({ message: "Generated", count: highlights.length }),
    { headers: { "Content-Type": "application/json" } }
  );
});
```

## 额外文件：pg_cron SQL

创建文件 `E:/claudpro/news/supabase/migrations/20260626_pg_cron_digest.sql`：

```sql
-- 每日 UTC 22:00（北京时间 06:00）触发 daily-digest Edge Function
-- 需要将 YOUR_PROJECT_REF 和 YOUR_ANON_KEY 替换为实际值后在 Supabase SQL Editor 运行
select cron.schedule(
  'daily-digest-job',
  '0 22 * * *',
  $$
  select net.http_post(
    url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-digest',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY", "Content-Type": "application/json"}'::jsonb,
    body := '{}'::jsonb
  )
  $$
);
```

## Validation
由于是 Deno/TypeScript 且无本地 Deno 环境要求，验证方式：
1. 确认文件创建成功
2. 用 TypeScript 关键结构检查（目视确认 serve、createClient、fetch 调用结构完整）
3. 确认 JSON 解析部分有 try/catch 防护
4. 确认 markdown 代码块清理逻辑存在（Claude 有时返回 ```json ... ```）

## Steps
1. 创建 `E:/claudpro/news/supabase/functions/daily-digest/index.ts`
2. 创建 `E:/claudpro/news/supabase/migrations/20260626_pg_cron_digest.sql`
3. git add 并 commit（注意：这两个文件在 E:/claudpro/news/supabase/ 目录，不在 dairy-intel-crawler 仓库下）

等等，supabase/ 目录在 E:/claudpro/news/supabase/，不在 git 仓库中。
所以：
- 把这两个文件创建在正确位置
- 在 dairy-intel-crawler 仓库中创建一个说明文件 `supabase-functions/README.md` 说明部署步骤
- git commit 到 dairy-intel-crawler 仓库（只 commit README）

## Report File
写报告到：E:/claudpro/news/dairy-intel-crawler/.superpowers/sdd/task-8-report.md
内容：创建的文件路径、目视检查清单（serve/createClient/fetch/try-catch/markdown清理）、commit hash。
最后一行：DONE / DONE_WITH_CONCERNS / BLOCKED
