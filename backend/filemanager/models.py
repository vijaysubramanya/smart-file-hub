import uuid
import hashlib
from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
import magic

class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    content = models.BinaryField()
    size = models.BigIntegerField()
    content_type = models.CharField(max_length=100)
    content_hash = models.CharField(max_length=64, db_index=True)  # SHA256 hash
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_original = models.BooleanField(default=True)  # True if this is the original file
    original_file = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='duplicates')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['content_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['content_hash']),
        ]

    def __str__(self):
        return f"{self.name} ({self.size} bytes)"

    def save(self, *args, **kwargs):
        if not self.content_type and self.content:
            # Detect content type from file content
            mime = magic.Magic(mime=True)
            self.content_type = mime.from_buffer(self.content[:2048])
        if not self.size:
            self.size = len(self.content)
        if not self.content_hash and self.content:
            # Generate SHA256 hash of content
            self.content_hash = hashlib.sha256(self.content).hexdigest()
        super().save(*args, **kwargs)

    @property
    def extension(self):
        return self.name.split('.')[-1] if '.' in self.name else ''

    def to_dict(self):
        """Convert file metadata to dictionary for Elasticsearch indexing"""
        return {
            'id': str(self.id),
            'name': self.name,
            'size': self.size,
            'content_type': self.content_type,
            'created_at': self.created_at,
            'extension': self.extension
        }
