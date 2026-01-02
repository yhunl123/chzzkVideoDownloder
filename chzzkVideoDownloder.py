import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import threading
import os
import queue
import json
import subprocess # FFmpeg 직접 실행을 위해 추가

CONFIG_FILE = "chzzk_config.json"

class ChzzkDownloaderFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다운로더 (최종: FFmpeg 직접 호출 모드)")
        self.root.geometry("800x650")

        # --- 변수 및 설정 ---
        self.max_concurrent_downloads = 4
        self.current_active_downloads = 0
        self.download_queue = queue.Queue()
        self.items_data = {}

        # 설정 기본값
        self.config = {
            "save_path": os.path.join(os.path.expanduser('~'), 'Downloads'),
            "filename_format": "{artist} {year}-{month}-{day} {hour}H {title}.mp4",
            "nid_aut": "",
            "nid_ses": ""
        }

        self.load_config()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for key in self.config.keys():
                        if key in loaded:
                            self.config[key] = loaded[key]
            except Exception as e:
                print(f"설정 로드 실패: {e}")

    def save_config_file(self):
        self.config["save_path"] = self.path_entry.get()
        self.config["filename_format"] = self.filename_entry.get()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"설정 저장 실패: {e}")

    def on_closing(self):
        self.save_config_file()
        self.root.destroy()

    def create_widgets(self):
        top_frame = tk.Frame(self.root, padx=10, pady=5)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="치지직 다운로더 Final", font=("Bold", 14)).pack(side="left")
        btn_cookie = tk.Button(top_frame, text="🔒 로그인 설정 (NID)", command=self.open_cookie_popup)
        btn_cookie.pack(side="right")

        path_frame = tk.LabelFrame(self.root, text="1. 저장 경로", padx=10, pady=10)
        path_frame.pack(fill="x", padx=10, pady=5)
        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.path_entry.insert(0, self.config["save_path"])
        btn_path = tk.Button(path_frame, text="폴더 변경", command=self.select_directory)
        btn_path.pack(side="right")

        format_frame = tk.LabelFrame(self.root, text="2. 파일 이름 형식", padx=10, pady=10)
        format_frame.pack(fill="x", padx=10, pady=5)
        desc_lbl = tk.Label(format_frame, text="{artist}:채널명, {title}:제목, {year}/{month}/{day}/{hour}:방송일시", fg="gray", font=("System", 9))
        desc_lbl.pack(anchor="w")
        self.filename_entry = tk.Entry(format_frame)
        self.filename_entry.pack(fill="x")
        self.filename_entry.insert(0, self.config["filename_format"])

        input_frame = tk.LabelFrame(self.root, text="3. 다운로드 추가", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=5)
        self.url_entry = tk.Entry(input_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", lambda event: self.add_to_queue())
        self.btn_add = tk.Button(input_frame, text="추가", bg="#00C73C", fg="white", command=self.add_to_queue)
        self.btn_add.pack(side="right")

        list_frame = tk.LabelFrame(self.root, text="4. 다운로드 목록 및 제어", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("filename", "status", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.tree.heading("filename", text="파일명 (확장자 제외)")
        self.tree.heading("status", text="상태")
        self.tree.heading("progress", text="정보")
        self.tree.column("filename", width=400)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("progress", width=120, anchor="center")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        control_frame = tk.Frame(list_frame, pady=5)
        control_frame.pack(side="bottom", fill="x")
        self.btn_pause = tk.Button(control_frame, text="일시정지", command=self.pause_item, state="disabled")
        self.btn_pause.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_resume = tk.Button(control_frame, text="다운로드 재개", command=self.resume_item, state="disabled")
        self.btn_resume.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_stop = tk.Button(control_frame, text="다운로드 중지", command=self.stop_item, state="disabled", fg="red")
        self.btn_stop.pack(side="left", padx=5, expand=True, fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="일시정지", command=self.pause_item)
        self.context_menu.add_command(label="재개", command=self.resume_item)
        self.context_menu.add_command(label="중지", command=self.stop_item)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def open_cookie_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("네이버 로그인 정보 (NID)")
        popup.geometry("450x250")
        popup.resizable(False, False)

        lbl_info = tk.Label(popup, text="성인/유료 영상을 받으려면 브라우저 쿠키 값이 필요합니다.\nF12(개발자도구) > Application > Cookies 에서 확인 가능", justify="center", fg="gray", pady=10)
        lbl_info.pack()

        form_frame = tk.Frame(popup, padx=20)
        form_frame.pack(fill="x")
        lbl_aut = tk.Label(form_frame, text="NID_AUT :", font=("Bold", 10))
        lbl_aut.grid(row=0, column=0, sticky="w", pady=5)
        entry_aut = tk.Entry(form_frame, width=40)
        entry_aut.grid(row=0, column=1, pady=5, padx=5)
        entry_aut.insert(0, self.config["nid_aut"])

        lbl_ses = tk.Label(form_frame, text="NID_SES :", font=("Bold", 10))
        lbl_ses.grid(row=1, column=0, sticky="w", pady=5)
        entry_ses = tk.Entry(form_frame, width=40)
        entry_ses.grid(row=1, column=1, pady=5, padx=5)
        entry_ses.insert(0, self.config["nid_ses"])

        def save_tokens():
            self.config["nid_aut"] = entry_aut.get().strip()
            self.config["nid_ses"] = entry_ses.get().strip()
            self.save_config_file()
            messagebox.showinfo("저장 완료", "로그인 정보가 저장되었습니다.", parent=popup)
            popup.destroy()

        btn_save = tk.Button(popup, text="저장 및 닫기", bg="#00C73C", fg="white", width=20, height=2, command=save_tokens)
        btn_save.pack(pady=20)

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
        # 직접 FFmpeg를 쓰므로 일시정지/재개는 지원하기 어려움 (FFmpeg 프로세스 제어 복잡성 때문)
        # 따라서 중지만 활성화
        if status == 'downloading':
            self.btn_pause.config(state="disabled")
            self.btn_resume.config(state="disabled")
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

    def pause_item(self):
        messagebox.showinfo("알림", "FFmpeg 직접 다운로드 모드에서는 일시정지를 지원하지 않습니다.")

    def resume_item(self):
        pass

    def stop_item(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            current_status = self.items_data[item_id]['status_code']
            if current_status == 'waiting':
                self.items_data[item_id]['status_code'] = 'stopped'
                self.update_status(item_id, "중지됨", "대기 취소")
            elif current_status == 'downloading':
                self.items_data[item_id]['flag'] = 'stop'
                self.update_status(item_id, status_text="중지 중...")

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

    # --- 메타데이터 추출용 쿠키 설정 ---
    def get_cookies_dict(self):
        nid_aut = self.config.get("nid_aut", "").strip()
        nid_ses = self.config.get("nid_ses", "").strip()
        if nid_aut and nid_ses:
            return {'NID_AUT': nid_aut, 'NID_SES': nid_ses}
        return {}

    # --- FFmpeg 헤더 문자열 생성 ---
    def get_ffmpeg_headers(self):
        headers = "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36\r\n"
        nid_aut = self.config.get("nid_aut", "").strip()
        nid_ses = self.config.get("nid_ses", "").strip()
        if nid_aut and nid_ses:
            headers += f"Cookie: NID_AUT={nid_aut}; NID_SES={nid_ses};\r\n"
        return headers

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url: return
        item_id = self.tree.insert("", "end", values=("정보 불러오는 중...", "대기 중", "0%"))
        self.items_data[item_id] = {
            "url": url, "output_path": self.path_entry.get(),
            "format_str": self.filename_entry.get(),
            "status_code": "waiting", "flag": "run",
            "process": None # subprocess 저장용
        }
        threading.Thread(target=self.prefetch_metadata, args=(item_id,), daemon=True).start()
        self.download_queue.put(item_id)
        self.url_entry.delete(0, tk.END)
        self.process_queue()

    def prefetch_metadata(self, item_id):
        # yt-dlp로 메타데이터(제목, m3u8 주소)만 가져옴
        data = self.items_data[item_id]

        ydl_opts = {
            'quiet': True, 'no_warnings': True,
            'format': 'best', # 메타데이터용
        }

        # 쿠키 적용
        cookies = self.get_cookies_dict()
        if cookies:
            ydl_opts['cookiefile'] = None # 파일 대신 딕셔너리 사용 시도 또는 헤더 주입 필요
            # yt-dlp에서 cookies dict 지원이 불안정할 수 있으므로 http_headers 사용
            cookie_str = f"NID_AUT={cookies['NID_AUT']}; NID_SES={cookies['NID_SES']};"
            ydl_opts['http_headers'] = {'Cookie': cookie_str}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(data['url'], download=False)
                # 실제 영상 스트림 URL (m3u8)
                data['stream_url'] = info.get('url')

                # 파일명 계산
                target_filename = ydl.prepare_filename(info)
                filename_only = os.path.splitext(os.path.basename(target_filename))[0]

                # 데이터 저장
                self.items_data[item_id]['target_filename'] = filename_only
                self.root.after(0, self.update_tree_filename, item_id, filename_only)

        except Exception as e:
            self.root.after(0, self.update_tree_filename, item_id, f"오류: {data['url']}")
            # 실패 시 다운로드 불가 처리
            self.items_data[item_id]['status_code'] = 'error'

    def process_queue(self):
        while self.current_active_downloads < self.max_concurrent_downloads and not self.download_queue.empty():
            item_id = self.download_queue.get()
            if self.items_data[item_id]['status_code'] == 'stopped': continue
            self.start_download_thread(item_id)

    def start_download_thread(self, item_id, is_resume=False):
        if not is_resume: self.current_active_downloads += 1
        self.items_data[item_id]['status_code'] = 'downloading'
        self.update_status(item_id, "다운로드 중", "FFmpeg 실행 중...")
        if self.tree.selection() and self.tree.selection()[0] == item_id:
            self.toggle_buttons('downloading')
        t = threading.Thread(target=self.download_task_ffmpeg, args=(item_id,))
        t.daemon = True
        t.start()

    def download_task_ffmpeg(self, item_id):
        # yt-dlp가 아닌 FFmpeg subprocess 직접 실행
        data = self.items_data[item_id]

        # 1. 스트림 URL 확보 확인
        if 'stream_url' not in data:
            # prefetch에서 실패했거나 아직 안된 경우 다시 시도 (생략, prefetch가 먼저 끝난다고 가정)
            self.root.after(0, self.update_status, item_id, "실패", "주소 확보 불가")
            self.root.after(0, lambda: self.finalize_task(item_id, True))
            return

        stream_url = data['stream_url']
        save_name = data.get('target_filename', 'download_video') + ".mp4"
        full_path = os.path.join(data['output_path'], save_name)

        # 중복 체크
        if os.path.exists(full_path):
            self.items_data[item_id]['status_code'] = 'error'
            self.root.after(0, self.update_status, item_id, "중복/취소", "파일 존재함")
            self.root.after(0, lambda: messagebox.showinfo("알림", f"중복 파일: {save_name}"))
            self.root.after(0, lambda: self.finalize_task(item_id, True))
            return

        # 2. FFmpeg 명령어 구성
        headers = self.get_ffmpeg_headers()

        # ffmpeg -y -headers "..." -i "URL" -c copy -bsf:a aac_adtstoasc "output.mp4"
        cmd = [
            'ffmpeg',
            '-y', # 덮어쓰기 허용 (어차피 중복체크 함)
            '-headers', headers,
            '-i', stream_url,
            '-c', 'copy', # 재인코딩 없이 복사 (최고속도/화질보존)
            '-bsf:a', 'aac_adtstoasc', # m3u8 to mp4 변환 시 필수 필터
            full_path
        ]

        # 3. 프로세스 실행
        try:
            # 윈도우에서 콘솔창 뜨지 않게 설정
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo
            )
            self.items_data[item_id]['process'] = process

            # 프로세스 종료 대기
            while process.poll() is None:
                # 사용자가 중지 요청했는지 확인
                if self.items_data[item_id]['flag'] == 'stop':
                    process.kill()
                    self.root.after(0, self.update_status, item_id, "중지됨", "사용자 취소")
                    self.root.after(0, lambda: self.finalize_task(item_id, True))
                    return

                # 진행률은 파싱하기 어려우므로 '진행 중' 표시 유지
                # 필요하다면 stderr를 읽어서 duration 대비 time을 계산해야 함 (복잡도 상승)
                self.root.after(0, self.update_status, item_id, "다운로드 중", "영상 저장 중...")

                process.wait(timeout=1.0) # 1초마다 상태 체크

            # 종료 후 상태 확인
            if process.returncode == 0:
                self.items_data[item_id]['status_code'] = 'completed'
                self.root.after(0, self.update_status, item_id, "완료", "100%")
            else:
                # 에러 발생
                self.items_data[item_id]['status_code'] = 'error'
                self.root.after(0, self.update_status, item_id, "실패", f"코드 {process.returncode}")

        except Exception as e:
            print(f"FFmpeg 실행 에러: {e}")
            self.items_data[item_id]['status_code'] = 'error'
            self.root.after(0, self.update_status, item_id, "실패", "실행 오류")

        finally:
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
        try:
            curr = self.tree.item(item_id)['values']
            new_status = status if status else curr[1]
            new_progress = progress if progress else (status_text if status_text else curr[2])
            self.tree.item(item_id, values=(curr[0], new_status, new_progress))
        except: pass

    def update_tree_filename(self, item_id, filename):
        try:
            curr = self.tree.item(item_id)['values']
            self.tree.item(item_id, values=(filename, curr[1], curr[2]))
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkDownloaderFinal(root)
    root.mainloop()