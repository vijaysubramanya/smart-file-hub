from django.test import TestCase
from unittest.mock import patch, MagicMock
from .models import File
from .documents import FileDocument

class FileModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.file_content = b"Test file content"
        self.file = File.objects.create(
            name="test.txt",
            content=self.file_content,
            size=len(self.file_content),
            content_type="text/plain"
        )

    def test_file_creation(self):
        """Test file creation and automatic field population"""
        file = File(
            name="auto_test.txt",
            content=b"Test content"
        )
        file.save()

        self.assertEqual(file.size, 12)  # len("Test content")
        self.assertEqual(file.content_type, "text/plain")
        self.assertIsNotNone(file.created_at)
        self.assertIsNotNone(file.updated_at)

    def test_file_string_representation(self):
        """Test the string representation of File model"""
        self.assertEqual(
            str(self.file),
            f"test.txt ({len(self.file_content)} bytes)"
        )

    def test_file_extension(self):
        """Test file extension property"""
        self.assertEqual(self.file.extension, "txt")
        
        # Test file without extension
        file = File.objects.create(
            name="noextension",
            content=b"test",
            size=4,
            content_type="text/plain"
        )
        self.assertEqual(file.extension, "")

    def test_to_dict_method(self):
        """Test conversion to dictionary for Elasticsearch"""
        file_dict = self.file.to_dict()
        
        self.assertEqual(file_dict['name'], "test.txt")
        self.assertEqual(file_dict['size'], len(self.file_content))
        self.assertEqual(file_dict['content_type'], "text/plain")
        self.assertEqual(file_dict['extension'], "txt")
        self.assertIsNotNone(file_dict['id'])
        self.assertIsNotNone(file_dict['created_at'])

    @patch('magic.Magic')
    def test_content_type_detection(self, mock_magic):
        """Test automatic content type detection"""
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_buffer.return_value = "application/pdf"
        mock_magic.return_value = mock_magic_instance

        file = File(
            name="test.pdf",
            content=b"%PDF-1.4 test content"
        )
        file.save()

        self.assertEqual(file.content_type, "application/pdf")
        mock_magic_instance.from_buffer.assert_called_once()

class FileDocumentTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.file = File.objects.create(
            name="test.txt",
            content=b"Test content",
            size=11,
            content_type="text/plain"
        )

    @patch('elasticsearch_dsl.Document.save')
    def test_document_indexing(self, mock_save):
        """Test Elasticsearch document creation and indexing"""
        doc = FileDocument(**self.file.to_dict())
        doc.save()

        self.assertEqual(doc.name, self.file.name)
        self.assertEqual(doc.size, self.file.size)
        self.assertEqual(doc.content_type, self.file.content_type)
        self.assertEqual(doc.extension, "txt")
        mock_save.assert_called_once() 