"""
Training Registration Router
Handles college and corporate training registrations.
"""

import json
import uuid
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import JSONResponse

from services.mysql_service import MySQLService
from services.payment_service import PaymentService
from utils_others.logger import logger

mysql_service = MySQLService()
payment_service = PaymentService()

router = APIRouter(prefix="/training", tags=["Training Registration"])

# ============================================================
# PRICING FROM DATABASE
# ============================================================

def _fetch_training_plans_from_db() -> dict:
    """
    Query pricing_plans for all active training plans.
    Accepts both service_type='training' and 'training_plan' so plans
    created via the admin panel (which uses 'training_plan') are found too.
    """
    from sqlalchemy import text
    from database import get_db

    plans = {}
    try:
        db = next(get_db())
        rows = db.execute(
            text("""
                SELECT id, service_key, name, price_inr, duration, description,
                       features, billing_cycle
                FROM pricing_plans
                WHERE service_type IN ('training', 'training_plan')
                  AND is_active = 1
                ORDER BY sort_order ASC, name ASC
            """)
        ).fetchall()

        for row in rows:
            key = row.service_key
            try:
                features = json.loads(row.features or "[]")
            except Exception:
                features = []
            plans[key] = {
                "plan_db_id": row.id,
                "name": row.name,
                "price": row.price_inr,
                "price_inr": row.price_inr,
                "duration": row.duration or "Custom",
                "description": row.description or "",
                "features": features,
                "billing_cycle": row.billing_cycle or "one_time",
            }
    except Exception as e:
        logger.error(f"Failed to load training plans from DB: {e}")

    return plans


# ============================================================
# PUBLIC ENDPOINTS
# ============================================================

@router.get("/courses")
async def get_training_courses():
    """Get list of available training courses, queried fresh from the DB each call."""
    plans = _fetch_training_plans_from_db()
    if not plans:
        logger.warning("No training plans found in pricing_plans (service_type in ['training','training_plan'])")
    return {"ok": True, "data": plans}


@router.get("/payment-config")
async def get_payment_config():
    """Get Razorpay public key for frontend payment initialisation."""
    return {"ok": True, "data": payment_service.get_public_config("Skreenit Training")}


@router.post("/register-college")
async def register_college_training(request: Request, registration_data: dict = Body(...)):
    """Register college/student for training."""
    try:
        first_name      = registration_data.get("firstName")
        last_name       = registration_data.get("lastName")
        email           = registration_data.get("email")
        mobile          = registration_data.get("mobile")
        college_name    = registration_data.get("collegeName")
        university_name = registration_data.get("universityName")
        college_address = registration_data.get("collegeAddress")
        roll_number     = registration_data.get("rollNumber")
        course          = registration_data.get("course")
        year_of_study   = registration_data.get("yearOfStudy")
        passing_year    = registration_data.get("passingYear")
        training_course = registration_data.get("trainingCourse")
        batch_timing    = registration_data.get("batchTiming")

        if not all([first_name, last_name, email, mobile, college_name, university_name,
                    college_address, roll_number, course, year_of_study, passing_year,
                    training_course, batch_timing]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        all_courses = _fetch_training_plans_from_db()
        course_info = all_courses.get(training_course)
        if not course_info:
            raise HTTPException(status_code=400, detail="Invalid training course")

        registration_id = f"STU{int(time.time() * 1000)}{str(uuid.uuid4())[:6].upper()}"

        base_payload = {
            "id": str(uuid.uuid4()),
            "registration_id": registration_id,
            "registration_type": "college",
            "training_course": training_course,
            "training_course_name": course_info["name"],
            "status": "pending",
            "payment_status": "pending",
            "amount": course_info["price"],
            "created_at": datetime.now(),
        }
        mysql_service.insert_record("training_registrations", base_payload)

        college_payload = {
            "id": str(uuid.uuid4()),
            "registration_id": registration_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile": mobile,
            "college_name": college_name,
            "university_name": university_name,
            "college_address": college_address,
            "roll_number": roll_number,
            "course": course,
            "year_of_study": year_of_study,
            "passing_year": int(passing_year),
            "training_course": training_course,
            "batch_timing": batch_timing,
            "created_at": datetime.now(),
        }
        mysql_service.insert_record("college_training_registrations", college_payload)

        logger.info(f"College training registration created: {registration_id}")

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "student_id": registration_id,
                "course": course_info["name"],
                "amount": course_info["price"],
                "status": "pending_payment",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"College training registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register-corporate")
