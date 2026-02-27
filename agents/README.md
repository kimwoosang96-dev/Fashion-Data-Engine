# 에이전트 협업 시스템

이 폴더는 멀티에이전트 실행을 위한 공유 운영 체계입니다.

> **언어 규칙**: 모든 문서, 로그, 보고서, GitHub Issue는 **한국어**로 작성합니다. (claude-pm, codex-dev 공통 적용)

## 역할

- `claude-pm`: 기획, 우선순위 결정, 태스크 배정, GitHub Issue 작성, PR 리뷰
- `codex-dev`: 구현, 테스트, 결과물 전달
- `gemini-db`: 일시 중단 (2026-02-27 기준)

## 핵심 파일

- `TASK_DIRECTIVE.md`: 단일 태스크 보드 (활성 + 최근 완료)
- `WORK_LOG.md`: 모든 에이전트의 추가 전용 활동 로그
- `archive/`: 자동으로 이동된 완료 태스크 보관

## 태스크 라인 형식

태스크당 한 줄 사용:

`- [ ] T-YYYYMMDD-XXX | <제목> | owner:<에이전트> | priority:P1|P2|P3 | status:active | created:YYYY-MM-DD | details:<설명>`

완료 시:

`- [x] ... | status:done | ... | completed:YYYY-MM-DD | ...`

## 자동화 명령

```bash
python scripts/agent_coord.py add-task --title "..." --owner codex-dev --priority P1 --details "..."
python scripts/agent_coord.py complete-task --id T-YYYYMMDD-XXX --agent codex-dev --summary "..."
python scripts/agent_coord.py log --agent codex-dev --task-id T-YYYYMMDD-XXX --message "..."
python scripts/agent_coord.py archive
```

`complete-task` 실행 시 항상 `WORK_LOG.md`에 추가 기록되며 아카이브 조건을 자동 확인합니다.

## 자동 아카이브 규칙

- `TASK_DIRECTIVE.md`가 220줄을 초과하면 트리거
- 가장 오래된 완료 태스크를 `archive/` 월별 파일로 이동
- 디렉티브를 170줄 수준으로 압축
