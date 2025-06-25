from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Sum, Case, When, F, IntegerField
try:
    from elasticsearch_dsl import Q
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
import hashlib
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class IsAuthorizedUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

from .models import File
from .serializers import FileSerializer
try:
    from .documents import FileDocument
except ImportError:
    FileDocument = None

# Create your views here.

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthorizedUser]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    
    def list(self, request):
        # Get search parameters
        search_query = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Get filter parameters
        min_size = request.query_params.get('min_size')
        max_size = request.query_params.get('max_size')
        file_type = request.query_params.get('type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if search_query and settings.USE_ELASTICSEARCH and ELASTICSEARCH_AVAILABLE and FileDocument:
            try:
                # Search in Elasticsearch
                search = FileDocument.search()
                q = Q('match', name=search_query)  # Only search in name field
                search = search.query(q)
                response = search.execute()
                
                # Get IDs from Elasticsearch results
                file_ids = [hit.id for hit in response.hits]
                queryset = self.queryset.filter(id__in=file_ids)
            except Exception as e:
                # Fallback to database search if Elasticsearch fails
                queryset = self.queryset.filter(name__icontains=search_query)
        else:
            # Use database search if Elasticsearch is not available
            if search_query:
                queryset = self.queryset.filter(name__icontains=search_query)
            else:
                queryset = self.queryset

        # Apply filters
        if min_size:
            queryset = queryset.filter(size__gte=int(min_size))
        if max_size:
            queryset = queryset.filter(size__lte=int(max_size))
        if file_type:
            queryset = queryset.filter(content_type=file_type)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Apply pagination
        paginator = Paginator(queryset, page_size)
        files = paginator.page(page)
        
        serializer = self.get_serializer(files, many=True)
        return Response({
            'results': serializer.data,
            'total': paginator.count,
            'pages': paginator.num_pages,
            'current_page': page
        })

    def create(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check file size
        if file_obj.size > settings.MAX_UPLOAD_SIZE:
            return Response(
                {
                    'error': f'File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB',
                    'max_size': settings.MAX_UPLOAD_SIZE,
                    'file_size': file_obj.size
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Read file content and generate hash
        content = file_obj.read()
        content_hash = hashlib.sha256(content).hexdigest()

        # Check for existing file with same hash
        existing_file = File.objects.filter(
            content_hash=content_hash,
            is_original=True
        ).first()
        
        if existing_file:
            # Create new file entry referencing the original file
            file_instance = File(
                name=file_obj.name,
                content=b'',  # No content needed for duplicate since we'll use original's content
                size=file_obj.size,
                content_type=file_obj.content_type,
                content_hash=content_hash,
                is_original=False,
                original_file=existing_file
            )
        else:
            # Create new original file entry
            file_instance = File(
                name=file_obj.name,
                content=content,
                size=file_obj.size,
                content_type=file_obj.content_type,
                content_hash=content_hash,
                is_original=True
            )
        
        file_instance.save()
        
        # Index in Elasticsearch if available
        if settings.USE_ELASTICSEARCH and ELASTICSEARCH_AVAILABLE and FileDocument:
            try:
                doc = FileDocument(**file_instance.to_dict())
                doc.save()
            except Exception as e:
                # Log the error but don't fail the upload
                print(f"Error indexing file in Elasticsearch: {e}")
        
        serializer = self.get_serializer(file_instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        try:
            instance = self.get_object()
            
            # Delete from Elasticsearch if available
            if settings.USE_ELASTICSEARCH and ELASTICSEARCH_AVAILABLE and FileDocument:
                try:
                    FileDocument.get(id=str(instance.id)).delete()
                except Exception as e:
                    # Log the error but don't fail the deletion
                    print(f"Error deleting file from Elasticsearch: {e}")
            
            # Delete from database
            instance.delete()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        instance = self.get_object()
        
        # If this is a duplicate, get content from the original file
        content = instance.original_file.content if instance.original_file else instance.content
        
        response = HttpResponse(
            content,
            content_type=instance.content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{instance.name}"'
        response['Content-Length'] = instance.size
        
        return response

    @action(detail=False, methods=['get'])
    def storage_savings(self, request):
        """Calculate storage savings from deduplication"""
        # Get all duplicate files
        duplicates = self.queryset.filter(is_original=False)
        
        # Calculate total size of duplicates (this is the storage saved)
        total_savings = duplicates.aggregate(
            total=Sum('size')
        )['total'] or 0
        
        # Get count of duplicates
        duplicate_count = duplicates.count()
        
        return Response({
            'bytes_saved': total_savings,
            'human_readable_saved': self._format_size(total_savings),
            'duplicate_count': duplicate_count
        })
    
    def _format_size(self, size):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], authentication_classes=[])
    def health(self, request):
        """Health check endpoint"""
        return Response({'status': 'healthy'}, status=status.HTTP_200_OK)
