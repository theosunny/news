-- Step 6: pg_cron 定时触发每日速览 Edge Function
-- 替换 YOUR_PROJECT_REF 和 YOUR_ANON_KEY 后再运行
select cron.schedule(
  'daily-digest-job',
  '0 22 * * *',  -- UTC 22:00 = 北京时间 06:00
  $$
  select net.http_post(
    url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-digest',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY", "Content-Type": "application/json"}'::jsonb,
    body := '{}'::jsonb
  )
  $$
);
