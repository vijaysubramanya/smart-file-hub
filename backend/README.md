# File Hub Backend

This is the backend service for the File Hub system, providing file management capabilities with features like deduplication and search.

## Features

- File upload/download
- File deduplication
- File search using Elasticsearch
- User authentication

## Technology Stack

- Python 3.9+
- Django 4.x
- Django REST Framework
- SQLite (Development database)
- Docker
- WhiteNoise for static file serving

## Prerequisites

- Python 3.9 or higher
- pip
- Docker (if using containerized setup)
- virtualenv or venv (recommended)
- PostgreSQL
- Elasticsearch
- Redis (optional, for caching)

## Installation & Setup

### Local Development

1. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   Create a `.env` file in the backend directory:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

4. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
   Note: SQLite database will be automatically created at `db.sqlite3`

5. **Run Development Server**
   ```bash
   python manage.py runserver
   ```
   Access the API at http://localhost:8000/api

### Docker Setup

```bash
# Build the image
docker build -t file-hub-backend .

# Run the container
docker run -p 8000:8000 file-hub-backend
```

## Project Structure

```
backend/
├── core/           # Project settings and main URLs
├── files/          # File management app
│   ├── models.py   # Data models
│   ├── views.py    # API views
│   ├── urls.py     # URL routing
│   └── tests.py    # Unit tests
├── db.sqlite3      # SQLite database
└── manage.py       # Django management script
```

## API Endpoints

### Files API (`/api/files/`)

- `GET /api/files/`: List all files
  - Query Parameters:
    - `search`: Search files by name
    - `sort`: Sort by created_at, name, or size

- `POST /api/files/`: Upload new file
  - Request: Multipart form data
  - Fields:
    - `file`: File to upload
    - `description`: Optional file description

- `GET /api/files/<uuid>/`: Get file details
- `DELETE /api/files/<uuid>/`: Delete file

### Authentication API (`/api/auth/`)

- `POST /api/auth/login/`: Login
- `POST /api/auth/logout/`: Logout

## Security Features

- UUID-based file identification
- WhiteNoise for secure static file serving
- CORS configuration for frontend integration
- Django's built-in security features:
  - CSRF protection
  - XSS prevention
  - SQL injection protection

## Testing

```bash
# Run all tests
python manage.py test

# Run specific test file
python manage.py test files.tests
```

## Troubleshooting

1. **Database Issues**
   ```bash
   # Reset database
   rm db.sqlite3
   python manage.py migrate
   ```

2. **Static Files**
   ```bash
   python manage.py collectstatic
   ```

3. **Permission Issues**
   - Check file permissions in media directory
   - Ensure write permissions for SQLite database directory

## Contributing

1. Fork the repository
2. Create your feature branch
3. Write and run tests
4. Commit your changes
5. Push to the branch
6. Create a Pull Request

## Documentation

- API documentation available at `/api/docs/`
- Admin interface at `/admin/`
- Detailed API schema at `/api/schema/`

## Users

- A new user can be created using
   `python manage.py createsuperuser`
- Only logged in users have access to the files
- For testing, use any of the users "alice", "bob", "carol" and "dave" with the password "password123".

## File Deduplication

The system automatically detects and handles duplicate files:
- Files are identified by their SHA256 hash
- Duplicate files share the same content storage
- Each duplicate maintains its own metadata
- Deleting a duplicate preserves the original content

## Search

Files can be searched by:
- Filename
- Size range
- Content type
- Upload date range

## How the Backend Works

### Architecture Overview

The File Hub backend is built using Django and Django REST Framework, providing a robust API-first architecture for file management. The system is designed around a single-app structure (`filemanager`) that handles all file operations, user authentication, and search functionality.

### Core Components

#### 1. Data Models (`models.py`)

The system centers around a single `File` model that handles both original files and duplicates:

**Key Features:**
- **UUID Primary Keys**: All files use UUIDs instead of sequential IDs for security
- **Content Hashing**: SHA256 hashes are automatically generated on save
- **MIME Type Detection**: Uses `python-magic` library to detect file types from content
- **Database Indexing**: Optimized indexes on name, content_type, created_at, and content_hash

#### 2. File Deduplication System

The deduplication system works at the content level using SHA256 hashes:

**Upload Process:**
1. File content is read and SHA256 hash is calculated
2. System checks for existing files with the same hash
3. If duplicate found:
   - Creates new File record with `is_original=False`
   - Sets `content` field to empty (saves storage)
   - Links to original file via `original_file` foreign key
4. If unique:
   - Creates new File record with `is_original=True`
   - Stores full content in `content` field

**Download Process:**
- Original files: Content served directly from `content` field
- Duplicate files: Content served from `original_file.content`

