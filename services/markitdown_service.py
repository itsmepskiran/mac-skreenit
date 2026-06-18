"""
MarkItDown Service
Microsoft's MarkItDown library for converting documents to Markdown
Supports: PDF, DOCX, PPTX, Images (PNG, JPG, etc.), HTML, and more
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

from utils_others.logger import logger

class MarkItDownService:
    """
    Service for converting various document formats to Markdown using Microsoft's MarkItDown library.
    This provides better text extraction and structure preservation compared to basic parsers.
    """
    
    def __init__(self):
        self.md = None
        self.supported_formats = [
            "pdf", "docx", "pptx", "xlsx", 
            "png", "jpg", "jpeg", "gif", "bmp", "tiff",
            "html", "htm", "txt", "md"
        ]
        
        if MARKITDOWN_AVAILABLE:
            try:
                self.md = MarkItDown()
                logger.info("MarkItDown service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MarkItDown: {e}")
                self.md = None
        else:
            logger.warning("MarkItDown library not available. Install with: pip install markitdown==0.0.1a2")
    
    def is_available(self) -> bool:
        """Check if MarkItDown is available and initialized"""
        return MARKITDOWN_AVAILABLE and self.md is not None
    
    def convert_to_markdown(self, file_path: str) -> Optional[str]:
        """
        Convert a document to Markdown format.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Markdown text content or None if conversion fails
        """
        if not self.is_available():
            logger.error("MarkItDown service is not available")
            return None
        
        try:
            result = self.md.convert(file_path)
            markdown_content = result.text_content
            
            logger.info(f"Successfully converted {file_path} to Markdown ({len(markdown_content)} chars)")
            return markdown_content
            
        except Exception as e:
            logger.error(f"MarkItDown conversion failed for {file_path}: {e}")
            return None
    
    def convert_with_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Convert a document to Markdown and extract metadata.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with markdown content and metadata
        """
        if not self.is_available():
            logger.error("MarkItDown service is not available")
            return None
        
        try:
            result = self.md.convert(file_path)
            
            response = {
                "markdown": result.text_content,
                "metadata": {
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "file_extension": Path(file_path).suffix.lower().lstrip('.'),
                    "content_length": len(result.text_content),
                }
            }
            
            # Add any additional metadata from MarkItDown result if available
            if hasattr(result, 'metadata'):
                response["metadata"].update(result.metadata)
            
            logger.info(f"Successfully converted {file_path} with metadata")
            return response
            
        except Exception as e:
            logger.error(f"MarkItDown conversion with metadata failed for {file_path}: {e}")
            return None
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the file format is supported by MarkItDown.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if format is supported, False otherwise
        """
        if not self.is_available():
            return False
        
        extension = Path(file_path).suffix.lower().lstrip('.')
        return extension in self.supported_formats
    
    def get_supported_formats(self) -> list:
        """Return list of supported file formats"""
        return self.supported_formats.copy()


# Singleton instance
markitdown_service = MarkItDownService()
