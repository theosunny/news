-- Step 4: 初始数据

insert into public.companies (name, exchange, ticker, country) values
  ('伊利股份', 'SSE', '600887', 'CN'),
  ('蒙牛乳业', 'HKEX', '02319', 'CN'),
  ('光明乳业', 'SSE', '600597', 'CN'),
  ('新乳业', 'SZE', '002946', 'CN'),
  ('澳亚集团', 'HKEX', '06963', 'CN'),
  ('Fonterra', 'NZX', 'FCG', 'NZ'),
  ('Bega Cheese', 'ASX', 'BGA', 'AU');

insert into public.rss_sources (name, url, category, scraping_method) values
  ('Dairy Reporter', 'https://www.dairyreporter.com/rss/news', 'news', 'rss'),
  ('USDA Dairy', 'https://www.ams.usda.gov/rss/mncs/dairy.xml', 'news', 'rss'),
  ('Fonterra News', 'https://www.fonterra.com/nz/en/news-and-media/news.rss.xml', 'news', 'rss'),
  ('农业农村部', 'http://www.moa.gov.cn/rssfeed/rss.xml', 'news', 'scrapling'),
  ('国家奶牛技术体系', 'http://www.chinacows.org', 'news', 'scrapling'),
  ('雪球乳业', 'https://xueqiu.com/search?q=乳业', 'social', 'scrapling'),
  ('东方财富乳业', 'https://search.eastmoney.com/快讯?keyword=乳业', 'social', 'scrapling'),
  ('GDT拍卖', 'https://www.globaldairytrade.info/en/product-results/', 'company', 'scrapling');
