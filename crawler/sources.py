"""Data source configurations for the dairy intelligence crawler."""

SOURCES = [
    {
        "name": "Dairy Reporter",
        "type": "RSS",
        "url": "https://www.dairyreporter.com/rss/news",
        "category": "news",
        "language": "en",
    },
    {
        "name": "USDA Dairy",
        "type": "RSS",
        "url": "https://www.ams.usda.gov/rss/mncs/dairy.xml",
        "category": "news",
        "language": "en",
    },
    {
        "name": "Fonterra News",
        "type": "RSS",
        "url": "https://www.fonterra.com/nz/en/news-and-media/news.rss.xml",
        "category": "news",
        "language": "en",
    },
    {
        "name": "农业农村部",
        "type": "scrapling",
        "url": "http://www.moa.gov.cn/govpublic/",
        "category": "news",
        "language": "zh",
        "selector": "div.main-list li a",
    },
    {
        "name": "GDT拍卖",
        "type": "scrapling",
        "url": "https://www.globaldairytrade.info/en/product-results/",
        "category": "company",
        "language": "en",
        "selector": "table.results-table tr",
    },
]

SOCIAL_SOURCES = [
    {
        "name": "xueqiu",
        "type": "scrapling",
        "url": "https://xueqiu.com/search?q=乳业&type=status",
        "selector": "div.timeline-item",
    },
    {
        "name": "eastmoney",
        "type": "scrapling",
        "url": "https://search.eastmoney.com/快讯?keyword=乳业",
        "selector": "div.news-item",
    },
]

COMPANY_SOURCES = [
    {"name": "伊利股份", "ticker": "600887", "exchange": "SSE", "is_premium": False},
    {"name": "蒙牛乳业", "ticker": "02319", "exchange": "HKEX", "is_premium": False},
    {"name": "光明乳业", "ticker": "600597", "exchange": "SSE", "is_premium": False},
    {"name": "新乳业", "ticker": "002946", "exchange": "SZE", "is_premium": False},
    {"name": "Fonterra", "ticker": "FCG", "exchange": "NZX", "is_premium": True},
    {"name": "Bega Cheese", "ticker": "BGA", "exchange": "ASX", "is_premium": True},
]
