"""
PDF Report Generation Service for Video Interview Analysis
Generates professional PDF reports with consistent grading.
"""

import io
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.platypus import PageTemplate, Frame, BaseDocTemplate
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

from utils_others.grading import GradeCalculator, get_grade

logger = logging.getLogger(__name__)

# Logo path - fixed to correctly resolve to backend/logos/logobrand.png
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logos', 'logobrand.png')
if not os.path.exists(LOGO_PATH):
    # Fallback for different deployment environments
    LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'logos', 'logobrand.png')


class PDFReportService:
    """Generate PDF reports for video analysis results with professional layout."""
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.logo_path = LOGO_PATH
    
    def _setup_styles(self):
        """Setup custom paragraph styles."""
        # Main title style (Candidate Name)
        self.styles.add(ParagraphStyle(
            name='CandidateTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_LEFT,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style (Position, ID, Date)
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#1e40af'),
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Parameter label style
        self.styles.add(ParagraphStyle(
            name='ParamLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_LEFT
        ))
        
        # Parameter value style
        self.styles.add(ParagraphStyle(
            name='ParamValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Analysis text style
        self.styles.add(ParagraphStyle(
            name='AnalysisText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#475569'),
            alignment=TA_JUSTIFY,
            spaceBefore=4,
            spaceAfter=8,
            leading=14
        ))
        
        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#334155'),
            alignment=TA_CENTER,
            spaceBefore=6,
            fontName='Helvetica-Oblique'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='FooterText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#94a3b8'),
            alignment=TA_CENTER
        ))
        
        # Score circle text
        self.styles.add(ParagraphStyle(
            name='ScoreNumber',
            parent=self.styles['Normal'],
            fontSize=28,
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Score label
        self.styles.add(ParagraphStyle(
            name='ScoreLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER
        ))

    def _add_header_footer(self, canvas_obj: canvas.Canvas, doc: BaseDocTemplate):
        """Add logo to top-right and footer to every page."""
        canvas_obj.saveState()
        
        # Add logo to top-right corner
        if os.path.exists(self.logo_path):
            try:
                logo_width = 35 * mm
                logo_height = 12 * mm
                logo_x = self.page_width - 25*mm - logo_width
                logo_y = self.page_height - 20*mm
                canvas_obj.drawImage(self.logo_path, logo_x, logo_y, 
                                     width=logo_width, height=logo_height, 
                                     preserveAspectRatio=True, mask='auto')
            except Exception as e:
                logger.warning(f"Could not add logo to PDF: {e}")
        
        # Add footer with tools and disclaimer
        footer_y = 12 * mm
        
        # Tools used text
        tools_text = "Analysis powered by: OpenCV (Face Detection), FER (Emotion Analysis), " \
                     "Whisper (Speech-to-Text), LanguageTool (Grammar), spaCy (NLP)"
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(colors.HexColor('#94a3b8'))
        canvas_obj.drawCentredString(self.page_width / 2, footer_y + 8, tools_text)
        
        # Disclaimer
        disclaimer = "This report is AI-generated and should be used as a supplementary assessment tool. " \
                     "Human judgment is recommended for final hiring decisions."
        canvas_obj.setFont('Helvetica-Oblique', 6)
        canvas_obj.setFillColor(colors.HexColor('#cbd5e1'))
        canvas_obj.drawCentredString(self.page_width / 2, footer_y, disclaimer)
        
        # Page number
        page_num = canvas_obj.getPageNumber()
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.HexColor('#94a3b8'))
        canvas_obj.drawRightString(self.page_width - 20*mm, footer_y, f"Page {page_num}")
        
        canvas_obj.restoreState()

    def _score_to_grade(self, score: int) -> tuple:
        """Convert numeric score to letter grade using shared GradeCalculator."""
        result = GradeCalculator.score_to_grade(score)
        return result["grade"], colors.HexColor(result["color"]), result["label"]
    
    def _calculate_wpm_grade(self, wpm: int) -> str:
        """Calculate grade for speaking pace using shared GradeCalculator."""
        return GradeCalculator.calculate_wpm_grade(wpm)
    
    def _calculate_filler_grade(self, count: int) -> str:
        """Calculate grade for filler words using shared GradeCalculator."""
        return GradeCalculator.calculate_filler_grade(count)

    def _create_score_circle(self, score: int, width: float = 140) -> Drawing:
        """Create a circular score display with letter grade inside."""
        drawing = Drawing(width, width + 45)  # Larger height for bigger circle
        
        # Get grade info
        grade, score_color, description = self._score_to_grade(score)
        
        radius = width / 2 - 8
        center_x = width / 2
        center_y = width / 2
        
        # Outer circle (border) - thicker for larger circle
        outer_circle = Circle(center_x, center_y, radius)
        outer_circle.fillColor = colors.white
        outer_circle.strokeColor = score_color
        outer_circle.strokeWidth = 6
        drawing.add(outer_circle)
        
        # Grade letter - upper part of circle (larger font)
        grade_str = String(center_x, center_y + 12, grade)
        grade_str.fontName = 'Helvetica-Bold'
        grade_str.fontSize = 44
        grade_str.fillColor = score_color
        grade_str.textAnchor = 'middle'
        drawing.add(grade_str)
        
        # Description text - lower part of circle
        desc_str = String(center_x, center_y - 18, description)
        desc_str.fontName = 'Helvetica-Bold'
        desc_str.fontSize = 11
        desc_str.fillColor = score_color
        desc_str.textAnchor = 'middle'
        drawing.add(desc_str)
        
        return drawing

    def _create_grade_index_table(self) -> Table:
        """Create a grade index/scale reference table."""
        grade_data = [
            ['Grade', 'Score Range', 'Description'],
            ['A+', '90-100', 'Excellent'],
            ['A', '80-89', 'Very Good'],
            ['B+', '70-79', 'Good'],
            ['B', '60-69', 'Above Average'],
            ['C', '50-59', 'Average'],
            ['D', '40-49', 'Below Average'],
            ['F', '0-39', 'Needs Improvement'],
        ]
        
        # Create table with grade colors
        grade_colors = [
            colors.HexColor('#f1f5f9'),  # Header
            colors.HexColor('#dcfce7'),  # A+ - green light
            colors.HexColor('#dcfce7'),  # A - green light
            colors.HexColor('#dbeafe'),  # B+ - blue light
            colors.HexColor('#dbeafe'),  # B - blue light
            colors.HexColor('#fef3c7'),  # C - amber light
            colors.HexColor('#ffedd5'),  # D - orange light
            colors.HexColor('#fee2e2'),  # F - red light
        ]
        
        table = Table(grade_data, colWidths=[50, 80, 120])
        style_commands = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Grade column centered
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Score range centered
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),     # Description left-aligned
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        for i, bg_color in enumerate(grade_colors):
            style_commands.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
        table.setStyle(TableStyle(style_commands))
        return table

    def _get_recommendation(self, score: int, summary: Dict, nlp: Dict) -> str:
        """Generate recommendation text based on scores."""
        recommendations = []
        
        if score >= 80:
            recommendations.append("Strong candidate with excellent presentation skills.")
        elif score >= 60:
            recommendations.append("Good candidate with solid communication abilities.")
        elif score >= 40:
            recommendations.append("Candidate shows potential but needs improvement in key areas.")
        else:
            recommendations.append("Candidate requires significant improvement before being considered.")
        
        # Add specific observations
        wpm = summary.get('speaking_pace', 0)
        if wpm > 0:
            if wpm < 100:
                recommendations.append("Speaking pace could be faster for better engagement.")
            elif wpm > 160:
                recommendations.append("Consider slowing down for clearer communication.")
            else:
                recommendations.append("Speaking pace is well-balanced.")
        
        fillers = summary.get('filler_words', 0)
        if fillers > 5:
            recommendations.append("Reduce filler words to sound more confident.")
        
        face = summary.get('face_presence', 0)
        if face < 70:
            recommendations.append("Better camera positioning would improve visibility.")
        
        # NLP insights
        if nlp.get('communication_skills', {}).get('score', 0) > 0:
            comm_level = nlp['communication_skills'].get('level', '')
            if comm_level in ['beginner', 'elementary']:
                recommendations.append("Communication skills need development.")
            elif comm_level in ['intermediate', 'advanced']:
                recommendations.append("Strong verbal communication abilities demonstrated.")
        
        return " ".join(recommendations[:4])  # Limit to 3-4 sentences

    def _get_parameter_analysis(self, param_name: str, data: Dict) -> str:
        """Generate 3-4 sentence analysis for a parameter."""
        analyses = {
            'speaking_pace': self._analyze_speaking_pace(data),
            'confidence': self._analyze_confidence(data),
            'face_presence': self._analyze_face_presence(data),
            'filler_words': self._analyze_fillers(data),
            'emotion': self._analyze_emotion(data),
            'grammar': self._analyze_grammar(data),
            'vocabulary': self._analyze_vocabulary(data),
            'sentence_formation': self._analyze_sentences(data),
            'pronunciation': self._analyze_pronunciation(data),
            'voice_modulation': self._analyze_voice_modulation(data),
        }
        return analyses.get(param_name, "No analysis available.")
    
    def _add_face_verification_section(self, elements: list, face_match: Dict):
        """Add Face Verification section to PDF report."""
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Face Verification", self.styles['SectionHeader']))
        
        overall_match = face_match.get("overall_match", False)
        avg_similarity = face_match.get("avg_similarity", 0)
        match_count = face_match.get("match_count", 0)
        mismatch_count = face_match.get("mismatch_count", 0)
        note = face_match.get("note", "")
        
        # Create status indicator
        if overall_match:
            status_text = "VERIFIED"
            status_color = colors.green
            status_bg = colors.Color(0.9, 1, 0.9)
        else:
            status_text = "MISMATCH DETECTED"
            status_color = colors.red
            status_bg = colors.Color(1, 0.9, 0.9)
        
        # Status table
        status_table = Table([
            [Paragraph(f"<b>Face Match Status:</b>", self.styles['AnalysisText']),
             Paragraph(f"<b>{status_text}</b>", ParagraphStyle(
                 'StatusStyle',
                 parent=self.styles['AnalysisText'],
                 textColor=status_color,
                 backColor=status_bg,
                 alignment=1
             ))]
        ], colWidths=[180, 150])
        status_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('BACKGROUND', (1, 0), (1, 0), status_bg),
            ('BOX', (1, 0), (1, 0), 1, status_color),
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 10))
        
        # Similarity score
        score_text = f"Average Face Similarity: {avg_similarity}%"
        elements.append(Paragraph(score_text, self.styles['AnalysisText']))
        
        # Match details
        details_text = f"Videos Matched: {match_count} | Videos with Mismatch: {mismatch_count}"
        elements.append(Paragraph(details_text, self.styles['AnalysisText']))
        
        # Note
        if note:
            elements.append(Paragraph(f"<i>{note}</i>", self.styles['AnalysisText']))
        
        # Warning for mismatch
        if not overall_match:
            elements.append(Spacer(1, 10))
            warning_style = ParagraphStyle(
                'WarningStyle',
                parent=self.styles['AnalysisText'],
                textColor=colors.red,
                backColor=colors.Color(1, 0.95, 0.9),
                borderPadding=8
            )
            warning_text = "WARNING: Face mismatch detected between intro video and response videos. This may indicate different persons appeared in the videos. Please verify candidate identity before proceeding."
            elements.append(Paragraph(warning_text, warning_style))
        
        elements.append(Spacer(1, 15))
    
    def _analyze_pronunciation(self, audio: Dict) -> str:
        """Analyze pronunciation from audio analysis data."""
        score = audio.get('score', 0)
        clarity = audio.get('clarity_score', 0)
        articulation = audio.get('articulation_score', 0)
        phoneme = audio.get('phoneme_accuracy', 0)
        
        if score == 0:
            return "Pronunciation analysis was not available for this recording."
        
        grade, _, _ = self._score_to_grade(score)
        
        analysis = f"Pronunciation received a {grade} grade ({score}/100). "
        
        if clarity >= 80:
            analysis += "Speech clarity was excellent with clear enunciation. "
        elif clarity >= 60:
            analysis += "Speech clarity was good with mostly clear pronunciation. "
        else:
            analysis += "Clarity could be improved with better enunciation. "
        
        if articulation >= 80:
            analysis += "Articulation of difficult words was handled well."
        elif articulation >= 60:
            analysis += "Most challenging words were articulated correctly."
        else:
            analysis += "Practice with complex words would improve articulation."
        
        return analysis
    
    def _analyze_voice_modulation(self, audio: Dict) -> str:
        """Analyze voice modulation from audio analysis data."""
        score = audio.get('score', 0)
        pitch = audio.get('pitch', {})
        energy = audio.get('energy', {})
        
        if score == 0:
            return "Voice modulation analysis was not available for this recording."
        
        grade, _, _ = self._score_to_grade(score)
        
        analysis = f"Voice modulation received a {grade} grade ({score}/100). "
        
        pitch_var = pitch.get('variation_score', 0)
        monotone = pitch.get('monotone_risk', False)
        
        if pitch_var >= 80:
            analysis += "Excellent pitch variation kept the delivery engaging. "
        elif pitch_var >= 60:
            analysis += "Good pitch variation maintained listener interest. "
        elif monotone:
            analysis += "Voice tended toward monotone, reducing engagement. "
        else:
            analysis += "More pitch variation would improve delivery. "
        
        energy_var = energy.get('variation_score', 0)
        if energy_var >= 70:
            analysis += "Dynamic energy levels conveyed enthusiasm effectively."
        elif energy_var >= 50:
            analysis += "Energy levels were appropriate for professional communication."
        else:
            analysis += "Increasing energy variation would enhance expressiveness."
        
        return analysis

    def _analyze_speaking_pace(self, summary: Dict) -> str:
        wpm = summary.get('speaking_pace', 0)
        if wpm == 0:
            return "Speaking pace could not be measured from the video recording. " \
                   "This may be due to audio quality issues or insufficient speech content. " \
                   "Ensure clear audio recording for accurate pace analysis. " \
                   "Speaking pace is crucial for effective communication assessment."
        
        # Calculate grade
        if 120 <= wpm <= 150:
            grade = 'A'
        elif (100 <= wpm < 120) or (150 < wpm <= 170):
            grade = 'B'
        elif (80 <= wpm < 100) or (170 < wpm <= 190):
            grade = 'C'
        else:
            grade = 'D'
        
        if 120 <= wpm <= 150:
            return f"The candidate achieved a {grade} grade with an excellent speaking pace of {wpm} words per minute. " \
                   f"This pace falls within the ideal range of 120-150 WPM for professional communication. " \
                   f"The rhythm was well-balanced, ensuring clarity while maintaining audience engagement throughout. " \
                   f"This demonstrates strong communication skills and comfort with the material being presented. " \
                   f"The candidate's delivery style is well-suited for interviews and professional presentations."
        elif 100 <= wpm < 120:
            return f"The candidate received a {grade} grade with a speaking pace of {wpm} words per minute. " \
                   f"While this pace is slightly below the ideal range of 120-150 WPM, it remains acceptable. " \
                   f"The slower pace may indicate thoughtful consideration of responses, which is positive. " \
                   f"However, increasing the pace slightly could improve overall engagement and energy. " \
                   f"Practice with timed responses can help achieve a more optimal delivery speed."
        elif 150 < wpm <= 170:
            return f"The candidate received a {grade} grade with a speaking pace of {wpm} words per minute. " \
                   f"This pace is slightly above the ideal range but still within acceptable limits. " \
                   f"The candidate spoke quickly but remained understandable throughout the presentation. " \
                   f"Slowing down slightly would improve clarity and allow listeners to process information better. " \
                   f"Incorporating natural pauses between key points would enhance overall delivery effectiveness."
        elif wpm < 100:
            return f"The candidate received a {grade} grade with a notably slow pace of {wpm} words per minute. " \
                   f"This pace is significantly below the ideal range of 120-150 WPM for professional settings. " \
                   f"Slow speech may indicate nervousness, uncertainty, or excessive overthinking during responses. " \
                   f"While clarity may be good, the pace could test listener patience and reduce engagement. " \
                   f"Regular practice and mock interviews can help build confidence and increase natural speaking speed."
        else:
            return f"The candidate received a {grade} grade with a rapid speaking pace of {wpm} words per minute. " \
                   f"This pace is well above the ideal range and may impact listener comprehension. " \
                   f"Rapid speech can make it difficult for interviewers to follow key points and arguments. " \
                   f"Taking deliberate pauses between sentences would significantly improve delivery quality. " \
                   f"Practicing with a metronome or timer can help develop a more measured speaking rhythm."

    def _analyze_confidence(self, summary: Dict) -> str:
        score = summary.get('confidence_score', 0)
        emotion = summary.get('dominant_emotion', 'neutral').lower()
        
        if score == 0:
            return "Confidence could not be assessed from the available video data. " \
                   "This may occur due to poor video quality, insufficient face visibility, or technical issues. " \
                   "Confidence analysis requires clear facial expressions and body language cues. " \
                   "Ensure proper lighting and camera positioning for accurate assessment."
        
        grade, _, _ = self._score_to_grade(score)
        
        if score >= 80:
            return f"The candidate achieved an {grade} grade with excellent confidence at {score}%. " \
                   f"The dominant emotion was {emotion}, indicating strong positive self-assurance throughout. " \
                   f"Body language and facial expressions conveyed professionalism and ease during the presentation. " \
                   f"This level of confidence suggests good preparation and familiarity with the subject matter. " \
                   f"The candidate would likely perform well in client-facing roles requiring poise and self-assurance."
        elif score >= 60:
            return f"The candidate received a {grade} grade with good confidence at {score}%. " \
                   f"The candidate appeared {emotion} and maintained reasonable composure throughout the interview. " \
                   f"Minor nervousness may have been present occasionally but did not significantly impact delivery. " \
                   f"This confidence level is appropriate for most professional settings and can improve with experience. " \
                   f"Additional preparation and mock interview practice could help elevate confidence further."
        elif score >= 40:
            return f"The candidate received a {grade} grade with moderate confidence at {score}%. " \
                   f"Some nervousness was detected, possibly stemming from interview anxiety or unfamiliarity with the format. " \
                   f"The {emotion} emotional state suggests the candidate was managing stress but not entirely comfortable. " \
                   f"With practice, experience, and exposure to interview situations, confidence is likely to improve notably. " \
                   f"Techniques such as deep breathing, visualization, and thorough preparation can help reduce anxiety."
        else:
            return f"The candidate received a {grade} grade with low confidence at {score}%. " \
                   f"The candidate appeared notably nervous, which affected their overall presentation quality. " \
                   f"The dominant {emotion} emotion indicates significant discomfort during the interview process. " \
                   f"Low confidence may stem from lack of preparation, unfamiliarity with the topic, or general interview anxiety. " \
                   f"Mock interviews, thorough preparation, and building subject matter expertise could significantly boost confidence."

    def _analyze_face_presence(self, summary: Dict) -> str:
        presence = summary.get('face_presence', 0)
        
        if presence == 0:
            return "Face visibility could not be measured from the video recording. " \
                   "This may be due to video quality issues, poor lighting, or camera positioning problems. " \
                   "Face visibility is important for assessing engagement and building rapport in video interviews. " \
                   "Ensure the camera is positioned at eye level with adequate lighting for accurate analysis."
        
        # Calculate grade
        if presence >= 90:
            grade = 'A'
        elif presence >= 70:
            grade = 'B'
        elif presence >= 50:
            grade = 'C'
        else:
            grade = 'D'
        
        if presence >= 90:
            return f"The candidate achieved an {grade} grade with excellent face visibility at {presence}%. " \
                   f"The candidate maintained consistent camera positioning throughout the entire interview. " \
                   f"This demonstrates strong awareness of professional video presentation standards and etiquette. " \
                   f"Good face visibility allows interviewers to better assess engagement, expressions, and non-verbal cues. " \
                   f"The candidate's video setup is well-optimized for remote interviews and virtual meetings."
        elif presence >= 70:
            return f"The candidate received a {grade} grade with good face visibility at {presence}%. " \
                   f"The candidate was generally well-positioned on camera with occasional minor positioning issues. " \
                   f"Most of the interview had clear face visibility, allowing for adequate non-verbal assessment. " \
                   f"Minor adjustments to camera angle or seating position could further improve visibility scores. " \
                   f"Overall, the video presentation meets professional standards for remote interviews."
        elif presence >= 50:
            return f"The candidate received a {grade} grade with average face visibility at {presence}%. " \
                   f"The candidate occasionally moved out of frame or had suboptimal lighting during the interview. " \
                   f"Inconsistent face visibility can make it challenging for interviewers to assess engagement levels. " \
                   f"Better camera setup, stable seating, and improved lighting would enhance the video interview experience. " \
                   f"Practicing with the camera setup before interviews can help maintain consistent positioning."
        else:
            return f"The candidate received a {grade} grade with poor face visibility at {presence}%. " \
                   f"The candidate was frequently off-camera or had significantly inadequate lighting throughout. " \
                   f"Poor face visibility hinders the interviewer's ability to assess expressions and build rapport. " \
                   f"Proper camera positioning, adequate lighting, and stable seating are essential for video interviews. " \
                   f"Investing time in setting up a proper video interview environment would significantly improve presentation."

    def _analyze_fillers(self, summary: Dict) -> str:
        count = summary.get('filler_words', 0)
        
        # Calculate grade based on filler count
        if count == 0:
            grade = 'A+'
        elif count <= 2:
            grade = 'A'
        elif count <= 5:
            grade = 'B'
        elif count <= 10:
            grade = 'C'
        else:
            grade = 'D'
        
        if count == 0:
            return f"The candidate achieved an {grade} grade with zero filler words detected throughout the interview. " \
                   f"This exceptional result indicates strong verbal discipline and thorough preparation before speaking. " \
                   f"The absence of fillers like 'um', 'uh', 'like', and 'you know' demonstrates polished communication skills. " \
                   f"Clean speech delivery enhances credibility and helps maintain listener engagement throughout. " \
                   f"This level of verbal precision is highly valued in professional and client-facing roles."
        elif count <= 2:
            return f"The candidate received an {grade} grade with only {count} filler word(s) detected during the interview. " \
                   f"This minimal usage shows excellent verbal discipline and strong preparation for the interview content. " \
                   f"The candidate's speech was clean and professional, with fillers not detracting from the message. " \
                   f"Occasional fillers are natural in conversation and this level is perfectly acceptable in any setting. " \
                   f"The candidate demonstrates strong communication skills suitable for professional environments."
        elif count <= 5:
            return f"The candidate received a {grade} grade with {count} filler words detected during the interview. " \
                   f"This level is within acceptable range for professional communication, though some improvement is possible. " \
                   f"Occasional fillers are natural but reducing them can enhance the clarity and professionalism of speech. " \
                   f"Awareness of filler word usage and conscious practice can help reduce their frequency over time. " \
                   f"Recording practice sessions and reviewing them can help identify and eliminate filler word patterns."
        elif count <= 10:
            return f"The candidate received a {grade} grade with {count} filler words detected during the interview. " \
                   f"This frequency may slightly impact the perceived professionalism and polish of verbal communication. " \
                   f"Regular use of fillers can make speech sound less confident and more hesitant to listeners. " \
                   f"Practicing pauses instead of fillers when thinking can significantly improve speech delivery quality. " \
                   f"Conscious effort to slow down and collect thoughts before speaking can reduce filler word usage."
        else:
            return f"The candidate received a {grade} grade with {count} filler words detected during the interview. " \
                   f"This high frequency of fillers can significantly impact perceived confidence and communication polish. " \
                   f"Excessive fillers may distract listeners and reduce the effectiveness of the message being conveyed. " \
                   f"The candidate would benefit significantly from focused practice on reducing filler word usage. " \
                   f"Techniques like pausing, breathing, and structured responses can help eliminate filler word habits."

    def _analyze_emotion(self, summary: Dict) -> str:
        emotion = summary.get('dominant_emotion', 'neutral').lower()
        emotion_map = {
            'happy': "positive and engaging",
            'neutral': "calm and composed",
            'confident': "self-assured and professional",
            'surprised': "reactive and attentive",
            'sad': "subdued",
            'angry': "intense",
            'fear': "anxious",
            'disgust': "critical"
        }
        description = emotion_map.get(emotion, emotion)
        return f"The candidate's dominant emotion was {emotion}, appearing {description}. " \
               f"This emotional tone was consistent throughout most of the interview. " \
               f"Emotional expression plays a key role in communication effectiveness."

    def _analyze_grammar(self, nlp: Dict) -> str:
        grammar = nlp.get('grammar', {})
        score = grammar.get('score', 0)
        errors = grammar.get('error_count', 0)
        error_breakdown = grammar.get('error_breakdown', {})
        
        if score == 0:
            return "Grammar analysis was not available for this interview recording. " \
                   "This may occur when the transcription service fails to process audio or when speech is unclear. " \
                   "Grammar assessment requires clear audio to identify sentence structure and word usage patterns. " \
                   "Future recordings with better audio quality will enable comprehensive grammar evaluation."
        
        grade, _, _ = self._score_to_grade(score)
        
        if score >= 80:
            spelling = error_breakdown.get('spelling', 0)
            grammar_errs = error_breakdown.get('grammar', 0)
            return f"The candidate achieved an {grade} grade in grammar with a score of {score}/100. " \
                   f"Only {errors} error(s) were detected throughout the entire transcript, demonstrating excellent command of English. " \
                   f"Error breakdown shows {spelling} spelling and {grammar_errs} grammar issues - both minimal and well within professional standards. " \
                   f"The candidate consistently used correct verb tenses, proper subject-verb agreement, and appropriate word forms. " \
                   f"This level of grammatical precision reflects strong educational background and attention to detail in communication."
        elif score >= 60:
            return f"The candidate received a {grade} grade in grammar with a score of {score}/100. " \
                   f"{errors} grammatical error(s) were noted, mostly minor issues that did not impede overall understanding. " \
                   f"Common errors included occasional tense inconsistencies and minor preposition usage, typical in spontaneous speech. " \
                   f"Overall language usage remained professional and appropriate for workplace communication contexts. " \
                   f"With minor attention to proofreading and self-correction, grammar skills could reach excellent levels."
        elif score >= 40:
            return f"The candidate received a {grade} grade in grammar with a score of {score}/100. " \
                   f"{errors} error(s) were detected, indicating some challenges with sentence structure and word usage patterns. " \
                   f"Issues may include inconsistent verb tenses, subject-verb disagreement, or incorrect word choices in complex sentences. " \
                   f"While meaning was generally conveyed, grammatical errors occasionally distracted from the professional presentation. " \
                   f"Targeted grammar exercises focusing on common error patterns would significantly improve communication effectiveness."
        else:
            return f"The candidate received a {grade} grade in grammar with a score of {score}/100, indicating significant improvement needed. " \
                   f"{errors} error(s) were found throughout the transcript, affecting clarity and professional impression. " \
                   f"Frequent grammatical issues included tense errors, sentence fragments, and incorrect word usage that impeded understanding. " \
                   f"These patterns suggest need for fundamental grammar review, particularly in verb forms and sentence construction. " \
                   f"Structured grammar courses and regular writing practice would provide substantial improvement in communication skills."

    def _analyze_vocabulary(self, nlp: Dict) -> str:
        vocab = nlp.get('vocabulary', {})
        score = vocab.get('score', 0)
        unique = vocab.get('unique_words', 0)
        total = vocab.get('total_words', 0)
        tier = vocab.get('word_frequency_tier', 'basic')
        diversity = vocab.get('diversity_score', 0)
        sophistication = vocab.get('sophistication', {})
        advanced = sophistication.get('advanced_words', 0)
        
        if score == 0:
            return "Vocabulary analysis was not available for this interview recording. " \
                   "This may occur due to transcription issues or insufficient speech content for analysis. " \
                   "Vocabulary assessment requires adequate sample size of spoken words to measure diversity and sophistication. " \
                   "Longer responses with more varied content will enable comprehensive vocabulary evaluation in future assessments."
        
        grade, _, _ = self._score_to_grade(score)
        
        if score >= 80:
            return f"The candidate achieved an {grade} grade in vocabulary with a score of {score}/100. " \
                   f"Analysis revealed {unique} unique words from {total} total words, demonstrating exceptional lexical diversity at {diversity}%. " \
                   f"The candidate employed {advanced} advanced-level words, indicating sophisticated language skills suitable for professional contexts. " \
                   f"Vocabulary tier rating of '{tier}' shows consistent use of precise, contextually appropriate terminology throughout the interview. " \
                   f"This level of verbal sophistication enhances credibility and is highly valued in roles requiring complex communication."
        elif score >= 60:
            return f"The candidate received a {grade} grade in vocabulary with a score of {score}/100. " \
                   f"The analysis identified {unique} unique words from {total} total words, showing good diversity at {diversity}%. " \
                   f"Vocabulary tier was rated as '{tier}', indicating appropriate word choices for most professional situations. " \
                   f"While effective for general communication, incorporating more varied and precise terminology could elevate expression further. " \
                   f"Reading diverse materials and practicing with industry-specific terminology would strengthen already solid vocabulary skills."
        elif score >= 40:
            return f"The candidate received a {grade} grade in vocabulary with a score of {score}/100. " \
                   f"With {unique} unique words from {total} total words, the diversity score of {diversity}% indicates room for lexical expansion. " \
                   f"The '{tier}' tier rating suggests reliance on common vocabulary with limited use of advanced or specialized terms. " \
                   f"While communication remained understandable, more varied word choices would enhance professionalism and engagement. " \
                   f"Deliberate vocabulary building through reading, word-of-the-day practices, and learning synonyms would significantly improve expression."
        else:
            return f"The candidate received a {grade} grade in vocabulary with a score of {score}/100, indicating substantial development needed. " \
                   f"Analysis showed only {unique} unique words from {total} total, with low diversity at {diversity}%. " \
                   f"The '{tier}' tier rating indicates predominantly basic vocabulary usage that may limit effective professional communication. " \
                   f"Repetitive word choices can make responses seem simplistic and may not convey expertise or confidence to interviewers. " \
                   f"Systematic vocabulary building through extensive reading, flashcards, and practicing alternative expressions would dramatically improve communication quality."

    def _analyze_sentences(self, nlp: Dict) -> str:
        sentences = nlp.get('sentence_formation', {})
        score = sentences.get('score', 0)
        complexity = sentences.get('complexity', 'unknown')
        avg_len = sentences.get('avg_sentence_length', 0)
        total = sentences.get('total_sentences', 0)
        sentence_types = sentences.get('sentence_types', {})
        simple = sentence_types.get('simple', 0)
        compound = sentence_types.get('compound', 0)
        complex_count = sentence_types.get('complex', 0)
        
        if score == 0:
            return "Sentence formation analysis was not available for this interview recording. " \
                   "This typically occurs when transcription quality is insufficient or speech content is too brief. " \
                   "Sentence structure assessment requires clear, structured speech with identifiable sentence boundaries. " \
                   "Future recordings with more extended responses will enable comprehensive sentence formation evaluation."
        
        grade, _, _ = self._score_to_grade(score)
        
        if score >= 80:
            return f"The candidate achieved an {grade} grade in sentence formation with a score of {score}/100. " \
                   f"Analysis of {total} sentences revealed an average length of {avg_len} words with {complexity} complexity patterns. " \
                   f"Sentence variety included {simple} simple, {compound} compound, and {complex_count} complex structures, demonstrating excellent syntactic range. " \
                   f"The candidate effectively used varied sentence beginnings, appropriate transitions, and well-constructed dependent clauses. " \
                   f"This sophisticated sentence construction enhances readability and demonstrates advanced communication skills suitable for professional writing and speaking roles."
        elif score >= 60:
            return f"The candidate received a {grade} grade in sentence formation with a score of {score}/100. " \
                   f"With {total} sentences averaging {avg_len} words, the candidate showed {complexity} structural patterns. " \
                   f"Sentence variety was adequate with {simple} simple, {compound} compound, and {complex_count} complex constructions used appropriately. " \
                   f"While generally effective, some sentences could benefit from more varied openings and smoother transitions between ideas. " \
                   f"Practicing sentence combining exercises and studying effective paragraph structure would further strengthen already solid sentence formation skills."
        elif score >= 40:
            return f"The candidate received a {grade} grade in sentence formation with a score of {score}/100. " \
                   f"Analysis of {total} sentences showed an average of {avg_len} words with predominantly {complexity} structures. " \
                   f"Limited variety in sentence types ({simple} simple, {compound} compound, {complex_count} complex) resulted in somewhat repetitive patterns. " \
                   f"Over-reliance on similar sentence constructions can make speech feel monotonous and less engaging for listeners. " \
                   f"Conscious practice varying sentence length and structure, along with studying transition words, would significantly improve overall communication flow."
        else:
            return f"The candidate received a {grade} grade in sentence formation with a score of {score}/100, indicating need for substantial improvement. " \
                   f"The analysis of {total} sentences revealed an average length of {avg_len} words with basic {complexity} construction patterns. " \
                   f"Very limited sentence variety ({simple} simple, {compound} compound, {complex_count} complex structures) created repetitive, choppy communication. " \
                   f"Frequent run-on sentences, fragments, or overly simplistic constructions impeded clear expression of ideas. " \
                   f"Focused study of sentence structure fundamentals, practice with combining sentences, and reading well-written content would dramatically improve sentence formation abilities."

    def generate_report(
        self,
        candidate_info: Dict[str, Any],
        job_info: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate a PDF report for video analysis with the new layout.
        """
        buffer = io.BytesIO()
        
        try:
            # Check for face verification failure FIRST - before any analysis
            face_match = analysis_data.get("face_match", {})
            face_mismatch_detected = face_match and not face_match.get("overall_match", False)
            
            # Check for technical failure (no face detected, errors)
            note = face_match.get("note", "") if face_match else ""
            is_technical_failure = (
                "No face detected" in note or
                "Face matching error" in note
            )
            
            # ANY face issue blocks analysis
            face_verification_failed = face_mismatch_detected or is_technical_failure
            
            # Create document with custom page template
            doc = BaseDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=25*mm,
                bottomMargin=25*mm
            )
            
            # Create frame and page template with header/footer
            frame = Frame(
                doc.leftMargin, 
                doc.bottomMargin, 
                doc.width, 
                doc.height,
                id='normal'
            )
            
            page_template = PageTemplate(
                id='main',
                frames=[frame],
                onPage=self._add_header_footer
            )
            
            doc.addPageTemplates([page_template])
            
            elements = []
            
            # ========== HEADER SECTION ==========
            candidate_name = candidate_info.get("name", "Candidate")
            elements.append(Paragraph(f"{candidate_name} Report", self.styles['CandidateTitle']))
            
            # Position, Candidate ID, Report Date
            position = job_info.get("position", "N/A")
            candidate_id = candidate_info.get("candidate_id", "N/A")
            report_date = datetime.now().strftime('%B %d, %Y')
            
            # Determine if this is an intro video analysis or job application
            analyses = analysis_data.get("analyses", [])
            is_intro_only = all(a.get("question_index", 0) < 0 for a in analyses) if analyses else True
            
            if position == "N/A" or is_intro_only:
                position_label = "Intro Video Analysis"
            else:
                position_label = f"Position Applied For: {position}"
            
            elements.append(Paragraph(position_label, self.styles['Subtitle']))
            elements.append(Paragraph(f"Candidate ID: {candidate_id}", self.styles['Subtitle']))
            elements.append(Paragraph(f"Report Date: {report_date}", self.styles['Subtitle']))
            elements.append(Spacer(1, 20))
            
            # ========== FACE VERIFICATION WARNING (PROMINENT - FIRST PAGE) ==========
            if face_verification_failed:
                # Determine warning type
                if is_technical_failure:
                    warning_title = "FACE VERIFICATION FAILED"
                    warning_detail = "Unable to verify candidate identity due to technical issues."
                    if "No face detected" in note:
                        warning_detail = "No face detected in the intro video. Face verification is required to proceed with analysis."
                else:
                    warning_title = "FACE MISMATCH DETECTED"
                    warning_detail = "The face in the intro video does not match the face(s) detected in the response videos. This indicates a potential identity mismatch."
                
                # Show prominent red warning banner using Table for better layout control
                elements.append(Spacer(1, 10))
                
                warning_text = Paragraph(
                    f"<b>{warning_title}</b>",
                    ParagraphStyle(
                        'WarningHeader',
                        parent=self.styles['Normal'],
                        fontSize=14,
                        textColor=colors.white,
                        alignment=TA_CENTER
                    )
                )
                
                # Create table with red background for the banner
                banner_table = Table(
                    [[warning_text]],
                    colWidths=[doc.width - 40]
                )
                banner_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#dc2626')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ]))
                elements.append(banner_table)
                
                # Add details box
                details_style = ParagraphStyle(
                    'WarningDetails',
                    parent=self.styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#7f1d1d'),
                    backColor=colors.HexColor('#fef2f2'),
                    borderPadding=12,
                    alignment=TA_CENTER
                )
                
                elements.append(Spacer(1, 15))
                elements.append(Paragraph(warning_detail, details_style))
                elements.append(Spacer(1, 15))
                
                # Add face verification details
                self._add_face_verification_section(elements, face_match)
                elements.append(Spacer(1, 15))
                
                # Add note that analysis is withheld
                # Add footer and return - NO ANALYSIS SECTIONS INCLUDED
                elements.append(Spacer(1, 30))
                elements.append(Paragraph(
                    "<i>Note: Detailed analysis has been withheld due to identity verification failure. "
                    "Please conduct manual verification of candidate identity.</i>",
                    self.styles['AnalysisText']
                ))
                
                # Build PDF with just the warning (no analysis)
                doc.build(elements)
                return buffer.getvalue()
            
            # ========== FACE VERIFICATION SECTION (if available and no mismatch) ==========
            if face_match and not face_mismatch_detected:
                self._add_face_verification_section(elements, face_match)
                elements.append(Spacer(1, 10))
            
            # ========== SCORE & PARAMETERS SECTION ==========
            summary = analysis_data.get("summary", {})
            nlp = analysis_data.get("nlp_analysis", {})
            audio = analysis_data.get("audio_analysis", {})
            overall_score = summary.get("overall_score", 0)
            
            # Create score circle on left (larger size)
            score_drawing = self._create_score_circle(overall_score, width=140)
            
            # Parameter scores with horizontal bars
            param_elements = self._create_parameter_scores_with_bars(summary, nlp, audio)
            
            # Combine score circle and parameters in a table
            param_container = Table([[e] for e in param_elements], colWidths=[340])
            param_container.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            header_table = Table([
                [score_drawing, param_container]
            ], colWidths=[150, 350])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('LEFTPADDING', (1, 0), (1, 0), 10),
            ]))
            elements.append(header_table)
            
            # Recommendation below score
            recommendation = self._get_recommendation(overall_score, summary, nlp)
            elements.append(Spacer(1, 15))
            elements.append(Paragraph(f"<b>Recommendation:</b> {recommendation}", self.styles['AnalysisText']))
            elements.append(Spacer(1, 20))
            
            # ========== DETAILED ANALYSIS SECTION ==========
            elements.append(Paragraph("Detailed Analysis", self.styles['SectionHeader']))
            
            # Always show Video Presentation section with all parameters
            elements.append(self._create_analysis_section("Video Presentation", [
                ("Speaking Pace", self._get_parameter_analysis('speaking_pace', summary)),
                ("Confidence", self._get_parameter_analysis('confidence', summary)),
                ("Face Visibility", self._get_parameter_analysis('face_presence', summary)),
                ("Filler Words", self._get_parameter_analysis('filler_words', summary)),
            ]))
            
            # Always show Audio Analysis section
            audio_sections = [
                ("Pronunciation", self._get_parameter_analysis('pronunciation', audio.get('pronunciation', {}))),
                ("Voice Modulation", self._get_parameter_analysis('voice_modulation', audio.get('voice_modulation', {}))),
            ]
            elements.append(self._create_analysis_section("Audio Analysis", audio_sections))
            
            # Always show Communication Skills section
            comm_sections = [
                ("Grammar", self._get_parameter_analysis('grammar', nlp)),
                ("Vocabulary", self._get_parameter_analysis('vocabulary', nlp)),
                ("Sentence Formation", self._get_parameter_analysis('sentence_formation', nlp)),
            ]
            elements.append(self._create_analysis_section("Communication Skills", comm_sections))
            
            # Response Analysis - Show Question-by-Question Breakdown if available
            analyses = analysis_data.get("analyses", [])
            if analyses and not all(a.get("question_index", 0) < 0 for a in analyses):
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Question-by-Question Breakdown", self.styles['SectionHeader']))
                
                for idx, analysis in enumerate(analyses[:5]):  # Limit to 5 questions
                    question = analysis.get("question", f"Question {idx + 1}")
                    q_summary = analysis.get("analysis", {}).get("summary", {})
                    q_score = q_summary.get("overall_score", 0)
                    q_grade, _, _ = self._score_to_grade(q_score)
                    
                    q_table = Table([
                        [Paragraph(f"<b>Q{idx + 1}:</b> {question[:80]}{'...' if len(question) > 80 else ''}", 
                                  self.styles['AnalysisText'])],
                        [Paragraph(f"Grade: {q_grade} | WPM: {q_summary.get('speaking_pace', 'N/A')} | "
                                  f"Duration: {q_summary.get('duration', 'N/A')}s | "
                                  f"Emotion: {q_summary.get('dominant_emotion', 'N/A').title()}", 
                                  self.styles['ParamLabel'])]
                    ], colWidths=[470])
                    q_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    elements.append(q_table)
                    elements.append(Spacer(1, 5))
            
            # ========== GRADE INDEX AT END ==========
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Grade Index", self.styles['SectionHeader']))
            elements.append(self._create_grade_index_table())
            
            # Build PDF
            doc.build(elements)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise

    def _create_progress_bar(self, value: int, max_val: int = 100, width: float = 200, height: float = 10, is_overall: bool = False) -> Drawing:
        """Create a horizontal progress bar visualization."""
        from reportlab.graphics.shapes import Rect
        
        drawing = Drawing(width, height + 4)
        
        # Background bar (gray)
        bg_rect = Rect(0, 0, width, height)
        bg_rect.fillColor = colors.HexColor('#e2e8f0')
        bg_rect.strokeWidth = 0
        drawing.add(bg_rect)
        
        # Calculate fill percentage
        percentage = min(value / max_val, 1.0) if max_val > 0 else 0
        fill_width = max(width * percentage, 0)
        
        # For very small values, show at least a tiny bar
        if 0 < fill_width < 4:
            fill_width = 4
        
        # Determine color based on score matching grade index
        if value >= 90:
            fill_color = colors.HexColor('#16a34a')  # A+ - Dark Green
        elif value >= 80:
            fill_color = colors.HexColor('#22c55e')  # A - Green
        elif value >= 70:
            fill_color = colors.HexColor('#2563eb')  # B+ - Dark Blue
        elif value >= 60:
            fill_color = colors.HexColor('#3b82f6')  # B - Blue
        elif value >= 50:
            fill_color = colors.HexColor('#eab308')  # C - Amber
        elif value >= 40:
            fill_color = colors.HexColor('#f97316')  # D - Orange
        else:
            fill_color = colors.HexColor('#dc2626')  # F - Red
        
        # Fill bar
        if fill_width > 0:
            fill_rect = Rect(0, 0, fill_width, height)
            fill_rect.fillColor = fill_color
            fill_rect.strokeWidth = 0
            drawing.add(fill_rect)
        
        return drawing
    
    def _create_parameter_scores_with_bars(self, summary: Dict, nlp: Dict, audio: Dict = None) -> List:
        """Create parameter rows with horizontal progress bars - only Overall shows score text."""
        if audio is None:
            audio = {}
        if nlp is None:
            nlp = {}
        
        elements = []
        
        # Helper to create a parameter row - only Overall shows text
        def add_param_row(label: str, score: int, sub_item: bool = False, is_overall: bool = False):
            bar_width = 200 if not is_overall else 170
            bar_height = 10
            
            # Create progress bar with rounded corners
            progress_bar = self._create_progress_bar(score, 100, bar_width, bar_height)
            
            # Parameter label style - compact
            label_style = ParagraphStyle(
                'ParamBarLabel',
                parent=self.styles['ParamLabel'],
                fontSize=9 if not sub_item else 8,
                textColor=colors.HexColor('#475569'),
                leftIndent=10 if sub_item else 0,
                spaceBefore=0,
                spaceAfter=0
            )
            
            label_para = Paragraph(f"{'  ' if sub_item else ''}{label}", label_style)
            
            if is_overall:
                # Overall Score shows grade and score with blue background
                grade, _, _ = self._score_to_grade(score)
                score_style = ParagraphStyle(
                    'OverallScoreSmall',
                    parent=self.styles['ParamValue'],
                    fontSize=10,
                    textColor=colors.HexColor('#1e40af')
                )
                score_para = Paragraph(f"<b>{grade}</b> | {score}/100", score_style)
                
                row_table = Table(
                    [[label_para, progress_bar, score_para]],
                    colWidths=[90, bar_width + 10, 80]
                )
                row_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(row_table)
            else:
                # Other parameters - just bar, no text, tight spacing
                row_table = Table(
                    [[label_para, progress_bar]],
                    colWidths=[100, bar_width + 10]
                )
                row_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(row_table)
        
        # Overall Score (highlighted with background)
        overall_score = summary.get("overall_score", 0)
        
        # Overall Score - use helper with is_overall=True
        add_param_row("Overall Score", overall_score, is_overall=True)
        elements.append(Spacer(1, 6))
        
        # Video metrics - just bars
        wpm = summary.get('speaking_pace', 0)
        wpm_normalized = min(wpm / 150 * 100, 100) if wpm > 0 else 0
        add_param_row("Speaking Pace", int(wpm_normalized))
        
        conf_score = summary.get('confidence_score', 0)
        add_param_row("Confidence", conf_score)
        
        face_score = summary.get('face_presence', 0)
        add_param_row("Face Visibility", face_score)
        
        # Filler words (inverse - lower is better)
        filler_count = summary.get('filler_words', 0)
        filler_normalized = max(0, 100 - (filler_count * 5))
        add_param_row("Filler Words", filler_normalized)
        
        # Audio Analysis - just bars
        pronunciation = audio.get('pronunciation', {})
        voice_modulation = audio.get('voice_modulation', {})
        
        pron_score = pronunciation.get('score', 0)
        add_param_row("Pronunciation", pron_score)
        
        voice_score = voice_modulation.get('score', 0)
        add_param_row("Voice Modulation", voice_score)
        
        # Communication Skills - just bars, compact header
        elements.append(Paragraph("  <i>Communication</i>", ParagraphStyle(
            'SubSection',
            parent=self.styles['ParamLabel'],
            fontSize=8,
            textColor=colors.HexColor('#64748b'),
            spaceBefore=4,
            spaceAfter=2
        )))
        
        grammar = nlp.get('grammar', {})
        gram_score = grammar.get('score', 0)
        add_param_row("Grammar", gram_score, sub_item=True)
        
        vocab = nlp.get('vocabulary', {})
        vocab_score = vocab.get('score', 0)
        add_param_row("Vocabulary", vocab_score, sub_item=True)
        
        sentences = nlp.get('sentence_formation', {})
        sent_score = sentences.get('score', 0)
        add_param_row("Sentences", sent_score, sub_item=True)
        
        # Emotion - compact display below
        elements.append(Spacer(1, 8))
        emotion = summary.get('dominant_emotion', 'Unknown')
        emotion_style = ParagraphStyle(
            'EmotionDisplay',
            parent=self.styles['ParamLabel'],
            fontSize=10,
            textColor=colors.HexColor('#475569'),
            backColor=colors.HexColor('#f8fafc'),
            borderPadding=8,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            f"<b>Dominant Emotion:</b> {emotion.title() if emotion else 'Unknown'}",
            emotion_style
        ))
        
        return elements

    def _create_analysis_section(self, title: str, items: list) -> Table:
        """Create a section with parameter analyses."""
        rows = [[Paragraph(f"<b>{title}</b>", self.styles['SectionHeader'])]]
        
        for param_name, analysis_text in items:
            rows.append([
                Paragraph(f"<b>{param_name}:</b> {analysis_text}", self.styles['AnalysisText'])
            ])
        
        table = Table(rows, colWidths=[470])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        return table

    def _assess_wpm(self, wpm: int) -> str:
        if wpm == 0: return '-'
        if 120 <= wpm <= 150: return 'Ideal'
        if 100 <= wpm <= 170: return 'Good'
        if wpm < 100: return 'Slow'
        return 'Fast'

    def _assess_duration(self, duration: int) -> str:
        if duration == 0: return '-'
        if 60 <= duration <= 90: return 'Ideal'
        if duration >= 30: return 'Adequate'
        return 'Short'

    def _assess_fillers(self, count: int) -> str:
        if count == 0: return 'Excellent'
        if count <= 3: return 'Good'
        if count <= 7: return 'Average'
        return 'High'

    def _assess_face(self, rate: float) -> str:
        if rate >= 90: return 'Excellent'
        if rate >= 70: return 'Good'
        if rate >= 50: return 'Average'
        return 'Poor'

    def _assess_confidence(self, score: float) -> str:
        if score >= 80: return 'High'
        if score >= 60: return 'Good'
        if score >= 40: return 'Moderate'
        return 'Low'

    def _get_score_assessment(self, score: int) -> str:
        if score >= 80: return 'Excellent'
        if score >= 60: return 'Good'
        if score >= 40: return 'Average'
        if score > 0: return 'Needs Work'
        return '-'
    
    def _calculate_wpm_grade(self, wpm: int) -> str:
        """Calculate grade based on speaking pace."""
        if wpm == 0: return 'N/A'
        if 120 <= wpm <= 150: return 'A'
        if (100 <= wpm < 120) or (150 < wpm <= 170): return 'B'
        if (80 <= wpm < 100) or (170 < wpm <= 190): return 'C'
        return 'D'
    
    def _calculate_filler_grade(self, count: int) -> str:
        """Calculate grade based on filler word count."""
        if count == 0: return 'A+'
        if count <= 2: return 'A'
        if count <= 5: return 'B'
        if count <= 10: return 'C'
        return 'D'


# Convenience function
def generate_analysis_pdf(
    candidate_info: Dict[str, Any],
    job_info: Dict[str, Any],
    analysis_data: Dict[str, Any]
) -> bytes:
    """
    Generate PDF report for video analysis.
    
    Args:
        candidate_info: {name, mobile, email, candidate_id}
        job_info: {position, company, interview_date}
        analysis_data: Full analysis from video_analysis_service
        
    Returns:
        PDF bytes
    """
    service = PDFReportService()
    return service.generate_report(candidate_info, job_info, analysis_data)
