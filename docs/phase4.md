# 📌 YunMin-EfficientData Phase 4: 통합 테스트 및 평가 실현 계획서

본 문서는 YunMin-EfficientData 프로젝트의 Phase 4인 **E2E 파이프라인 통합 테스트 및 정량·정성 평가 단계**에 대한 구체적인 실현 계획을 설명합니다. 이 단계는 전체 데이터 파이프라인과 모델 결과를 최종 점검하며, 성능 개선 효과를 정량화하는 데 목적이 있습니다.

---

## 🎯 목표

* 전체 데이터 파이프라인(Phase 1\~3) 자동화 및 실행 검증
* 모델 성능 비교(PPL, BLEU, 응답 품질) 실험 수행
* 결과 보고서 및 차기 개선 방향 정리

---

## 🏗️ 전체 구조

```
run_pipeline.sh                  # 전체 파이프라인 자동 실행 스크립트
 ↓
pipeline_run.log / errors.log     # 실행 로그 및 오류 기록
 ↓
eval/                            # 평가용 prompt, 결과 응답 저장
 ↓
results/                         # 수치 결과, 그래프, 비교 문서
 ↓
docs/report.md                   # 최종 성능 평가 및 요약 보고서
```

---

## ⚙️ 4-1. E2E 파이프라인 실행 테스트

### ✅ 구성 요소

1. **스크립트 구성**

   * 각 Phase 스크립트(`dedup.py`, `jsonl_to_parquet.py`, `train_individual.py`, `merge_model.py`)를 순차 호출
   * 환경 변수 및 데이터 경로 자동 지정 (예: `.env` 또는 argparse)

2. **로그 기록**

   * 표준 출력 → `pipeline_run.log`
   * stderr 출력 또는 예외 → `pipeline_errors.log`

3. **검증 항목**

   * 단계별 성공 여부
   * 소요 시간 측정
   * 출력 파일 유효성 검사 (`os.path.exists`, schema 체크 등)

### 📦 출력 결과

* `pipeline_run.log`, `pipeline_errors.log`
* 각 Phase 출력 파일 및 검증 플래그

---

## 📈 4-2. 성능 비교 실험

### ✅ 지표 구성

1. **Perplexity (PPL)**

   * 평가용 문장 100개에 대해 base vs merged 모델 비교
   * `transformers.EvalPrediction` 또는 custom GPT 추론

2. **BLEU / ROUGE / BERTScore**

   * reference 응답과 모델 생성 응답 비교 (문장 단위 기준)
   * `sacrebleu`, `rouge_score`, `bertscore` 라이브러리 활용

3. **응답 비교 정성 평가**

   * 프롬프트 10개에 대해 base/merged 응답 나란히 저장
   * 평가자(또는 룰베이스) 기준 3점 척도 평가 (정보성, 자연성, 일관성)

4. **로딩 및 메모리 사용량 측정 (선택적)**

   * 각 모델 추론 시 peak memory 기록 (`psutil`, `tracemalloc`)

### 📦 출력 결과

* `results/perplexity.csv`
* `results/bleu_rouge_bertscore.csv`
* `eval/eval_prompt_comparison.md`

---

## 📝 4-3. 최종 보고서 작성

### ✅ 보고서 구조

1. **요약 개요**

   * 파이프라인 요약 구조 및 수행 기간
   * 데이터, 모델 크기, 스펙 등

2. **중복 제거 및 효율성 지표**

   * 중복률 감소 (%), 파일 수, 용량 변화
   * parquet 변환 후 로딩 속도 개선율

3. **모델 성능 비교**

   * PPL 및 BLEU 수치 비교
   * 정성적 응답 평가 요약

4. **기술 스택 및 인프라 요약**

   * 사용 GPU, 실행 시간, 비용 등

5. **문제점 및 개선 제안**

   * 병합 과정에서의 손실 가능성
   * 데이터 편향 및 정규화 필요성
   * 차기 버전(Phase 5)의 제안 항목

### 📦 출력 결과

* `docs/report.md`: 마크다운 형식 최종 보고서
* `docs/report.pdf` (선택): PDF 렌더링 버전

---

## 📊 평가 기준 요약

| 항목             | 기대 수치 또는 기준         |
| -------------- | ------------------- |
| 파이프라인 실행 성공률   | 100%                |
| PPL 감소율        | base 대비 ≥ 5%        |
| BLEU 향상        | ≥ 2.0 BLEU 점수 상승    |
| 응답 정성 평가 우수 비율 | 10개 중 ≥ 6개 우수 평가 응답 |
| 오류 발생률         | 1% 이하               |

---

## 📎 체크리스트 요약

* [ ] run\_pipeline.sh 작성 및 실행 검증
* [ ] logs, errors 로그 파일 자동 생성 확인
* [ ] base vs merged 모델 평가셋 PPL 측정 완료
* [ ] BLEU/ROUGE 정량 비교 완료
* [ ] 응답 비교 문서화 및 정성 평가 수행
* [ ] 최종 보고서 `docs/report.md` 작성 완료

---

## ⏱️ 예상 소요 시간

| 작업 단계           | 예상 시간      |
| --------------- | ---------- |
| 전체 파이프라인 실행     | 30분\~1시간   |
| 평가 프롬프트 추론 및 분석 | 1시간        |
| 지표 계산 및 그래프 정리  | 30분        |
| 보고서 작성 및 편집     | 1시간        |
| **총합**          | **3\~4시간** |

---

## 🔧 필요 라이브러리

* `transformers`, `datasets`, `torch`
* `sacrebleu`, `rouge_score`, `bertscore`
* `psutil`, `matplotlib`, `pandas`
* `markdown`, `jinja2` (보고서 자동화 시)

---

## 📌 후속 작업 (Phase 5 연계)

* 일반화 테스트셋(MMLU, KoNLI 등) 확장 평가
* 자동 보고서 템플릿 생성 및 시각화 대시보드 연결
* merged 모델 기준 지속적 적응 학습 실험 설계

---

본 계획은 YunMin-Mamba의 최종 통합 성능을 정량적으로 검증하고, 프로젝트의 ROI(Return on Infrastructure)를 극대화하는 데 초점을 둡니다.
