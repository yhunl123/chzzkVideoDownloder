# Chzzk VOD Downloader (치지직 다시보기 다운로더)

네이버 치지직(Chzzk)의 다시보기(VOD) 영상을 다운로드할 수 있는 Python 기반의 GUI 프로그램입니다.
**yt-dlp**를 사용하여 메타데이터를 파싱하고, **FFmpeg**를 직접 호출하여 다운로드 안정성을 극대화했습니다.

## 📌 주요 기능

1. **편리한 GUI**: 명령 프롬프트(CLI)가 아닌 직관적인 윈도우 창에서 조작.
2. **대기열 시스템**: 여러 개의 링크를 등록하면 순차적/동시(최대 4개) 다운로드 진행.
3. **파일명 커스텀**: 채널명, 날짜, 시간, 제목 등을 조합하여 원하는 형식으로 파일명 자동 지정.
4. **중복 방지**: 이미 다운로드한 파일이 있거나, 중복된 요청일 경우 자동으로 건너뜀.
5. **로그인(쿠키) 지원**: 성인 인증 또는 유료 회원 전용 영상 다운로드 지원 (NID_AUT, NID_SES 입력).
6. **강력한 호환성**: `yt-dlp`에서 발생하는 `Initialization fragment` 오류를 우회하기 위해 **FFmpeg 직접 다운로드 모드** 탑재.
7. **설정 저장**: 저장 경로, 파일명 형식, 쿠키 정보를 프로그램 종료 후에도 유지.

## 🛠️ 필수 요구 사항 (Prerequisites)

이 프로그램은 **FFmpeg**가 반드시 필요합니다.

1. **FFmpeg 설치**: [FFmpeg 공식 홈페이지](https://ffmpeg.org/download.html)에서 다운로드.
2. **파일 배치**: `ffmpeg.exe` 파일을 **프로그램(소스코드 또는 exe)과 동일한 폴더**에 위치시켜야 합니다.

## 📥 설치 및 실행 방법 (소스 코드)

### 1. 라이브러리 설치
Python이 설치된 환경에서 아래 명령어로 필수 라이브러리를 설치합니다.
```bash
pip install yt-dlp pyinstaller
```
(Tkinter는 Python 내장 라이브러리이므로 별도 설치 불필요)

### 2. 코드 실행
최종 버전 코드(chzzk_downloader_final_v11.py)를 실행합니다.

```Bash
python chzzkVideoDownloder.py
```
📦 실행 파일(EXE) 만들기
다른 컴퓨터에서도 파이썬 없이 실행할 수 있도록 exe 파일로 패키징하는 방법입니다.

# 1. PyInstaller 실행
CMD 또는 터미널에서 다음 명령어를 입력합니다.

```Bash
pyinstaller --noconsole --onefile --name "ChzzkDownloader" chzzkVideoDownloder.py
```
--noconsole: 실행 시 검은색 콘솔 창을 띄우지 않음.

--onefile: 하나의 exe 파일로 생성.

# 2. 배포 시 주의사항
생성된 dist/ChzzkDownloader.exe 파일을 실행하려면, 반드시 같은 폴더에 ffmpeg.exe가 있어야 합니다.


## [폴더 구조 예시]

    📁 MyDownloader
    ├── 📄 ChzzkDownloader.exe
    └── 📄 ffmpeg.exe
## ⚙️ 설정 가이드
파일명 형식 변수
{artist}: 채널명 (예: 침착맨)

{title}: 영상 제목

{year}, {month}, {day}: 방송 날짜 (YYYY-MM-DD)

{hour}: 방송 시작 시간 (HH)

쿠키 설정 (성인/유료 영상)
브라우저에서 치지직(네이버) 로그인.

F12 (개발자 도구) -> Application 탭 -> Cookies -> https://nid.naver.com 또는 naver.com.

NID_AUT와 NID_SES의 값을 복사.

프로그램 우측 상단 **[🔒 로그인 설정]** 버튼 클릭 후 값 입력 및 저장.

## 📝 개발 히스토리 (Changelog)
이 프로젝트는 사용자의 피드백을 통해 다음과 같이 발전했습니다.

v1 ~ v2: 기본 GUI 구현 및 다중 다운로드 대기열(Queue) 시스템 적용.

v3: 파일명 포맷 확장 ({artist} 등) 및 중복 파일 감지 로직 추가.

v4: 다운로드 제어 버튼 (중지 등) 및 리스트 내 파일명 미리보기 기능 추가.

v5 ~ v6: 프로그램 설정(경로, 포맷) 및 쿠키 값 영구 저장 기능(config.json) 구현.

v7: 쿠키 입력 방식을 NID_AUT, NID_SES 분리 입력 방식으로 개선.

v8 ~ v10: 치지직 스트림 구조 문제로 인한 Initialization fragment found after media fragments 에러 해결 시도.

옵션 변경(hls_use_mpegts) -> 실패

해결책: yt-dlp는 주소 추출만 담당하고, 실제 다운로드는 FFmpeg Subprocess를 직접 호출하는 방식으로 변경 (v9, v10).

v11 : Deprecated Feature: Passing cookies as a header 보안 경고 해결.

헤더 주입 방식 대신 임시 쿠키 파일(Netscape format) 생성 방식으로 변경하여 안정성 확보.

**v8이 가장 이상적으로 v8로 롤백.**


## ⚠️ 트러블슈팅
**다운로드가 바로 실패해요**: 폴더에 ffmpeg.exe가 있는지 확인하세요.

**바이러스로 감지돼요**: 서명되지 않은 개인 개발 프로그램이라 발생하는 오진입니다. 백신 예외 설정을 하시면 됩니다.