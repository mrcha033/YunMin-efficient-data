# 🧠 YunMin-EfficientData

> **High-efficiency data pipeline for YunMin-Mamba Korean language model optimization**

YunMin-EfficientData는 한국어 특화 LLM인 YunMin-Mamba의 학습 효율성을 극대화하기 위한 데이터 파이프라인입니다. SlimPajama 기반 중복 제거, Youmu 기반 컬럼형 데이터 로딩, DEM 기반 효율적 모델 병합의 3가지 최신 기술을 통합하여 최대 90%의 학습 비용 절감과 5배의 데이터 로딩 속도 향상을 목표로 합니다.

## 🎯 주요 특징

- **🧹 SlimPajama 기반 중복 제거**: MinHash + LSH를 활용한 고효율 중복 제거 (3% 이하 중복률 유지)
- **📦 Youmu 기반 포맷 최적화**: Parquet 컬럼형 저장으로 최대 5배 로딩 속도 향상
- **🔗 DEM 기반 모델 병합**: 도메인별 LoRA 학습 후 차이 벡터 병합으로 70-90% 학습 비용 절감
- **⚡ 완전 자동화**: 원클릭 파이프라인 실행 및 상세한 로깅/모니터링

## 🏗️ 프로젝트 구조

```
YunMin-efficient-data/
├── data/                    # 데이터 저장소
│   ├── raw/                # 원본 JSONL 데이터
│   ├── deduped/            # 중복 제거 완료 데이터
│   └── parquet/            # Parquet 변환 결과
├── dedup/                  # Phase 1: 중복 제거 모듈
├── format/                 # Phase 2: 포맷 변환 모듈
├── dem/                    # Phase 3: DEM 학습 및 병합
├── evaluation/             # Phase 4: 성능 평가
├── scripts/                # 자동화 스크립트
├── configs/                # 설정 파일
├── tests/                  # 단위 테스트
└── docs/                   # 상세 문서
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-org/YunMin-efficient-data.git
cd YunMin-efficient-data

# 환경 자동 설정 (Python 3.8+ 필요)
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# 또는 venv\Scripts\activate  # Windows
```

### 2. 데이터 준비

```bash
# 원본 JSONL 데이터를 data/raw/ 디렉토리에 배치
# 각 줄은 다음 형식의 JSON이어야 합니다:
# {"text": "텍스트 내용", "source": "출처", "domain": "도메인", "lang": "ko"}
```

### 3. 파이프라인 실행

```bash
# 전체 파이프라인 실행
./scripts/run_pipeline.sh data/raw/your_dataset.jsonl

# 특정 단계만 실행
./scripts/run_pipeline.sh --phase1-only data/raw/dataset.jsonl  # 중복 제거만
./scripts/run_pipeline.sh --phase2-only data/deduped/dataset.jsonl  # 포맷 변환만

# 특정 단계 건너뛰기
./scripts/run_pipeline.sh --skip-phase4 data/raw/dataset.jsonl  # 평가 단계 제외
```

## 📋 4단계 파이프라인

### Phase 1: 중복 제거 (SlimPajama)
- **입력**: 원본 JSONL 데이터
- **처리**: MinHash + LSH 기반 유사 문서 탐지 및 제거
- **출력**: 중복 제거된 JSONL 데이터
- **효과**: 데이터 크기 최대 50% 감소

### Phase 2: 포맷 변환 (Youmu)
- **입력**: 중복 제거된 JSONL 데이터
- **처리**: Parquet 컬럼형 포맷으로 변환
- **출력**: 최적화된 Parquet 파일
- **효과**: 로딩 속도 최대 5배 향상, 메모리 사용량 80% 절감

### Phase 3: DEM 학습 및 병합
- **입력**: Parquet 형식 도메인별 데이터
- **처리**: 도메인별 LoRA 학습 → 차이 벡터 계산 → 가중 병합
- **출력**: 통합 고성능 모델
- **효과**: 학습 비용 70-90% 절감

### Phase 4: 통합 테스트 및 평가
- **입력**: 병합된 모델
- **처리**: 성능 지표 측정 (PPL, BLEU, ROUGE 등)
- **출력**: 상세한 성능 보고서
- **효과**: 객관적 성능 검증 및 개선점 도출

## ⚙️ 설정

### 데이터셋 설정 (`configs/dataset_config.yaml`)
```yaml
# 클라우드 스토리지 설정
storage:
  provider: "s3"  # s3, gcs, local
  bucket: "yunmin-data"

# 스키마 정의
schema:
  required_columns: ["text", "tokens", "source", "lang", "domain"]
  
# 도메인 목록
domains: ["main_data", "textbook", "assembly", "web", "social"]
```

### DEM 설정 (`configs/dem_config.yaml`)
```yaml
# 학습 파라미터
training:
  learning_rate: 5e-5
  batch_size: 8
  max_epochs: 1

# 도메인별 병합 가중치
domain_weights:
  main_data: 0.4
  textbook: 0.25
  assembly: 0.15
  web: 0.15
  social: 0.05
```

## 📊 성능 지표

| 항목 | 개선 효과 |
|------|-----------|
| 데이터 용량 감소 | 최대 50% ↓ |
| 학습 비용 절감 | 70-90% ↓ |
| 로딩 속도 향상 | 최대 5× ↑ |
| 메모리 효율성 | 최대 80% ↓ |
| 모델 성능 향상 | MMLU 기준 최대 15% ↑ |

## 🧪 테스트

```bash
# 단위 테스트 실행
pytest tests/

# 특정 모듈 테스트
pytest tests/test_dedup.py

# 커버리지 포함 테스트
pytest --cov=. tests/
```

## 📖 상세 문서

- [📦 전체 아키텍처](docs/architecture.md)
- [🧹 Phase 1: 중복 제거 상세 계획](docs/phase1.md)
- [📦 Phase 2: 포맷 변환 상세 계획](docs/phase2.md)
- [🔗 Phase 3: DEM 학습 상세 계획](docs/phase3.md)
- [📊 Phase 4: 평가 상세 계획](docs/phase4.md)
- [✅ 세부 태스크 목록](docs/tasks.md)

## 🔧 고급 사용법

### 클라우드 스토리지 연동

```bash
# AWS S3 설정
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export S3_BUCKET_NAME=yunmin-data

# 클라우드 데이터로 파이프라인 실행
./scripts/run_pipeline.sh s3://yunmin-data/raw/dataset.jsonl
```

### 커스텀 설정으로 실행

```bash
# 커스텀 설정 파일 사용
./scripts/run_pipeline.sh --config custom_configs/ data/raw/dataset.jsonl

# 로그 디렉토리 변경
./scripts/run_pipeline.sh --log-dir /custom/logs data/raw/dataset.jsonl
```

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- **SlimPajama** 팀의 중복 제거 방법론
- **Youmu** 팀의 컬럼형 데이터 로딩 최적화
- **DEM** 연구팀의 효율적 모델 병합 기법

## 📞 문의 및 지원

- 🐛 이슈 리포트: [GitHub Issues](https://github.com/your-org/YunMin-efficient-data/issues)
- 💬 토론: [GitHub Discussions](https://github.com/your-org/YunMin-efficient-data/discussions)
- 📧 이메일: contact@yunmin.ai

---

**YunMin-EfficientData**로 더 효율적인 한국어 AI 모델 개발을 시작하세요! 🚀