**Storage Savings:**
- Duplicate files consume only metadata storage (no content duplication)
- Provides `/api/files/storage_savings/` endpoint to track savings

#### 3. Authentication System (`auth_views.py`)

**Session-Based Authentication:**
- Uses Django's built-in session authentication
- CSRF protection enabled for security
- Supports both session and basic authentication

**User Management:**
- Pre-configured test users: alice, bob, carol, dave (password: "password123")
- Custom management commands for user creation

#### 4. File Management API (`views.py`)

**FileViewSet** provides full CRUD operations via Django REST Framework:

**Core Endpoints:**
- `GET /api/files/`: List files with filtering and search
- `POST /api/files/`: Upload new files
- `GET /api/files/{id}/`: Get file metadata
- `DELETE /api/files/{id}/`: Delete file
- `GET /api/files/{id}/download/`: Download file content

**Advanced Features:**
- `GET /api/files/storage_savings/`: Get deduplication statistics
- `GET /api/health/`: Health check endpoint

**File Upload Process:**
1. **Validation**: Check file size against `MAX_UPLOAD_SIZE` (10MB)
2. **Content Processing**: Read file content and generate SHA256 hash
3. **Deduplication Check**: Search for existing files with same hash
4. **Storage Decision**: Store as original or duplicate based on hash check
5. **Elasticsearch Indexing**: Index metadata for search (if enabled)
6. **Response**: Return file metadata with download URLs

**Filtering and Search:**
- **Database Search**: Uses Django ORM with `icontains` for filename search
- **Elasticsearch Search**: Advanced search when Elasticsearch is available
- **Filters**: Size range, content type, date range filtering
- **Pagination**: Configurable page size with default of 10 items

#### 5. Search Integration (`documents.py`, `elasticsearch.py`)

**Elasticsearch Integration:**
- Optional feature controlled by `USE_ELASTICSEARCH` setting
- Graceful fallback to database search if Elasticsearch unavailable
- Automatic indexing on file upload and deletion

#### 6. Security Features

**Authentication & Authorization:**
- Custom `IsAuthorizedUser` permission class
- Session-based authentication with CSRF protection
- All file operations require authentication

**Data Security:**
- UUID-based file identification (no sequential IDs)
- CORS configuration for frontend integration
- Input validation and file size limits
- Secure file serving with proper content headers

**CORS Configuration:**
- Allows requests from `localhost:3000` (frontend)
- Credentials support enabled
- Proper header exposure for file downloads

#### 7. API Serialization (`serializers.py`)

**FileSerializer Features:**
- Exposes essential file metadata
- Generates download URLs dynamically
- Handles original/duplicate file relationships
- Read-only fields for system-generated data

**Response Format:**
```json
{
    "id": "uuid",
    "name": "filename.ext",
    "size": 1024,
    "content_type": "text/plain",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "url": "/api/files/{id}/download/",
    "original_file_url": "/api/files/{original_id}/download/",
    "is_original": true
}
```

#### 10. Containerization & Deployment

**Docker Configuration:**
- Multi-stage build with Python 3.10 slim base
- Non-root user execution for security
- Health check endpoint integration
- Static file collection during build

**Startup Process (`start.sh`):**
1. Create data directories with proper permissions
2. Run database migrations
3. Start Gunicorn WSGI server on port 8000

**Production Considerations:**
- WhiteNoise for static file serving
- Gunicorn for WSGI application serving
- Health check endpoint for container orchestration
- Environment-based configuration

### Data Flow

1. **File Upload**: Client uploads file → Authentication check → File validation → Hash calculation → Deduplication check → Database storage → Elasticsearch indexing → Response
2. **File Search**: Client search request → Authentication check → Elasticsearch query (if available) → Database filtering → Paginated response
3. **File Download**: Client download request → Authentication check → File retrieval → Content serving (from original if duplicate)
4. **File Deletion**: Client delete request → Authentication check → Elasticsearch cleanup → Database deletion → Cascade handling

### Performance Optimizations

- **Database Indexing**: Strategic indexes on frequently queried fields
- **Content Deduplication**: Significant storage savings for duplicate files
- **Lazy Loading**: File content only loaded when needed for downloads
- **Caching**: Django's built-in caching for session management
- **Static File Optimization**: WhiteNoise for efficient static file serving

### Error Handling & Resilience

- **Graceful Degradation**: Elasticsearch failures don't break core functionality
- **Validation**: Comprehensive input validation at multiple levels
- **Transaction Safety**: Database operations wrapped in transactions
- **Logging**: Structured logging for debugging and monitoring
- **Health Checks**: Built-in health endpoints for monitoring 