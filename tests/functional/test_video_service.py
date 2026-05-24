import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import uuid

# Import the app from the video-service main module
# Since we are in a different directory, we need to adjust the path
import sys
sys.path.append('C:\\Users\\Maks\\Desktop\\ДИПЛОМ\\video.dgi.mos.ru\\services\\video-service\\src')

from main import app

client = TestClient(app)

# Mock data
mock_user_id = str(uuid.uuid4())
mock_video_id = str(uuid.uuid4())
mock_channel_id = str(uuid.uuid4())
mock_token = "mock_token"

# Mock responses for auth service
mock_auth_response = {
    "id": mock_user_id,
    "username": "testuser",
    "email": "test@example.com"
}

mock_internal_auth_token = "internal-secret-token"

# Mock database responses
mock_video_data = {
    "id": mock_video_id,
    "title": "Test Video",
    "description": "Test Description",
    "user_id": mock_user_id,
    "channel_id": mock_channel_id,
    "file_size": 1024,
    "minio_key": f"{mock_video_id}/test.mp4",
    "status": "uploaded",
    "is_private": False,
    "tags": ["test"],
    "classification": "public",
    "created_at": "2026-05-18T14:43:46+03:00",
    "duration": 300,
    "resolution": "1280x720",
    "bitrate": 5000,
    "thumbnail_url": f"{mock_video_id}/thumbnail.jpg",
    "hls_playlist_url": f"{mock_video_id}/hls/master.m3u8",
    "views_count": 0,
    "transcoding_progress": 0
}

mock_channel_data = {
    "id": mock_channel_id,
    "name": "Test Channel",
    "description": "Test Channel Description",
    "handle": "testhandle",
    "avatar_url": None,
    "banner_url": None,
    "owner_id": mock_user_id,
    "subscribers_count": 0,
    "is_verified": False,
    "created_at": "2026-05-18T14:43:46+03:00"
}

# Mock MinIO client
class MockMinioClient:
    def presigned_put_object(self, bucket, key, expires):
        return f"https://mock-minio.com/{bucket}/{key}?presigned=true"
    
    def presigned_get_object(self, bucket, key, expires):
        return f"https://mock-minio.com/{bucket}/{key}?presigned=true"
    
    def put_object(self, bucket, key, data, length, content_type):
        pass
    
    def get_object(self, bucket, key):
        class MockObject:
            def __init__(self):
                self.data = b"mock video data"
            def stream(self, chunk_size):
                yield self.data
            def close(self):
                pass
            def release_conn(self):
                pass
        return MockObject()
    
    def bucket_exists(self, bucket):
        return True
    
    def make_bucket(self, bucket):
        pass
    
    def remove_object(self, bucket, key):
        pass
    
    def list_objects(self, bucket, prefix, recursive):
        return []

# Mock database session
class MockAsyncSession:
    async def execute(self, query, params=None):
        class MockResult:
            def __init__(self, data=None):
                self.data = data or []
            def fetchall(self):
                return self.data
            def first(self):
                return self.data[0] if self.data else None
            def scalar(self):
                return 1 if self.data else 0
        
        # Handle different query types
        query_str = str(query)
        if "SELECT" in query_str and "videos" in query_str:
            return MockResult([mock_video_data])
        elif "SELECT" in query_str and "channels" in query_str:
            return MockResult([mock_channel_data])
        elif "INSERT" in query_str:
            return MockResult([None])
        elif "UPDATE" in query_str:
            return MockResult([None])
        elif "DELETE" in query_str:
            return MockResult([None])
        else:
            return MockResult([])
    
    async def commit(self):
        pass

# Mock auth client
class MockAuthClient:
    async def verify_token(self, token):
        if token == mock_token:
            return mock_auth_response
        return None
    
    async def get_user_service_permissions(self, user_id):
        if user_id == mock_user_id:
            return {"permissions": ["view_public_videos", "upload_video"]}
        return {}
    
    async def get_internal_user_service_role(self, user_id, service_name):
        if service_name == "video":
            return {"role": "uploader"}

# Mock functions
def mock_get_current_user_id():
    return mock_user_id

def mock_require_current_user():
    return mock_user_id

def mock_get_db():
    return MockAsyncSession()

