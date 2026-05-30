


# Git Branch 사용 규칙 및 연습 방법

## 브랜치란?

브랜치는 프로젝트를 안전하게 작업하기 위한 독립 작업 공간이다.

예를 들어:

* main → 최종 안정 버전
* practice/이름 → 개인 Git 연습용
* feature/기능명 → 실제 기능 개발용

으로 사용한다.

---

# 현재 브랜치 구조

```txt id="m4x8pq"
main                    -> 최종 안정 버전
practice/junghyeok     -> 중혁 연습용
practice/hyunseo       -> 현서 연습용
practice/dahyun        -> 다현 연습용
```

---

# 중요한 개념

## commit

```txt id="f8r2ny"
내 PC(로컬)에 저장
```

즉 commit은:

* 자기 컴퓨터에만 기록된다.
* 다른 팀원은 볼 수 없다.
* GitHub에도 아직 올라가지 않는다.

---

## push

```txt id="q3v9we"
GitHub 업로드
```

push 해야만:

* GitHub에 올라감
* 다른 팀원이 볼 수 있음

---

# 연습 단계 규칙

## 현재는 push 남발 금지

연습 목적은:

```txt id="d0m7tk"
add
commit
branch 이동
```

흐름 익히기이다.

따라서:

* 기본은 로컬 commit 연습
* push는 필요할 때만 사용

---

# main 브랜치 규칙

## main 직접 작업 금지

main 브랜치는:

* 최종 안정 버전 유지 목적
* 실행 가능한 상태 유지 목적

이다.

따라서:

* main에서 직접 코드 수정 금지
* practice 브랜치에서만 연습

---

# 현재 브랜치 확인

```bash id="u6k2ls"
git branch
```

현재 사용 중인 브랜치 앞에는 `*` 표시가 붙는다.

예:

```txt id="z9h1aq"
* practice/junghyeok
  main
```

---

# 자기 브랜치 이동

예시:

```bash id="x1p5vo"
git switch practice/junghyeok
```

---

# 연습 흐름

## 1. 파일 수정

예:

* README 수정
* 코드 추가
* 테스트 코드 작성

---

## 2. 변경 파일 등록(add)

```bash id="c7m4rq"
git add .
```

---

## 3. commit

```bash id="n2v8yz"
git commit -m "Practice commit"
```

현재 상태를 자기 PC에 저장한다.

---

## 4. 필요할 때만 push

```bash id="l5q0bw"
git push
```

GitHub에 업로드된다.

연습 단계에서는 무분별한 push 금지.

---

# 브랜치 변경 시 주의사항

브랜치를 변경하면 프로젝트 파일 상태도 같이 변경된다.

예:

```bash id="r8x3md"
git switch main
```

→ main 상태로 변경

```bash id="t1n7vk"
git switch practice/junghyeok
```

→ 중혁 브랜치 상태로 변경

---

# 원격 브랜치 확인

```bash id="p4k6qa"
git branch -a
```

예:

```txt id="g7m1ze"
main
remotes/origin/main
remotes/origin/practice/junghyeok
```

---

# 실수했을 때 확인

현재 상태 확인:

```bash id="w3r9lc"
git status
```

현재 브랜치 확인:

```bash id="y0m4pt"
git branch
```
