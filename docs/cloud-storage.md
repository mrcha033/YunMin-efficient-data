# ☁️ 클라우드 스토리지 가이드

YunMin-EfficientData는 AWS S3, Google Cloud Storage, Azure Blob Storage를 통합 지원하는 클라우드 네이티브 데이터 파이프라인입니다.

## 🎯 지원 기능

- **다중 클라우드 지원**: AWS S3, GCS, Azure Blob Storage
- **통합 API**: 단일 인터페이스로 모든 클라우드 제공자 지원
- **스트리밍 처리**: 대용량 파일 효율적 처리
- **자동 인증**: 환경 변수 기반 자동 인증
- **오류 복구**: 네트워크 오류 자동 재시도

## 🚀 빠른 시작

### 1. 자동 설정

```bash
# Linux/macOS
./scripts/setup_cloud.sh

# Windows
.\scripts\setup_cloud.ps1
```

### 2. 수동 설정

#### AWS S3

```bash
# AWS CLI 설치 및 구성
aws configure

# 환경 변수 설정
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-2

# 버킷 생성 (선택사항)
aws s3 mb s3://yunmin-data
```

#### Google Cloud Storage

```bash
# Google Cloud SDK 설치 및 인증
gcloud auth login
gcloud config set project your-project-id

# 서비스 계정 키 생성
gcloud iam service-accounts create yunmin-data-sa
gcloud iam service-accounts keys create gcs-key.json \
    --iam-account=yunmin-data-sa@your-project.iam.gserviceaccount.com

# 환경 변수 설정
export GOOGLE_APPLICATION_CREDENTIALS=./gcs-key.json

# 버킷 생성 (선택사항)
gsutil mb gs://yunmin-data
```

#### Azure Blob Storage

```bash
# Azure CLI 설치 및 로그인
az login

# 스토리지 계정 생성
az storage account create \
    --name yunmindata \
    --resource-group your-resource-group \
    --location koreacentral \
    --sku Standard_LRS

# 연결 문자열 가져오기
az storage account show-connection-string \
    --name yunmindata \
    --resource-group your-resource-group

# 환경 변수 설정
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"
```

## ⚙️ 설정 파일

`configs/dataset_config.yaml` 파일에서 클라우드 설정을 관리합니다:

```yaml
# Cloud Storage Settings
storage:
  provider: "s3"  # Options: s3, gcs, azure
  bucket: "yunmin-data"
  region: "ap-northeast-2"
  
  # AWS S3 Configuration
  access_key: null  # Set via AWS_ACCESS_KEY_ID
  secret_key: null  # Set via AWS_SECRET_ACCESS_KEY
  
  # GCS Configuration (alternative)
  # credentials_path: "path/to/service-account.json"
  
  # Azure Configuration (alternative)
  # connection_string: null  # Set via AZURE_STORAGE_CONNECTION_STRING
  # account_url: null

# Data Paths (Cloud Storage)
paths:
  raw_data: "s3://yunmin-data/raw/"
  dedup_ready: "s3://yunmin-data/dedup_ready/"
  deduped: "s3://yunmin-data/deduped/"
  parquet: "s3://yunmin-data/parquet/"
  local_cache: "./cache/"  # Local cache for temporary files
```

## 📁 클라우드 스토리지 구조

```
클라우드 버킷 (예: s3://yunmin-data/)
├── raw/                    # 원본 JSONL 데이터
│   ├── dataset1.jsonl
│   └── dataset2.jsonl
├── dedup_ready/           # 전처리된 데이터
├── deduped/               # 중복 제거 완료 데이터
│   ├── dataset1_deduped.jsonl
│   └── dataset1_stats.json
├── parquet/               # Parquet 형식 변환 결과
│   ├── dataset1.parquet
│   └── dataset1_benchmark.json
├── models/                # 학습된 모델 및 체크포인트
│   ├── lora/
│   ├── diff_vectors/
│   └── merged/
└── logs/                  # 파이프라인 실행 로그
    ├── dedup_20231201.log
    └── pipeline_run.log
```

## 🔧 API 사용법

### CloudStorageManager 기본 사용법

```python
from utils.cloud_storage import CloudStorageManager

# S3 클라이언트 초기화
storage = CloudStorageManager(
    provider='s3',
    access_key='your_key',
    secret_key='your_secret',
    region='ap-northeast-2'
)

# 파일 목록 조회
files = storage.list_files('yunmin-data', prefix='raw/', suffix='.jsonl')

# JSONL 파일 읽기 (스트리밍)
for document in storage.read_jsonl_file('s3://yunmin-data/raw/dataset.jsonl'):
    print(document['text'])

# 파일 업로드
success = storage.upload_file('./local_file.jsonl', 's3://yunmin-data/raw/uploaded.jsonl')

# 텍스트 파일 작성
content = "Hello, World!"
storage.write_text_file('s3://yunmin-data/test.txt', content)

# 파일 존재 확인
exists = storage.file_exists('s3://yunmin-data/raw/dataset.jsonl')

# 파일 메타데이터 조회
info = storage.get_file_info('s3://yunmin-data/raw/dataset.jsonl')
print(f"File size: {info['size']} bytes")
```

### 설정 기반 클라이언트 생성

```python
from utils.cloud_storage import get_storage_client
import yaml

# 설정 파일 로드
with open('configs/dataset_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 클라이언트 생성
storage = get_storage_client(config)

# 파이프라인에서 사용
for doc in storage.read_jsonl_file(config['paths']['raw_data'] + 'dataset.jsonl'):
    # 문서 처리
    pass
```

