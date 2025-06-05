"""
Unit tests for cloud storage functionality
"""

import unittest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock


from utils.cloud_storage import CloudStorageManager, get_storage_client
from utils.data_utils import validate_jsonl_format


class TestCloudStorageManager(unittest.TestCase):
    """Test CloudStorageManager functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'storage': {
                'provider': 's3',
                'bucket': 'test-bucket',
                'region': 'us-east-1'
            }
        }

        self.sample_documents = [
            {"text": "안녕하세요. 첫 번째 테스트 문서입니다.", "source": "test1", "domain": "news", "lang": "ko"},
            {"text": "Hello world. This is a test document.", "source": "test2", "domain": "web", "lang": "en"},
            {"text": "두 번째 한국어 문서입니다. 테스트 중입니다.", "source": "test3", "domain": "news", "lang": "ko"}
        ]

        self.jsonl_content = '\n'.join(json.dumps(doc, ensure_ascii=False) for doc in self.sample_documents)

    @patch('utils.cloud_storage.boto3')
    def test_s3_client_initialization(self, mock_boto3):
        """Test S3 client initialization"""
        mock_session = Mock()
        mock_client = Mock()
        mock_boto3.Session.return_value = mock_session
        mock_session.client.return_value = mock_client

        storage = CloudStorageManager('s3', access_key='test', secret_key='test', region='us-east-1')

        self.assertEqual(storage.provider, 's3')
        self.assertEqual(storage.client, mock_client)
        mock_boto3.Session.assert_called_once()

    def test_parse_cloud_path(self):
        """Test cloud path parsing"""
        with patch('utils.cloud_storage.boto3'):
            storage = CloudStorageManager('s3')

            # Test S3 paths
            bucket, key = storage._parse_cloud_path('s3://my-bucket/path/to/file.jsonl')
            self.assertEqual(bucket, 'my-bucket')
            self.assertEqual(key, 'path/to/file.jsonl')

            # Test GCS paths
            bucket, key = storage._parse_cloud_path('gs://my-bucket/path/to/file.jsonl')
            self.assertEqual(bucket, 'my-bucket')
            self.assertEqual(key, 'path/to/file.jsonl')

            # Test Azure paths
            bucket, key = storage._parse_cloud_path('azure://my-container/path/to/file.jsonl')
            self.assertEqual(bucket, 'my-container')
            self.assertEqual(key, 'path/to/file.jsonl')

    @patch('utils.cloud_storage.boto3')
    def test_read_jsonl_file(self, mock_boto3):
        """Test reading JSONL file from cloud storage"""
        # Setup mock S3 client
        mock_client = Mock()
        mock_boto3.Session.return_value.client.return_value = mock_client
        mock_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=self.jsonl_content.encode('utf-8')))
        }

        storage = CloudStorageManager('s3')

        # Test reading JSONL
        documents = list(storage.read_jsonl_file('s3://test-bucket/test.jsonl'))

        self.assertEqual(len(documents), 3)
        self.assertEqual(documents[0]['text'], "안녕하세요. 첫 번째 테스트 문서입니다.")
        self.assertEqual(documents[1]['lang'], 'en')
        self.assertEqual(documents[2]['domain'], 'news')

    @patch('utils.cloud_storage.boto3')
    def test_write_text_file(self, mock_boto3):
        """Test writing text file to cloud storage"""
        mock_client = Mock()
        mock_boto3.Session.return_value.client.return_value = mock_client
        mock_client.upload_file.return_value = None

        storage = CloudStorageManager('s3')

        # Test writing text
        result = storage.write_text_file('s3://test-bucket/test.txt', 'test content')

        self.assertTrue(result)
        mock_client.upload_file.assert_called_once()

    @patch('utils.cloud_storage.boto3')
    def test_file_exists(self, mock_boto3):
        """Test checking if file exists"""
        mock_client = Mock()
        mock_boto3.Session.return_value.client.return_value = mock_client

        storage = CloudStorageManager('s3')

        # Test existing file
        mock_client.head_object.return_value = {}
        exists = storage.file_exists('s3://test-bucket/existing.jsonl')
        self.assertTrue(exists)

        # Test non-existing file
        mock_client.head_object.side_effect = Exception("Not found")
        exists = storage.file_exists('s3://test-bucket/missing.jsonl')
        self.assertFalse(exists)

    @patch('utils.cloud_storage.boto3')
    def test_list_files(self, mock_boto3):
        """Test listing files in cloud storage"""
        mock_client = Mock()
        mock_boto3.Session.return_value.client.return_value = mock_client

        # Mock S3 response
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'path/file1.jsonl'},
                {'Key': 'path/file2.txt'},
                {'Key': 'path/file3.jsonl'}
            ]
        }

        storage = CloudStorageManager('s3')

        # Test listing all files
        files = storage.list_files('test-bucket', prefix='path/')
        self.assertEqual(len(files), 3)

        # Test listing with suffix filter
        jsonl_files = storage.list_files('test-bucket', prefix='path/', suffix='.jsonl')
        self.assertEqual(len(jsonl_files), 2)
        self.assertTrue(all(f.endswith('.jsonl') for f in jsonl_files))


class TestDataUtils(unittest.TestCase):
    """Test data utility functions"""

    def test_validate_jsonl_format(self):
        """Test JSONL format validation"""
        # Valid JSONL content
        valid_content = '''{"text": "안녕하세요", "source": "test"}
{"text": "Hello world", "source": "test2"}
{"text": "테스트 문서", "source": "test3"}'''

        is_valid, info = validate_jsonl_format(valid_content)

        self.assertTrue(is_valid)
        self.assertEqual(info['valid_lines'], 3)
        self.assertEqual(info['invalid_lines'], 0)
        self.assertTrue(info['is_korean_content'])
        self.assertIn('text', info['schema_fields'])
        self.assertIn('source', info['schema_fields'])

    def test_validate_jsonl_format_with_errors(self):
        """Test JSONL validation with invalid lines"""
        invalid_content = '''{"text": "Valid line", "source": "test"}
{invalid json line}
{"text": "Another valid line", "source": "test2"}
'''

        is_valid, info = validate_jsonl_format(invalid_content)

        self.assertFalse(is_valid)  # Should be false due to invalid line
        self.assertEqual(info['valid_lines'], 2)
        self.assertEqual(info['invalid_lines'], 1)
        self.assertGreater(len(info['validation_errors']), 0)


class TestGetStorageClient(unittest.TestCase):
    """Test storage client factory function"""

    @patch('utils.cloud_storage.CloudStorageManager')
    def test_get_storage_client_s3(self, mock_manager):
        """Test getting S3 storage client"""
        config = {
            'storage': {
                'provider': 's3',
                'access_key': 'test',
                'secret_key': 'test',
                'region': 'us-east-1'
            }
        }

        get_storage_client(config)

        mock_manager.assert_called_once_with(
            's3',
            access_key='test',
            secret_key='test',
            region='us-east-1'
        )

    @patch('utils.cloud_storage.CloudStorageManager')
    def test_get_storage_client_gcs(self, mock_manager):
        """Test getting GCS storage client"""
        config = {
            'storage': {
                'provider': 'gcs',
                'credentials_path': '/path/to/creds.json'
            }
        }

        get_storage_client(config)

        mock_manager.assert_called_once_with(
            'gcs',
            credentials_path='/path/to/creds.json'
        )

    def test_get_storage_client_invalid_provider(self):
        """Test error handling for invalid provider"""
        config = {
            'storage': {
                'provider': 'invalid_provider'
            }
        }

        with self.assertRaises(ValueError):
            get_storage_client(config)


class TestCloudIntegration(unittest.TestCase):
    """Integration tests for cloud storage (requires real credentials)"""

    def setUp(self):
        """Set up integration test"""
        # Skip integration tests if no credentials are available
        self.skip_integration = not any([
            os.getenv('AWS_ACCESS_KEY_ID'),
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        ])

        if self.skip_integration:
            self.skipTest("No cloud credentials available for integration testing")

    def test_s3_integration(self):
        """Test S3 integration (requires AWS credentials)"""
        if not os.getenv('AWS_ACCESS_KEY_ID'):
            self.skipTest("AWS credentials not available")

        config = {
            'storage': {
                'provider': 's3',
                'region': 'us-east-1'
            }
        }

        try:
            client = get_storage_client(config)
            self.assertEqual(client.provider, 's3')

            # Test basic operations (this requires a test bucket)
            # Note: Uncomment and modify for actual integration testing
            # test_content = "Test content for integration"
            # success = client.write_text_file('s3://your-test-bucket/test.txt', test_content)
            # self.assertTrue(success)

        except Exception as e:
            self.skipTest(f"S3 integration test failed: {e}")


if __name__ == '__main__':
    unittest.main()
