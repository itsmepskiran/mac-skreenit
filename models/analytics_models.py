from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any


# ---------------------------------------------------------
# REQUEST MODEL (from frontend)
# ---------------------------------------------------------
class AnalyticsEventRequest(BaseModel):
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # user_id is injected by backend (request.state.user)
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# RESPONSE MODEL (to frontend)
# ---------------------------------------------------------
class AnalyticsEventResponse(BaseModel):
    id: str
    user_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# OPTIONAL: ANALYTICS SUMMARY MODEL
# ---------------------------------------------------------
class AnalyticsSummary(BaseModel):
    total_events: int
    events_by_type: Dict[str, int]
    events_by_day: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# OPTIONAL: FILTER MODEL
# ---------------------------------------------------------
class AnalyticsFilter(BaseModel):
    event_type: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