async def register_corporate_training(request: Request, registration_data: dict = Body(...)):
    """Register company for corporate training."""
    try:
        company_name            = registration_data.get("companyName")
        company_hq              = registration_data.get("companyHQ")
        company_headcount       = registration_data.get("companyHC")
        industry                = registration_data.get("industry")
        company_type            = registration_data.get("companyType")
        company_website         = registration_data.get("companyWebsite")
        contact_name            = registration_data.get("contactName")
        contact_designation     = registration_data.get("contactDesignation")
        contact_email           = registration_data.get("contactEmail")
        contact_mobile          = registration_data.get("contactMobile")
        training_course         = registration_data.get("trainingCourse")
        employee_count          = registration_data.get("employeeCount")
        training_mode           = registration_data.get("trainingMode")
        preferred_date          = registration_data.get("preferredDate")
        duration                = registration_data.get("duration")
        additional_requirements = registration_data.get("additionalRequirements")

        if not all([company_name, company_hq, company_headcount, industry, company_type,
                    contact_name, contact_designation, contact_email, contact_mobile,
                    training_course, employee_count, training_mode, duration]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        all_courses = _fetch_training_plans_from_db()
        course_info = all_courses.get(training_course)
        if not course_info:
            raise HTTPException(status_code=400, detail="Invalid training course")

        total_amount = course_info["price"] * int(employee_count) if training_course != "custom" else 0
        registration_id = f"CORP{int(time.time() * 1000)}{str(uuid.uuid4())[:6].upper()}"

        base_payload = {
            "id": str(uuid.uuid4()),
            "registration_id": registration_id,
            "registration_type": "corporate",
            "training_course": training_course,
            "training_course_name": course_info["name"],
            "status": "pending",
            "payment_status": "pending",
            "amount": total_amount,
            "created_at": datetime.now(),
        }
        mysql_service.insert_record("training_registrations", base_payload)

        corporate_payload = {
            "id": str(uuid.uuid4()),
            "registration_id": registration_id,
            "company_name": company_name,
            "company_hq": company_hq,
            "company_headcount": company_headcount,
            "industry": industry,
            "company_type": company_type,
            "company_website": company_website,
            "contact_name": contact_name,
            "contact_designation": contact_designation,
            "contact_email": contact_email,
            "contact_mobile": contact_mobile,
            "training_course": training_course,
            "employee_count": int(employee_count),
            "training_mode": training_mode,
            "preferred_date": datetime.strptime(preferred_date, "%Y-%m-%d") if preferred_date else None,
            "duration": duration,
            "additional_requirements": additional_requirements,
            "created_at": datetime.now(),
        }
        mysql_service.insert_record("corporate_training_registrations", corporate_payload)

        logger.info(f"Corporate training registration created: {registration_id}")

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "corporate_id": registration_id,
                "course": course_info["name"],
                "amount": total_amount,
                "employee_count": employee_count,
                "status": "pending_quote" if training_course == "custom" else "pending_payment",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Corporate training registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PAYMENT ENDPOINTS
# ============================================================

@router.post("/create-order")
async def create_payment_order(request: Request, body: dict = Body(...)):
    """
    Create a Razorpay order for a registration.
    Frontend must call this BEFORE opening the Razorpay checkout modal.
    Returns order_id which must be passed to the Razorpay SDK options.
    """
    try:
        registration_id = body.get("registration_id")
        if not registration_id:
            raise HTTPException(status_code=400, detail="Missing registration_id")

        reg = mysql_service.get_single_record("training_registrations", {
            "registration_id": registration_id
        })
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")

        if reg.get("payment_status") == "completed":
            raise HTTPException(status_code=400, detail="Payment already completed for this registration")

        amount = reg.get("amount", 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Cannot create order for zero-amount registration")

        order = payment_service.create_order(
            amount_inr=amount,
            receipt=registration_id,
            notes={
                "registration_id": registration_id,
                "course": reg.get("training_course_name", ""),
                "type": reg.get("registration_type", ""),
            },
        )

        mysql_service.update_record(
            "training_registrations",
            {"razorpay_order_id": order["id"], "updated_at": datetime.now()},
            {"registration_id": registration_id},
        )

        logger.info(f"Payment order created: {order['id']} for registration: {registration_id}")

        return {
            "ok": True,
            "data": {
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "registration_id": registration_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-success")
async def training_payment_success(request: Request, payment_data: dict = Body(...)):
    """
    Verify Razorpay payment signature and mark registration as paid.
    Requires: registration_id, razorpay_order_id, razorpay_payment_id, razorpay_signature
    """
    try:
        registration_id    = payment_data.get("registration_id")
        razorpay_order_id  = payment_data.get("razorpay_order_id")
        razorpay_payment_id = payment_data.get("razorpay_payment_id")
        razorpay_signature = payment_data.get("razorpay_signature")

        if not all([registration_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: registration_id, razorpay_order_id, razorpay_payment_id, razorpay_signature",
            )

        is_valid = payment_service.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not is_valid:
            logger.warning(f"Invalid payment signature for registration: {registration_id}")
            raise HTTPException(status_code=400, detail="Payment signature verification failed")

        mysql_service.update_record(
            "training_registrations",
            {
                "payment_status": "completed",
                "payment_id": razorpay_payment_id,
                "razorpay_order_id": razorpay_order_id,
                "payment_date": datetime.now(),
                "status": "confirmed",
                "updated_at": datetime.now(),
            },
            {"registration_id": registration_id},
        )

        logger.info(f"Training payment verified & confirmed: {registration_id} | payment={razorpay_payment_id}")

        return {
            "ok": True,
            "data": {"message": "Payment verified and confirmed", "registration_id": registration_id},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment success update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def training_payment_webhook(request: Request):
    """
    Razorpay webhook endpoint — receives server-side payment events.
    Configure this URL in your Razorpay Dashboard → Webhooks.
    Supported events: payment.captured, payment.failed, order.paid
    """
    try:
        raw_body = await request.body()
        razorpay_signature = request.headers.get("X-Razorpay-Signature", "")

        if not payment_service.verify_webhook_signature(raw_body, razorpay_signature):
            logger.warning("Webhook received with invalid signature — rejected.")
            return JSONResponse(status_code=400, content={"error": "Invalid webhook signature"})

        event = json.loads(raw_body)
        event_type = event.get("event")
        logger.info(f"Webhook received: {event_type}")

        if event_type in ("payment.captured", "order.paid"):
            payload = event.get("payload", {})
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")

            if order_id:
                reg = mysql_service.get_single_record("training_registrations", {
                    "razorpay_order_id": order_id
                })
                if reg and reg.get("payment_status") != "completed":
                    mysql_service.update_record(
                        "training_registrations",
                        {
                            "payment_status": "completed",
                            "payment_id": payment_id,
                            "payment_date": datetime.now(),
                            "status": "confirmed",
                            "updated_at": datetime.now(),
                        },
                        {"razorpay_order_id": order_id},
                    )
                    logger.info(f"Webhook confirmed payment for order: {order_id} | payment: {payment_id}")

        elif event_type == "payment.failed":
            payload = event.get("payload", {})
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")

            if order_id:
                mysql_service.update_record(
                    "training_registrations",
                    {"payment_status": "failed", "updated_at": datetime.now()},
                    {"razorpay_order_id": order_id},
                )
                logger.warning(f"Webhook received payment.failed for order: {order_id}")

        return JSONResponse(status_code=200, content={"status": "ok"})

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Webhook processing failed"})


@router.get("/registrations/{registration_id}")
async def get_registration(registration_id: str):
    """Get registration details by ID."""
    try:
        base_reg = mysql_service.get_single_record("training_registrations", {
            "registration_id": registration_id
        })

        if not base_reg:
            raise HTTPException(status_code=404, detail="Registration not found")

        if base_reg["registration_type"] == "college":
            details = mysql_service.get_single_record("college_training_registrations", {
                "registration_id": registration_id
            })
        else:
            details = mysql_service.get_single_record("corporate_training_registrations", {
                "registration_id": registration_id
            })

        return {"ok": True, "data": {"base": base_reg, "details": details}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# TRAINING ASSESSMENT ENDPOINTS
# ============================================================

@router.get("/assessment-questions/{registration_id}")
async def get_assessment_questions(registration_id: str):
    """Get assessment questions for a training registration."""
    try:
        # Check if registration exists
        registration = mysql_service.get_single_record("training_registrations", {
            "registration_id": registration_id
        })
        if not registration:
            raise HTTPException(status_code=404, detail="Training registration not found")

        # Get or create assessment completion record
        completion = mysql_service.get_single_record("training_assessment_completions", {
            "registration_id": registration_id
        })

        if not completion:
            # Create new assessment completion record
            completion_id = str(uuid.uuid4())
            total_questions = 5  # Default number of questions

            completion_payload = {
                "id": completion_id,
                "registration_id": registration_id,
                "total_questions": total_questions,
                "questions_completed": 0,
                "completion_status": "pending",
                "completion_percentage": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            mysql_service.insert_record("training_assessment_completions", completion_payload)
            completion = completion_payload
        else:
            total_questions = completion.get("total_questions", 5)

        # Get assessment questions
        questions = mysql_service.get_records("training_assessment_questions", {
            "registration_id": registration_id
        }, limit=100)

        # If no questions exist, generate them
        if not questions:
            questions = []
            from services.ollama_service import ollama_service

            # Get training course info for question generation
            course_name = registration.get("training_course_name", "Training Assessment")

            # Generate questions using Ollama
            generated_questions = ollama_service.generate_questions(
                assessment_name=course_name,
                assessment_desc=f"Assessment for {course_name}",
                skills="Communication, Technical Skills, Problem Solving",
                num_questions=total_questions,
                assessment_type="general"
            )

            # Save generated questions to database
            for idx, q in enumerate(generated_questions or []):
                question_payload = {
                    "id": str(uuid.uuid4()),
                    "registration_id": registration_id,
                    "question_index": idx,
                    "question_text": q.get("question", ""),
                    "question_type": "video_response",
                    "duration": q.get("duration", 60),
                    "created_at": datetime.now(),
                }
                mysql_service.insert_record("training_assessment_questions", question_payload)
                questions.append(question_payload)

            if not questions:
                # Fallback template questions
                questions = []
                for i in range(total_questions):
                    questions.append({
                        "id": str(uuid.uuid4()),
                        "registration_id": registration_id,
                        "question_index": i,
                        "question_text": f"{course_name} - Question {i+1}: Tell us about your experience and why you're interested in this training.",
                        "question_type": "video_response",
                        "duration": 60,
                        "created_at": datetime.now(),
                    })

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "questions": questions,
                "total_questions": len(questions),
                "completion_status": completion.get("completion_status"),
                "questions_completed": completion.get("questions_completed", 0),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get assessment questions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-response/{registration_id}")
async def submit_assessment_response(registration_id: str, response_data: dict = Body(...)):
    """Submit assessment response for a training registration."""
    try:
        question_index = response_data.get("question_index")
        response_path = response_data.get("response_path")  # S3 path
        response_duration = response_data.get("response_duration", 0)
        response_type = response_data.get("response_type", "video")

        if question_index is None or not response_path:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Check if registration exists
        registration = mysql_service.get_single_record("training_registrations", {
            "registration_id": registration_id
        })
        if not registration:
            raise HTTPException(status_code=404, detail="Training registration not found")

        # Save response
        response_payload = {
            "id": str(uuid.uuid4()),
            "registration_id": registration_id,
            "question_index": question_index,
            "response_type": response_type,
            "response_path": response_path,
            "response_duration": response_duration,
            "submitted_at": datetime.now(),
            "created_at": datetime.now(),
        }
        mysql_service.insert_record("training_assessment_responses", response_payload)

        # Update completion record
        completion = mysql_service.get_single_record("training_assessment_completions", {
            "registration_id": registration_id
        })

        if completion:
            # Count responses
            responses = mysql_service.get_records("training_assessment_responses", {
                "registration_id": registration_id
            })
            total_responses = len(responses)
            total_questions = completion.get("total_questions", 5)
            completion_percentage = int((total_responses / total_questions) * 100)

            update_payload = {
                "questions_completed": total_responses,
                "completion_percentage": completion_percentage,
                "completion_status": "in_progress" if total_responses < total_questions else "completed",
                "updated_at": datetime.now(),
            }
            if total_responses >= total_questions:
                update_payload["completed_at"] = datetime.now()

            mysql_service.update_record("training_assessment_completions", update_payload, {
                "registration_id": registration_id
            })

        logger.info(f"Assessment response submitted for registration {registration_id}, question {question_index}")

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "question_index": question_index,
                "status": "submitted"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit response failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assessment-status/{registration_id}")
async def get_assessment_status(registration_id: str):
    """Get assessment completion status for a training registration."""
    try:
        completion = mysql_service.get_single_record("training_assessment_completions", {
            "registration_id": registration_id
        })

        if not completion:
            raise HTTPException(status_code=404, detail="Assessment record not found")

        # Get responses
        responses = mysql_service.get_records("training_assessment_responses", {
            "registration_id": registration_id
        })

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "total_questions": completion.get("total_questions"),
                "questions_completed": len(responses),
                "completion_percentage": completion.get("completion_percentage", 0),
                "completion_status": completion.get("completion_status"),
                "started_at": completion.get("started_at"),
                "completed_at": completion.get("completed_at"),
                "evaluation_score": completion.get("evaluation_score"),
                "evaluation_feedback": completion.get("evaluation_feedback"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get assessment status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
