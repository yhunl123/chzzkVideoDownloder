import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import yt_dlp
import threading
import os
from concurrent.futures import ThreadPoolExecutor

class ChzzkDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다시보기 다운로더")
        self.root.geometry("600x550")
        self.root.resizable(False, False)

        # 1. 다운로드 경로 선택
        self.path_frame = tk.LabelFrame(root, text="1. 저장 경로", padx=10, pady=10)
        self.path_frame.pack(fill="x", padx=10, pady=5)

        self.path_entry = tk.Entry(self.path_frame, width=50)
        self.path_entry.pack(side="left", padx=5)
        self.path_entry.insert(0, os.path.join(os.path.expanduser('~'), 'Downloads')) # 기본값: 다운로드 폴더

        self.btn_path = tk.Button(self.path_frame, text="폴더 변경", command=self.select_directory)
        self.btn_path.pack(side="right")

        # 2. 파일명 형식 지정
        self.format_frame = tk.LabelFrame(root, text="2. 파일 이름 형식 설정", padx=10, pady=10)
        self.format_frame.pack(fill="x", padx=10, pady=5)

        self.format_desc = tk.Label(self.format_frame, text="사용 가능 변수: {artist}, {title}, {year}, {month}, {day}, {hour}", fg="gray", font=("System", 9))
        self.format_desc.pack(anchor="w", pady=(0, 5))

        self.filename_entry = tk.Entry(self.format_frame, width=60)
        self.filename_entry.pack(fill="x")
        # 기본 예시 설정
        self.filename_entry.insert(0, "{artist} {year}-{month}-{day} {hour}H {title}.mp4")

        # 3. URL 입력 (다중)
        self.url_frame = tk.LabelFrame(root, text="3. 다시보기 링크 입력 (한 줄에 하나씩)", padx=10, pady=10)
        self.url_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.url_text = scrolledtext.ScrolledText(self.url_frame, height=5)
        self.url_text.pack(fill="both", expand=True)

        # 4. 실행 버튼 및 상태
        self.btn_frame = tk.Frame(root, padx=10, pady=10)
        self.btn_frame.pack(fill="x")

        self.status_label = tk.Label(self.btn_frame, text="대기 중...", fg="blue")
        self.status_label.pack(side="left")

        self.btn_start = tk.Button(self.btn_frame, text="다운로드 시작", bg="#00C73C", fg="white", font=("Bold", 12), command=self.start_download_thread)
        self.btn_start.pack(side="right")

        # 5. 로그 창
        self.log_frame = tk.LabelFrame(root, text="진행 상황", padx=10, pady=5)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8, state='disabled', bg="#f0f0f0")
        self.log_text.pack(fill="both", expand=True)

    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def convert_filename_format(self, user_format):
        """
        사용자가 입력한 포맷을 yt-dlp 포맷으로 변환합니다.
        """
        fmt = user_format
        fmt = fmt.replace("{artist}", "%(uploader)s")
        fmt = fmt.replace("{title}", "%(title)s")
        fmt = fmt.replace("{year}", "%(upload_date>%Y)s")
        fmt = fmt.replace("{month}", "%(upload_date>%m)s")
        fmt = fmt.replace("{day}", "%(upload_date>%d)s")
        fmt = fmt.replace("{hour}", "%(upload_date>%H)s") # 주의: VOD 업로드 시간 기준

        # 확장자가 없으면 mp4 강제
        if not fmt.endswith(".mp4"):
            fmt += ".%(ext)s"

        return fmt

    def download_video(self, url, output_path, output_template):
        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # 최고화질 mp4
                'outtmpl': f"{output_path}/{output_template}",
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }

            self.root.after(0, self.log, f"▶ 다운로드 시작: {url}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                self.root.after(0, self.log, f"✅ 완료: {title}")

        except Exception as e:
            self.root.after(0, self.log, f"❌ 실패 ({url}): {str(e)}")

    def run_downloads(self):
        urls = self.url_text.get("1.0", tk.END).strip().split('\n')
        urls = [u.strip() for u in urls if u.strip()]

        if not urls:
            messagebox.showwarning("경고", "다운로드할 링크를 입력해주세요.")
            self.btn_start.config(state='normal')
            return

        output_path = self.path_entry.get()
        user_format = self.filename_entry.get()
        yt_dlp_template = self.convert_filename_format(user_format)

        self.root.after(0, lambda: self.status_label.config(text=f"다운로드 중... (총 {len(urls)}개)"))

        # 다중 다운로드를 위한 스레드 풀 (최대 3개 동시 다운로드)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for url in urls:
                futures.append(executor.submit(self.download_video, url, output_path, yt_dlp_template))

            # 모든 작업 완료 대기
            for future in futures:
                future.result()

        self.root.after(0, lambda: self.status_label.config(text="모든 작업 완료"))
        self.root.after(0, lambda: messagebox.showinfo("완료", "모든 다운로드가 완료되었습니다."))
        self.root.after(0, lambda: self.btn_start.config(state='normal'))

    def start_download_thread(self):
        self.btn_start.config(state='disabled')
        thread = threading.Thread(target=self.run_downloads)
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkDownloaderApp(root)
    root.mainloop()