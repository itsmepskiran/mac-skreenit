"""
Premium Assessment Router
Handles AI-based assessments for premium features
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Body
from datetime import datetime
from typing import Optional
import logging
import json
import uuid

from database import get_db
from sqlalchemy.orm import Session
from models.premium_assessment_models import (
    AssessmentQuestion,
    AssessmentQuestionsResponse,
    AssessmentResponse,
    AssessmentFinishRequest
)
from services.mysql_service import MySQLService
from services.ollama_service import OllamaService
from services.subscription_service import SubscriptionService
from routers.assessment_formats import (
    build_sections, get_format_type, get_format_description,
)

logger = logging.getLogger(__name__)
mysql_service = MySQLService()
ollama_service = OllamaService()
router = APIRouter(prefix="/premium", tags=["Premium Assessments"])

# Assessment metadata mapping (maps service_key to assessment details)
ASSESSMENT_METADATA = {
    # BPO & CUSTOMER SUPPORT
    'bpo_accent_neutral': {
        'name': 'Accent Neutralization Trainer',
        'description': 'Evaluate clarity and neutrality of speech patterns',
        'skills': 'Pronunciation, stress patterns, pacing, articulation, accent adaptability',
        'type': 'general',
        'questions': 5
    },
    'bpo_versant_pro': {
        'name': 'Versant Pro Test',
        'description': 'Assess spoken English proficiency for customer-facing roles',
        'skills': 'Speaking, listening, pronunciation, fluency, reading comprehension',
        'type': 'general',
        'questions': 5
    },
    'bpo_cust_handling': {
        'name': 'Customer Handling Simulation',
        'description': 'Evaluate response to difficult customer situations',
        'skills': 'Empathy, listening, de-escalation, problem solving, communication',
        'type': 'general',
        'questions': 4
    },
    'bpo_objection_handling': {
        'name': 'Objection Handling Test',
        'description': 'Measure ability to address and overcome customer objections',
        'skills': 'Persuasion, composure, active listening, rebuttal quality, confidence',
        'type': 'general',
        'questions': 3
    },
    'bpo_chat_email_etiquette': {
        'name': 'Chat & Email Etiquette Test',
        'description': 'Evaluate written communication quality in digital channels',
        'skills': 'Grammar, tone, clarity, sentence structure, professional etiquette',
        'type': 'general',
        'questions': 4
    },
    'bpo_call_quality': {
        'name': 'Call Quality Scorecard',
        'description': 'Measure quality of customer interactions in voice-based support',
        'skills': 'Empathy, clarity, call control, issue resolution, service standards',
        'type': 'general',
        'questions': 3
    },
    # IT & SOFTWARE
    'it_adv_coding': {
        'name': 'Advanced Coding Challenge',
        'description': 'Evaluate hands-on programming ability through coding problems',
        'skills': 'Data structures, algorithms, code correctness, optimization',
        'type': 'technical',
        'questions': 3
    },
    'it_algorithmic_thinking': {
        'name': 'Algorithmic Thinking Test',
        'description': 'Measure computational problem-solving ability',
        'skills': 'Recursion, dynamic programming, greedy logic, graph reasoning',
        'type': 'technical',
        'questions': 3
    },
    'it_debugging': {
        'name': 'Debugging Simulator',
        'description': 'Evaluate ability to identify and fix code issues',
        'skills': 'Bug detection, error diagnosis, code reading, execution tracing',
        'type': 'technical',
        'questions': 4
    },
    'it_system_design_lite': {
        'name': 'System Design Lite',
        'description': 'Evaluate foundational low-level software design ability',
        'skills': 'Object-oriented design, class relationships, modular thinking',
        'type': 'technical',
        'questions': 3
    },
    'it_system_design_pro': {
        'name': 'System Design Pro',
        'description': 'Evaluate production-grade system design ability',
        'skills': 'Service decomposition, database selection, caching, load balancing',
        'type': 'advanced',
        'questions': 4
    },
    'it_sql_pro': {
        'name': 'SQL Query Pro Test',
        'description': 'Evaluate practical SQL ability using real-world database tasks',
        'skills': 'SELECT queries, joins, filtering, aggregation, subqueries',
        'type': 'technical',
        'questions': 4
    },
    'it_react_skills': {
        'name': 'React Skills Test',
        'description': 'Measure front-end development ability within React ecosystem',
        'skills': 'Components, props, state, hooks, routing, form handling',
        'type': 'technical',
        'questions': 4
    },
    'it_js_pro': {
        'name': 'JavaScript Pro Challenge',
        'description': 'Measure deep JavaScript proficiency',
        'skills': 'Closures, scope, hoisting, prototypes, promises, async',
        'type': 'technical',
        'questions': 3
    },
    # SALES & MARKETING
    'sales_video_pitch': {
        'name': 'Sales Pitch Video Analyzer',
        'description': 'Evaluate sales pitch presentation and delivery',
        'skills': 'Persuasion, verbal clarity, product positioning, confidence',
        'type': 'general',
        'questions': 3
    },
    'sales_objection_sim': {
        'name': 'Objection Handling Simulator',
        'description': 'Test ability to handle buyer concerns during sales',
        'skills': 'Rebuttal quality, confidence, negotiation, active listening',
        'type': 'general',
        'questions': 3
    },
    'sales_creativity': {
        'name': 'Marketing Creativity Challenge',
        'description': 'Evaluate creative thinking in brand messaging',
        'skills': 'Ad copy writing, slogan creation, campaign creativity, originality',
        'type': 'general',
        'questions': 3
    },
    'sales_digital_mcq': {
        'name': 'Digital Marketing MCQ Pro',
        'description': 'Evaluate digital marketing concepts and strategies',
        'skills': 'SEO, SEM, social media metrics, paid campaigns, analytics',
        'type': 'general',
        'questions': 5
    },
    'sales_lead_conv': {
        'name': 'Lead Conversion Simulation',
        'description': 'Measure ability to convert interest into qualified leads',
        'skills': 'Lead qualification, persuasion, need discovery, follow-up logic',
        'type': 'general',
        'questions': 4
    },
    'sales_empathy': {
        'name': 'Customer Empathy Test',
        'description': 'Evaluate understanding of customer perspective',
        'skills': 'Emotional intelligence, listening, patience, situational matching',
        'type': 'general',
        'questions': 3
    },
    # FINANCE & BANKING
    'fin_reasoning': {
        'name': 'Financial Reasoning Test',
        'description': 'Measure ability to solve finance-related numerical problems',
        'skills': 'EMI calculation, interest computation, ratios, percentages',
        'type': 'general',
        'questions': 4
    },
    'fin_awareness': {
        'name': 'Banking Awareness Test',
        'description': 'Evaluate knowledge of banking concepts and frameworks',
        'skills': 'RBI guidelines, NBFC concepts, KYC norms, banking products',
        'type': 'general',
        'questions': 5
    },
    'fin_kyc_aml': {
        'name': 'KYC/AML Compliance Test',
        'description': 'Measure understanding of compliance processes',
        'skills': 'KYC verification, AML red flags, suspicious activity, compliance',
        'type': 'general',
        'questions': 4
    },
    'fin_rm_simulation': {
        'name': 'Relationship Manager Simulation',
        'description': 'Evaluate client relationship management ability',
        'skills': 'Customer profiling, needs analysis, cross-selling, trust building',
        'type': 'general',
        'questions': 3
    },
    'fin_integrity': {
        'name': 'Financial Integrity Test',
        'description': 'Evaluate ethical judgment in finance-sensitive situations',
        'skills': 'Integrity, compliance metrics, conflict-of-interest awareness',
        'type': 'general',
        'questions': 3
    },
    'fin_insurance_product': {
        'name': 'Insurance Product Knowledge Test',
        'description': 'Measure understanding of insurance products',
        'skills': 'Life insurance, health insurance, policy structures, benefits',
        'type': 'general',
        'questions': 4
    },
    # HEALTHCARE
    'hc_terminology': {
        'name': 'Medical Terminology Test',
        'description': 'Evaluate understanding of medical vocabulary',
        'skills': 'Medical terminology, abbreviations, anatomy terms',
        'type': 'general',
        'questions': 5
    },
    'hc_communication': {
        'name': 'Patient Communication Assessment',
        'description': 'Measure communication with patients in care settings',
        'skills': 'Empathy, clarity, reassurance, listening accuracy',
        'type': 'general',
        'questions': 3
    },
    'hc_ethics': {
        'name': 'Healthcare Ethics Test',
        'description': 'Evaluate ethical decision-making in healthcare',
        'skills': 'Confidentiality, consent awareness, patient rights, compliance',
        'type': 'general',
        'questions': 4
    },
    'hc_case_handling': {
        'name': 'Case Handling Simulation',
        'description': 'Assess response to realistic patient-care scenarios',
        'skills': 'Situation monitoring, prioritization, empathy, coordination',
        'type': 'general',
        'questions': 3
    },
    # RETAIL & HOSPITALITY
    'retail_video_test': {
        'name': 'Customer Interaction Video Test',
        'description': 'Evaluate service behavior in retail environments',
        'skills': 'Greeting etiquette, service orientation, attentiveness',
        'type': 'general',
        'questions': 3
    },
    'retail_etiquette': {
        'name': 'Service Etiquette Test',
        'description': 'Measure professional etiquette in hospitality',
        'skills': 'Grooming awareness, politeness, situational conduct',
        'type': 'general',
        'questions': 3
    },
    'retail_complaint': {
        'name': 'Complaint Handling Simulation',
        'description': 'Evaluate management of unhappy customers',
        'skills': 'De-escalation, patience, problem mapping, brand restoration',
        'type': 'general',
        'questions': 3
    },
    'retail_pos_knowledge': {
        'name': 'POS System Knowledge Test',
        'description': 'Measure familiarity with point-of-sale operations',
        'skills': 'Billing operations, transaction processing, return handling',
        'type': 'technical',
        'questions': 4
    },
    # MANUFACTURING
    'mfg_safety': {
        'name': 'Safety Compliance Test',
        'description': 'Evaluate knowledge of workplace safety practices',
        'skills': 'Hazard identification, PPE compliance, safe handling',
        'type': 'general',
        'questions': 4
    },
    'mfg_process': {
        'name': 'Process Understanding Test',
        'description': 'Measure understanding of standard operating procedures',
        'skills': 'SOP tracking, checklist execution, procedural sequence',
        'type': 'general',
        'questions': 3
    },
    'mfg_machine_op': {
        'name': 'Machine Operation Knowledge Test',
        'description': 'Evaluate knowledge of machine operation principles',
        'skills': 'Equipment verification, tolerance baselines, instrumentation',
        'type': 'technical',
        'questions': 4
    },
    'mfg_qc': {
        'name': 'Quality Control Assessment',
        'description': 'Measure ability to identify quality issues',
        'skills': 'Defect discovery, inspection logic, attention to detail',
        'type': 'general',
        'questions': 3
    },
    # LOGISTICS & SUPPLY CHAIN
    'log_inventory': {
        'name': 'Inventory Management Test',
        'description': 'Evaluate stock control and inventory accuracy',
        'skills': 'Stock tracking, auditing, verification precision, variance',
        'type': 'general',
        'questions': 4
    },
    'log_route': {
        'name': 'Route Optimization Test',
        'description': 'Measure ability to plan efficient delivery routes',
        'skills': 'Time calculation, sequence mapping, route optimization',
        'type': 'general',
        'questions': 3
    },
    'log_safety': {
        'name': 'Safety Protocol Test',
        'description': 'Evaluate knowledge of warehouse safety protocols',
        'skills': 'Loading dock safety, PPE compliance, hazard identification',
        'type': 'general',
        'questions': 3
    },
    # TELECOM
    'tel_network': {
        'name': 'Network Basics Test',
        'description': 'Evaluate foundational knowledge of telecom networking concepts',
        'skills': 'IP configurations, packet routing, architectural layers, gateway nodes',
        'type': 'technical',
        'questions': 4
    },
    'tel_troubleshoot': {
        'name': 'Troubleshooting Simulation',
        'description': 'Assess ability to diagnose and resolve telecom-related issues',
        'skills': 'Root-cause diagnostics, network loop analysis, topology defect mapping',
        'type': 'technical',
        'questions': 4
    },
    'tel_tech_support': {
        'name': 'Customer Tech Support Test',
        'description': "Evaluate ability to support customers with technical telecom queries",
        'skills': 'Technical diagnostics, step-by-step explanation, customer communication',
        'type': 'general',
        'questions': 4
    },
    'tel_field_safety': {
        'name': 'Field Operations Safety Test',
        'description': 'Measure safety awareness for on-site telecom field configurations',
        'skills': 'High-elevation routines, line management, current safety protocols',
        'type': 'general',
        'questions': 3
    },
    # AVIATION
    'av_cabin_comm': {
        'name': 'Cabin Crew Communication Test',
        'description': 'Evaluate communication quality and service readiness for aviation roles',
        'skills': 'Verbal accuracy, flight management etiquette, composure, service protocols',
        'type': 'general',
        'questions': 4
    },
    'av_safety': {
        'name': 'Aviation Safety Protocol Test',
        'description': 'Measure understanding of aviation safety rules and emergency response',
        'skills': 'Emergency systems, cabin depressurization, evacuation procedures',
        'type': 'general',
        'questions': 4
    },
    'av_passenger': {
        'name': 'Passenger Handling Simulation',
        'description': 'Evaluate response to difficult passenger situations in-flight',
        'skills': 'Conflict management, disruption response, cabin service standards',
        'type': 'general',
        'questions': 3
    },
    'av_terminology': {
        'name': 'Aviation Terminology Test',
        'description': 'Measure familiarity with aviation terms, abbreviations, and operational language',
        'skills': 'IATA/ICAO protocols, code designations, operational jargon',
        'type': 'general',
        'questions': 5
    },
    # CONSTRUCTION
    'con_site_safety': {
        'name': 'Site Safety Test',
        'description': 'Evaluate knowledge of essential construction-site safety practices',
        'skills': 'OSHA configurations, hazard containment, fall-protection structures',
        'type': 'general',
        'questions': 4
    },
    'con_blueprint': {
        'name': 'Blueprint Reading Test',
        'description': 'Measure ability to interpret engineering drawings and construction plans',
        'skills': 'Geometric tolerance maps, layout reading, symbol allocation, indexing',
        'type': 'technical',
        'questions': 4
    },
    'con_material': {
        'name': 'Material Knowledge Test',
        'description': 'Evaluate familiarity with key construction materials and their use cases',
        'skills': 'Stress tolerance grading, concrete hydration ratios, material selection',
        'type': 'general',
        'questions': 4
    },
    'con_project_coord': {
        'name': 'Project Coordination Assessment',
        'description': 'Measure ability to coordinate tasks, timelines, and communication on construction projects',
        'skills': 'Critical path calculations, material scheduling, site timeline control',
        'type': 'general',
        'questions': 3
    },
    # EDUCATION & TRAINING
    'edu_teaching_demo': {
        'name': 'Teaching Demo Video Analysis',
        'description': 'Evaluate teaching delivery quality through demo-based presentation analysis',
        'skills': 'Concept parsing, articulation cadence, class retention, engagement hooks',
        'type': 'general',
        'questions': 4
    },
    'edu_subject_knowledge': {
        'name': 'Subject Knowledge Test',
        'description': "Measure a candidate's command over their subject area",
        'skills': 'Conceptual depth, academic domain validation, subject accuracy',
        'type': 'general',
        'questions': 5
    },
    'edu_classroom_mgmt': {
        'name': 'Classroom Management Test',
        'description': 'Evaluate ability to maintain order, engagement, and discipline in a learning environment',
        'skills': 'Behavior optimization, focus metrics, disruption isolation, engagement strategies',
        'type': 'general',
        'questions': 4
    },
    'edu_delivery': {
        'name': 'Communication & Delivery Assessment',
        'description': 'Measure effectiveness of communication during instruction or training delivery',
        'skills': 'Cadence control, dynamic feedback, structural concept breakdown, clarity',
        'type': 'general',
        'questions': 4
    },
    # GENERAL/FALLBACK
    'general_assessment': {
        'name': 'General Assessment',
        'description': 'Comprehensive assessment across general competencies',
        'skills': 'Communication, problem-solving, teamwork, adaptability',
        'type': 'general',
        'questions': 5
    },
    # FREE / GENERAL PLAN ASSESSMENTS
    'gen_video_intro': {
        'name': 'Introduction Test',
        'description': 'One-way video introduction: present yourself confidently and clearly',
        'skills': 'Communication, clarity, confidence, professional presentation',
        'type': 'general',
        'questions': 3
    },
    'gen_coding_basic': {
        'name': 'Basic Coding Challenge',
        'description': 'Entry-level coding problems testing fundamental programming logic',
        'skills': 'Basic algorithms, loops, conditionals, functions, problem-solving',
        'type': 'technical',
        'questions': 3
    },
    'gen_typing': {
        'name': 'Typing Test',
        'description': 'Measure typing speed and accuracy with real-world text passages',
        'skills': 'Typing speed, accuracy, attention to detail, data entry',
        'type': 'general',
        'questions': 2
    },
    'gen_aptitude': {
        'name': 'Aptitude & Logical Reasoning',
        'description': 'Numerical and logical reasoning questions for cognitive ability screening',
        'skills': 'Numerical reasoning, pattern recognition, logical deduction, problem-solving',
        'type': 'general',
        'questions': 10
    },
    'gen_psychometric': {
        'name': 'Psychometric Test',
        'description': 'Situational judgment test assessing workplace behavioral traits',
        'skills': 'Teamwork, integrity, stress handling, decision-making, work ethic',
        'type': 'general',
        'questions': 10
    },
    'gen_attention_detail': {
        'name': 'Attention to Detail & Speed Math',
        'description': 'Tests data accuracy, error spotting, and basic arithmetic speed',
        'skills': 'Attention to detail, numerical accuracy, speed, error detection',
        'type': 'general',
        'questions': 10
    },
    'gen_english_prof': {
        'name': 'English & Cyber Security Awareness',
        'description': 'Tests English grammar proficiency and basic cyber security knowledge',
        'skills': 'Grammar, vocabulary, reading comprehension, cyber security basics',
        'type': 'general',
        'questions': 10
    },
    'gen_resume_quiz': {
        'name': 'Resume Writing Self-Assessment',
        'description': 'Practise writing professional summaries and achievement statements for your CV',
        'skills': 'Resume writing, professional summary, achievement framing, self-presentation',
        'type': 'general',
        'questions': 4
    },
    'gen_interview_prep': {
        'name': 'Interview Readiness Quiz',
        'description': 'Test your knowledge of interview etiquette, STAR method, and professional conduct',
        'skills': 'Interview etiquette, STAR method, body language, professional communication',
        'type': 'general',
        'questions': 10
    },
}

@router.get("/assessment-questions")
async def get_assessment_questions(
    request: Request,
    planId: Optional[str] = None,
    mode: Optional[str] = None,
    type: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns structured section-based assessment data.
    Supports: voice_test, voice_scenario, text_writing, coding_test, mcq formats.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        assessment_key = None
        if planId and mode:
            assessment_key = mode
        elif type:
            assessment_key = type

        if not assessment_key:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Resolve metadata — try hardcoded dict first, then fall back to DB
        db_plan = None
        if assessment_key in ASSESSMENT_METADATA:
            metadata = ASSESSMENT_METADATA[assessment_key]
        else:
            from sqlalchemy import text as sa_text
            row = db.execute(
                sa_text("SELECT * FROM pricing_plans WHERE service_key = :key AND is_active = 1 LIMIT 1"),
                {"key": assessment_key}
            ).fetchone()
            if not row:
                logger.warning(f"Assessment not found: planId={planId}, mode={mode}, type={type}")
                raise HTTPException(status_code=404, detail="Assessment not found")
            db_plan = dict(row._mapping)
            skills_list = [s.strip() for s in (db_plan.get("skills_measured") or "").split(",") if s.strip()]
            metadata = {
                "name":        db_plan["name"],
                "description": db_plan.get("description", ""),
                "skills":      skills_list,
                "type":        "general",
                "questions":   5,
            }

        # Access control — user must have an active subscription for this specific assessment
        user_id = user.get("sub") or user.get("id") or user.get("user_id")
        if user_id:
            sub_service = SubscriptionService(db)
            access = sub_service.check_feature_access(user_id, assessment_key)
            if not access.get("accessible"):
                raise HTTPException(
                    status_code=403,
                    detail={"locked": True, "assessment_key": assessment_key,
                            "message": "You don't have an active subscription for this assessment."}
                )

        format_type = (db_plan.get("assessment_format") if db_plan else None) or get_format_type(assessment_key)
        logger.info(f"Loading assessment: key={assessment_key}, format={format_type}")

        skills_str = metadata['skills'] if isinstance(metadata['skills'], str) else ', '.join(metadata['skills'])

        # Sanitize platform value
        allowed_platforms = {'python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'sql'}
        platform = platform.lower() if platform and platform.lower() in allowed_platforms else None

        # Always attempt Ollama first — hardcoded content is the fallback
        ollama_questions = []
        ollama_mcq = []
        if ollama_service.is_ollama_available():
            try:
                if format_type == 'mcq':
                    ollama_mcq = ollama_service.generate_mcq_questions(
                        assessment_name=metadata['name'],
                        assessment_desc=metadata['description'],
                        skills=skills_str,
                        num_questions=metadata.get('questions', 5),
                    )
                elif format_type == 'coding_test' and platform:
                    # Use specialized coding challenge generator for platform-specific problems
                    ollama_questions = ollama_service.generate_coding_challenge_questions(
                        platform=platform,
                        num_questions=metadata.get('questions', 3),
                    )
                else:
                    ollama_questions = ollama_service.generate_questions(
                        assessment_name=metadata['name'],
                        assessment_desc=metadata['description'],
                        skills=skills_str,
                        num_questions=metadata.get('questions', 5),
                        assessment_type=metadata.get('type', 'general'),
                    )
            except Exception as e:
                logger.warning(f"Ollama generation failed: {str(e)}")

        sections = build_sections(
            assessment_key, metadata,
            ollama_questions=ollama_questions or None,
            format_override=format_type,
            ollama_mcq=ollama_mcq or None,
            platform=platform,
        )
        total_duration = sum(
            s.get('duration_per_item', 60) * len(s.get('items', []))
            for s in sections
            if isinstance(s.get('items'), list)
        )

        return {
            "ok": True,
            "data": {
                "assessment_key": assessment_key,
                "assessment_name": metadata['name'],
                "format": format_type,
                "format_description": get_format_description(format_type),
                "sections": sections,
                "total_duration": total_duration,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get assessment questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assessment-response")
async def submit_assessment_response(
    request: Request,
    response_data: AssessmentResponse = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit individual assessment response (video + metadata).
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        logger.info(f"Storing assessment response for user {user_id}: planId={response_data.planId}, questionId={response_data.questionId}")

        # Store response in database
        record_data = {
            'user_id': user_id,
            'plan_id': response_data.planId,
            'mode': response_data.mode,
            'question_id': response_data.questionId,
            'video_path': response_data.videoPath,
            'duration': response_data.duration,
            'timestamp': response_data.timestamp,
            'created_at': datetime.utcnow().isoformat()
        }

        mysql_service.create_record('premium_assessment_responses', record_data)

        return {
            "ok": True,
            "data": {
                "responseId": response_data.questionId,
                "status": "saved"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit assessment response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment-finish")
async def finish_assessment(
    request: Request,
    finish_data: AssessmentFinishRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Save all exercise responses for a completed assessment and return the session ID.
    Creates one assessment_sessions row and one assessment_responses row per exercise.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        assessment_key = finish_data.planId
        metadata = ASSESSMENT_METADATA.get(assessment_key, {})
        now = datetime.utcnow()

        # Auto-grade MCQ responses: count correct answers
        mcq_correct = 0
        mcq_total = 0

        # Collect per-row data; parse questionId = "{sectionId}_{itemId}"
        response_rows = []
        for r in finish_data.responses:
            # Split sectionId_itemId — only on first underscore group that makes sense
            parts = r.questionId.split('_', 1)
            section_id = parts[0] if len(parts) == 2 else r.questionId
            item_id    = parts[1] if len(parts) == 2 else None

            is_correct = None
            if r.type == 'mcq' and r.selectedIdx is not None:
                mcq_total += 1
                # Look up correct answer in MCQ_FALLBACK
                # (imported from assessment_formats if available)
                try:
                    from routers.assessment_formats import MCQ_FALLBACK
                    items = MCQ_FALLBACK.get(assessment_key, [])
                    # Match by item_id
                    match = next((q for q in items if q.get('id') == item_id), None)
                    if match and match.get('correct') is not None:
                        is_correct = 1 if r.selectedIdx == match['correct'] else 0
                        if is_correct:
                            mcq_correct += 1
                except Exception:
                    pass

            response_rows.append({
                'id':                 str(uuid.uuid4()),
                'section_id':         section_id,
                'item_id':            item_id,
                'exercise_type':      None,   # not sent from frontend; available from sections
                'response_type':      r.type,
                'text_response':      r.text or None,
                'selected_option_idx':r.selectedIdx,
                'is_correct':         is_correct,
                'has_recording':      1 if r.hasRecording else 0,
                'recording_url':      None,   # future: upload to R2 and store URL here
                'created_at':         now.isoformat(),
            })

        # Create the session record
        session_id = str(uuid.uuid4())
        session_record = {
            'id':                  session_id,
            'user_id':             user_id,
            'assessment_key':      assessment_key,
            'assessment_name':     metadata.get('name', assessment_key),
            'format':              get_format_type(assessment_key),
            'status':              'completed',
            'total_exercises':     len(finish_data.responses),
            'completed_exercises': len(finish_data.responses),
            'mcq_score':           mcq_correct if mcq_total > 0 else None,
            'mcq_total':           mcq_total   if mcq_total > 0 else None,
            'time_taken_seconds':  finish_data.timeTakenSeconds,
            'completed_at':        now.isoformat(),
        }
        from sqlalchemy import text as sa_text
        db.execute(sa_text("""
            INSERT INTO assessment_sessions
                (id, user_id, assessment_key, assessment_name, format, status,
                 total_exercises, completed_exercises, mcq_score, mcq_total,
                 time_taken_seconds, completed_at)
            VALUES
                (:id, :user_id, :assessment_key, :assessment_name, :format, :status,
                 :total_exercises, :completed_exercises, :mcq_score, :mcq_total,
                 :time_taken_seconds, :completed_at)
        """), session_record)

        # Save each exercise response, linked to the session
        for row in response_rows:
            row['session_id'] = session_id
            row['user_id']    = user_id
            db.execute(sa_text("""
                INSERT INTO assessment_responses
                    (id, session_id, user_id, section_id, item_id, exercise_type,
                     response_type, text_response, selected_option_idx, is_correct,
                     has_recording, recording_url, created_at)
                VALUES
                    (:id, :session_id, :user_id, :section_id, :item_id, :exercise_type,
                     :response_type, :text_response, :selected_option_idx, :is_correct,
                     :has_recording, :recording_url, :created_at)
            """), row)

        db.commit()

        logger.info(f"Assessment saved: session={session_id}, user={user_id}, key={assessment_key}, responses={len(response_rows)}")

        return {
            "ok": True,
            "data": {
                "session_id": session_id,
                "status": "completed",
                "mcq_score": mcq_correct if mcq_total > 0 else None,
                "mcq_total": mcq_total   if mcq_total > 0 else None,
                "total_exercises": len(response_rows),
                "message": "Assessment submitted successfully."
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to finish assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/typing-paragraph")
async def get_typing_paragraph(
    request: Request,
    duration: int = 3,
):
    """
    Return an Ollama-generated prose paragraph sized for a timed typing test.
    duration: test length in minutes (clamped 1-10). No subscription gate —
    gen_typing is a free-plan assessment.
    """
    duration = max(1, min(10, duration))
    text = ollama_service.generate_typing_paragraph(duration)
    return {
        "ok": True,
        "data": {
            "paragraph": text,
            "duration_minutes": duration,
            "word_count": len(text.split()),
        }
    }


_INTRO_FALLBACK_QUESTIONS = [
    "Describe your key professional strengths and how they add value to a team.",
    "Tell us about a challenge you have overcome and what you learned from it.",
    "Where do you see yourself professionally in the next three to five years?",
]

@router.get("/video-intro-questions")
async def get_video_intro_questions(request: Request):
    """Return 4 video intro questions: 1 fixed + 3 Ollama-generated."""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    fixed = "Please introduce yourself — share your background, key skills, and what makes you unique."

    extra: list = []
    if ollama_service.is_ollama_available():
        try:
            raw = ollama_service.generate_questions(
                assessment_name="Video Introduction",
                assessment_desc="One-way video self-introduction for professional assessment",
                skills="Communication, confidence, professional presentation, clarity",
                num_questions=3,
                assessment_type='general',
            )
            extra = [
                (q.get('question') or q.get('text') or str(q)) if isinstance(q, dict) else str(q)
                for q in raw
            ][:3]
        except Exception as e:
            logger.warning(f"Ollama video intro generation failed: {e}")

    while len(extra) < 3:
        extra.append(_INTRO_FALLBACK_QUESTIONS[len(extra) % 3])

    questions = [
        {"index": 0, "text": fixed, "duration": 60},
        *[{"index": i + 1, "text": q, "duration": 60} for i, q in enumerate(extra)],
    ]

    return {"ok": True, "data": {"questions": questions, "assessment_name": "Video Introduction"}}


@router.get("/assessment-results/{session_id}")
async def get_assessment_results(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Return saved results for a completed assessment session.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        from sqlalchemy import text as sa_text
        row = db.execute(
            sa_text("SELECT * FROM assessment_sessions WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": session_id, "uid": user_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Assessment session not found")
        session = dict(row._mapping)

        resp_rows = db.execute(
            sa_text("SELECT * FROM assessment_responses WHERE session_id = :sid"),
            {"sid": session_id}
        ).fetchall()
        responses = [dict(r._mapping) for r in resp_rows]

        return {
            "ok": True,
            "data": {
                "session_id":        session_id,
                "assessment_key":    session.get('assessment_key'),
                "assessment_name":   session.get('assessment_name'),
                "format":            session.get('format'),
                "status":            session.get('status'),
                "completed_at":      str(session.get('completed_at', '')),
                "total_exercises":   session.get('total_exercises', 0),
                "time_taken_seconds":session.get('time_taken_seconds'),
                "mcq_score":         session.get('mcq_score'),
                "mcq_total":         session.get('mcq_total'),
                "overall_score":     session.get('overall_score'),
                "reviewer_notes":    session.get('reviewer_notes'),
                "responses": [
                    {
                        "section_id":    r.get('section_id'),
                        "item_id":       r.get('item_id'),
                        "response_type": r.get('response_type'),
                        "text_response": r.get('text_response'),
                        "selected_option_idx": r.get('selected_option_idx'),
                        "is_correct":    r.get('is_correct'),
                        "has_recording": bool(r.get('has_recording')),
                    }
                    for r in responses
                ],
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get assessment results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-assessments")
async def get_my_assessments(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Return all assessment sessions for the current user.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        from sqlalchemy import text as sa_text
        sess_rows = db.execute(
            sa_text("SELECT * FROM assessment_sessions WHERE user_id = :uid ORDER BY completed_at DESC"),
            {"uid": user_id}
        ).fetchall()
        sessions = [dict(r._mapping) for r in sess_rows]

        return {
            "ok": True,
            "data": [
                {
                    "session_id":      s.get('id'),
                    "assessment_key":  s.get('assessment_key'),
                    "assessment_name": s.get('assessment_name'),
                    "format":          s.get('format'),
                    "status":          s.get('status'),
                    "completed_at":    str(s.get('completed_at', '')),
                    "mcq_score":       s.get('mcq_score'),
                    "mcq_total":       s.get('mcq_total'),
                    "overall_score":   s.get('overall_score'),
                }
                for s in sessions
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user assessments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
