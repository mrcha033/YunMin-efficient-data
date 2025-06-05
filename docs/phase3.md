# 📌 YunMin-EfficientData Phase 3: DEM 기반 학습 및 병합 실현 계획서

본 문서는 YunMin-EfficientData 프로젝트의 Phase 3인 **Data Efficiency Method (DEM)** 기반 학습 및 모델 병합 작업의 구체적인 실행 계획을 다룹니다. 이 단계는 도메인별 데이터셋을 각각 LoRA 방식으로 경량 학습한 후, 파라미터 차이를 통합하여 하나의 고성능 모델을 생성하는 것을 목표로 합니다.

---

## 🎯 목표

* 도메인별 LoRA 경량 학습을 통해 데이터 특화 표현 학습
* 차이 벡터 기반 병합을 통해 전체 학습 없이 고효율 통합 모델 생성
* 학습 비용 최소화 + 성능 손실 없는 다도메인 수렴 유도

---

## 🏗️ 전체 구조

```
parquet_ready/                   # 도메인별 Parquet 학습 데이터
 ↓
dem/train_individual.py          # 도메인별 LoRA 모델 학습
 ↓
dem/vector_diff.py               # 차이 벡터(diff vector) 생성
 ↓
dem/merge_model.py               # 차이 벡터 기반 병합 모델 생성
 ↓
results/                         # 성능 비교, 로그, 병합 결과 저장
```

---

## 🧩 3-1. 개별 LoRA 모델 학습

### ✅ 학습 설정

1. **도메인 정의**

   * 예: `main_data`, `textbook`, `assembly`, `web`, `social`
   * 각 도메인은 `parquet_ready/<domain>.parquet`로 구성

2. **학습 방식**

   * LoRA 기반 경량 파인튜닝
   * Base 모델: `YunMin-Mamba 3B`
   * 고정 설정: `learning_rate=5e-5`, `batch_size=8`, `epochs=1`

3. **훈련 환경**

   * AWS: `ml.g5.2xlarge` or local A100 환경
   * mixed precision (`fp16`), gradient checkpointing enabled

4. **로그 관리**

   * loss, eval\_loss, epoch/step → `logs/train_<domain>.log`
   * 수렴 패턴 요약: `summary/train_<domain>.csv`

### 📦 출력 결과

* `checkpoints/lora_<domain>/adapter_model.bin`
* `logs/train_<domain>.log`, `summary/train_<domain>.csv`

---

## 🧮 3-2. 모델 차이 벡터 생성

### ✅ 절차

1. **기준 모델 로딩**

   * 학습 이전의 base model: `YunMin-Mamba 3B (pretrained)`

2. **도메인별 파라미터 로딩**

   * `LoRA weights + base model` → 전체 weight로 merge

3. **차이 벡터 계산**

   * 각 파라미터에 대해 `diff[key] = domain_model[key] - base_model[key]`
   * 정규화 옵션: 없음 or `L2 norm = 1` 표준화 가능

4. **검증**

   * `diff_vector` 평균 및 분산 통계 확인
   * 극단값 탐지: `|diff| > 3σ` 파라미터 비율 확인

### 📦 출력 결과

* `diff_vectors/diff_<domain>.npy`
* `diff_stats/diff_<domain>_summary.json`

---

## ➕ 3-3. 모델 병합 및 통합 검증

### ✅ 병합 전략

1. **가중치 조합 설정**

   * 예: `{main: 0.5, assembly: 0.3, web: 0.2}`
   * 총합 1.0으로 정규화

2. **병합 방식**

   * 병합 weight = `base + Σ(wᵢ × diffᵢ)`
   * 동일 파라미터 키만 병합 대상으로 포함

3. **응답 샘플링 검증**

   * Prompt 10개에 대해 base vs domain vs merged 모델 응답 비교
   * 평가 기준: 정보량, 논리성, 간결성, 톤 유지 여부 (5점 척도)

4. **수치 평가 지표**

   * perplexity (PPL), BLEU/ROUGE, MMLU 하위셋 (가능 시)

### 📦 출력 결과

* `merged_model/` (병합된 full weights)
* `results/eval_prompt_comparison.md`
* `results/metric_summary.csv`

---

## 📊 평가 기준

| 항목              | 기준 또는 기대 수치            |
| --------------- | ---------------------- |
| 학습 시간           | 도메인당 ≤ 2시간 (LoRA)      |
| 병합 소요 시간        | 전체 ≤ 20분               |
| PPL 개선률         | base 대비 3\~10% 향상      |
| 평가 프롬프트 유의미 개선률 | 10문장 중 6문장 이상          |
| 차이 벡터 정규성       | norm < 1.0, 무작위성 분포 유지 |

---

## 📎 체크리스트 요약

* [ ] 도메인별 parquet 데이터 확인
* [ ] train\_individual.py 학습 성공 및 로그 생성
* [ ] LoRA + base → 전체 weight 병합 스크립트 확인
* [ ] diff\_vector numpy 생성 및 요약 통계 검증
* [ ] merge\_model.py 병합 모델 정확히 생성됨
* [ ] 응답 비교 실험 및 평가 결과 문서화

---

## ⏱️ 예상 소요 시간

| 작업 단계          | 예상 시간 (1 도메인 기준) |
| -------------- | ---------------- |
| 개별 LoRA 학습     | 1.5\~2시간         |
| diff 벡터 계산     | 5분               |
| 병합 및 검증        | 15\~20분          |
| 전체 (5개 도메인 기준) | 10시간 이내          |

---

## 🔧 필요 라이브러리

* `peft`, `transformers`, `torch`
* `numpy`, `json`, `scipy`
* `accelerate`, `datasets`

---

## 📌 후속 연계 작업

* 병합 모델 기반 평가(BLEU, PPL, MMLU)
* Phase 4 리포트에 통합 성능 반영
* 병합 weight 시각화 및 선택 자동화 모듈 개발 (선택적)

---
