"""
Reference data router - provides dropdown options from database tables.
"""

from fastapi import APIRouter, Request
from typing import Optional, List, Dict, Any
from services.mysql_service import MySQLService
from middleware.role_required import ensure_permission
from utils_others.logger import logger

router = APIRouter(prefix="/reference", tags=["Reference Data"])
mysql = MySQLService()


@router.get("/departments")
async def get_departments(request: Request, active_only: bool = True):
    """Get all departments."""
    try:
        conditions = {"is_active": True} if active_only else {}
        departments = mysql.get_records(
            "departments", 
            conditions, 
            order_by="sort_order ASC, name ASC"
        )
        return {"ok": True, "data": departments or []}
    except Exception as e:
        logger.error(f"Get departments failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/roles")
async def get_roles(request: Request, department_id: Optional[str] = None, active_only: bool = True):
    """Get all roles, optionally filtered by department."""
    try:
        conditions = {"is_active": True} if active_only else {}
        if department_id:
            conditions["department_id"] = department_id
        
        roles = mysql.get_records(
            "roles", 
            conditions, 
            order_by="level ASC, sort_order ASC, name ASC"
        )
        return {"ok": True, "data": roles or []}
    except Exception as e:
        logger.error(f"Get roles failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/employment-types")
async def get_employment_types(request: Request, active_only: bool = True):
    """Get all employment types."""
    try:
        conditions = {"is_active": True} if active_only else {}
        types = mysql.get_records(
            "employment_types", 
            conditions, 
            order_by="sort_order ASC, name ASC"
        )
        return {"ok": True, "data": types or []}
    except Exception as e:
        logger.error(f"Get employment types failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/industries")
async def get_industries(request: Request, active_only: bool = True):
    """Get all industries."""
    try:
        conditions = {"is_active": True} if active_only else {}
        industries = mysql.get_records(
            "industries", 
            conditions, 
            order_by="sort_order ASC, name ASC"
        )
        return {"ok": True, "data": industries or []}
    except Exception as e:
        logger.error(f"Get industries failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/job-types")
async def get_job_types(request: Request, active_only: bool = True):
    """Get all job types (work location preferences)."""
    try:
        conditions = {"is_active": True} if active_only else {}
        types = mysql.get_records(
            "job_types", 
            conditions, 
            order_by="sort_order ASC, name ASC"
        )
        return {"ok": True, "data": types or []}
    except Exception as e:
        logger.error(f"Get job types failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/education-levels")
async def get_education_levels(request: Request, active_only: bool = True):
    """Get all education levels."""
    try:
        conditions = {"is_active": True} if active_only else {}
        levels = mysql.get_records(
            "education_levels", 
            conditions, 
            order_by="sort_order ASC, name ASC"
        )
        return {"ok": True, "data": levels or []}
    except Exception as e:
        logger.error(f"Get education levels failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/salary-ranges")
async def get_salary_ranges(request: Request, active_only: bool = True):
    """Get all salary ranges."""
    try:
        conditions = {"is_active": True} if active_only else {}
        ranges = mysql.get_records(
            "salary_ranges", 
            conditions, 
            order_by="sort_order ASC"
        )
        return {"ok": True, "data": ranges or []}
    except Exception as e:
        logger.error(f"Get salary ranges failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/experience-levels")
async def get_experience_levels(request: Request, active_only: bool = True):
    """Get all experience levels."""
    try:
        conditions = {"is_active": True} if active_only else {}
        levels = mysql.get_records(
            "experience_levels", 
            conditions, 
            order_by="sort_order ASC"
        )
        return {"ok": True, "data": levels or []}
    except Exception as e:
        logger.error(f"Get experience levels failed: {str(e)}")
        return {"ok": True, "data": []}


@router.get("/all")
async def get_all_reference_data(request: Request):
    """Get all reference data in a single call (for page initialization)."""
    try:
        active_conditions = {"is_active": True}
        
        result = {
            "departments": mysql.get_records("departments", active_conditions, order_by="sort_order ASC, name ASC") or [],
            "roles": mysql.get_records("roles", active_conditions, order_by="level ASC, sort_order ASC, name ASC") or [],
            "employment_types": mysql.get_records("employment_types", active_conditions, order_by="sort_order ASC, name ASC") or [],
            "industries": mysql.get_records("industries", active_conditions, order_by="sort_order ASC, name ASC") or [],
            "job_types": mysql.get_records("job_types", active_conditions, order_by="sort_order ASC, name ASC") or [],
            "education_levels": mysql.get_records("education_levels", active_conditions, order_by="sort_order ASC, name ASC") or [],
            "salary_ranges": mysql.get_records("salary_ranges", active_conditions, order_by="sort_order ASC") or [],
            "experience_levels": mysql.get_records("experience_levels", active_conditions, order_by="sort_order ASC") or []
        }
        
        return {"ok": True, "data": result}
    except Exception as e:
        logger.error(f"Get all reference data failed: {str(e)}")
        return {"ok": True, "data": {}}
