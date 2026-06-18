from typing import Optional, Dict, Any, List
from services.mysql_service import MySQLService
from utils_others.logger import logger
from datetime import datetime, timezone


class AnalyticsService:
    """
    Handles analytics event creation and retrieval.
    """

    def __init__(self, mysql_service: Optional[MySQLService] = None):
        self.mysql = mysql_service or MySQLService()

    # ---------------------------------------------------------
    # CREATE EVENT
    # ---------------------------------------------------------
    def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert an analytics event into analytics_events table.
        Ensures event_data is always a dict and timestamp is normalized.
        """
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "user_id": data.get("user_id"),
                "event_type": data.get("event_type"),
                "event_data": data.get("event_data") or {},
                "ip_address": data.get("ip_address"),
                "user_agent": data.get("user_agent"),
                "created_at": datetime.now(timezone.utc),
            }

            event_id = self.mysql.insert_record("analytics_events", payload)

            logger.info(
                "Analytics event created",
                extra={
                    "user_id": payload["user_id"],
                    "event_type": payload["event_type"],
                },
            )

            return {"data": payload, "id": event_id}

        except Exception as e:
            logger.error(
                f"Create analytics event failed: {str(e)}",
                extra={
                    "user_id": data.get("user_id"),
                    "event_type": data.get("event_type"),
                },
            )
            raise RuntimeError("Failed to create analytics event")

    # ---------------------------------------------------------
    # RETRIEVE EVENTS
    # ---------------------------------------------------------
    def get_user_events(
        self, 
        user_id: str, 
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get analytics events for a specific user.
        """
        try:
            conditions = {"user_id": user_id}
            if event_type:
                conditions["event_type"] = event_type

            events = self.mysql.get_records(
                "analytics_events",
                conditions,
                order_by="created_at DESC",
                limit=limit
            )
            
            return events or []

        except Exception as e:
            logger.error(f"Get user events failed: {str(e)}")
            return []

    def get_events_by_type(
        self, 
        event_type: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get analytics events by event type.
        """
        try:
            events = self.mysql.get_records(
                "analytics_events",
                {"event_type": event_type},
                order_by="created_at DESC",
                limit=limit
            )
            
            return events or []

        except Exception as e:
            logger.error(f"Get events by type failed: {str(e)}")
            return []

    def get_events_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get analytics events within a date range.
        """
        try:
            conditions = {
                "created_at >=": start_date,
                "created_at <=": end_date
            }
            
            if user_id:
                conditions["user_id"] = user_id

            events = self.mysql.get_records(
                "analytics_events",
                conditions,
                order_by="created_at DESC"
            )
            
            return events or []

        except Exception as e:
            logger.error(f"Get events by date range failed: {str(e)}")
            return []

    # ---------------------------------------------------------
    # ANALYTICS AGGREGATIONS
    # ---------------------------------------------------------
    def get_event_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get summary of events by type for analytics dashboard.
        """
        try:
            conditions = {}
            if start_date:
                conditions["created_at >="] = start_date
            if end_date:
                conditions["created_at <="] = end_date

            # Get all events in date range
            events = self.mysql.get_records("analytics_events", conditions)
            
            if not events:
                return {"total_events": 0, "by_type": {}, "by_user": {}}

            # Aggregate by event type
            by_type = {}
            for event in events:
                event_type = event.get("event_type", "unknown")
                by_type[event_type] = by_type.get(event_type, 0) + 1

            # Aggregate by user
            by_user = {}
            for event in events:
                user_id = event.get("user_id", "unknown")
                by_user[user_id] = by_user.get(user_id, 0) + 1

            return {
                "total_events": len(events),
                "by_type": by_type,
                "by_user": by_user,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }

        except Exception as e:
            logger.error(f"Get event summary failed: {str(e)}")
            return {"total_events": 0, "by_type": {}, "by_user": {}}

    def get_user_activity_summary(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific user over the last N days.
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            events = self.get_events_by_date_range(
                start_date=start_date,
                end_date=datetime.now(timezone.utc),
                user_id=user_id
            )

            # Group events by type
            activity_by_type = {}
            for event in events:
                event_type = event.get("event_type", "unknown")
                if event_type not in activity_by_type:
                    activity_by_type[event_type] = []
                activity_by_type[event_type].append(event)

            return {
                "user_id": user_id,
                "days_analyzed": days,
                "total_events": len(events),
                "activity_by_type": activity_by_type,
                "most_active_day": self._find_most_active_day(events)
            }

        except Exception as e:
            logger.error(f"Get user activity summary failed: {str(e)}")
            return {"user_id": user_id, "days_analyzed": days, "total_events": 0}

    # ---------------------------------------------------------
    # UTILITY METHODS
    # ---------------------------------------------------------
    def _find_most_active_day(self, events: List[Dict[str, Any]]) -> Optional[str]:
        """Find the day with most events."""
        try:
            if not events:
                return None

            # Group events by date
            events_by_date = {}
            for event in events:
                event_date = event.get("created_at", "")
                if isinstance(event_date, str):
                    event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                
                date_key = event_date.strftime("%Y-%m-%d")
                if date_key not in events_by_date:
                    events_by_date[date_key] = 0
                events_by_date[date_key] += 1

            # Find date with most events
            most_active_date = max(events_by_date.items(), key=lambda x: x[1])
            return most_active_date[0]

        except Exception as e:
            logger.error(f"Find most active day failed: {str(e)}")
            return None

    # ---------------------------------------------------------
    # TRACKING HELPERS
    # ---------------------------------------------------------
    def track_login(self, user_id: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Track user login event."""
        return self.create_event({
            "user_id": user_id,
            "event_type": "login",
            "event_data": {"action": "user_login"},
            "ip_address": ip_address,
            "user_agent": user_agent
        })

    def track_job_application(self, user_id: str, job_id: str, ip_address: str) -> Dict[str, Any]:
        """Track job application event."""
        return self.create_event({
            "user_id": user_id,
            "event_type": "job_application",
            "event_data": {"job_id": job_id, "action": "applied"},
            "ip_address": ip_address
        })

    def track_profile_update(self, user_id: str, updated_fields: List[str]) -> Dict[str, Any]:
        """Track profile update event."""
        return self.create_event({
            "user_id": user_id,
            "event_type": "profile_update",
            "event_data": {"updated_fields": updated_fields, "action": "profile_updated"}
        })

    def track_video_upload(self, user_id: str, video_type: str, file_size: int) -> Dict[str, Any]:
        """Track video upload event."""
        return self.create_event({
            "user_id": user_id,
            "event_type": "video_upload",
            "event_data": {
                "video_type": video_type, 
                "file_size": file_size, 
                "action": "video_uploaded"
            }
        })

    def track_page_view(self, user_id: str, page: str, ip_address: str) -> Dict[str, Any]:
        """Track page view event."""
        return self.create_event({
            "user_id": user_id,
            "event_type": "page_view",
            "event_data": {"page": page, "action": "page_viewed"},
            "ip_address": ip_address
        })
