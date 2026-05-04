#!/bin/sh
# Wait for MinIO to start
sleep 5

# Set bucket policy to public read-only
mc config host add local http://minio:9000 minioadmin minioadmin --api s3v4
mc policy set download local/videos

echo "MinIO bucket 'videos' configured as public read-only"