# Apply patches
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch('main.get_db', return_value=MockAsyncSession()), \
         patch('main.require_current_user', return_value=mock_user_id), \
         patch('main.minio_client', MockMinioClient()), \
         patch('main.auth_client', MockAuthClient()), \
         patch('main.settings') as mock_settings:
        # Mock settings
        mock_settings.minio_endpoint = "localhost:9000"
        mock_settings.minio_access_key = "minioadmin"
        mock_settings.minio_secret_key = "minioadmin"
        mock_settings.minio_secure = False
        mock_settings.minio_bucket = "videos"
        mock_settings.minio_external_endpoint = "localhost:9000"
        mock_settings.public_media_via_api = True
        mock_settings.public_video_api_url = "http://localhost:8001"
        mock_settings.upload_expiry_seconds = 3600
        mock_settings.signed_url_expiry_seconds = 3600
        mock_settings.internal_auth_token = mock_internal_auth_token
        mock_settings.auth_service_url = "http://auth-service:8000"
        mock_settings.transcoding_qualities = ["180p", "360p", "480p", "720p", "1080p"]
        mock_settings.hls_segment_duration = 2
        yield

def test_init_upload():
    """Test video upload initialization"""
    response = client.post(
        "/videos/upload/init",
        data={
            "title": "Test Video",
            "description": "Test Description",
            "is_private": "false",
            "tags": '["test"]',
            "classification": "public",
            "filename": "test.mp4",
            "file_size": 1024,
            "channel_id": mock_channel_id
        },
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "video_id" in data
    assert "upload_url" in data
    assert "minio_key" in data
    assert data["upload_url"].startswith("https://mock-minio.com")

def test_upload_video_data():
    """Test uploading video data"""
    # First create a video record
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            status="uploading",
            minio_key=f"{mock_video_id}/test.mp4"
        )
        
        # Mock file upload
        response = client.post(
            f"/videos/{mock_video_id}/upload-data",
            files={"file": ("test.mp4", b"mock video content", "video/mp4")},
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "File uploaded successfully"

def test_complete_upload():
    """Test completing upload"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            status="uploading"
        )
        mock_video.update_status.return_value = None
        
        response = client.post(
            f"/videos/{mock_video_id}/complete",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Upload completed, ready to publish"

def test_publish_video():
    """Test publishing video"""
    with patch('main.Video') as mock_video, \
         patch('main.BackgroundTasks') as mock_bg:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            status="uploaded",
            minio_key=f"{mock_video_id}/test.mp4"
        )
        mock_video.status = "uploaded"
        
        response = client.post(
            f"/videos/{mock_video_id}/publish",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Publishing started"

def test_get_video():
    """Test getting video details"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            title="Test Video",
            description="Test Description",
            user_id=mock_user_id,
            channel_id=mock_channel_id,
            file_size=1024,
            status="ready",
            is_private=False,
            tags=["test"],
            classification="public",
            created_at="2026-05-18T14:43:46+03:00",
            duration=300,
            resolution="1280x720",
            bitrate=5000,
            thumbnail_url=f"{mock_video_id}/thumbnail.jpg",
            hls_playlist_url=f"{mock_video_id}/hls/master.m3u8",
            views_count=0,
            transcoding_progress=0
        )
        
        # Mock channel lookup
        with patch('main.Channel') as mock_channel:
            mock_channel.get_by_id.return_value = MagicMock(
                name="Test Channel",
                handle="testhandle"
            )
            
            response = client.get(
                f"/videos/{mock_video_id}",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_video_id
            assert data["title"] == "Test Video"
            assert data["owner_username"] == "Test Channel"

def test_list_videos():
    """Test listing videos"""
    with patch('main.Video') as mock_video:
        mock_video.get_all.return_value = [MagicMock(
            id=mock_video_id,
            title="Test Video",
            description="Test Description",
            user_id=mock_user_id,
            channel_id=mock_channel_id,
            file_size=1024,
            status="ready",
            is_private=False,
            tags=["test"],
            classification="public",
            created_at="2026-05-18T14:43:46+03:00",
            duration=300,
            resolution="1280x720",
            bitrate=5000,
            thumbnail_url=f"{mock_video_id}/thumbnail.jpg",
            hls_playlist_url=f"{mock_video_id}/hls/master.m3u8",
            views_count=0,
            transcoding_progress=0
        )]
        
        # Mock channel lookup
        with patch('main.Channel') as mock_channel:
            mock_channel.get_by_id.return_value = MagicMock(
                name="Test Channel",
                handle="testhandle"
            )
            
            response = client.get(
                "/videos",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == mock_video_id

def test_create_channel():
    """Test creating a channel"""
    with patch('main.Channel') as mock_channel:
        mock_channel.get_by_owner.return_value = None  # No existing channel
        mock_channel.get_by_handle.return_value = None  # Handle not taken
        mock_channel.create.return_value = MagicMock(
            id=mock_channel_id,
            name="Test Channel",
            description="Test Channel Description",
            handle="testhandle",
            avatar_url=None,
            banner_url=None,
            owner_id=mock_user_id,
            subscribers_count=0,
            is_verified=False,
            created_at="2026-05-18T14:43:46+03:00"
        )
        
        response = client.post(
            "/channels",
            json={
                "name": "Test Channel",
                "description": "Test Channel Description",
                "handle": "testhandle"
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_channel_id
        assert data["name"] == "Test Channel"

def test_get_my_channel():
    """Test getting own channel"""
    with patch('main.Channel') as mock_channel:
        mock_channel.get_by_owner.return_value = MagicMock(
            id=mock_channel_id,
            name="Test Channel",
            description="Test Channel Description",
            handle="testhandle",
            avatar_url=None,
            banner_url=None,
            owner_id=mock_user_id,
            subscribers_count=0,
            is_verified=False,
            created_at="2026-05-18T14:43:46+03:00"
        )
        
        response = client.get(
            "/channels/my",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_channel_id
        assert data["name"] == "Test Channel"

def test_like_video():
    """Test liking a video"""
    with patch('main.text') as mock_text:
        # Mock the database execute for checking existing like
        mock_result = MagicMock()
        mock_result.first.return_value = None  # Not liked yet
        mock_text.return_value = mock_result
        
        # Mock the database execute for inserting like
        mock_insert_result = MagicMock()
        mock_text.side_effect = [mock_result, mock_insert_result]
        
        # Mock get_likes_count
        with patch('main.get_likes_count', return_value=1):
            response = client.post(
                f"/videos/{mock_video_id}/like",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Liked"
            assert data["likes_count"] == 1

def test_get_video_likes():
    """Test getting video likes"""
    with patch('main.text') as mock_text:
        # Mock the database execute for checking if user liked
        mock_result = MagicMock()
        mock_result.first.return_value = None  # Not liked
        mock_text.return_value = mock_result
        
        # Mock get_likes_count
        with patch('main.get_likes_count', return_value=5):
            response = client.get(
                f"/videos/{mock_video_id}/likes",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["likes_count"] == 5
            assert data["user_liked"] == False

def test_record_view():
    """Test recording a view"""
    with patch('main.text') as mock_text:
        # Mock the database execute for checking existing view
        mock_result = MagicMock()
        mock_result.first.return_value = None  # Not viewed yet
        mock_text.return_value = mock_result
        
        response = client.post(
            f"/videos/{mock_video_id}/views",
            json={"watched_duration": 120},
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "View recorded"

def test_get_signed_url():
    """Test getting signed URL"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            minio_key=f"{mock_video_id}/test.mp4",
            is_private=False
        )
        
        # Mock minio_client.presigned_get_object
        with patch('main.minio_client') as mock_minio:
            mock_minio.presigned_get_object.return_value = "https://mock-minio.com/videos/test?signed=true"
            
            response = client.get(
                f"/videos/{mock_video_id}/signed-url",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "signed_url" in data
            assert data["signed_url"] == "https://mock-minio.com/videos/test?signed=true"

def test_get_video_thumbnail():
    """Test getting video thumbnail"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            thumbnail_url=f"{mock_video_id}/thumbnail.jpg",
            is_private=False
        )
        
        response = client.get(
            f"/videos/{mock_video_id}/thumbnail",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "thumbnail_url" in data
        assert data["thumbnail_url"] == "http://localhost:9000/videos/{mock_video_id}/thumbnail.jpg"

def test_get_video_playlist():
    """Test getting video playlist"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            status="ready",
            hls_playlist_url=f"{mock_video_id}/hls/master.m3u8",
            is_private=False
        )
        
        # Mock _storage_public_url
        with patch('main._storage_public_url', return_value="http://localhost:8001/media/{mock_video_id}/hls/master.m3u8"):
            response = client.get(
                f"/videos/{mock_video_id}/playlist",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "playlist_url" in data
            assert data["status"] == "ready"

def test_update_video():
    """Test updating video metadata"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id
        )
        mock_video.update_metadata.return_value = None
        
        response = client.put(
            f"/videos/{mock_video_id}",
            json={
                "title": "Updated Title",
                "description": "Updated Description"
            },
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Video updated successfully"

def test_delete_video():
    """Test deleting video"""
    with patch('main.Video') as mock_video:
        mock_video.get_by_id.return_value = MagicMock(
            id=mock_video_id,
            user_id=mock_user_id,
            minio_key=f"{mock_video_id}/test.mp4"
        )
        
        # Mock MinIO operations
        with patch('main.minio_client') as mock_minio:
            mock_minio.remove_object.return_value = None
            mock_minio.list_objects.return_value = []
            
            response = client.delete(
                f"/videos/{mock_video_id}",
                headers={"Authorization": f"Bearer {mock_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Video deleted successfully"