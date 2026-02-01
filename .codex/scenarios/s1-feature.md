# S1: 기능 추가 (4-10 files)

단일 repo 내 중간 규모 변경. 스펙과 문서가 필수.

---

## 전제조건
- 단일 repo 대상
- 파일 4-10개
- LOC 1000줄 이하

---

## 흐름

```
1. 사용자: 기능 요청
2. AI: local-search로 관련 코드 검색
3. AI: Mini Spec 작성 (목표/범위/영향)
4. 사용자: 스펙 승인
5. AI: 변경 수행 + 증거
6. AI: lessons/debt/state 업데이트
```

---

## Preflight 체크

- [ ] 목표/제약 1~2줄로 재진술
- [ ] 진행 의도 확인됨
- [ ] **local-search로 먼저 검색** (MCP `search` 도구)
- [ ] lessons ≤10줄 확인
- [ ] debt ≤20줄 확인
- [ ] current-state ≤12줄 확인
- [ ] **관련 API/ERD/glossary 검색** (버그 방지)

---

## Mini Spec 템플릿

```markdown
## 목표
- [1~2줄 목표]

## 범위
- 변경 파일: [목록]
- 예상 LOC: [숫자]

## 영향
- API 변경: [있음/없음]
- 테스트 필요: [있음/없음]

## 위험
- [주요 리스크 1줄]
```

---

## Postflight 체크

- [ ] 증거: 경로 + diff (파일별)
- [ ] Self-Review x2 완료
- [ ] lessons/debt/state 업데이트
- [ ] 테스트 증거 (있으면)

---

## 위험 신호 (S2+로 승격)

- 파일 11개 이상 필요
- Cross-repo 영향
- 데이터 마이그레이션 필요
- 성능/동시성 영향