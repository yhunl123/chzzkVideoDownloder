import tkinter as tk
from tkinter import filedialog, ttk
import yt_dlp
import threading
import os
import queue

class ChzzkQueueDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다시보기 대기열 다운로더")
        self.root.geometry("700x600")

        # --- 변수 및 설정 ---
        self.max_concurrent_downloads = 4  # 동시에 다운로드할 최대 개수
        self.current_active_downloads = 0
        self.download_queue = queue.Queue() # 대기열 (item_id 저장)
        self.items_data = {} # item_id 별 URL 및 상태 관리

        # --- UI 구성 ---
        self.create_widgets()

    def create_widgets(self):
        # 1. 저장 경로 설정
        path_frame = tk.LabelFrame(self.root, text="1. 저장 경로", padx=10, pady=10)
        path_frame.pack(fill="x", padx=10, pady=5)

        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.path_entry.insert(0, os.path.join(os.path.expanduser('~'), 'Downloads'))

        btn_path = tk.Button(path_frame, text="폴더 변경", command=self.select_directory)
        btn_path.pack(side="right")

        # 2. 파일 이름 포맷 설정
        format_frame = tk.LabelFrame(self.root, text="2. 파일 이름 형식", padx=10, pady=10)
        format_frame.pack(fill="x", padx=10, pady=5)

        desc_lbl = tk.Label(format_frame, text="{artist}, {title}, {year}/{month}/{day}/{hour}",
                            fg="gray", font=("System", 9))
        desc_lbl.pack(anchor="w")

        self.filename_entry = tk.Entry(format_frame)
        self.filename_entry.pack(fill="x")
        # 요청하신 기본 포맷
        self.filename_entry.insert(0, "{artist} {year}-{month}-{day} {hour}H {title}.mp4")

        # 3. 링크 입력 및 추가
        input_frame = tk.LabelFrame(self.root, text="3. 다운로드 추가 (실시간)", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        self.url_entry = tk.Entry(input_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", lambda event: self.add_to_queue()) # 엔터키 지원

        self.btn_add = tk.Button(input_frame, text="추가", bg="#00C73C", fg="white", command=self.add_to_queue)
        self.btn_add.pack(side="right")

        # 4. 대기열 리스트 (Treeview)
        list_frame = tk.LabelFrame(self.root, text="다운로드 목록 (최대 4개 동시 진행)", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("url", "status", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        self.tree.heading("url", text="링크 / 제목")
        self.tree.heading("status", text="상태")
        self.tree.heading("progress", text="정보")

        self.tree.column("url", width=350)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("progress", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def convert_format(self, user_fmt):
        """
        사용자 입력 포맷을 yt-dlp 포맷으로 변환
        {hour} -> %(timestamp>%H)s (timestamp 기준 시간)
        """
        fmt = user_fmt
        # yt-dlp 템플릿으로 매핑
        fmt = fmt.replace("{artist}", "%(uploader)s")
        fmt = fmt.replace("{title}", "%(title)s")
        # 날짜/시간: timestamp(epoch) 기반 포맷팅 사용
        fmt = fmt.replace("{year}", "%(timestamp>%Y)s")
        fmt = fmt.replace("{month}", "%(timestamp>%m)s")
        fmt = fmt.replace("{day}", "%(timestamp>%d)s")
        fmt = fmt.replace("{hour}", "%(timestamp>%H)s")

        if not fmt.endswith(".mp4"):
            fmt += ".%(ext)s"
        return fmt

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        # UI 리스트에 추가
        item_id = self.tree.insert("", "end", values=(url, "대기 중", "-"))

        # 데이터 저장
        self.items_data[item_id] = {
            "url": url,
            "output_path": self.path_entry.get(),
            "format_str": self.filename_entry.get()
        }

        # 대기열 큐에 넣기
        self.download_queue.put(item_id)

        # 입력창 초기화
        self.url_entry.delete(0, tk.END)

        # 큐 처리 시도
        self.process_queue()

    def process_queue(self):
        """
        현재 실행 중인 다운로드 수가 최대치 미만이고,
        대기열에 항목이 있다면 작업을 시작함
        """
        if self.current_active_downloads < self.max_concurrent_downloads and not self.download_queue.empty():
            item_id = self.download_queue.get()
            self.start_download_thread(item_id)

    def start_download_thread(self, item_id):
        self.current_active_downloads += 1
        self.update_status(item_id, "다운로드 중", "시작하는 중...")

        # 스레드 시작
        t = threading.Thread(target=self.download_task, args=(item_id,))
        t.daemon = True
        t.start()

    def download_task(self, item_id):
        data = self.items_data[item_id]
        url = data['url']
        out_path = data['output_path']
        user_fmt = data['format_str']

        yt_template = self.convert_format(user_fmt)
        full_template = f"{out_path}/{yt_template}"

        # yt-dlp 옵션
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': full_template,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            # 진행 상황 hook (선택 사항: 원하면 구현 가능하나 여기선 단순화)
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. 메타데이터 먼저 추출 (제목 업데이트용)
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', url)

                # UI 업데이트 (메인 스레드에서 실행되도록 after 사용 권장이나 간단한 config는 보통 허용됨)
                self.root.after(0, self.update_tree_title, item_id, video_title)
                self.root.after(0, self.update_status, item_id, "다운로드 중", "영상 받는 중...")

                # 2. 실제 다운로드
                ydl.download([url])

            self.root.after(0, self.update_status, item_id, "완료", "성공")

        except Exception as e:
            err_msg = str(e).split('\n')[0] # 첫 줄만 표시
            self.root.after(0, self.update_status, item_id, "실패", "에러 발생")
            print(f"Error: {e}")

        finally:
            # 작업 종료 처리
            self.root.after(0, self.on_task_finished)

    def on_task_finished(self):
        """작업 하나가 끝났을 때 호출"""
        self.current_active_downloads -= 1
        # 다음 대기열 확인 및 시작
        self.process_queue()

    def update_status(self, item_id, status, progress_text):
        try:
            current_values = self.tree.item(item_id)['values']
            # url(0), status(1), progress(2)
            self.tree.item(item_id, values=(current_values[0], status, progress_text))
        except:
            pass

    def update_tree_title(self, item_id, title):
        try:
            current_values = self.tree.item(item_id)['values']
            self.tree.item(item_id, values=(title, current_values[1], current_values[2]))
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkQueueDownloader(root)
    root.mainloop()