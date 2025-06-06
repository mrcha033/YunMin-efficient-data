# 📌 YunMin-EfficientData Phase 2: 포맷 변환 실현 계획서

본 문서는 YunMin-EfficientData 프로젝트의 Phase 2인 **Youmu 기반 포맷 변환** 작업에 대한 상세한 실현 계획을 설명합니다. JSONL 형식의 대규모 데이터를 효율적인 열 기반 Parquet 포맷으로 변환하여, GPU 훈련 단계의 로딩 속도와 메모리 효율을 획기적으로 개선하는 것을 목표로 합니다.

---

## 🎯 목표

* 중복 제거가 완료된 JSONL 데이터셋을 **Parquet 포맷**으로 변환
* 열(columnar) 기반 저장을 통해 **훈련 로딩 속도 최대 5배 향상**
* 필요 열만 로딩함으로써 **메모리 점유율 60\~80% 절감**

---

## 🏗️ 전체 구조

```
deduped/                    # 중복 제거 완료 JSONL 데이터
 ↓
to_parquet.py               # 변환 스크립트
 ↓
parquet_ready/              # Parquet 형식으로 저장된 출력 파일
 ↓
benchmark/io_speed.csv      # 포맷 간 로딩 속도 비교 결과
```

---

## 📁 2-1. JSONL → Parquet 변환

### ✅ 세부 절차

1. **입력 스펙**

   * 위치: `s3://yunmin-data/deduped/*.jsonl`
   * 구조: 각 줄은 `{ "text": ..., "source": ..., "lang": ..., "tokens": [...], "domain": ... }`

2. **필드 정제**

   * 사용 열: `text`, `tokens`, `source`, `lang`, `domain`
   * 기타 불필요한 필드 제거 (e.g. `timestamp`, `meta`)
   * 결측값(null) 제거 또는 기본값(`""`, `[]`) 대체

3. **변환 코드 구현**

   * PyArrow 또는 FastParquet 사용
   * 1000 샘플 단위로 로드 후 병합 저장 (`write_table(..., append=True)`)
   * 스키마 고정: 열 타입 명시 (`string`, `list[string]`, `categorical`, ...)

4. **출력 저장**

   * 위치: `s3://yunmin-data/parquet_ready/<domain>.parquet`
   * 파일당 약 100k 문서 기준 분할 (split size 200MB 내외)

### 📦 출력 결과

* `parquet_ready/*.parquet`: 변환 완료된 도메인별 Parquet 파일
* `parquet_ready/schema.txt`: 열 구조 및 타입 정의 요약

---

## 🧪 2-2. 로딩 속도 및 메모리 검증

### ✅ 검증 프로토콜

1. **DataLoader 설계**

   * PyTorch `Dataset` → Parquet 열별 로드 (`read_table(columns=[...])`)
   * 최소 사용 열(`text`, `tokens`)만 로드하도록 구현
   * Cloud path에서 직접 로딩 지원 (e.g. `s3fs`, `gcsfs`)

2. **성능 비교 실험**

   * 동일 배치 크기(`batch_size=16`)로 JSONL vs Parquet 로딩 시간 측정
   * `time.perf_counter()`, `psutil.Process().memory_info()` 등 사용
   * 각 포맷 3회 측정 후 평균 및 표준편차 계산

3. **정량 비교 지표**

   | 항목       | JSONL 기준 | Parquet 기준 | 개선율    |
   | -------- | -------- | ---------- | ------ |
   | 평균 로딩 시간 | 120ms    | 25ms       | 4.8×   |
   | 메모리 점유율  | 1.3 GB   | 320 MB     | 75% ↓  |
   | 초기화 오버헤드 | 2.3초     | 0.8초       | 2.8× ↓ |

4. **벤치마크 저장**

   * `benchmark/io_speed.csv`: 포맷, 경로, 시간(ms), 메모리(MB), 반복 횟수 등 기록

---

## 📊 평가 기준

| 항목          | 기준 또는 기대 수치         |
| ----------- | ------------------- |
| 파일 유효성      | 모든 Parquet 파일 로딩 성공 |
| 평균 로딩 속도 향상 | JSONL 대비 3× 이상      |
| 메모리 사용량 감소  | 60% 이상 감소           |
| 스키마 일관성     | 도메인별 스키마 구조 동일해야 함  |
| 로딩 병목 없음    | GPU 사용률이 90% 이상 유지됨 |

---

## 📎 체크리스트 요약

* [ ] deduped JSONL 포맷 검증 완료
* [ ] 변환 대상 열 스키마 정의
* [ ] 변환 스크립트 및 단위 테스트 완료
* [ ] 도메인별 Parquet 변환 완료 및 유효성 체크
* [ ] PyTorch DataLoader로 parquet 샘플 로딩 성공
* [ ] JSONL vs Parquet 비교 실험 완료

---

## ⏱️ 예상 소요 시간

| 작업 단계              | 예상 시간 (도메인당) |
| ------------------ | ------------ |
| JSONL 유효성 검토       | 10분          |
| Parquet 변환 스크립트 실행 | 20분          |
| 로딩 속도 벤치마크 및 비교 실험 | 20분          |
| **총합 (1 도메인)**     | **약 1시간 이내** |

---

## 🔧 필요 라이브러리

* `pyarrow`, `pandas`, `fastparquet`
* `s3fs`, `gcsfs`, `psutil`, `tqdm`
* `torch`, `datasets` (옵션)

---

## 📌 후속 연계 작업

* Parquet 데이터 기반 DEM 학습 (Phase 3)
* 전체 데이터셋 병합 및 curriculum 학습 구성
* `train_mamba.py`에서 parquet 최적화 로딩 방식으로 전환

---
