"""
Resume Analyzer Service
Analyzes parsed resume data and provides improvement recommendations
"""

import re
from typing import Dict, Any, List, Tuple
import logging
from utils_others.logger import logger

class ResumeAnalyzer:
    def __init__(self):
        self.format_templates = self._load_format_templates()
        self.section_weights = {
            "summary": 0.15,
            "experience": 0.35,
            "education": 0.20,
            "skills": 0.20,
            "projects": 0.10
        }
        
    async def analyze_resume(self, parsed_data: Dict[str, Any], content_type: str) -> Dict[str, Any]:
        """
        Comprehensive resume analysis with scoring and recommendations
        """
        try:
            # Analyze each section
            section_analyses = []
            total_score = 0.0
            
            for section_name, section_content in parsed_data.get("sections", {}).items():
                analysis = self._analyze_section(section_name, section_content)
                section_analyses.append(analysis)
                
                # Weight the score
                weight = self.section_weights.get(section_name, 0.1)
                total_score += analysis["score"] * weight
            
            # Analyze overall format and structure
            format_issues = self._analyze_format(parsed_data)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(parsed_data, section_analyses, format_issues)
            
            result = {
                "overall_score": min(total_score, 100.0),  # Cap at 100
                "sections": section_analyses,
                "format_issues": format_issues,
                "recommendations": recommendations
            }
            
            logger.info(f"Resume analysis completed with overall score: {result['overall_score']:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"Resume analysis failed: {str(e)}")
            raise Exception(f"Failed to analyze resume: {str(e)}")
    
    async def check_format_compliance(self, parsed_data: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """
        Check if resume complies with a specific format template
        """
        try:
            if format_type not in self.format_templates:
                raise ValueError(f"Unknown format type: {format_type}")
            
            template = self.format_templates[format_type]
            issues = []
            suggestions = []
            
            # Check required sections
            for required_section in template["required_sections"]:
                if required_section not in parsed_data.get("sections", {}):
                    issues.append(f"Missing required section: {required_section}")
                    suggestions.append(f"Add a {required_section} section to your resume")
            
            # Check section order
            current_sections = list(parsed_data.get("sections", {}).keys())
            if current_sections != template["section_order"][:len(current_sections)]:
                issues.append("Section order doesn't match recommended format")
                suggestions.append(f"Reorder sections to: {', '.join(template['section_order'])}")
            
            # Check formatting guidelines
            format_issues = self._analyze_format(parsed_data)
            issues.extend(format_issues)
            
            # Calculate compliance score
            compliance_score = max(0, 100 - len(issues) * 10)
            
            return {
                "is_compliant": compliance_score >= 80,
                "issues": issues,
                "suggestions": suggestions,
                "compliance_score": compliance_score
            }
            
        except Exception as e:
            logger.error(f"Format compliance check failed: {str(e)}")
            raise Exception(f"Failed to check format compliance: {str(e)}")
    
    def _analyze_section(self, section_name: str, section_content: str) -> Dict[str, Any]:
        """Analyze individual resume section"""
        analysis = {
            "name": section_name,
            "content": section_content,
            "score": 0.0,
            "issues": [],
            "suggestions": []
        }
        
        if not section_content or len(section_content.strip()) < 10:
            analysis["issues"].append("Section appears to be empty or too short")
            analysis["suggestions"].append(f"Add more content to the {section_name} section")
            analysis["score"] = 20.0
            return analysis
        
        # Section-specific analysis
        if section_name == "summary":
            analysis.update(self._analyze_summary(section_content))
        elif section_name == "experience":
            analysis.update(self._analyze_experience(section_content))
        elif section_name == "education":
            analysis.update(self._analyze_education(section_content))
        elif section_name == "skills":
            analysis.update(self._analyze_skills(section_content))
        elif section_name == "projects":
            analysis.update(self._analyze_projects(section_content))
        else:
            # Generic analysis for other sections
            analysis.update(self._analyze_generic_section(section_content))
        
        return analysis
    
    def _analyze_summary(self, content: str) -> Dict[str, Any]:
        """Analyze professional summary section"""
        issues = []
        suggestions = []
        score = 80.0
        
        # Check length
        word_count = len(content.split())
        if word_count < 30:
            issues.append("Summary is too short (should be 30-60 words)")
            suggestions.append("Expand your summary to 2-3 sentences highlighting key achievements")
            score -= 20
        elif word_count > 100:
            issues.append("Summary is too long (should be 30-60 words)")
            suggestions.append("Condense your summary to 2-3 sentences")
            score -= 15
        
        # Check for action verbs
        action_verbs = ['led', 'managed', 'developed', 'implemented', 'created', 'achieved', 'improved']
        action_verb_count = sum(1 for verb in action_verbs if verb.lower() in content.lower())
        
        if action_verb_count < 2:
            issues.append("Summary lacks strong action verbs")
            suggestions.append("Include action verbs like 'led', 'managed', 'developed'")
            score -= 10
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_experience(self, content: str) -> Dict[str, Any]:
        """Analyze work experience section"""
        issues = []
        suggestions = []
        score = 80.0
        
        # Check for bullet points
        bullet_patterns = [r'•', r'-', r'\*', r'\d+\.', r'→']
        has_bullets = any(re.search(pattern, content) for pattern in bullet_patterns)
        
        if not has_bullets:
            issues.append("Experience section should use bullet points")
            suggestions.append("Format experience with bullet points for better readability")
            score -= 20
        
        # Check for quantifiable achievements
        number_patterns = [r'\d+%', r'\$\d+', r'\d+\s*(?:users|customers|projects|team members)']
        has_metrics = any(re.search(pattern, content, re.IGNORECASE) for pattern in number_patterns)
        
        if not has_metrics:
            issues.append("Include quantifiable achievements")
            suggestions.append("Add metrics like 'increased sales by 25%' or 'managed team of 5'")
            score -= 15
        
        # Check for action verbs at start of lines
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        action_start_count = 0
        action_verbs = ['led', 'managed', 'developed', 'implemented', 'created', 'achieved', 'improved', 'coordinated']
        
        for line in lines[:10]:  # Check first 10 lines
            if any(line.lower().startswith(verb) for verb in action_verbs):
                action_start_count += 1
        
        if action_start_count < len(lines) * 0.5:
            issues.append("Start bullet points with strong action verbs")
            suggestions.append("Begin each bullet point with action verbs")
            score -= 10
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_education(self, content: str) -> Dict[str, Any]:
        """Analyze education section"""
        issues = []
        suggestions = []
        score = 85.0
        
        # Check for degree information
        degree_patterns = [r'Bachelor|Master|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Tech|M\.Tech']
        has_degree = any(re.search(pattern, content, re.IGNORECASE) for pattern in degree_patterns)
        
        if not has_degree:
            issues.append("Education section should include degree information")
            suggestions.append("Clearly specify your degree (e.g., Bachelor of Science)")
            score -= 25
        
        # Check for graduation year
        year_pattern = r'\b(19|20)\d{2}\b'
        has_year = bool(re.search(year_pattern, content))
        
        if not has_year:
            issues.append("Include graduation year")
            suggestions.append("Add your graduation year for clarity")
            score -= 15
        
        # Check for institution name
        if len(content.split()) < 5:
            issues.append("Education section seems incomplete")
            suggestions.append("Include full institution name and location")
            score -= 20
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_skills(self, content: str) -> Dict[str, Any]:
        """Analyze skills section"""
        issues = []
        suggestions = []
        score = 80.0
        
        # Check skill categorization
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if len(lines) == 1 and ',' in content:
            # Skills are in a single line with commas
            if len(content.split(',')) < 5:
                issues.append("List more skills or categorize them")
                suggestions.append("Group skills by category (e.g., Technical, Soft Skills)")
                score -= 15
        elif len(lines) < 3:
            issues.append("Consider categorizing your skills")
            suggestions.append("Organize skills into categories for better presentation")
            score -= 10
        
        # Check for specific vs generic skills
        generic_skills = ['communication', 'teamwork', 'leadership', 'problem solving']
        specific_skills = ['python', 'java', 'react', 'aws', 'sql', 'machine learning']
        
        content_lower = content.lower()
        generic_count = sum(1 for skill in generic_skills if skill in content_lower)
        specific_count = sum(1 for skill in specific_skills if skill in content_lower)
        
        if generic_count > specific_count * 2:
            issues.append("Balance generic and specific skills")
            suggestions.append("Include more technical/hard skills alongside soft skills")
            score -= 10
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_projects(self, content: str) -> Dict[str, Any]:
        """Analyze projects section"""
        issues = []
        suggestions = []
        score = 85.0
        
        # Check for project descriptions
        if len(content.split()) < 20:
            issues.append("Project descriptions are too brief")
            suggestions.append("Provide more detail about your projects and contributions")
            score -= 20
        
        # Check for technologies used
        tech_keywords = ['python', 'java', 'javascript', 'react', 'nodejs', 'sql', 'aws', 'docker']
        tech_count = sum(1 for tech in tech_keywords if tech.lower() in content.lower())
        
        if tech_count == 0:
            issues.append("Mention technologies used in projects")
            suggestions.append("Include programming languages, frameworks, and tools")
            score -= 15
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_generic_section(self, content: str) -> Dict[str, Any]:
        """Analyze generic resume section"""
        issues = []
        suggestions = []
        score = 75.0
        
        if len(content.split()) < 15:
            issues.append("Section content is too brief")
            suggestions.append("Add more detail to this section")
            score -= 25
        
        return {"score": score, "issues": issues, "suggestions": suggestions}
    
    def _analyze_format(self, parsed_data: Dict[str, Any]) -> List[str]:
        """Analyze overall resume format and structure"""
        issues = []
        
        # Check contact information
        contact_info = parsed_data.get("contact_info", {})
        if not contact_info.get("emails"):
            issues.append("Missing email address")
        if not contact_info.get("phones"):
            issues.append("Missing phone number")
        
        # Check section completeness
        sections = parsed_data.get("sections", {})
        required_sections = ["experience", "education"]
        
        for section in required_sections:
            if section not in sections:
                issues.append(f"Missing essential section: {section}")
        
        # Check overall length
        word_count = parsed_data.get("metadata", {}).get("word_count", 0)
        if word_count < 150:
            issues.append("Resume appears too short (aim for 300-500 words)")
        elif word_count > 800:
            issues.append("Resume appears too long (aim for 300-500 words)")
        
        return issues
    
    def _generate_recommendations(self, parsed_data: Dict[str, Any], section_analyses: List[Dict], format_issues: List[str]) -> List[str]:
        """Generate overall improvement recommendations"""
        recommendations = []
        
        # High-priority recommendations
        if format_issues:
            recommendations.append("Fix critical format issues before applying")
        
        # Section-specific recommendations
        low_score_sections = [analysis for analysis in section_analyses if analysis["score"] < 60]
        if low_score_sections:
            recommendations.append(f"Focus on improving: {', '.join([s['name'] for s in low_score_sections])}")
        
        # Content recommendations
        contact_info = parsed_data.get("contact_info", {})
        if not contact_info.get("linkedin"):
            recommendations.append("Add LinkedIn profile URL")
        
        skills = parsed_data.get("skills", [])
        if len(skills) < 5:
            recommendations.append("Expand your skills section with more relevant abilities")
        
        # General recommendations
        recommendations.append("Tailor your resume for each job application")
        recommendations.append("Use action verbs to start bullet points")
        recommendations.append("Quantify achievements with metrics and numbers")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _load_format_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined resume format templates"""
        return {
            "modern": {
                "name": "Modern Professional",
                "required_sections": ["summary", "experience", "education", "skills"],
                "section_order": ["summary", "experience", "education", "skills", "projects", "certifications"],
                "guidelines": {
                    "length": "1-2 pages",
                    "font": "Modern sans-serif (Calibri, Arial, Helvetica)",
                    "font_size": "10-12pt",
                    "margins": "0.5-1 inch",
                    "format": "Clean, single-column layout"
                }
            },
            "traditional": {
                "name": "Traditional Conservative",
                "required_sections": ["experience", "education"],
                "section_order": ["summary", "experience", "education", "skills", "certifications"],
                "guidelines": {
                    "length": "1 page",
                    "font": "Traditional (Times New Roman, Georgia)",
                    "font_size": "11-12pt",
                    "margins": "1 inch",
                    "format": "Conservative, single-column"
                }
            },
            "ats": {
                "name": "ATS Optimized",
                "required_sections": ["summary", "experience", "education", "skills"],
                "section_order": ["summary", "experience", "education", "skills", "certifications"],
                "guidelines": {
                    "length": "1-2 pages",
                    "font": "Simple (Calibri, Arial, Times New Roman)",
                    "font_size": "11-12pt",
                    "margins": "1 inch",
                    "format": "No tables, columns, or graphics"
                }
            },
            "creative": {
                "name": "Creative Industry",
                "required_sections": ["summary", "experience", "skills", "projects"],
                "section_order": ["summary", "skills", "experience", "projects", "education"],
                "guidelines": {
                    "length": "1-2 pages",
                    "font": "Modern (Can be creative)",
                    "font_size": "10-12pt",
                    "margins": "0.5-1 inch",
                    "format": "Can include design elements"
                }
            }
        }
