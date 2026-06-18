"""
Cloudflare R2 File Upload Service
Handles file uploads to Cloudflare R2 storage.
"""

import os
import uuid
import boto3
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from utils_others.logger import logger

# Load environment variables
load_dotenv()


class R2Service:
    """Service for uploading files to Cloudflare R2."""
    
    def __init__(self):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY")
        self.secret_key = os.getenv("CLOUDFLARE_R2_SECRET_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.endpoint = os.getenv("R2_ENDPOINT", "https://storage.skreenit.com")
        
        # Validate credentials
        if not all([self.account_id, self.access_key, self.secret_key, self.bucket_name]):
            missing = []
            if not self.account_id:
                missing.append("CLOUDFLARE_ACCOUNT_ID")
            if not self.access_key:
                missing.append("CLOUDFLARE_R2_ACCESS_KEY")
            if not self.secret_key:
                missing.append("CLOUDFLARE_R2_SECRET_KEY")
            if not self.bucket_name:
                missing.append("R2_BUCKET_NAME")
            raise ValueError(f"Missing R2 credentials: {', '.join(missing)}")
        
        # Initialize R2 client
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='auto'
        )
    
    def upload_file(self, file_content: bytes, filename: str, folder: str) -> str:
        """
        Upload file to R2 and return public URL.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            folder: Folder name (resumes, videos, profilepics)
            
        Returns:
            Public URL of uploaded file
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = filename.split(".")[-1] if "." in filename else ""
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
            
            # R2 key (path)
            key = f"datastorage/{folder}/{unique_filename}"
            
            # Determine content type
            content_type = self._get_content_type(filename)
            logger.info(f"Uploading file: {filename} -> {unique_filename} with content-type: {content_type}")
            
            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Return public URL
            public_url = f"{self.endpoint}/datastorage/{folder}/{unique_filename}"
            
            logger.info(f"File uploaded successfully: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"R2 upload failed: {str(e)}")
            raise Exception(f"File upload failed: {str(e)}")
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        extension = filename.lower().split(".")[-1] if "." in filename else ""
        
        content_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "webm": "video/webm"
        }
        
        return content_types.get(extension, "application/octet-stream")
    
    def delete_file(self, url: str) -> bool:
        """
        Delete file from R2 by URL.
        
        Args:
            url: Full public URL of the file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Extract key from URL
            # URL format: https://storage.skreenit.com/datastorage/folder/filename
            if self.endpoint in url:
                key = url.split(self.endpoint + "/")[-1]
            elif "datastorage/" in url:
                key = url.split("datastorage/")[-1]
                key = f"datastorage/{key}"
            else:
                logger.warning(f"Cannot extract R2 key from URL: {url}")
                return False
            
            logger.info(f"Deleting file from R2: {key}")
            
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"File deleted successfully: {key}")
            return True
            
        except Exception as e:
            logger.error(f"R2 delete failed: {str(e)}")
            return False


# Global R2 service instance
r2_service = R2Service()