## 🚀 파이프라인 실행

클라우드 경로를 사용하여 파이프라인을 실행합니다:

```bash
# 전체 파이프라인 실행
./scripts/run_pipeline.sh s3://yunmin-data/raw/korean_dataset.jsonl

# Google Cloud Storage 사용
./scripts/run_pipeline.sh gs://yunmin-data/raw/korean_dataset.jsonl

# Azure Blob Storage 사용
./scripts/run_pipeline.sh azure://yunmin-data/raw/korean_dataset.jsonl

# 단계별 실행
./scripts/run_pipeline.sh --phase1-only s3://yunmin-data/raw/dataset.jsonl
./scripts/run_pipeline.sh --phase2-only s3://yunmin-data/deduped/dataset.jsonl
```

## 📊 성능 최적화

### 1. 병렬 처리

```python
import concurrent.futures
from utils.cloud_storage import get_storage_client

def process_file(file_path):
    storage = get_storage_client(config)
    return storage.read_jsonl_file(file_path)

# 여러 파일 병렬 처리
files = ['s3://bucket/file1.jsonl', 's3://bucket/file2.jsonl']
with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(executor.map(process_file, files))
```

### 2. 배치 처리

```python
# 대용량 파일 배치 처리
def process_large_file(storage, file_path, batch_size=1000):
    documents = []
    for i, doc in enumerate(storage.read_jsonl_file(file_path)):
        documents.append(doc)
        
        if len(documents) >= batch_size:
            yield documents
            documents = []
    
    if documents:
        yield documents

# 사용 예시
for batch in process_large_file(storage, 's3://bucket/large_file.jsonl'):
    # 배치 단위로 처리
    process_batch(batch)
```

### 3. 로컬 캐시 활용

```python
import os
from pathlib import Path

def get_cached_file(storage, cloud_path, cache_dir='./cache'):
    """클라우드 파일을 로컬 캐시로 다운로드"""
    cache_file = Path(cache_dir) / Path(cloud_path).name
    
    if not cache_file.exists():
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        storage.download_file(cloud_path, str(cache_file))
    
    return str(cache_file)

# 사용 예시
local_file = get_cached_file(storage, 's3://bucket/large_dataset.jsonl')
```

## 🔒 보안 모범 사례

### 1. 환경 변수 사용

```bash
# .env 파일 또는 시스템 환경 변수
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# 코드에서 하드코딩 금지
# ❌ storage = CloudStorageManager('s3', access_key='AKIA123...', secret_key='abc123...')
# ✅ storage = CloudStorageManager('s3')  # 환경 변수에서 자동 로드
```

### 2. IAM 권한 최소화

AWS S3 IAM 정책 예시:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::yunmin-data",
                "arn:aws:s3:::yunmin-data/*"
            ]
        }
    ]
}
```

### 3. 네트워크 보안

```python
# VPC 엔드포인트 사용 (AWS)
storage = CloudStorageManager(
    's3',
    region='ap-northeast-2',
    endpoint_url='https://vpce-123-s3.ap-northeast-2.vpce.amazonaws.com'
)
```

## 🔍 모니터링 및 로깅

### 1. 로깅 설정

```python
import logging

# 클라우드 스토리지 작업 로깅
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cloud_storage')

# 작업 로그 예시
logger.info(f"Starting upload: {local_file} -> {cloud_path}")
logger.info(f"Upload completed: {file_size} bytes in {duration:.2f}s")
```

### 2. 메트릭 수집

```python
import time
from utils.cloud_storage import get_storage_client

def upload_with_metrics(storage, local_path, cloud_path):
    start_time = time.time()
    file_size = os.path.getsize(local_path)
    
    success = storage.upload_file(local_path, cloud_path)
    
    duration = time.time() - start_time
    speed = file_size / duration / 1024 / 1024  # MB/s
    
    print(f"Upload: {success}, Size: {file_size/1024/1024:.1f}MB, Speed: {speed:.1f}MB/s")
    return success
```

## ❗ 문제 해결

### 일반적인 오류

1. **인증 실패**
   ```
   NoCredentialsError: Unable to locate credentials
   ```
   - 환경 변수 확인: `echo $AWS_ACCESS_KEY_ID`
   - AWS CLI 설정: `aws configure list`

2. **권한 부족**
   ```
   AccessDenied: Access Denied
   ```
   - IAM 정책 확인
   - 버킷 정책 확인

3. **네트워크 오류**
   ```
   ConnectionError: Unable to connect
   ```
   - 네트워크 연결 확인
   - 방화벽 설정 확인
   - 프록시 설정 확인

### 디버깅 모드

```python
import logging

# 상세 로깅 활성화
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)

# 요청/응답 로깅
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### 연결 테스트

```bash
# 클라우드 연결 테스트
python -c "
from utils.cloud_storage import get_storage_client
import yaml

with open('configs/dataset_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = get_storage_client(config)
print(f'✅ {client.provider} connection successful')
"
```

## 📚 추가 리소스

- [AWS S3 문서](https://docs.aws.amazon.com/s3/)
- [Google Cloud Storage 문서](https://cloud.google.com/storage/docs)
- [Azure Blob Storage 문서](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [boto3 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [google-cloud-storage 문서](https://cloud.google.com/python/docs/reference/storage/latest)
- [azure-storage-blob 문서](https://docs.microsoft.com/en-us/python/api/azure-storage-blob/) 