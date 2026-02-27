# PM-개발자 플레이북 (claude-pm + codex-dev)

> **언어 규칙**: 모든 문서, 로그, 보고서, GitHub Issue는 **한국어**로 작성합니다.
> claude-pm과 codex-dev 모두 공통 적용. 영어 작성 금지.

## 워크플로우

1. `claude-pm`이 `TASK_DIRECTIVE.md`에 `agent_coord.py add-task`로 태스크 등록
2. `codex-dev`가 구현 후 `agent_coord.py log`로 진행상황 기록
3. DB 관련 태스크는 현재 `codex-dev`가 담당 (gemini-db 일시 중단)
4. `codex-dev`가 `agent_coord.py complete-task`로 태스크 완료 처리
5. 완료 시 자동으로 `WORK_LOG.md` 기록 및 아카이브 조건 확인

## 역할별 책임

- **PM (claude-pm)**: 우선순위 결정, 범위 조정, 인수 기준 정의, GitHub Issue 작성, PR 리뷰
- **개발자 (codex-dev)**: 구현 세부사항, 테스트, 기술 리스크 노트
- DB 담당은 현재 `codex-dev` (일시 변경)
- 완료된 태스크는 반드시 `--summary`에 완료 요약 포함

## 필수 로그 규칙

- **착수 로그**: `action:log`으로 구현 시작 메모
- **완료 로그**: `complete-task`로 `action:complete` 기록
- **인수인계 로그**: PM이 리뷰 노트를 `action:log`로 추가 가능

## 네이밍 규칙

- 태스크 ID: `T-YYYYMMDD-XXX`
- 담당자: `claude-pm`, `codex-dev`, 또는 `shared`
- 우선순위: `P1`, `P2`, `P3`

## 명령어 예시

```bash
# 태스크 추가
python scripts/agent_coord.py add-task --title "..." --owner codex-dev --priority P1 --details "..."

# DB 태스크 추가 (현재 codex-dev 담당)
python scripts/agent_coord.py add-task --title "..." --owner codex-dev --priority P1 --details "..."

# 진행 로그
python scripts/agent_coord.py log --agent codex-dev --task-id T-YYYYMMDD-001 --message "..."

# 완료 처리
python scripts/agent_coord.py complete-task --id T-YYYYMMDD-001 --agent codex-dev --summary "..."
```
