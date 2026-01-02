import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import threading
import os
import queue
import time

class ChzzkDownloaderV3:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다시보기 다운로더 (제어 기능 추가판)")
        self.root.geometry("800x650")

        # --- 변수 및 설정 ---
        self.max_concurrent_downloads = 4
        self.current_active_downloads = 0 # 일시정지 상태도 포함하여 카운트
        self.download_queue = queue.Queue()

        # item_id를 키로 사용하여 각 다운로드의 상태와 제어 플래그를 관리
        # flags: 'run' (기본), 'pause' (일시정지 요청), 'stop' (중지 요청)
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

        desc_lbl = tk.Label(format_frame, text="{artist}:채널명, {title}:제목, {year}/{month}/{day}/{hour}:방송일시",
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
        columns = ("url", "status", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.tree.heading("url", text="링크 / 제목")
        self.tree.heading("status", text="상태")
        self.tree.heading("progress", text="정보")
        self.tree.column("url", width=350)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("progress", width=150, anchor="center")

        # 스크롤바
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

        # 트리뷰 선택 이벤트 바인딩
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
        """리스트 선택 시 버튼 상태 업데이트"""
        selected = self.tree.selection()
        if not selected:
            self.toggle_buttons(None)
            return

        item_id = selected[0]
        status = self.items_data[item_id]['status_code'] # internal status code
        self.toggle_buttons(status)

    def toggle_buttons(self, status):
        """상태에 따라 버튼 활성화/비활성화"""
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
        else: # stopped, completed, etc.
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
            # 이미 다운로드 중일 때만
            if self.items_data[item_id]['status_code'] == 'downloading':
                self.items_data[item_id]['flag'] = 'pause'
                # UI 업데이트는 스레드 종료 시점에 처리되지만 즉각 반응을 위해
                self.update_status(item_id, "일시정지 중...", "종료 대기")

    def resume_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            if self.items_data[item_id]['status_code'] == 'paused':
                # 재개: 상태 변경 후 스레드 다시 시작
                self.items_data[item_id]['flag'] = 'run'
                self.start_download_thread(item_id, is_resume=True)

    def stop_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            current_status = self.items_data[item_id]['status_code']

            if current_status == 'waiting':
                # 대기열에 있는 경우 바로 취소 처리
                self.items_data[item_id]['status_code'] = 'stopped'
                self.update_status(item_id, "중지됨", "대기 취소")
                # 대기열 큐에서 제거하는 건 복잡하므로, 큐에서 꺼낼 때 status 확인하여 스킵하는 로직 필요
                # (여기서는 간단히 status_code를 체크하므로 process_queue에서 처리됨)

            elif current_status in ['downloading', 'paused']:
                self.items_data[item_id]['flag'] = 'stop'
                self.update_status(item_id, "중지 중...", "종료 대기")

    # --- 다운로드 로직 ---
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

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url: return

        item_id = self.tree.insert("", "end", values=(url, "대기 중", "0%"))

        self.items_data[item_id] = {
            "url": url,
            "output_path": self.path_entry.get(),
            "format_str": self.filename_entry.get(),
            "status_code": "waiting", # waiting, downloading, paused, stopped, completed, error
            "flag": "run" # run, pause, stop
        }

        self.download_queue.put(item_id)
        self.url_entry.delete(0, tk.END)
        self.process_queue()

    def process_queue(self):
        # 대기열 처리: 활성 다운로드 수가 최대치 미만이고 큐가 비어있지 않을 때
        while self.current_active_downloads < self.max_concurrent_downloads and not self.download_queue.empty():
            item_id = self.download_queue.get()

            # 큐에서 꺼냈는데 이미 사용자가 중지 버튼을 누른 경우 스킵
            if self.items_data[item_id]['status_code'] == 'stopped':
                continue

            self.start_download_thread(item_id)

    def start_download_thread(self, item_id, is_resume=False):
        # 재개가 아닌 신규 시작일 때만 슬롯 카운트 증가
        # 재개(Resume)는 이미 슬롯을 차지하고 있는 상태(Paused)에서 스레드만 다시 돌리는 것
        if not is_resume:
            self.current_active_downloads += 1

        self.items_data[item_id]['status_code'] = 'downloading'
        self.update_status(item_id, "다운로드 중", "시작 중...")

        # 버튼 상태 갱신 (현재 선택된 항목이라면)
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

        # 진행 상황 후크 (Pause/Stop 감지용)
        def progress_hook(d):
            if d['status'] == 'downloading':
                # 사용자 제어 플래그 확인
                flag = self.items_data[item_id]['flag']

                if flag == 'pause':
                    raise Exception("USER_PAUSE")
                elif flag == 'stop':
                    raise Exception("USER_STOP")

                # 진행률 표시
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
                # 메타데이터 업데이트
                info = ydl.extract_info(url, download=False)
                title = info.get('title', url)
                self.root.after(0, self.update_tree_title, item_id, title)

                # 중복 검사 (재개가 아닐 때만)
                target_file = ydl.prepare_filename(info)
                if not os.path.exists(target_file + ".part") and os.path.exists(target_file):
                    self.items_data[item_id]['status_code'] = 'error'
                    self.root.after(0, self.update_status, item_id, "중복/취소", "파일 존재함")
                    self.root.after(0, lambda: messagebox.showinfo("알림", f"중복 파일: {os.path.basename(target_file)}"))
                    self.root.after(0, lambda: self.finalize_task(item_id, False)) # 슬롯 반납
                    return

                # 다운로드 시작
                ydl.download([url])

            # 정상 완료
            self.items_data[item_id]['status_code'] = 'completed'
            self.root.after(0, self.update_status, item_id, "완료", "100%")
            self.root.after(0, lambda: self.finalize_task(item_id, True)) # 슬롯 반납

        except Exception as e:
            msg = str(e)
            if "USER_PAUSE" in msg:
                # 일시정지 처리: 슬롯 반납 안 함 (queue process 호출 안 함)
                self.items_data[item_id]['status_code'] = 'paused'
                self.root.after(0, self.update_status, item_id, "일시정지", "대기 중...")
                # 버튼 갱신
                if self.tree.selection() and self.tree.selection()[0] == item_id:
                    self.root.after(0, lambda: self.toggle_buttons('paused'))

            elif "USER_STOP" in msg:
                # 중지 처리: 슬롯 반납 함
                self.items_data[item_id]['status_code'] = 'stopped'
                self.root.after(0, self.update_status, item_id, "중지됨", "사용자 취소")
                self.root.after(0, lambda: self.finalize_task(item_id, True))

            else:
                # 실제 에러
                self.items_data[item_id]['status_code'] = 'error'
                self.root.after(0, self.update_status, item_id, "실패", "에러 발생")
                print(e)
                self.root.after(0, lambda: self.finalize_task(item_id, True))

    def finalize_task(self, item_id, release_slot):
        """작업 종료 시 슬롯 관리 및 대기열 실행"""
        if release_slot:
            self.current_active_downloads -= 1
            if self.current_active_downloads < 0: self.current_active_downloads = 0
            self.process_queue()

        # 선택된 항목의 버튼 상태 갱신
        if self.tree.selection() and self.tree.selection()[0] == item_id:
            status = self.items_data[item_id]['status_code']
            self.toggle_buttons(status)

    def update_status(self, item_id, status, progress):
        try:
            curr = self.tree.item(item_id)['values']
            self.tree.item(item_id, values=(curr[0], status, progress))
        except: pass

    def update_tree_title(self, item_id, title):
        try:
            curr = self.tree.item(item_id)['values']
            self.tree.item(item_id, values=(title, curr[1], curr[2]))
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkDownloaderV3(root)
    root.mainloop()