# S0: 단순 버그 수정 (≤3 files)

가장 흔한 시나리오. 빠르게 수정하고 증거를 남긴다.

---

## 전제조건
- 단일 repo 대상
- 파일 3개 이하
- LOC 300줄 이하

---

## 흐름

```
1. 사용자: "OOO 버그 고쳐줘" (진행 의도 포함)
2. AI: local-search로 관련 파일 검색 (토큰 절감!)
3. AI: 검색 결과 기반 파일 탐색 (≤10 files 읽기)
4. AI: 변경 제안 + 영향 범위 설명
5. 사용자: "진행해" / "적용해"
6. AI: 변경 수행 + 증거(diff) 제시
7. AI: current-state 업데이트 (≤6줄)
```

---

## Preflight 체크

- [ ] 목표/제약 1~2줄로 재진술
- [ ] 진행 의도 확인됨
- [ ] **local-search로 먼저 검색** (MCP `search` 도구)
- [ ] current-state.md 확인 (≤6줄)

---

## Postflight 체크

- [ ] 증거: 경로 + diff (1~3 hunk)
- [ ] Self-Review x2 완료
- [ ] current-state 업데이트 (≤6줄)
- [ ] 변경 경로 목록 제시

---

## 예시 대화

**사용자**: `PaymentService에서 null pointer 버그 고쳐줘`

**AI 응답**:
```
1. local-search "PaymentService null" → 3개 파일 발견

변경 대상:
- PaymentService.java (null 체크 추가)

diff:
+ if (account == null) {
+     throw new IllegalArgumentException("account is null");
+ }

증거: PaymentService.java:45-48
업데이트: docs/_shared/state/current-state.md
```

---

## 위험 신호 (S1+로 승격)

아래 중 하나라도 해당하면 S1+ 시나리오로 전환:
- 파일 4개 이상 수정 필요
- API/DTO 변경 필요
- 테스트 파일 다수 수정 필요
- Cross-repo 영향