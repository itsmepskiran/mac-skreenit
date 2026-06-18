from fastapi import APIRouter, Depends, HTTPException, Query, Request
from services.notification_service_mysql import NotificationService
from utils_others.logger import logger
from typing import List, Optional

router = APIRouter(prefix="/notifications", tags=["Notifications"])

def get_user_from_request(request: Request):
    """Get user from request state."""
    return getattr(request.state, "user", None)

def get_notification_service():
    """Dependency to get notification service instance"""
    return NotificationService()

@router.get("/")
async def get_notifications(
    request: Request,
    unread_only: bool = Query(False, description="Get only unread notifications"),
    limit: int = Query(50, description="Maximum number of notifications to return"),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Get notifications for the current user
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        notifications = notification_service.get_user_notifications(
            user_id=current_user_id,
            unread_only=unread_only,
            limit=limit
        )
        
        return {
            "ok": True,
            "data": {
                "notifications": notifications,
                "count": len(notifications)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get notifications failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@router.get("/unread-count")
async def get_unread_count(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Get count of unread notifications for the current user
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        count = notification_service.get_unread_count(current_user_id)
        
        return {
            "ok": True,
            "data": {
                "unread_count": count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get unread count failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve unread count")

@router.put("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Mark a specific notification as read
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        success = notification_service.mark_as_read(notification_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found or cannot be updated")
        
        return {
            "ok": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark notification as read failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.put("/read-all")
async def mark_all_notifications_as_read(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Mark all notifications for the current user as read
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        count = notification_service.mark_all_as_read(current_user_id)
        
        return {
            "ok": True,
            "data": {
                "marked_count": count
            },
            "message": f"Marked {count} notifications as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark all as read failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Delete a specific notification
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        success = notification_service.delete_notification(notification_id, current_user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found or cannot be deleted")
        
        return {
            "ok": True,
            "message": "Notification deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete notification failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")

@router.delete("/")
async def clear_all_notifications(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Clear all notifications for the current user
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        current_user_id = user.get("sub")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        count = notification_service.clear_all_notifications(current_user_id)
        
        return {
            "ok": True,
            "data": {
                "cleared_count": count
            },
            "message": f"Cleared {count} notifications"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear all notifications failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear notifications")
