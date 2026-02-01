# S2: Cross-repo 변경 (11-20 files)

여러 repo 간 변경. 롤백 계획과 재확인 필수.

---

## 전제조건
- 2개 이상 repo 대상
- 파일 11-20개
- LOC 2000줄 이하

---

## 흐름

```
1. 사용자: Cross-repo 요청
2. AI: local-search로 전체 검색 (MCP `repo_candidates`)
3. AI: 후보 repo 2~3개 제시
4. 사용자: repo 선택
5. AI: Mini Spec + 롤백 계획 작성
6. 사용자: 스펙 승인
7. AI: repo별 순차 변경 + 증거
8. AI: 전체 문서 업데이트
```

---

## Preflight 체크

- [ ] 목표/제약 1~2줄로 재진술
- [ ] 진행 의도 확인됨
- [ ] **local-search `repo_candidates`로 후보 탐색**
- [ ] repo 선택 완료 (Active scope 고정)
- [ ] lessons/debt/state 확인
- [ ] 롤백 계획 작성

---

## 롤백 계획 템플릿

```markdown
## 롤백 정의 (S2)
- git revert 단위: [커밋 해시 또는 설명]
- 검증 방법: [테스트 명령 또는 확인 방법]
```

---

## Postflight 체크

- [ ] 증거: repo별 경로 + diff
- [ ] Self-Review x2 완료
- [ ] lessons/debt/state 업데이트
- [ ] 롤백 검증 완료
- [ ] 테스트 증거

---

## 위험 신호 (S3로 승격)

- 파일 21개 이상 필요
- 데이터 마이그레이션 포함
- 인프라/배포 변경 필요
- 성능 크리티컬 영역