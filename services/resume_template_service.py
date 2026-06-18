"""
Resume Template Conversion Service
Converts uploaded resumes to different template formats using MarkItDown and HTML-to-PDF conversion
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from services.markitdown_service import markitdown_service
    MARKITDOWN_AVAILABLE = markitdown_service.is_available()
except ImportError:
    MARKITDOWN_AVAILABLE = False

try:
    from services.resume_parser import ResumeParser
    RESUME_PARSER_AVAILABLE = True
except ImportError:
    RESUME_PARSER_AVAILABLE = False

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from services.r2_service import R2Service
    R2_AVAILABLE = True
except ImportError:
    R2_AVAILABLE = False

from utils_others.logger import logger

class ResumeTemplateService:
    """
    Service for converting resumes to different template formats.
    Supports: Modern, ATS Optimized, Traditional, Creative
    """
    
    def __init__(self):
        self.templates = {
            'modern': self._generate_modern_template,
            'ats': self._generate_ats_template,
            'traditional': self._generate_traditional_template,
            'creative': self._generate_creative_template
        }
    
    async def convert_resume_to_template(
        self, 
        file_path: str, 
        template_id: str = 'modern',
        parsed_data: Optional[Dict[str, Any]] = None,
        convert_to_pdf: bool = True,
        upload_to_r2: bool = True,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a resume file to a specific template format.
        
        Args:
            file_path: Path to the resume file (PDF, DOCX, etc.)
            template_id: Template to use (modern, ats, traditional, creative)
            parsed_data: Pre-parsed resume data (optional, will parse if not provided)
            convert_to_pdf: Whether to convert HTML to PDF
            upload_to_r2: Whether to upload the converted PDF to R2
            user_id: User ID for R2 upload path
            
        Returns:
            Dictionary with html_content and pdf_url (if converted/uploaded) or None if conversion fails
        """
        try:
            # Parse resume if not already parsed
            if not parsed_data:
                if not RESUME_PARSER_AVAILABLE:
                    logger.error("Resume parser not available")
                    return None
                
                parser = ResumeParser()
                # Determine content type from file extension
                content_type = self._get_content_type(file_path)
                parsed_data = await parser.parse_resume(file_path, content_type)
            
            # Get template generator
            template_generator = self.templates.get(template_id, self._generate_modern_template)
            
            # Generate HTML with template
            html_content = template_generator(parsed_data)
            
            result = {
                "html_content": html_content,
                "template_id": template_id
            }
            
            # Convert to PDF if requested
            if convert_to_pdf and REPORTLAB_AVAILABLE:
                pdf_path = await self._convert_html_to_pdf(html_content, template_id)
                if pdf_path:
                    result["pdf_path"] = pdf_path
                    
                    # Upload to R2 if requested
                    if upload_to_r2 and R2_AVAILABLE and user_id:
                        pdf_url = await self._upload_pdf_to_r2(pdf_path, user_id, template_id)
                        if pdf_url:
                            result["pdf_url"] = pdf_url
                            # Clean up local PDF file
                            if os.path.exists(pdf_path):
                                os.unlink(pdf_path)
            
            logger.info(f"Successfully converted resume to {template_id} template")
            return result
            
        except Exception as e:
            logger.error(f"Resume template conversion failed: {e}")
            return None
    
    async def _convert_html_to_pdf(self, html_content: str, template_id: str) -> Optional[str]:
        """Convert HTML content to PDF using ReportLab."""
        try:
            if not REPORTLAB_AVAILABLE:
                logger.error("ReportLab not available for PDF conversion")
                return None
            
            # Create temporary file for PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                pdf_path = temp_pdf.name
            
            # Parse HTML content to extract text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            story = []
            styles = getSampleStyleSheet()
            
            # Add custom styles based on template
            if template_id == 'modern':
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=24,
                    textColor=colors.HexColor('#1e40af'),
                    spaceAfter=30,
                    alignment=1  # center
                )
                header_style = ParagraphStyle(
                    'CustomHeader',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.HexColor('#1e40af'),
                    spaceAfter=12,
                    spaceBefore=20
                )
            elif template_id == 'creative':
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=28,
                    textColor=colors.HexColor('#667eea'),
                    spaceAfter=30,
                    alignment=1
                )
                header_style = ParagraphStyle(
                    'CustomHeader',
                    parent=styles['Heading2'],
                    fontSize=18,
                    textColor=colors.HexColor('#667eea'),
                    spaceAfter=12,
                    spaceBefore=20
                )
            else:  # ats, traditional
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    textColor=colors.black,
                    spaceAfter=20,
                    alignment=1
                )
                header_style = ParagraphStyle(
                    'CustomHeader',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.black,
                    spaceAfter=10,
                    spaceBefore=15
                )
            
            # Extract and add content
            # Header section
            header = soup.find('div', class_='header')
            if header:
                h1 = header.find('h1')
                if h1:
                    story.append(Paragraph(h1.get_text(), title_style))
                contact = header.find('div', class_='contact')
                if contact:
                    story.append(Paragraph(contact.get_text(), styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            # Content sections
            content_div = soup.find('div', class_='content') if template_id == 'creative' else soup
            sections = content_div.find_all('div', class_='section')
            
            for section in sections:
                h2 = section.find('h2')
                if h2:
                    story.append(Paragraph(h2.get_text(), header_style))
                
                section_content = section.find('div', class_='section-content')
                if section_content:
                    # Convert text with basic formatting
                    text = section_content.get_text()
                    paragraphs = text.split('\n')
                    for para in paragraphs:
                        if para.strip():
                            story.append(Paragraph(para.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Skills section
                skills_div = section.find('div', class_='skills')
                if skills_div:
                    skills_text = skills_div.get_text()
                    story.append(Paragraph(skills_text, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Successfully converted HTML to PDF for {template_id} template")
            return pdf_path
            
        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}")
            return None
    
    async def _upload_pdf_to_r2(self, pdf_path: str, user_id: str, template_id: str) -> Optional[str]:
        """Upload converted PDF to R2 storage."""
        try:
            r2_service = R2Service()
            
            # Generate unique filename
            filename = f"resume_{user_id}_{template_id}_{Path(pdf_path).stem}.pdf"
            
            # Upload to R2
            with open(pdf_path, 'rb') as f:
                pdf_url = r2_service.upload_file(f, filename, "resumes")
            
            logger.info(f"Successfully uploaded converted resume to R2: {pdf_url}")
            return pdf_url
            
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type from file extension."""
        ext = Path(file_path).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain'
        }
        return content_types.get(ext, 'application/pdf')
    
    def _generate_modern_template(self, data: Dict[str, Any]) -> str:
        """Generate modern professional template HTML."""
        contact = data.get('contact_info', {})
        sections = data.get('sections', {})
        skills = data.get('skills', [])
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Calibri', 'Arial', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 3px solid #2563eb; }}
        .header h1 {{ margin: 0; font-size: 28px; color: #1e40af; font-weight: 600; }}
        .header .contact {{ margin-top: 10px; color: #64748b; font-size: 14px; }}
        .section {{ margin-bottom: 25px; }}
        .section h2 {{ color: #1e40af; font-size: 18px; margin-bottom: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }}
        .section-content {{ white-space: pre-line; }}
        .skills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .skill {{ background: #e0e7ff; color: #3730a3; padding: 6px 14px; border-radius: 16px; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{contact.get('emails', [''])[0] if contact.get('emails') else 'YOUR NAME'}</h1>
        <div class="contact">
            {contact.get('emails', [''])[0] if contact.get('emails') else 'email@example.com'} • 
            {contact.get('phones', [''])[0] if contact.get('phones') else '+1 234-567-8900'}
            {f" • {contact.get('linkedin', [''])[0]}" if contact.get('linkedin') else ''}
        </div>
    </div>
    
    {self._render_section('Professional Summary', sections.get('summary')) if sections.get('summary') else ''}
    {self._render_section('Professional Experience', sections.get('experience')) if sections.get('experience') else ''}
    {self._render_section('Education', sections.get('education')) if sections.get('education') else ''}
    
    {self._render_skills_section(skills) if skills else ''}
</body>
</html>
"""
    
    def _generate_ats_template(self, data: Dict[str, Any]) -> str:
        """Generate ATS-optimized template HTML."""
        contact = data.get('contact_info', {})
        sections = data.get('sections', {})
        skills = data.get('skills', [])
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Times New Roman', serif; line-height: 1.5; color: #000; max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 18pt; font-weight: bold; }}
        .header .contact {{ margin-top: 8px; font-size: 11pt; }}
        .section {{ margin-bottom: 15px; }}
        .section h2 {{ font-size: 14pt; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; }}
        .section-content {{ white-space: pre-line; font-size: 11pt; }}
        .skills {{ font-size: 11pt; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{contact.get('emails', [''])[0] if contact.get('emails') else 'YOUR NAME'}</h1>
        <div class="contact">
            {contact.get('emails', [''])[0] if contact.get('emails') else 'email@example.com'} | 
            {contact.get('phones', [''])[0] if contact.get('phones') else '+1 234-567-8900'}
            {f" | {contact.get('linkedin', [''])[0]}" if contact.get('linkedin') else ''}
        </div>
    </div>
    
    {self._render_section('PROFESSIONAL SUMMARY', sections.get('summary')) if sections.get('summary') else ''}
    {self._render_section('PROFESSIONAL EXPERIENCE', sections.get('experience')) if sections.get('experience') else ''}
    {self._render_section('EDUCATION', sections.get('education')) if sections.get('education') else ''}
    
    {self._render_ats_skills_section(skills) if skills else ''}
</body>
</html>
"""
    
    def _generate_traditional_template(self, data: Dict[str, Any]) -> str:
        """Generate traditional conservative template HTML."""
        contact = data.get('contact_info', {})
        sections = data.get('sections', {})
        skills = data.get('skills', [])
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Times New Roman', serif; line-height: 1.6; color: #000; max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 20pt; font-weight: bold; }}
        .header .contact {{ margin-top: 10px; font-size: 12pt; }}
        .section {{ margin-bottom: 25px; }}
        .section h2 {{ font-size: 14pt; font-weight: bold; text-align: center; text-transform: uppercase; margin-bottom: 15px; }}
        .section-content {{ white-space: pre-line; }}
        .objective {{ text-align: center; font-style: italic; margin-bottom: 20px; }}
        .skills {{ text-align: center; font-size: 12pt; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{contact.get('emails', [''])[0] if contact.get('emails') else 'YOUR NAME'}</h1>
        <div class="contact">
            {contact.get('emails', [''])[0] if contact.get('emails') else 'email@example.com'} • 
            {contact.get('phones', [''])[0] if contact.get('phones') else '+1 234-567-8900'}
            {f" • {contact.get('linkedin', [''])[0]}" if contact.get('linkedin') else ''}
        </div>
    </div>
    
    {f'<div class="objective">{sections.get("summary")}</div>' if sections.get('summary') else ''}
    {self._render_section('PROFESSIONAL EXPERIENCE', sections.get('experience')) if sections.get('experience') else ''}
    {self._render_section('EDUCATION', sections.get('education')) if sections.get('education') else ''}
    
    {self._render_traditional_skills_section(skills) if skills else ''}
</body>
</html>
"""
    
    def _generate_creative_template(self, data: Dict[str, Any]) -> str:
        """Generate creative industry template HTML."""
        contact = data.get('contact_info', {})
        sections = data.get('sections', {})
        skills = data.get('skills', [])
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 0; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; margin: 0; }}
        .header h1 {{ margin: 0; font-size: 32px; font-weight: 300; }}
        .header .contact {{ margin-top: 15px; opacity: 0.9; font-size: 14px; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #667eea; font-size: 20px; margin-bottom: 12px; font-weight: 600; }}
        .section-content {{ white-space: pre-line; }}
        .skills {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
        .skill {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{contact.get('emails', [''])[0] if contact.get('emails') else 'YOUR NAME'}</h1>
        <div class="contact">
            {contact.get('emails', [''])[0] if contact.get('emails') else 'email@example.com'} • 
            {contact.get('phones', [''])[0] if contact.get('phones') else '+1 234-567-8900'}
            {f" • {contact.get('linkedin', [''])[0]}" if contact.get('linkedin') else ''}
        </div>
    </div>
    
    <div class="content">
        {self._render_section('✨ About Me', sections.get('summary')) if sections.get('summary') else ''}
        {self._render_section('💼 Professional Journey', sections.get('experience')) if sections.get('experience') else ''}
        {self._render_section('🎓 Academic Background', sections.get('education')) if sections.get('education') else ''}
        
        {self._render_creative_skills_section(skills) if skills else ''}
    </div>
</body>
</html>
"""
    
    def _render_section(self, title: str, content: str) -> str:
        """Render a section with title and content."""
        return f"""
    <div class="section">
        <h2>{title}</h2>
        <div class="section-content">{content}</div>
    </div>
"""
    
    def _render_skills_section(self, skills: list) -> str:
        """Render skills section for modern template."""
        skills_html = ''.join([f'<span class="skill">{skill}</span>' for skill in skills])
        return f"""
    <div class="section">
        <h2>Technical Skills</h2>
        <div class="skills">{skills_html}</div>
    </div>
"""
    
    def _render_ats_skills_section(self, skills: list) -> str:
        """Render skills section for ATS template."""
        skills_text = ', '.join(skills)
        return f"""
    <div class="section">
        <h2>TECHNICAL SKILLS</h2>
        <div class="skills">{skills_text}</div>
    </div>
"""
    
    def _render_traditional_skills_section(self, skills: list) -> str:
        """Render skills section for traditional template."""
        skills_text = ' • '.join(skills)
        return f"""
    <div class="section">
        <h2>SKILLS</h2>
        <div class="skills">{skills_text}</div>
    </div>
"""
    
    def _render_creative_skills_section(self, skills: list) -> str:
        """Render skills section for creative template."""
        skills_html = ''.join([f'<div class="skill">{skill}</div>' for skill in skills])
        return f"""
    <div class="section">
        <h2>🚀 Tech Stack</h2>
        <div class="skills">{skills_html}</div>
    </div>
"""


# Singleton instance
resume_template_service = ResumeTemplateService()
