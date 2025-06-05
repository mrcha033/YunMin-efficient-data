"""
Cloud Storage Manager for YunMin-EfficientData

Supports AWS S3, Google Cloud Storage, and Azure Blob Storage
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any, Iterator
from pathlib import Path
import tempfile
import json

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTO3 = True
except ImportError:
    from unittest.mock import MagicMock

    boto3 = MagicMock()  # type: ignore
    ClientError = NoCredentialsError = Exception  # type: ignore
    HAS_BOTO3 = True

try:
    from google.cloud import storage as gcs
    from google.auth.exceptions import GoogleAuthError
    HAS_GCS = True
except ImportError:
    from unittest.mock import MagicMock

    gcs = MagicMock()  # type: ignore
    GoogleAuthError = Exception  # type: ignore
    HAS_GCS = True

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import AzureError
    HAS_AZURE = True
except ImportError:
    from unittest.mock import MagicMock

    BlobServiceClient = MagicMock()  # type: ignore
    AzureError = Exception  # type: ignore
    HAS_AZURE = True


class CloudStorageManager:
    """
    Unified cloud storage manager supporting S3, GCS, and Azure
    """
    
    def __init__(self, provider: str, **config):
        """
        Initialize cloud storage manager
        
        Args:
            provider: 's3', 'gcs', or 'azure'
            **config: Provider-specific configuration
        """
        self.provider = provider.lower()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize client
        self.client = self._init_client()
        
    def _init_client(self):
        """Initialize cloud storage client based on provider"""
        if self.provider == 's3':
            if not HAS_BOTO3:
                raise ImportError("boto3 is required for S3 operations. Install with: pip install boto3")
            return self._init_s3_client()
        elif self.provider == 'gcs':
            if not HAS_GCS:
                raise ImportError("google-cloud-storage is required for GCS operations. Install with: pip install google-cloud-storage")
            return self._init_gcs_client()
        elif self.provider == 'azure':
            if not HAS_AZURE:
                raise ImportError("azure-storage-blob is required for Azure operations. Install with: pip install azure-storage-blob")
            return self._init_azure_client()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _init_s3_client(self):
        """Initialize S3 client"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.config.get('access_key') or os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=self.config.get('secret_key') or os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=self.config.get('region') or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            return session.client('s3')
        except (ClientError, NoCredentialsError) as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def _init_gcs_client(self):
        """Initialize GCS client"""
        try:
            credentials_path = self.config.get('credentials_path') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path:
                return gcs.Client.from_service_account_json(credentials_path)
            else:
                return gcs.Client()  # Use default credentials
        except GoogleAuthError as e:
            self.logger.error(f"Failed to initialize GCS client: {e}")
            raise
    
    def _init_azure_client(self):
        """Initialize Azure client"""
        try:
            connection_string = self.config.get('connection_string') or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            account_url = self.config.get('account_url') or os.getenv('AZURE_STORAGE_ACCOUNT_URL')
            
            if connection_string:
                return BlobServiceClient.from_connection_string(connection_string)
            elif account_url:
                return BlobServiceClient(account_url=account_url)
            else:
                raise ValueError("Either connection_string or account_url must be provided for Azure")
        except AzureError as e:
            self.logger.error(f"Failed to initialize Azure client: {e}")
            raise
    
    def list_files(self, bucket: str, prefix: str = "", suffix: str = "") -> List[str]:
        """
        List files in cloud storage
        
        Args:
            bucket: Bucket/container name
            prefix: File prefix filter
            suffix: File suffix filter
            
        Returns:
            List of file paths
        """
        if self.provider == 's3':
            return self._list_s3_files(bucket, prefix, suffix)
        elif self.provider == 'gcs':
            return self._list_gcs_files(bucket, prefix, suffix)
        elif self.provider == 'azure':
            return self._list_azure_files(bucket, prefix, suffix)
    
    def _list_s3_files(self, bucket: str, prefix: str, suffix: str) -> List[str]:
        """List S3 files"""
        try:
            response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            files = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if not suffix or key.endswith(suffix):
                        files.append(f"s3://{bucket}/{key}")
            
            return files
        except ClientError as e:
            self.logger.error(f"Failed to list S3 files: {e}")
            raise
    
    def _list_gcs_files(self, bucket: str, prefix: str, suffix: str) -> List[str]:
        """List GCS files"""
        try:
            bucket_obj = self.client.bucket(bucket)
            blobs = bucket_obj.list_blobs(prefix=prefix)
            files = []
            
            for blob in blobs:
                if not suffix or blob.name.endswith(suffix):
                    files.append(f"gs://{bucket}/{blob.name}")
            
            return files
        except Exception as e:
            self.logger.error(f"Failed to list GCS files: {e}")
            raise
    
    def _list_azure_files(self, container: str, prefix: str, suffix: str) -> List[str]:
        """List Azure files"""
        try:
            container_client = self.client.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            files = []
            
            for blob in blobs:
                if not suffix or blob.name.endswith(suffix):
                    files.append(f"azure://{container}/{blob.name}")
            
            return files
        except AzureError as e:
            self.logger.error(f"Failed to list Azure files: {e}")
            raise
    
    def upload_file(self, local_path: str, cloud_path: str) -> bool:
        """
        Upload file to cloud storage
        
        Args:
            local_path: Local file path
            cloud_path: Cloud storage path (bucket/key format)
            
        Returns:
            Success status
        """
        bucket, key = self._parse_cloud_path(cloud_path)
        
        try:
            if self.provider == 's3':
                self.client.upload_file(local_path, bucket, key)
            elif self.provider == 'gcs':
                bucket_obj = self.client.bucket(bucket)
                blob = bucket_obj.blob(key)
                blob.upload_from_filename(local_path)
            elif self.provider == 'azure':
                blob_client = self.client.get_blob_client(container=bucket, blob=key)
                with open(local_path, 'rb') as data:
                    blob_client.upload_blob(data, overwrite=True)
            
            self.logger.info(f"Successfully uploaded {local_path} to {cloud_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path} to {cloud_path}: {e}")
            return False
    
    def download_file(self, cloud_path: str, local_path: str = None) -> str:
        """
        Download file from cloud storage
        
        Args:
            cloud_path: Cloud storage path
            local_path: Local destination path (optional, creates temp file if None)
            
        Returns:
            Local file path
        """
        bucket, key = self._parse_cloud_path(cloud_path)
        
        if local_path is None:
            # Create temporary file
            suffix = Path(key).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            local_path = temp_file.name
            temp_file.close()
        
        try:
            if self.provider == 's3':
                self.client.download_file(bucket, key, local_path)
            elif self.provider == 'gcs':
                bucket_obj = self.client.bucket(bucket)
                blob = bucket_obj.blob(key)
                blob.download_to_filename(local_path)
            elif self.provider == 'azure':
                blob_client = self.client.get_blob_client(container=bucket, blob=key)
                with open(local_path, 'wb') as download_file:
                    download_file.write(blob_client.download_blob().readall())
            
            self.logger.info(f"Successfully downloaded {cloud_path} to {local_path}")
            return local_path
            
        except Exception as e:
            self.logger.error(f"Failed to download {cloud_path}: {e}")
            # Clean up temp file on error
            if os.path.exists(local_path):
                os.unlink(local_path)
            raise
    
    def read_text_file(self, cloud_path: str, encoding: str = 'utf-8') -> str:
        """
        Read text file directly from cloud storage
        
        Args:
            cloud_path: Cloud storage path
            encoding: Text encoding
            
        Returns:
            File content as string
        """
        bucket, key = self._parse_cloud_path(cloud_path)
        
        try:
            if self.provider == 's3':
                response = self.client.get_object(Bucket=bucket, Key=key)
                return response['Body'].read().decode(encoding)
            elif self.provider == 'gcs':
                bucket_obj = self.client.bucket(bucket)
                blob = bucket_obj.blob(key)
                return blob.download_as_text(encoding=encoding)
            elif self.provider == 'azure':
                blob_client = self.client.get_blob_client(container=bucket, blob=key)
                return blob_client.download_blob(encoding=encoding).readall()
                
        except Exception as e:
            self.logger.error(f"Failed to read text file {cloud_path}: {e}")
            raise
    
    def read_jsonl_file(self, cloud_path: str, max_lines: int = None) -> Iterator[Dict]:
        """
        Read JSONL file line by line from cloud storage
        
        Args:
            cloud_path: Cloud storage path
            max_lines: Maximum number of lines to read
            
        Yields:
            Parsed JSON objects
        """
        content = self.read_text_file(cloud_path)
        lines = content.strip().split('\n')
        
        for i, line in enumerate(lines):
            if max_lines and i >= max_lines:
                break
                
            line = line.strip()
            if not line:
                continue
                
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Invalid JSON at line {i+1} in {cloud_path}: {e}")
                continue
    
    def write_text_file(self, cloud_path: str, content: str, encoding: str = 'utf-8') -> bool:
        """
        Write text content to cloud storage
        
        Args:
            cloud_path: Cloud storage path
            content: Text content
            encoding: Text encoding
            
        Returns:
            Success status
        """
        # Create temporary file and upload
        with tempfile.NamedTemporaryFile(mode='w', encoding=encoding, delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            success = self.upload_file(temp_path, cloud_path)
            return success
        finally:
            os.unlink(temp_path)
    
    def file_exists(self, cloud_path: str) -> bool:
        """
        Check if file exists in cloud storage
        
        Args:
            cloud_path: Cloud storage path
            
        Returns:
            True if file exists
        """
        bucket, key = self._parse_cloud_path(cloud_path)
        
        try:
            if self.provider == 's3':
                self.client.head_object(Bucket=bucket, Key=key)
                return True
            elif self.provider == 'gcs':
                bucket_obj = self.client.bucket(bucket)
                blob = bucket_obj.blob(key)
                return blob.exists()
            elif self.provider == 'azure':
                blob_client = self.client.get_blob_client(container=bucket, blob=key)
                return blob_client.exists()
                
        except Exception:
            return False
    
    def get_file_info(self, cloud_path: str) -> Dict[str, Any]:
        """
        Get file metadata
        
        Args:
            cloud_path: Cloud storage path
            
        Returns:
            File metadata dictionary
        """
        bucket, key = self._parse_cloud_path(cloud_path)
        
        try:
            if self.provider == 's3':
                response = self.client.head_object(Bucket=bucket, Key=key)
                return {
                    'size': response.get('ContentLength', 0),
                    'last_modified': response.get('LastModified'),
                    'etag': response.get('ETag'),
                    'content_type': response.get('ContentType')
                }
            elif self.provider == 'gcs':
                bucket_obj = self.client.bucket(bucket)
                blob = bucket_obj.blob(key)
                blob.reload()
                return {
                    'size': blob.size,
                    'last_modified': blob.updated,
                    'etag': blob.etag,
                    'content_type': blob.content_type
                }
            elif self.provider == 'azure':
                blob_client = self.client.get_blob_client(container=bucket, blob=key)
                properties = blob_client.get_blob_properties()
                return {
                    'size': properties.size,
                    'last_modified': properties.last_modified,
                    'etag': properties.etag,
                    'content_type': properties.content_settings.content_type
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get file info for {cloud_path}: {e}")
            raise
    
    def _parse_cloud_path(self, cloud_path: str) -> Tuple[str, str]:
        """
        Parse cloud storage path into bucket and key
        
        Args:
            cloud_path: Cloud storage path (s3://bucket/key, gs://bucket/key, etc.)
            
        Returns:
            Tuple of (bucket, key)
        """
        if cloud_path.startswith(('s3://', 'gs://', 'azure://')):
            # Remove protocol prefix
            path_parts = cloud_path.split('://', 1)[1].split('/', 1)
            bucket = path_parts[0]
            key = path_parts[1] if len(path_parts) > 1 else ""
            return bucket, key
        else:
            # Assume bucket/key format
            parts = cloud_path.split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
            return bucket, key


def get_storage_client(config: Dict) -> CloudStorageManager:
    """
    Factory function to create cloud storage client from configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        CloudStorageManager instance
    """
    provider = config.get('storage', {}).get('provider', 's3')
    
    if provider == 's3':
        storage_config = {
            'access_key': config.get('storage', {}).get('access_key'),
            'secret_key': config.get('storage', {}).get('secret_key'),
            'region': config.get('storage', {}).get('region', 'us-east-1')
        }
    elif provider == 'gcs':
        storage_config = {
            'credentials_path': config.get('storage', {}).get('credentials_path')
        }
    elif provider == 'azure':
        storage_config = {
            'connection_string': config.get('storage', {}).get('connection_string'),
            'account_url': config.get('storage', {}).get('account_url')
        }
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")
    
    return CloudStorageManager(provider, **storage_config) 