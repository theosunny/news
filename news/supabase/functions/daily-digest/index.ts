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
    .maybeSingle();

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

  if (!anthropicRes.ok) {
    const errText = await anthropicRes.text();
    console.error(`[daily-digest] Anthropic API error ${anthropicRes.status}: ${errText}`);
    return new Response(
      JSON.stringify({ message: "AI service error", status: anthropicRes.status }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
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
  const { error: insertError } = await supabase.from("daily_digest").insert({
    date: today,
    highlights,
  });

  if (insertError) {
    console.error(`[daily-digest] Insert error: ${insertError.message}`);
    return new Response(
      JSON.stringify({ message: "Database error", error: insertError.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(
    JSON.stringify({ message: "Generated", count: highlights.length }),
    { headers: { "Content-Type": "application/json" } }
  );
});
