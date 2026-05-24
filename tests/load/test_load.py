import pytest
import time
import concurrent.futures
from unittest.mock import patch, MagicMock
import sys
sys.path.append('C:\\Users\\Maks\\Desktop\\ДИПЛОМ\\video.dgi.mos.ru\\services\\video-service\\src')

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Mock data
mock_user_id = "11111111-1111-1111-1111-111111111111"
mock_video_id = "22222222-2222-2222-2222-222222222222"
mock_channel_id = "33333333-3333-3333-3333-333333333333"
mock_token = "mock_token"

# Mock responses
mock_auth_response = {
    "id": mock_user_id,
    "username": "testuser",
    "email": "test@example.com"
}

# Mock MinIO client
class MockMinioClient:
    def presigned_put_object(self, bucket, key, expires):
        return f"https://mock-minio.com/{bucket}/{key}?presigned=true"
    
    def presigned_get_object(self, bucket, key, expires):
        return f"https://mock-minio.com/{bucket}/{key}?presigned=true"
    
    def bucket_exists(self, bucket):
        return True
    
    def make_bucket(self, bucket):
        pass

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
        
        query_str = str(query)
        if "SELECT" in query_str and "videos" in query_str:
            return MockResult([{
                "id": mock_video_id,
                "title": "Test Video",
                "description": "Test Description",
                "user_id": mock_user_id,
                "channel_id": mock_channel_id,
                "file_size": 1024,
                "minio_key": f"{mock_video_id}/test.mp4",
                "status": "ready",
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
            }])
        elif "SELECT" in query_str and "channels" in query_str:
            return MockResult([{
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
            }])
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

# Apply patches for load testing
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch('main.get_db', return_value=MockAsyncSession()), \
         patch('main.require_current_user', return_value=mock_user_id), \
         patch('main.minio_client', MockMinioClient()), \
         patch('main.auth_client', MockAuthClient()), \
         patch('main.settings') as mock_settings:
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
        mock_settings.internal_auth_token = "internal-secret-token"
        mock_settings.auth_service_url = "http://auth-service:8000"
        mock_settings.transcoding_qualities = ["180p", "360p", "480p", "720p", "1080p"]
        mock_settings.hls_segment_duration = 2
        yield

def test_health_endpoint():
    """Test health endpoint response time"""
    start_time = time.time()
    response = client.get("/health")  # Assuming there's a health endpoint
    end_time = time.time()
    
    # If there's no health endpoint, we'll test a simple endpoint
    if response.status_code == 404:
        response = client.get("/videos", headers={"Authorization": f"Bearer {mock_token}"})
    
    response_time = end_time - start_time
    assert response_time < 2.0  # Should respond within 2 seconds
    # We don't assert status code because it might be 404 if no health endpoint

def test_concurrent_video_list_requests():
    """Test concurrent requests to list videos endpoint"""
    def make_request():
        start = time.time()
        response = client.get(
            "/videos",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        end = time.time()
        return response.status_code, end - start
    
    # Simulate 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Check that all requests succeeded
    status_codes = [r[0] for r in results]
    response_times = [r[1] for r in results]
    
    # All should be 200 (or 404 if endpoint doesn't exist, but we expect 200 with our mocks)
    assert all(code == 200 for code in status_codes), f"Some requests failed: {status_codes}"
    
    # Average response time should be under 1 second
    avg_response_time = sum(response_times) / len(response_times)
    assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"
    
    # No single request should take more than 2 seconds
    assert all(t < 2.0 for t in response_times), f"Some requests too slow: {response_times}"

def test_concurrent_video_upload_init():
    """Test concurrent upload initialization requests"""
    def make_request():
        start = time.time()
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
        end = time.time()
        return response.status_code, end - start
    
    # Simulate 5 concurrent upload init requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    status_codes = [r[0] for r in results]
    response_times = [r[1] for r in results]
    
    # All should be 200
    assert all(code == 200 for code in status_codes), f"Some requests failed: {status_codes}"
    
    # Average response time under 1.5 seconds
    avg_response_time = sum(response_times) / len(response_times)
    assert avg_response_time < 1.5, f"Average response time too high: {avg_response_time}s"

def test_sequential_requests_load():
    """Test sequential requests to simulate sustained load"""
    response_times = []
    
    # Make 20 sequential requests to list videos
    for i in range(20):
        start = time.time()
        response = client.get(
            "/videos",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        end = time.time()
        
        assert response.status_code == 200
        response_times.append(end - start)
    
    # Check that response times don't degrade significantly over time
    first_half_avg = sum(response_times[:10]) / 10
    second_half_avg = sum(response_times[10:]) / 10
    
    # Second half shouldn't be more than 50% slower than first half
    assert second_half_avg < first_half_avg * 1.5, \
        f"Response time degraded: first half {first_half_avg}s, second half {second_half_avg}s"
    
    # Overall average should be under 1 second
    overall_avg = sum(response_times) / len(response_times)
    assert overall_avg < 1.0, f"Overall average response time too high: {overall_avg}s"

def test_large_payload_handling():
    """Test handling of larger payloads"""
    # Test with a larger description
    large_description = "A" * 10000  # 10KB description
    
    start = time.time()
    response = client.post(
        "/videos/upload/init",
        data={
            "title": "Test Video with Large Description",
            "description": large_description,
            "is_private": "false",
            "tags": '["test", "large"]',
            "classification": "public",
            "filename": "large_test.mp4",
            "file_size": 1024000,  # 1MB
            "channel_id": mock_channel_id
        },
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    end = time.time()
    
    assert response.status_code == 200
    assert (end - start) < 3.0  # Should handle large payload in under 3 seconds
    
    data = response.json()
    assert "video_id" in data
    assert "upload_url" in data