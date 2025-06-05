# 📦 프로젝트 개요: YunMin-EfficientData

**YunMin-EfficientData**는 YunMin-Mamba의 성능을 뒷받침할 고효율 데이터 파이프라인을 구축하는 프로젝트입니다. 본 프로젝트는 다음 세 가지 최신 기술을 통합 적용합니다:

1. **SlimPajama 기반 중복 제거 (Deduplication)**
2. **Youmu 기반 컬럼형 고성능 데이터 로딩**
3. **DEM (Data Efficiency Method) 기반 다중 데이터셋 학습 최적화**

---

## 🧭 프로젝트 목표

* 한국어 대규모 말뭉치에 대한 **정제(deduplication)·최적화·효율적 학습 구조화**를 수행한다.
* 최대한 적은 비용으로 **최대의 성능 향상**을 이끌어낸다.
* 추후 YunMin-Mamba 3B/7B의 사전학습 또는 SFT에 사용 가능한 **범용 고효율 데이터 포맷**을 생산한다.

---

## 🏗️ 프로젝트 구조

```
YunMin-efficient-data/
├── data/                      # 데이터 저장 (raw, 중복 제거, parquet)
│   ├── raw/                  # 원본 JSONL 데이터 (from S3 or local)
│   ├── dedup_ready/          # 정제된 JSONL 파일
│   ├── deduped/              # 중복 제거 완료 파일
│   └── parquet/              # 열 기반 Parquet 포맷 변환 결과
│
├── models/                   # 모델 체크포인트 및 병합 결과
│   ├── base/                 # 사전학습된 YunMin-Mamba base 모델
│   ├── lora_<domain>/        # 도메인별 LoRA adapter weight
│   └── merged/               # DEM 병합 결과 모델
│
├── dedup/                    # SlimPajama 기반 중복 제거 모듈
│   ├── slimpajama_dedup.py  # 메인 중복 제거 스크립트
│   ├── minhash_utils.py     # MinHash + LSH 처리 모듈
│   ├── cluster_reduction.py # 대표 문서 선택 로직
│   └── stats_analysis.ipynb # 중복률 시각화 및 통계 분석
│
├── format/                   # Youmu 포맷 변환 (JSONL → Parquet)
│   ├── to_parquet.py        # 변환 메인 스크립트
│   ├── parquet_utils.py     # schema 지정 및 열 필터링 유틸
│   └── parquet_profile.ipynb # 포맷별 속도/용량 분석 notebook
│
├── dem/                      # Data Efficiency Method 학습 및 병합
│   ├── train_individual.py  # 도메인별 LoRA 미세조정 스크립트
│   ├── vector_diff.py       # base와의 차이 벡터 계산
│   ├── merge_model.py       # diff vector 병합 스크립트
│   └── diff_analysis.ipynb  # diff 벡터 norm 및 시각화 notebook
│
├── evaluation/               # Phase 4: 성능 평가 및 비교
│   ├── compute_metrics.py   # PPL, BLEU, ROUGE 등 지표 계산기
│   ├── eval_prompts.jsonl   # 비교용 prompt 리스트 (10~100개)
│   ├── eval_runner.py       # base vs merged 응답 생성 및 비교
│   ├── summarize_eval.ipynb # 평가 수치 분석 및 표 그리기
│   └── scoring_rules.yaml   # 정성 평가 기준 정의
│
├── scripts/                  # 실행 자동화 및 공통 유틸
│   ├── run_pipeline.sh      # 전체 파이프라인 실행 스크립트
│   ├── setup_env.sh         # venv, requirements 설치 스크립트
│   └── test_loading_speed.py# parquet vs jsonl I/O 벤치마크
│
├── configs/                  # 설정 파일 저장소
│   ├── dataset_config.yaml  # S3 경로, 열 명세, 토큰화 설정 등
│   ├── dem_config.yaml      # DEM 가중치 설정
│   └── logging.yaml         # 로깅 포맷 및 레벨
│
├── docs/                     # 문서 및 리포트
│   ├── architecture.md      # 전체 시스템 설계 개요
│   ├── tasks.md             # 단계별 granular task 목록
│   ├── phase1.md            # 중복 제거 상세 계획
│   ├── phase2.md            # 포맷 변환 상세 계획
│   ├── phase3.md            # DEM 학습 상세 계획
│   ├── phase4.md            # 성능 평가 상세 계획
│   └── report.md            # 최종 성능 보고서
│
├── tests/                    # PyTest 기반 유닛 테스트
│   ├── test_dedup.py        # dedup 관련 기능 테스트
│   ├── test_format.py       # parquet 변환 테스트
│   ├── test_dem.py          # diff vector 병합 검증
│   └── test_eval.py         # 지표 계산 및 응답 비교 테스트
│
├── requirements.txt         # Python 패키지 목록
├── .env.example             # 환경변수 템플릿
├── .gitignore
└── README.md```

---

## 🔍 각 기술 적용 방식

### 1. SlimPajama 기반 중복 제거

* **목표**: 동일/유사 문장의 반복을 제거하여 GPU 리소스 낭비 방지
* **방법**:

  * MinHash + LSH를 이용한 유사도 기반 중복 제거
  * token-level N-gram 기반 fingerprint 생성
  * 중복률 0.8 이상일 경우 제거

### 2. Youmu 포맷 적용

* **목표**: 데이터 로딩 시간 최소화, GPU 메모리 점유율 절감
* **방법**:

  * Parquet 포맷으로 변환 (열 기반 저장)
  * 필요한 열만 로드하여 DataLoader 구성
  * DDP 학습에서도 columnar shard로 병렬 I/O 지원

### 3. DEM (Data Efficiency Method)

* **목표**: 여러 도메인별 데이터셋을 효과적으로 통합
* **방법**:

  * 각 도메인별로 미니 모델 훈련
  * 해당 모델들의 차이값(difference vector)을 계산
  * 적절한 가중치로 병합해 전체 모델 생성

---

## 📊 기대 효과

| 항목        | 기대 수치                |
| --------- | -------------------- |
| 데이터 용량 감소 | 최대 50% ↓             |
| 훈련 비용 절감  | DEM 기준 70\~90% ↓     |
| 로딩 속도 개선  | 기존 JSONL 대비 최대 5× ↑  |
| 메모리 효율성   | 최대 80% 절감 (Youmu 기준) |
| 성능 향상     | MMLU 기준 최대 15% ↑     |

---

## 🗓️ 일정 (예정)

| 단계                 | 기간     | 주요 산출물                  |
| ------------------ | ------ | ----------------------- |
| Phase 1: 중복 제거     | 1주차    | dedup된 한국어 말뭉치          |
| Phase 2: 포맷 변환     | 2주차    | Parquet 포맷 변환 완료        |
| Phase 3: DEM 모델 학습 | 3\~4주차 | 각 도메인별 모델, 병합된 모델       |
| Phase 4: 통합 테스트    | 5주차    | end-to-end 파이프라인 성능 보고서 |

---

## 📌 참고 문헌 및 기술 출처

* SlimPajama: [https://www.cerebras.ai/blog/slimpajama-a-627b-token-cleaned-and-deduplicated-version-of-redpajama](https://www.cerebras.ai/blog/slimpajama-a-627b-token-cleaned-and-deduplicated-version-of-redpajama)
* Youmu: [https://mlsys.org/media/mlsys-2025/Slides/3272.pdf](https://mlsys.org/media/mlsys-2025/Slides/3272.pdf)
* DEM: [https://arxiv.org/abs/2406.15570](https://arxiv.org/abs/2406.15570)
