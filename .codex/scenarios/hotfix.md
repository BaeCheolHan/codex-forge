# Hotfix: 긴급 수정

> 속도는 올리되 P0~P2(안전/무결성/예산)는 절대 완화 금지.

---

## 핵심 원칙

1. Change/Run 승인 게이트 **유지**
2. Preflight/Postflight 문서 루프 **유지** (최소 예산)
3. 증거 **필수** (간소화 가능, 생략 불가)

---

## 최소 요구사항

- [ ] 목표 1줄로 명시
- [ ] 진행 의도 확인
- [ ] **local-search로 빠르게 탐색** (토큰 절감!)
- [ ] 변경 + diff 증거
- [ ] current-state ≤6줄 업데이트
- [ ] debt 1~2줄 기록 (필요 시)

---

## 흐름 (간소화)

```
1. 사용자: "긴급! OOO 수정해줘"
2. AI: local-search로 빠르게 탐색
3. AI: 변경 제안 (간략)
4. 사용자: "진행"
5. AI: 변경 + diff
6. AI: current-state + debt 업데이트
```

---

## 예외 없음

Hotfix라도 아래는 반드시 수행:

1. `02-knowledge.md`: Debt 기록 (1~2줄)
2. `01-checklists.md`: 경로 목록 + current-state ≤6줄

---

## 후속 조치 (Hotfix 후)

- [ ] 정식 테스트 추가 (1일 내)
- [ ] 문서 보완 (lessons 기록)
- [ ] 코드 리뷰 (동료)
