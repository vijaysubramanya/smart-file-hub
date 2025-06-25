from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import File
from .documents import FileDocument

User = get_user_model()

class FileAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user = User.objects.create_user(
            username='apitest_user',
            email='apitest@example.com',
            password='testpass123'
        )
        
        self.other_user = User.objects.create_user(
            username='apitest_other',
            email='apitest_other@example.com',
            password='otherpass123'
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Create a test file
        self.file_content = b"Test file content"
        self.file = File.objects.create(
            name="test.txt",
            content=self.file_content,
            size=len(self.file_content),
            content_type="text/plain",
            is_original=True
        )
        
        # URLs
        self.list_url = reverse('file-list')
        self.detail_url = reverse('file-detail', kwargs={'pk': self.file.id})
        self.download_url = reverse('file-download', kwargs={'pk': self.file.id})

    def test_authentication_required(self):
        """Test that authentication is required for all endpoints"""
        # Create an unauthenticated client
        client = APIClient()
        
        # Test list endpoint
        response = client.get(self.list_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # Test detail endpoint
        response = client.get(self.detail_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # Test create endpoint
        file_content = b"Test content"
        upload_file = SimpleUploadedFile(
            "test.txt",
            file_content,
            content_type="text/plain"
        )
        response = client.post(self.list_url, {'file': upload_file}, format='multipart')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # Test download endpoint
        response = client.get(self.download_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_user_can_access_all_files(self):
        """Test that users can access all files in the system"""
        # Create another file
        other_content = b"Other content"
        other_file = File.objects.create(
            name="other.txt",
            content=other_content,
            size=len(other_content),
            content_type="text/plain",
            is_original=True
        )
        other_detail_url = reverse('file-detail', kwargs={'pk': other_file.id})
        
        # Access the file
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'other.txt')
        
        # Switch to other user
        self.client.force_authenticate(user=self.other_user)
        
        # Other user can access first file
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test.txt')

    def test_file_list_shows_all_files(self):
        """Test that file list shows all files in the system"""
        # Create another file
        other_content = b"Other content"
        File.objects.create(
            name="other.txt",
            content=other_content,
            size=len(other_content),
            content_type="text/plain",
            is_original=True
        )
        
        # Get file list
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Shows all files
        file_names = [file['name'] for file in response.data['results']]
        self.assertIn('test.txt', file_names)
        self.assertIn('other.txt', file_names)

    @patch('filemanager.views.FileDocument')
    def test_list_files(self, mock_file_document):
        """Test listing files"""
        # Test without search
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'test.txt')

        # Test with search
        mock_search = MagicMock()
        mock_search.execute.return_value.hits = [MagicMock(id=str(self.file.id))]
        mock_file_document.search.return_value.query.return_value = mock_search

        response = self.client.get(f"{self.list_url}?search=test")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_file(self):
        """Test file upload"""
        file_content = b"New test file content"
        upload_file = SimpleUploadedFile(
            "new_test.txt",
            file_content,
            content_type="text/plain"
        )

        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': upload_file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'new_test.txt')
        
        # Verify file was saved in database
        self.assertTrue(File.objects.filter(name='new_test.txt').exists())

    def test_get_file_details(self):
        """Test retrieving file details"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test.txt')
        self.assertEqual(response.data['size'], len(self.file_content))
        self.assertEqual(response.data['content_type'], 'text/plain')

    @patch('filemanager.views.FileDocument')
    def test_delete_file(self, mock_file_document):
        """Test file deletion"""
        # Mock Elasticsearch document
        mock_doc = MagicMock()
        mock_file_document.get.return_value = mock_doc
        
        # Mock settings
        with self.settings(USE_ELASTICSEARCH=True):
            response = self.client.delete(self.detail_url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            
            # Verify file was deleted from database
            self.assertFalse(File.objects.filter(id=self.file.id).exists())
            
            # Verify Elasticsearch document was deleted
            mock_file_document.get.assert_called_once_with(id=str(self.file.id))
            mock_doc.delete.assert_called_once()

    def test_download_file(self):
        """Test file download"""
        response = self.client.get(self.download_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{self.file.name}"')
        self.assertEqual(response.content, self.file_content)

    def test_file_size_validation(self):
        """Test file size validation"""
        # Create a file larger than MAX_UPLOAD_SIZE
        large_content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        large_file = SimpleUploadedFile(
            "large_file.txt",
            large_content,
            content_type="text/plain"
        )

        response = self.client.post(
            self.list_url,
            {'file': large_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_file(self):
        """Test upload without file"""
        response = self.client.post(self.list_url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagination(self):
        """Test pagination of file list"""
        # Create 15 more files
        for i in range(15):
            content = f"content{i}".encode()
            File.objects.create(
                name=f"test_{i}.txt",
                content=content,
                size=len(content),
                content_type="text/plain",
                is_original=True
            )

        # Test first page
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)  # Default page size
        self.assertEqual(response.data['total'], 16)  # Total files
        self.assertEqual(response.data['pages'], 2)  # Total pages

        # Test second page
        response = self.client.get(f"{self.list_url}?page=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 6)  # Remaining files

    def tearDown(self):
        """Clean up after tests"""
        File.objects.all().delete()
        User.objects.all().delete()

class FileDeduplicationTests(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user with unique username
        self.user = User.objects.create_user(
            username='dedup_user',
            email='dedup@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.file_content = b"Test file content"
        self.content_hash = None  # Will be set by model's save method
        
        # Create original file
        self.original_file = File.objects.create(
            name="original.txt",
            content=self.file_content,
            size=len(self.file_content),
            content_type="text/plain",
            is_original=True
        )
        self.content_hash = self.original_file.content_hash  # Get hash from saved model
        
        self.list_url = reverse('file-list')

        # Create another user for permission testing
        self.other_user = User.objects.create_user(
            username='dedup_other',
            email='dedup_other@example.com',
            password='otherpass123'
        )

    def test_duplicate_file_upload(self):
        """Test uploading a duplicate file"""
        # Create a file with same content but different name
        duplicate_file = SimpleUploadedFile(
            "duplicate.txt",
            self.file_content,
            content_type="text/plain"
        )

        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': duplicate_file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'duplicate.txt')
        self.assertEqual(response.data['size'], len(self.file_content))
        self.assertFalse(response.data['is_original'])
        self.assertIsNotNone(response.data['original_file_url'])
        
        # Verify the duplicate file doesn't store content
        duplicate = File.objects.get(id=response.data['id'])
        self.assertEqual(duplicate.content, b'')
        self.assertEqual(duplicate.original_file, self.original_file)
        self.assertEqual(duplicate.content_hash, self.content_hash)

    def test_unique_file_upload(self):
        """Test uploading a unique file"""
        unique_content = b"Unique file content"
        unique_file = SimpleUploadedFile(
            "unique.txt",
            unique_content,
            content_type="text/plain"
        )

        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': unique_file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'unique.txt')
        self.assertEqual(response.data['size'], len(unique_content))
        self.assertTrue(response.data['is_original'])
        self.assertIsNone(response.data['original_file_url'])
        
        # Verify the file stores content
        unique = File.objects.get(id=response.data['id'])
        self.assertEqual(unique.content, unique_content)
        self.assertIsNone(unique.original_file)
        self.assertTrue(unique.content_hash)  # Just verify hash exists

    def test_duplicate_detection(self):
        """Test the duplicate detection system with multiple file uploads"""
        # Create test file content
        file_content = b"Test content for duplicate detection"
        
        # Upload first file - should be marked as original
        first_file = SimpleUploadedFile(
            "first.txt",
            file_content,
            content_type="text/plain"
        )
        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': first_file},
                format='multipart'
            )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_original'])
        self.assertIsNone(response.data['original_file_url'])
        first_file_id = response.data['id']
        
        # Upload same content with different name - should be marked as duplicate
        second_file = SimpleUploadedFile(
            "second.txt",
            file_content,
            content_type="text/plain"
        )
        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': second_file},
                format='multipart'
            )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_original'])
        self.assertIsNotNone(response.data['original_file_url'])
        
        # Verify the duplicate file references the original
        duplicate = File.objects.get(id=response.data['id'])
        original = File.objects.get(id=first_file_id)
        self.assertEqual(duplicate.original_file, original)
        self.assertEqual(duplicate.content_hash, original.content_hash)
        self.assertEqual(duplicate.content, b'')  # Duplicate should have empty content
        self.assertEqual(duplicate.size, len(file_content))  # Size should match original

    def test_download_duplicate(self):
        """Test downloading a duplicate file"""
        # Create a duplicate
        duplicate_file = SimpleUploadedFile(
            "duplicate.txt",
            self.file_content,
            content_type="text/plain"
        )

        with patch('filemanager.views.FileDocument.save') as mock_save:
            response = self.client.post(
                self.list_url,
                {'file': duplicate_file},
                format='multipart'
            )

        # Download the duplicate
        download_url = reverse('file-download', kwargs={'pk': response.data['id']})
        response = self.client.get(download_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, self.file_content)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="duplicate.txt"'
        )

    def test_delete_original_with_duplicates(self):
        """Test deleting an original file that has duplicates"""
        # Create a duplicate
        duplicate_file = SimpleUploadedFile(
            "duplicate.txt",
            self.file_content,
            content_type="text/plain"
        )

        with patch('filemanager.views.FileDocument.save'):
            response = self.client.post(
                self.list_url,
                {'file': duplicate_file},
                format='multipart'
            )
            duplicate_id = response.data['id']

        # Delete the original file
        with patch('filemanager.views.FileDocument.get') as mock_get:
            mock_get.return_value = MagicMock()
            response = self.client.delete(
                reverse('file-detail', kwargs={'pk': self.original_file.id})
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify the duplicate was also deleted (cascade)
        self.assertFalse(File.objects.filter(id=duplicate_id).exists())

    def tearDown(self):
        """Clean up after tests"""
        File.objects.all().delete()
        User.objects.all().delete()
