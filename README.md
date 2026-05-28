

# Smart Road Risk System

실시간 센서 데이터와 공공데이터를 활용한 도로 위험도 분석 IoT 시스템

---

# 프로젝트 구조

```txt
150_project/
│
├── firmware/
├── backend/
├── frontend/
└── docs/
```

---

# 개발 환경

* STM32CubeIDE
* Node.js
* Python
* SQLite
* MQTT

---

# 프로젝트 Clone

```bash
git clone 저장소주소
cd 150_project
```

---

# Git 사용자 설정

각자 자신의 GitHub 계정으로 설정

```bash
git config user.name "본인이름"
git config user.email "본인이메일"
```

확인:

```bash
git config --list
```

---

# Node.js 서버 실행 환경 설정

realtime_server 이동

```bash
cd backend/realtime_server
```

패키지 설치

```bash
npm install
```

서버 실행

```bash
node src/app.js
```

---

# Python ML 서버 환경 설정

ml_server 이동

```bash
cd backend/ml_server
```

가상환경 생성

Windows:

```bash
python -m venv team_env
```

가상환경 활성화

PowerShell:

```powershell
team_env\Scripts\Activate.ps1
```

패키지 설치

```bash
pip install -r requirements.txt
```

Flask 서버 실행

```bash
python app.py
```

---

# STM32 프로젝트 열기

STM32CubeIDE 실행

* File
* Import
* Existing Projects into Workspace

프로젝트 경로:

```txt
firmware/stm32
```

---

# Git 협업 규칙

* main 브랜치 직접 push 금지
* feature 브랜치 생성 후 작업
* Pull Request 생성 후 merge

브랜치 예시:

```txt
feature/stm32
feature/server
feature/ml
feature/dashboard
```

---

# .gitignore 대상

다음 파일은 GitHub에 업로드하지 않음

```txt
node_modules/
team_env/
Debug/
.vscode/
.metadata/
... 
ignore 파일보면 훨씬 많음
```
