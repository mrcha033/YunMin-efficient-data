# ✅ YunMin-EfficientData Granular Task 목록

이 문서는 `YunMin-EfficientData` 프로젝트의 각 phase별로 **간결하며 검증 가능한 세부 작업(Task)** 을 정의합니다. 각 task는 **명확한 입력/출력 조건**, **구현 기준**, **테스트 방식**을 포함해야 하며, 기술 구현 계획서(`architecture.md`)의 전략을 실제 작업 단위로 분해한 것입니다.

---

## 🧹 Phase 1: 중복 제거 (SlimPajama 기반)

### 📁 1-1. 클라우드 기반 데이터 유효성 검증

* [ ] S3 `data/raw/` 경로에서 JSONL 스트리밍 로딩 구현 (`smart_open`, `boto3`)
* [ ] 각 라인별 JSON 유효성 검사 함수(`validate_json`) 구현 및 적용
* [ ] 유효/무효 문서 카운트 및 로그 출력
* [ ] 정제된 라인은 `data/dedup_ready/`에 저장, 샘플 5개는 `sample_preview.json`에 기록

### 🧠 1-2. MinHash-LSH 유사 문서 탐지

* [ ] 하이브리드 tokenizer 구현 (자모 3-gram + 단어 5-gram)
* [ ] `datasketch.MinHash`를 통해 128-perm 서명 생성
* [ ] Redis 기반 분산 LSH 인덱싱 (`MinHashLSH` with redis backend)
* [ ] 유사도 ≥ 0.8인 문서쌍 추출 및 `candidates.json`에 저장

### 🧹 1-3. 중복 제거 병렬화

* [ ] 중복 문서 클러스터에서 대표 문서 선정 (토큰 수 기반)
* [ ] Spark RDD 또는 Ray를 이용한 중복 제거 병렬 처리 (`mapPartitions`)
* [ ] 제거 전/후 문서 수 비교 및 `dedup_log.csv` 저장

---

## 📦 Phase 2: Parquet 변환 (Youmu 기반)

### 🔄 2-1. 스트리밍 기반 Parquet 변환

* [ ] `pyarrow.json.read_json`을 이용한 청크 단위 JSONL 처리
* [ ] 명시적 스키마 설정 및 `ParquetWriter.write_batch()` 구현
* [ ] 변환된 parquet는 `data/parquet/<domain>.parquet`에 저장
* [ ] 도메인별 스키마 파일(`schema.txt`) 작성 및 검증 코드 포함

### 🧪 2-2. 컬럼 압축 최적화 및 벤치마크

* [ ] 컬럼별 압축 전략 지정 (text → Brotli, tokens → Zstd)
* [ ] PyTorch Dataloader에서 Parquet 로딩 속도 측정 (JSONL 대비)
* [ ] `benchmark/io_speed.csv`에 속도, 메모리, 개선율 기록

---

## 🧠 Phase 3: DEM 기반 모델 학습 및 병합

### 🧩 3-1. 도메인별 LoRA 학습

* [ ] `dem/train_individual.py`에서 LoRA 경량 학습 (base model 고정)
* [ ] 학습 로그(`logs/train_<domain>.log`) 및 요약(`summary.csv`) 저장
* [ ] 학습된 adapter는 `models/lora_<domain>/adapter_model.bin`으로 저장

### 🧮 3-2. 차이 벡터 생성

* [ ] `vector_diff.py`로 base 모델과 LoRA 모델 간 weight 차이 계산
* [ ] 각 도메인 diff vector를 `.npy`로 저장 + norm, max, min 통계 기록
* [ ] 통계 결과는 `diff_stats/<domain>_summary.json`에 저장

### ➕ 3-3. 병합 및 성능 비교

* [ ] `merge_model.py`에서 diff vector 기반 병합 수행 (`base + Σ(wᵢ×diffᵢ)` 계산)
* [ ] 병합 모델을 `models/merged/`에 저장
* [ ] `eval/eval_prompt_comparison.md`에 base vs merged 응답 비교 저장

---

## 🔬 Phase 4: 통합 테스트 및 평가

### ⚙️ 4-1. 전체 파이프라인 자동 실행

* [ ] `scripts/run_pipeline.sh`에 전체 단계 연결
* [ ] 각 단계별 소요 시간, 성공 여부 기록 (`pipeline_run.log`)
* [ ] 오류 발생 시 `pipeline_errors.log`에 스택 트레이스 저장

### 📈 4-2. 평가 지표 계산 및 정량/정성 분석

* [ ] `compute_metrics.py`로 PPL, BLEU, ROUGE 계산
* [ ] `eval_runner.py`로 base vs merged 모델 응답 생성
* [ ] `summarize_eval.ipynb`에서 지표 시각화 및 비교표 생성
* [ ] 모든 결과는 `results/` 하위에 저장

### 📝 4-3. 최종 보고서 작성

* [ ] `docs/report.md`에 전체 지표 요약, 비교 그래프, 정성 평가 요약 포함
* [ ] 성능 향상 요인 및 한계, 개선 제안 포함

---

## 📎 전제 조건 및 기준

* 모든 py 파일은 **모듈화 + CLI 진입점(argparse)** 포함
* 모든 ipynb는 **출력 포함 상태**로 커밋, 내부에 그래프 시각화 존재해야 함
* 각 단계는 테스트 코드 1개 이상(`tests/`) 작성 필수

이 task 목록은 기술 전략서(`implementation-plan.md`)의 내용을 실행 가능한 granularity로 전개한 것으로, 각 항목은 자동화 스크립트와 병렬화 구성을 통해 반복 실행 가능해야 합니다.
