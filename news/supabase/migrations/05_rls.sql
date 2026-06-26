-- Step 5: RLS 权限策略

alter table public.users enable row level security;
alter table public.articles enable row level security;
alter table public.company_updates enable row level security;
alter table public.social_posts enable row level security;
alter table public.daily_digest enable row level security;
alter table public.subscriptions enable row level security;

-- articles: 免费内容公开，付费内容仅 pro 用户可读
create policy "free articles are public" on public.articles
  for select using (is_premium = false);

create policy "premium articles for pro users" on public.articles
  for select using (
    is_premium = true
    and exists (
      select 1 from public.users
      where id = auth.uid()
      and subscription_tier = 'pro'
      and (subscription_expires_at is null or subscription_expires_at > now())
    )
  );

-- company_updates: 同 articles 逻辑
create policy "free company updates are public" on public.company_updates
  for select using (is_premium = false);

create policy "premium company updates for pro users" on public.company_updates
  for select using (
    is_premium = true
    and exists (
      select 1 from public.users
      where id = auth.uid()
      and subscription_tier = 'pro'
      and (subscription_expires_at is null or subscription_expires_at > now())
    )
  );

-- social_posts / daily_digest: 全部公开
create policy "social posts are public" on public.social_posts
  for select using (true);

create policy "daily digest is public" on public.daily_digest
  for select using (true);

-- users: 只能读写自己的记录
create policy "users can read own profile" on public.users
  for select using (auth.uid() = id);

create policy "users can update own profile" on public.users
  for update using (auth.uid() = id);

-- subscriptions: 只能读自己的订阅
create policy "users can read own subscriptions" on public.subscriptions
  for select using (auth.uid() = user_id);
