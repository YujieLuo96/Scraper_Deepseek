import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
import asyncio
import threading
import random
import webbrowser  # 新增：用于打开链接
from urllib.parse import urlparse, urljoin
from queue import Queue
from datetime import datetime

# 用户代理列表用于随机选择
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
]


class AdvancedScraper:
    def __init__(self):
        self.visited = set()
        self.results = []
        self.queue = Queue()
        self.lock = threading.Lock()
        self.is_crawling = True
        self.start_time = None

    async def get_random_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }

    async def extract_links(self, soup, base_url):
        """提取当前页面的所有有效链接"""
        links = []
        domain = urlparse(base_url).netloc
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc == domain:
                links.append(full_url)
        return links

    async def crawl_page(self, url, keyword, max_depth):
        """单页面爬取实现"""
        if not self.is_crawling:
            return []

        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = await context.new_page()

            # 设置随机请求间隔
            await asyncio.sleep(random.uniform(0.5, 2.0))

            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle")

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()

            matches = re.finditer(fr'\b(\w*{keyword}\w*)\b', text, re.IGNORECASE)
            page_results = []
            for match in matches:
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context_text = text[context_start:context_end].replace('\n', ' ')
                highlight_text = context_text.replace(
                    match.group(),
                    f"[{match.group()}]"
                )
                page_results.append({
                    'url': url,
                    'keyword': keyword,
                    'match': match.group(),
                    'context': highlight_text,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            links = await self.extract_links(soup, url)
            return page_results, links

        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return [], []
        finally:
            try:
                await page.close()
                await context.close()
                await browser.close()
                await playwright.stop()
            except:
                pass

    async def start_crawl(self, start_url, keyword, max_depth=2, max_concurrency=3):
        """启动多级爬取"""
        self.start_time = datetime.now()
        self.queue.put((start_url, 0))

        async def worker():
            while not self.queue.empty() and self.is_crawling:
                try:
                    url, depth = self.queue.get_nowait()
                except:
                    break

                if depth > max_depth:
                    continue

                with self.lock:
                    if url in self.visited:
                        continue
                    self.visited.add(url)

                results, links = await self.crawl_page(url, keyword, max_depth)

                with self.lock:
                    self.results.extend(results)
                    for link in links:
                        if link not in self.visited:
                            self.queue.put((link, depth + 1))

        # 启动异步任务
        tasks = [worker() for _ in range(max_concurrency)]
        await asyncio.gather(*tasks)


class EnhancedApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智能网页爬虫专业版 v3.0")
        self.geometry("1200x800")
        self.scraper = AdvancedScraper()
        self.create_ui()
        self.create_menu()
        self.running = False

    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self)

        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="导出CSV", command=lambda: self.export_data('csv'))
        file_menu.add_command(label="导出Excel", command=lambda: self.export_data('excel'))
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)

        # 视图菜单
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="清空结果", command=self.clear_results)
        menu_bar.add_cascade(label="视图", menu=view_menu)

        self.config(menu=menu_bar)

    def create_ui(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板")
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="起始URL:").grid(row=0, column=0, padx=5, sticky='w')
        self.url_entry = ttk.Entry(control_frame, width=80)
        self.url_entry.grid(row=0, column=1, padx=5, sticky='ew')

        ttk.Label(control_frame, text="关键词:").grid(row=1, column=0, padx=5, sticky='w')
        self.keyword_entry = ttk.Entry(control_frame, width=30)
        self.keyword_entry.grid(row=1, column=1, padx=5, sticky='w')

        ttk.Label(control_frame, text="爬取深度:").grid(row=1, column=2, padx=5)
        self.depth_spin = ttk.Spinbox(control_frame, from_=1, to=5, width=5)
        self.depth_spin.set(2)
        self.depth_spin.grid(row=1, column=3, padx=5)

        ttk.Label(control_frame, text="并发数:").grid(row=1, column=4, padx=5)
        self.concurrency_spin = ttk.Spinbox(control_frame, from_=1, to=10, width=5)
        self.concurrency_spin.set(3)
        self.concurrency_spin.grid(row=1, column=5, padx=5)

        self.start_btn = ttk.Button(control_frame, text="开始爬取", command=self.start_crawl)
        self.start_btn.grid(row=1, column=6, padx=10)

        self.stop_btn = ttk.Button(control_frame, text="停止", command=self.stop_crawl, state=tk.DISABLED)
        self.stop_btn.grid(row=1, column=7, padx=10)

        # 结果展示
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("timestamp", "url", "keyword", "match", "context")
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # 配置列
        self.result_tree.heading("timestamp", text="时间", anchor='w')
        self.result_tree.heading("url", text="来源URL", anchor='w')
        self.result_tree.heading("keyword", text="关键词", anchor='w')
        self.result_tree.heading("match", text="匹配内容", anchor='w')
        self.result_tree.heading("context", text="上下文", anchor='w')

        # 设置列宽
        self.result_tree.column("timestamp", width=150, minwidth=100)
        self.result_tree.column("url", width=250, minwidth=150)
        self.result_tree.column("keyword", width=100, minwidth=80)
        self.result_tree.column("match", width=120, minwidth=80)
        self.result_tree.column("context", width=400, minwidth=300)

        # 滚动条
        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_tree.yview)
        hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 布局
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 绑定点击事件
        self.result_tree.bind("<Button-1>", self.on_treeview_click)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 配置网格布局权重
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # 绑定排序事件
        for col in columns:
            self.result_tree.heading(col, command=lambda _col=col: self.treeview_sort_column(_col))

    def on_treeview_click(self, event):
        """Treeview点击事件处理"""
        region = self.result_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.result_tree.identify_row(event.y)
            column = self.result_tree.identify_column(event.x)
            if column == "#2":  # URL列
                url = self.result_tree.item(item, "values")[1]
                webbrowser.open(url)

    def treeview_sort_column(self, col):
        """Treeview列排序功能"""
        data = [(self.result_tree.set(child, col), child) for child in self.result_tree.get_children('')]
        data.sort(reverse=self.sort_direction.get(col, False))
        for index, (val, child) in enumerate(data):
            self.result_tree.move(child, '', index)
        self.sort_direction[col] = not self.sort_direction.get(col, False)

    def validate_input(self):
        """验证输入有效性"""
        url = self.url_entry.get().strip()
        keyword = self.keyword_entry.get().strip()

        if not url:
            messagebox.showwarning("警告", "请输入有效的URL")
            return False

        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return False

        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("无效的URL格式")
        except:
            messagebox.showwarning("警告", "请输入有效的URL格式")
            return False

        return True

    def start_crawl(self):
        """启动爬取任务"""
        if not self.validate_input():
            return

        self.running = True
        self.scraper.is_crawling = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.result_tree.delete(*self.result_tree.get_children())
        self.scraper.results.clear()
        self.scraper.visited.clear()

        def update_ui():
            """定时更新UI界面"""
            if not self.running:
                return

            # 更新结果
            for result in self.scraper.results[:]:  # 使用切片复制防止数据变化
                if result.get('processed'):
                    continue
                self.result_tree.insert("", tk.END, values=(
                    result['timestamp'],
                    result['url'],
                    result['keyword'],
                    result['match'],
                    result['context']
                ))
                result['processed'] = True

            # 更新状态
            elapsed = datetime.now() - self.scraper.start_time
            status_text = f"运行中 | 已爬取: {len(self.scraper.visited)} 页 | 发现结果: {len(self.scraper.results)} | 运行时间: {elapsed}"
            self.status_var.set(status_text)
            self.after(1000, update_ui)

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.scraper.start_crawl(
                start_url=self.url_entry.get(),
                keyword=self.keyword_entry.get(),
                max_depth=int(self.depth_spin.get()),
                max_concurrency=int(self.concurrency_spin.get())
            ))
            self.running = False
            self.after(0, self.on_crawl_finished)

        threading.Thread(target=run_async, daemon=True).start()
        self.after(1000, update_ui)

    def on_crawl_finished(self):
        """爬取完成后的处理"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        elapsed = datetime.now() - self.scraper.start_time
        self.status_var.set(f"完成！总耗时: {elapsed} | 总结果数: {len(self.scraper.results)}")

    def stop_crawl(self):
        """停止爬取"""
        self.scraper.is_crawling = False
        self.running = False
        self.status_var.set("正在停止...")

    def clear_results(self):
        """清空结果"""
        self.result_tree.delete(*self.result_tree.get_children())
        self.scraper.results.clear()
        self.status_var.set("已清空所有结果")

    def export_data(self, file_type):
        """导出数据"""
        if not self.scraper.results:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{file_type}",
            filetypes=[(f"{file_type.upper()}文件", f"*.{file_type}")]
        )
        if not file_path:
            return

        try:
            df = pd.DataFrame(self.scraper.results)
            df = df.drop(columns=['processed'], errors='ignore')

            if file_type == 'csv':
                df.to_csv(file_path, index=False)
            elif file_type == 'excel':
                df.to_excel(file_path, index=False)

            messagebox.showinfo("成功", f"数据已导出到：{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")


if __name__ == "__main__":
    app = EnhancedApplication()
    app.mainloop()