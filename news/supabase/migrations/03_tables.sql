-- Step 3: 所有业务表

create table public.articles (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  summary text,
  content text,
  source_url text unique,
  source_name text,
  category text not null check (category in ('news','sentiment','social','company','insight')),
  tags text[] default '{}',
  sentiment_score float check (sentiment_score >= -1.0 and sentiment_score <= 1.0),
  is_premium boolean not null default false,
  published_at timestamptz,
  created_at timestamptz not null default now()
);
create index articles_category_published_idx on public.articles(category, published_at desc);
create index articles_is_premium_idx on public.articles(is_premium);

create table public.companies (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  exchange text,
  ticker text,
  country text,
  is_active boolean not null default true
);

create table public.company_updates (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid not null references public.companies(id),
  title text not null,
  summary text,
  price_data jsonb,
  is_premium boolean not null default false,
  published_at timestamptz not null default now()
);

create table public.social_posts (
  id uuid primary key default uuid_generate_v4(),
  platform text not null check (platform in ('weibo','wechat','xueqiu','eastmoney','twitter')),
  content text not null,
  author text,
  engagement_count int default 0,
  url text unique,
  created_at timestamptz not null default now()
);

create table public.daily_digest (
  id uuid primary key default uuid_generate_v4(),
  date date not null unique,
  highlights jsonb not null default '[]',
  created_at timestamptz not null default now()
);

create table public.rss_sources (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  url text not null,
  category text not null,
  scraping_method text not null default 'rss' check (scraping_method in ('rss','scrapling')),
  is_active boolean not null default true,
  last_fetched_at timestamptz
);

create table public.subscriptions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id),
  plan text not null check (plan in ('monthly','yearly')),
  amount int not null,
  payment_method text not null check (payment_method in ('wechat','alipay')),
  status text not null default 'pending' check (status in ('pending','active','expired','cancelled')),
  out_trade_no text unique,
  started_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);
