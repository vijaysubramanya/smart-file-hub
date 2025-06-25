from rest_framework import serializers
from .models import File

class FileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    original_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = [
            'id', 'name', 'size', 'content_type', 'created_at', 
            'updated_at', 'url', 'original_file_url', 'is_original'
        ]
        read_only_fields = [
            'id', 'size', 'content_type', 'created_at', 'updated_at',
            'original_file_url', 'is_original'
        ]

    def get_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None
        return request.build_absolute_uri(f'/api/files/{obj.id}/download/')

    def get_original_file_url(self, obj):
        if not obj.original_file:
            return None
        request = self.context.get('request')
        if request is None:
            return None
        return request.build_absolute_uri(f'/api/files/{obj.original_file.id}/download/') 