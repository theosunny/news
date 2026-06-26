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
