import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urlparse


class DynamicScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

    def scrape(self, url, keyword, timeout=30000):
        """执行爬取操作，返回包含关键词的文本片段列表"""
        context = self.browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, timeout=timeout)
            page.wait_for_load_state("networkidle")

            # 获取完整渲染后的HTML
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            text_content = soup.get_text()

            # 使用正则表达式查找包含关键词的上下文
            pattern = re.compile(f'(\w*{keyword}\w*)', re.IGNORECASE)
            matches = pattern.findall(text_content)

            return list(set(matches))  # 去重后返回

        except Exception as e:
            raise Exception(f"爬取失败: {str(e)}")
        finally:
            page.close()
            context.close()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智能动态网页爬虫 v1.0")
        self.geometry("800x600")
        self.scraper = DynamicScraper()
        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        # 输入区域
        input_frame = ttk.LabelFrame(self, text="爬取参数")
        input_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(input_frame, text="目标URL:").grid(row=0, column=0, padx=5, pady=5)
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="关键词:").grid(row=1, column=0, padx=5, pady=5)
        self.keyword_entry = ttk.Entry(input_frame, width=50)
        self.keyword_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 按钮区域
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        self.start_btn = ttk.Button(btn_frame, text="开始爬取", command=self.start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(btn_frame, text="导出结果", command=self.export_data, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)

        # 结果展示
        result_frame = ttk.LabelFrame(self, text="搜索结果")
        result_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.result_tree = ttk.Treeview(result_frame, columns=("result"), show="headings")
        self.result_tree.heading("result", text="匹配内容")
        self.result_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # 状态栏
        self.status = ttk.Label(self, text="准备就绪", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

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

    def start_scraping(self):
        """启动爬取任务"""
        if not self.validate_input():
            return

        self.start_btn.config(state=tk.DISABLED)
        self.status.config(text="正在爬取...")
        self.result_tree.delete(*self.result_tree.get_children())

        try:
            results = self.scraper.scrape(
                self.url_entry.get(),
                self.keyword_entry.get()
            )

            if not results:
                messagebox.showinfo("提示", "未找到匹配内容")
                return

            for res in results:
                self.result_tree.insert("", tk.END, values=(res,))

            self.export_btn.config(state=tk.NORMAL)
            self.status.config(text=f"找到 {len(results)} 条匹配结果")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status.config(text="爬取失败")
        finally:
            self.start_btn.config(state=tk.NORMAL)

    def export_data(self):
        """导出数据到文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("Excel文件", "*.xlsx")]
        )

        if not file_path:
            return

        try:
            data = [self.result_tree.item(i)['values'][0]
                    for i in self.result_tree.get_children()]

            if file_path.endswith('.csv'):
                pd.DataFrame(data, columns=["结果"]).to_csv(file_path, index=False)
            else:
                pd.DataFrame(data, columns=["结果"]).to_excel(file_path, index=False)

            messagebox.showinfo("成功", "数据导出完成")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")


if __name__ == "__main__":
    app = Application()
    app.mainloop()