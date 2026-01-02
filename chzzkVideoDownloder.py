import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import threading
import os
import queue

class ChzzkDownloaderV4:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다시보기 다운로더")
        self.root.geometry("800x650")

        # --- 변수 및 설정 ---
        self.max_concurrent_downloads = 4
        self.current_active_downloads = 0
        self.download_queue = queue.Queue()
        self.items_data = {}

        # --- UI 구성 ---
        self.create_widgets()

    def create_widgets(self):
        # 1. 저장 경로
        path_frame = tk.LabelFrame(self.root, text="1. 저장 경로", padx=10, pady=10)
        path_frame.pack(fill="x", padx=10, pady=5)

        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.path_entry.insert(0, os.path.join(os.path.expanduser('~'), 'Downloads'))

        btn_path = tk.Button(path_frame, text="폴더 변경", command=self.select_directory)
        btn_path.pack(side="right")

        # 2. 파일 이름 포맷
        format_frame = tk.LabelFrame(self.root, text="2. 파일 이름 형식", padx=10, pady=10)
        format_frame.pack(fill="x", padx=10, pady=5)

        desc_lbl = tk.Label(format_frame, text="{artist}, {title}, {year}/{month}/{day}/{hour}",
                            fg="gray", font=("System", 9))
        desc_lbl.pack(anchor="w")
        self.filename_entry = tk.Entry(format_frame)
        self.filename_entry.pack(fill="x")
        self.filename_entry.insert(0, "{artist} {year}-{month}-{day} {hour}H {title}.mp4")

        # 3. 링크 입력
        input_frame = tk.LabelFrame(self.root, text="3. 다운로드 추가", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        self.url_entry = tk.Entry(input_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", lambda event: self.add_to_queue())

        self.btn_add = tk.Button(input_frame, text="추가", bg="#00C73C", fg="white", command=self.add_to_queue)
        self.btn_add.pack(side="right")

        # 4. 리스트 및 제어 버튼
        list_frame = tk.LabelFrame(self.root, text="4. 다운로드 목록 및 제어", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 트리뷰 (리스트)
        columns = ("filename", "status", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        # 컬럼명 수정: 링크 -> 파일명
        self.tree.heading("filename", text="파일명")
        self.tree.heading("status", text="상태")
        self.tree.heading("progress", text="정보")

        self.tree.column("filename", width=400)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("progress", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 제어 버튼 영역
        control_frame = tk.Frame(list_frame, pady=5)
        control_frame.pack(side="bottom", fill="x")

        self.btn_pause = tk.Button(control_frame, text="일시정지", command=self.pause_item, state="disabled")
        self.btn_pause.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_resume = tk.Button(control_frame, text="다운로드 재개", command=self.resume_item, state="disabled")
        self.btn_resume.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_stop = tk.Button(control_frame, text="다운로드 중지", command=self.stop_item, state="disabled", fg="red")
        self.btn_stop.pack(side="left", padx=5, expand=True, fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # 우클릭 메뉴
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="일시정지", command=self.pause_item)
        self.context_menu.add_command(label="재개", command=self.resume_item)
        self.context_menu.add_command(label="중지", command=self.stop_item)
        self.tree.bind("<Button-3>", self.show_context_menu)

    # --- UI 이벤트 핸들러 ---
    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def on_item_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.toggle_buttons(None)
            return
        item_id = selected[0]
        status = self.items_data[item_id]['status_code']
        self.toggle_buttons(status)

    def toggle_buttons(self, status):
        if status == 'downloading':
            self.btn_pause.config(state="normal")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="normal")
        elif status == 'paused':
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="normal")
            self.btn_stop.config(state="normal")
        elif status in ['waiting']:
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="normal")
        else:
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
            self.btn_stop.config(state="disabled")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.on_item_select(None)
            self.context_menu.post(event.x_root, event.y_root)

    # --- 제어 로직 ---
    def pause_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            if self.items_data[item_id]['status_code'] == 'downloading':
                self.items_data[item_id]['flag'] = 'pause'
                self.update_status(item_id, status_text="일시정지 중...")

    def resume_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            if self.items_data[item_id]['status_code'] == 'paused':
                self.items_data[item_id]['flag'] = 'run'
                self.start_download_thread(item_id, is_resume=True)

    def stop_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            current_status = self.items_data[item_id]['status_code']
            if current_status == 'waiting':
                self.items_data[item_id]['status_code'] = 'stopped'
                self.update_status(item_id, "중지됨", "대기 취소")
            elif current_status in ['downloading', 'paused']:
                self.items_data[item_id]['flag'] = 'stop'
                self.update_status(item_id, status_text="중지 중...")

    # --- 포맷 변환 ---
    def convert_format(self, user_fmt):
        fmt = user_fmt.replace("{artist}", "%(channel)s")
        fmt = fmt.replace("{title}", "%(title)s")
        fmt = fmt.replace("{year}", "%(timestamp>%Y)s")
        fmt = fmt.replace("{month}", "%(timestamp>%m)s")
        fmt = fmt.replace("{day}", "%(timestamp>%d)s")
        fmt = fmt.replace("{hour}", "%(timestamp>%H)s")
        if not fmt.endswith(".mp4"):
            fmt += ".%(ext)s"
        return fmt

    # --- 다운로드 및 대기열 관리 ---
    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url: return

        # 초기에는 '정보 불러오는 중...'으로 표시
        item_id = self.tree.insert("", "end", values=("정보 불러오는 중...", "대기 중", "0%"))

        self.items_data[item_id] = {
            "url": url,
            "output_path": self.path_entry.get(),
            "format_str": self.filename_entry.get(),
            "status_code": "waiting",
            "flag": "run"
        }

        # 1. 메타데이터 미리보기 스레드 시작 (파일명 표시용)
        threading.Thread(target=self.prefetch_metadata, args=(item_id,), daemon=True).start()

        # 2. 대기열 추가 및 처리
        self.download_queue.put(item_id)
        self.url_entry.delete(0, tk.END)
        self.process_queue()

    def prefetch_metadata(self, item_id):
        """다운로드 전에 파일명을 미리 계산해서 리스트에 표시"""
        data = self.items_data[item_id]
        url = data['url']
        out_path = data['output_path']
        yt_template = self.convert_format(data['format_str'])
        full_template = f"{out_path}/{yt_template}"

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': full_template,
            'format': 'best' # 메타데이터만 필요하므로 포맷은 크게 상관없음
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # 실제 생성될 파일 경로 계산
                target_filename = ydl.prepare_filename(info)

                # 확장자 제거 및 경로 제거 (파일명만 표시)
                filename_only = os.path.splitext(os.path.basename(target_filename))[0]

                # UI 업데이트
                self.root.after(0, self.update_tree_filename, item_id, filename_only)
        except Exception as e:
            # 실패 시 URL 그대로 유지하거나 에러 표시
            self.root.after(0, self.update_tree_filename, item_id, f"오류: {url}")

    def process_queue(self):
        while self.current_active_downloads < self.max_concurrent_downloads and not self.download_queue.empty():
            item_id = self.download_queue.get()
            if self.items_data[item_id]['status_code'] == 'stopped':
                continue
            self.start_download_thread(item_id)

    def start_download_thread(self, item_id, is_resume=False):
        if not is_resume:
            self.current_active_downloads += 1

        self.items_data[item_id]['status_code'] = 'downloading'
        self.update_status(item_id, "다운로드 중", "준비 중...")

        if self.tree.selection() and self.tree.selection()[0] == item_id:
            self.toggle_buttons('downloading')

        t = threading.Thread(target=self.download_task, args=(item_id,))
        t.daemon = True
        t.start()

    def download_task(self, item_id):
        data = self.items_data[item_id]
        url = data['url']
        out_path = data['output_path']
        yt_template = self.convert_format(data['format_str'])
        full_template = f"{out_path}/{yt_template}"

        def progress_hook(d):
            if d['status'] == 'downloading':
                flag = self.items_data[item_id]['flag']
                if flag == 'pause': raise Exception("USER_PAUSE")
                elif flag == 'stop': raise Exception("USER_STOP")

                p = d.get('_percent_str', '').strip()
                self.root.after(0, self.update_status, item_id, "다운로드 중", p)

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': full_template,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 다운로드 전 중복 체크
                info = ydl.extract_info(url, download=False)
                target_file = ydl.prepare_filename(info)

                # 다운로드 시작 시에도 파일명 다시 한 번 갱신 (확실하게 하기 위함)
                filename_only = os.path.splitext(os.path.basename(target_file))[0]
                self.root.after(0, self.update_tree_filename, item_id, filename_only)

                if not os.path.exists(target_file + ".part") and os.path.exists(target_file):
                    self.items_data[item_id]['status_code'] = 'error'
                    self.root.after(0, self.update_status, item_id, "중복/취소", "파일 존재함")
                    self.root.after(0, lambda: messagebox.showinfo("알림", f"중복 파일: {filename_only}"))
                    self.root.after(0, lambda: self.finalize_task(item_id, False))
                    return

                ydl.download([url])

            self.items_data[item_id]['status_code'] = 'completed'
            self.root.after(0, self.update_status, item_id, "완료", "100%")
            self.root.after(0, lambda: self.finalize_task(item_id, True))

        except Exception as e:
            msg = str(e)
            if "USER_PAUSE" in msg:
                self.items_data[item_id]['status_code'] = 'paused'
                self.root.after(0, self.update_status, item_id, "일시정지", "대기 중...")
                if self.tree.selection() and self.tree.selection()[0] == item_id:
                    self.root.after(0, lambda: self.toggle_buttons('paused'))

            elif "USER_STOP" in msg:
                self.items_data[item_id]['status_code'] = 'stopped'
                self.root.after(0, self.update_status, item_id, "중지됨", "사용자 취소")
                self.root.after(0, lambda: self.finalize_task(item_id, True))
            else:
                self.items_data[item_id]['status_code'] = 'error'
                self.root.after(0, self.update_status, item_id, "실패", "에러 발생")
                print(f"Error: {e}")
                self.root.after(0, lambda: self.finalize_task(item_id, True))

    def finalize_task(self, item_id, release_slot):
        if release_slot:
            self.current_active_downloads -= 1
            if self.current_active_downloads < 0: self.current_active_downloads = 0
            self.process_queue()

        if self.tree.selection() and self.tree.selection()[0] == item_id:
            status = self.items_data[item_id]['status_code']
            self.toggle_buttons(status)

    def update_status(self, item_id, status=None, progress=None, status_text=None):
        """상태 컬럼만 안전하게 업데이트"""
        try:
            curr = self.tree.item(item_id)['values']
            new_status = status if status else curr[1]
            new_progress = progress if progress else (status_text if status_text else curr[2])
            self.tree.item(item_id, values=(curr[0], new_status, new_progress))
        except: pass

    def update_tree_filename(self, item_id, filename):
        """파일명 컬럼 업데이트"""
        try:
            curr = self.tree.item(item_id)['values']
            # curr[0]이 파일명 자리
            self.tree.item(item_id, values=(filename, curr[1], curr[2]))
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkDownloaderV4(root)
    root.mainloop()