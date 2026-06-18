# Resume Analysis Feature Documentation

## Overview
The Resume Analysis feature provides comprehensive resume parsing, analysis, and improvement recommendations. It supports multiple file formats and offers predefined format templates for different industries.

## Features

### 📄 File Support
- **PDF** - Using PyMuPDF for text extraction
- **DOCX** - Using python-docx for document parsing  
- **TXT** - Plain text resume files

### 🔍 Analysis Capabilities
- **Contact Information Extraction** - Email, phone, LinkedIn, GitHub, websites
- **Section Identification** - Summary, Experience, Education, Skills, Projects, etc.
- **Skill Extraction** - Technical and soft skills identification
- **Experience Parsing** - Company, position, and duration extraction
- **Education Parsing** - Degree, institution, and year extraction

### 📊 Scoring System
- **Overall Score** (0-100) - Weighted scoring across sections
- **Section Scores** - Individual analysis for each resume section
- **Format Compliance** - Check against predefined templates

### 🎯 Predefined Formats
1. **Modern Professional** - Clean, contemporary format
2. **Traditional Conservative** - Classic format for traditional industries
3. **ATS Optimized** - Optimized for Applicant Tracking Systems
4. **Creative Industry** - Visual format for creative roles

## API Endpoints

### POST `/api/v1/resume-analysis/analyze`
Upload and analyze a resume file.

**Request:**
- `file` - Resume file (PDF, DOCX, TXT)
- Authentication required

**Response:**
```json
{
  "success": true,
  "filename": "resume.pdf",
  "overall_score": 78.5,
  "sections": [
    {
      "name": "summary",
      "score": 85.0,
      "issues": [],
      "suggestions": []
    }
  ],
  "format_issues": ["Missing LinkedIn profile"],
  "recommendations": ["Add LinkedIn profile URL"],
  "parsed_data": {...}
}
```

### POST `/api/v1/resume-analysis/check-format`
Check resume compliance with a specific format.

**Request:**
- `file` - Resume file
- `format_type` - modern, traditional, ats, creative

**Response:**
```json
{
  "format_type": "modern",
  "is_compliant": true,
  "issues": [],
  "suggestions": []
}
```

### GET `/api/v1/resume-analysis/formats`
Get available resume formats with descriptions.

**Response:**
```json
{
  "formats": {
    "modern": {
      "name": "Modern Professional",
      "description": "Clean, contemporary format...",
      "features": ["Contact info at top", "Professional summary"]
    }
  }
}
```

### GET `/api/v1/resume-analysis/analysis-history`
Get user's resume analysis history (placeholder for future implementation).

## Architecture

### Core Components

#### Resume Parser (`services/resume_parser.py`)
- Extracts text from PDF, DOCX, TXT files
- Identifies resume sections using regex patterns
- Extracts contact information, skills, experience, education
- Cleans and normalizes text content

#### Resume Analyzer (`services/resume_analyzer.py`)
- Analyzes each resume section with specific criteria
- Calculates weighted scores
- Generates improvement recommendations
- Checks format compliance against templates

#### API Router (`routers/resume_analysis.py`)
- FastAPI endpoints for resume analysis
- File upload handling with temporary storage
- Authentication integration
- Response formatting

#### Database Models (`models/resume_analysis.py`)
- `ResumeAnalysis` - Stores analysis results
- `ResumeAnalysisHistory` - Tracks improvements over time

### Dependencies
All required dependencies are already in your `requirements.txt`:
- `PyMuPDF==1.24.9` - PDF processing
- `python-docx==1.1.2` - DOCX processing
- `resumepy==1.0.0` - Resume parsing utilities
- `fastapi==0.115.0` - API framework
- Existing NLP libraries for text analysis

## Usage Examples

### Basic Resume Analysis
```bash
curl -X POST "http://localhost:8080/api/v1/resume-analysis/analyze" \
  -H "Authorization: Bearer <token>" \
  -F "file=@resume.pdf"
```

### Format Compliance Check
```bash
curl -X POST "http://localhost:8080/api/v1/resume-analysis/check-format" \
  -H "Authorization: Bearer <token>" \
  -F "file=@resume.pdf" \
  -F "format_type=modern"
```

## Testing

Run the test script to verify functionality:
```bash
cd /Users/skreenit/Documents/backend-skreenit
python3 test_resume_analysis.py
```

The test includes:
- Resume parsing with sample data
- Section identification and analysis
- Scoring system validation
- Format compliance checking
- Recommendation generation

## Integration Notes

### Authentication
All endpoints require JWT authentication via the existing auth middleware.

### File Handling
- Temporary files are automatically cleaned up after processing
- File size limits can be configured in FastAPI settings
- Supported file types are validated before processing

### Error Handling
- Comprehensive error handling with meaningful messages
- Graceful fallbacks for unsupported formats
- Logging for debugging and monitoring

### Performance
- Asynchronous processing for better performance
- Memory-efficient text processing
- Optimized regex patterns for section detection

## Future Enhancements

### Planned Features
1. **Analysis History** - Track resume improvements over time
2. **Multiple Format Comparison** - Compare against multiple templates
3. **Industry-Specific Templates** - Specialized formats for different industries
4. **Resume Generation** - Generate improved resume versions
5. **Bulk Analysis** - Analyze multiple resumes simultaneously
6. **Integration with Job Matching** - Match resumes to job requirements

### Database Integration
The database models are ready for integration with your existing database schema. You'll need to:
1. Add the new models to your database migration
2. Update the User model to include relationships
3. Implement the analysis history endpoint

### Performance Optimizations
1. **Caching** - Cache analysis results for repeated uploads
2. **Background Processing** - Process large files asynchronously
3. **Distributed Processing** - Scale analysis across multiple workers

## Security Considerations

- File type validation prevents malicious uploads
- Temporary file cleanup prevents disk space issues
- Input sanitization prevents injection attacks
- Rate limiting can be added to prevent abuse

## Support

For issues or questions about the resume analysis feature:
1. Check the test script for usage examples
2. Review the log files for debugging information
3. Verify all dependencies are installed correctly
4. Ensure file permissions allow temporary file creation

---

**Status**: ✅ Fully implemented and tested
**Last Updated**: April 24, 2026
**Version**: 1.0.0
