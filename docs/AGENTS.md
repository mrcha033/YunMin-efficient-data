# 🧠 AGENTS.md — YunMin-EfficientData 프로젝트 지침서

## 📁 프로젝트 개요

* **프로젝트명**: YunMin-EfficientData
* **목표**: 한국어 특화 LLM인 YunMin-Mamba의 학습 효율성 향상을 위한 데이터 파이프라인 구축 및 최적화
* **구성 단계**:

  * Phase 1: JSONL 중복 제거 및 정제
  * Phase 2: Parquet 포맷 변환 및 열 정규화
  * Phase 3: 도메인별 LoRA 학습 및 DEM 병합
  * Phase 4: 통합 테스트 및 평가

## 🧾 작업 지침

### 1. 데이터 처리

* **중복 제거**: SlimPajama 기반의 LSH를 활용하여 중복률을 3% 이하로 유지합니다.
* **포맷 변환**: JSONL 데이터를 Parquet 포맷으로 변환하며, 열 이름은 소문자 스네이크 케이스(snake\_case)를 사용합니다.
* **열 정규화**: 필요한 열만 선택하여 저장 공간을 최적화합니다.

### 2. 모델 학습 및 병합

* **LoRA 학습**: 도메인별로 LoRA 방식의 경량 학습을 수행하며, 학습률은 5e-5, 배치 크기는 8, 에폭 수는 1로 설정합니다.
* **DEM 병합**: 도메인별로 생성된 파라미터 차이 벡터(diff vector)를 가중 평균하여 통합 모델을 생성합니다.

### 3. 테스트 및 평가

* **자동화 스크립트**: `run_pipeline.sh`를 통해 전체 파이프라인을 자동으로 실행합니다.
* **성능 평가**: Perplexity, BLEU, ROUGE, BERTScore 등의 지표를 활용하여 모델 성능을 평가합니다.
* **정성 평가**: 프롬프트에 대한 모델 응답을 비교하여 정보성, 자연성, 일관성 측면에서 평가합니다.

## 🧪 테스트 및 검증

* **단위 테스트**: 각 모듈에 대해 pytest를 활용한 단위 테스트를 작성합니다.
* **통합 테스트**: 전체 파이프라인의 통합 테스트를 수행하여 단계 간 연계를 검증합니다.
* **성능 검증**: 모델의 성능 지표를 기준으로 개선 여부를 판단합니다.

## 📂 파일 및 디렉토리 구조

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
│   └── tests/test_loading_speed.py # parquet vs jsonl I/O 벤치마크
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



## 📌 참고 사항

* **코딩 스타일**: PEP8을 준수하며, 변수명은 소문자 스네이크 케이스(snake\_case)를 사용합니다.
* **문서화**: 각 함수와 클래스에는 docstring을 작성하여 사용법과 목적을 명확히 합니다.
* **버전 관리**: Git을 활용하여 코드 변경 사항을 관리하며, 주요 변경 사항은 커밋 메시지에 명확히 기록합니다.

---

