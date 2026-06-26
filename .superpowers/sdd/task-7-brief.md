# Task 7: GitHub Actions 定时任务

## Context
乳业情报平台爬虫，位于 E:/claudpro/news/dairy-intel-crawler。
Tasks 5-6 已完成：crawler/ 包含完整的 rss_fetcher、scrapling_fetcher、ai_summarizer、main.py。
这是 Task 7：创建 GitHub Actions workflow，每小时自动运行爬虫。

## Global Constraints
- Python 3.11
- 所有密钥从 GitHub Actions Secrets 读取（SUPABASE_URL、SUPABASE_SERVICE_KEY、ANTHROPIC_API_KEY）
- workflow 文件必须支持 schedule（每小时）和 workflow_dispatch（手动触发）
- Scrapling 依赖 Playwright chromium，需要在 CI 中安装
- 运行命令：`python -m crawler.main`
- 失败时上传日志 artifact，保留 3 天

## File to Create
- `.github/workflows/crawler.yml`

## Implementation

```yaml
name: Dairy Intel Crawler

on:
  schedule:
    - cron: '0 * * * *'   # 每小时整点
  workflow_dispatch:        # 允许手动触发

jobs:
  crawl:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright (Scrapling dependency)
        run: playwright install chromium --with-deps

      - name: Run crawler
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ANTHROPIC_BASE_URL: ${{ secrets.ANTHROPIC_BASE_URL }}
        run: python -m crawler.main

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: crawler-logs-${{ github.run_id }}
          path: '*.log'
          retention-days: 3
```

## TDD Note
GitHub Actions YAML 无法本地单元测试。验证方式：
1. 用 `python -m py_compile` 验证 Python 文件无语法错误（已在 Task 6 完成）
2. 用 yaml 语法检查验证 workflow 文件（安装 pyyaml 后 `python -c "import yaml; yaml.safe_load(open('.github/workflows/crawler.yml'))"`)
3. 确认 workflow 文件结构符合 GitHub Actions 规范（steps 顺序、secrets 引用格式）

## Steps
1. 创建 `.github/workflows/crawler.yml`（内容完全按上面的 yaml）
2. 运行 yaml 语法验证：
   ```powershell
   cd E:/claudpro/news/dairy-intel-crawler
   python -c "import yaml; yaml.safe_load(open('.github/workflows/crawler.yml')); print('YAML valid')"
   ```
   预期输出：`YAML valid`
3. git commit -m "feat(task-7): github actions hourly crawler workflow"

## Report File
写报告到：E:/claudpro/news/dairy-intel-crawler/.superpowers/sdd/task-7-report.md
内容：创建的文件、验证命令输出、commit hash。
最后一行：DONE / DONE_WITH_CONCERNS / BLOCKED
