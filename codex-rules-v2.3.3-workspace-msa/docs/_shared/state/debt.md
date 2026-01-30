# Technical Debt

> 기술 부채 목록 (비커밋). 항목당 1~2줄, 총 ≤10줄.

## 형식
```
[YYYY-MM-DD] [tag1][tag2] 부채 설명 1~2줄
```

[2026-01-30] [process][docs] 문서 정합성 정리로 신규 부채 없음.
[2026-01-30] [tools][perf] docs/루트 인덱싱 확장 후 성능/노이즈 영향 모니터링 필요.
[2026-01-30] [tools][ops] 캐시 자동 마이그레이션 실패 시 레거시 경로 fallback 유지 가능.
[2026-01-30] [process][ops] install.sh 단독 실행은 git 의존(오프라인 대안 필요).
