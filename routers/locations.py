"""
Location Router - API endpoints for world location data
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from database import engine
from sqlalchemy import text

router = APIRouter(prefix="/locations", tags=["Locations"])


# Response Models
class CountryResponse(BaseModel):
    id: int
    name: str
    iso2: Optional[str]
    iso3: Optional[str]
    phonecode: Optional[str]
    capital: Optional[str]
    currency: Optional[str]
    emoji: Optional[str]
    region: Optional[str]
    subregion: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


class StateResponse(BaseModel):
    id: int
    name: str
    country_id: int
    country_code: Optional[str]
    country_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


class CityResponse(BaseModel):
    id: int
    name: str
    state_id: int
    state_code: Optional[str]
    state_name: Optional[str]
    country_id: int
    country_code: Optional[str]
    country_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]
    population: Optional[int]


class LocationSearchResponse(BaseModel):
    cities: List[CityResponse]
    states: List[StateResponse]
    countries: List[CountryResponse]


class UniversityResponse(BaseModel):
    id: int
    name: str
    state_id: Optional[int]
    state_name: Optional[str]
    country_id: Optional[int]
    university_type: Optional[str]
    established_year: Optional[int]
    website: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


class CollegeResponse(BaseModel):
    id: int
    name: str
    university_id: int
    university_name: Optional[str]
    city_id: Optional[int]
    city_name: Optional[str]
    state_id: Optional[int]
    state_name: Optional[str]
    country_id: Optional[int]
    college_type: Optional[str]
    established_year: Optional[int]
    affiliation_number: Optional[str]
    website: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    accreditation_status: Optional[str]


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/countries", response_model=List[CountryResponse])
async def get_countries(
    region: Optional[str] = Query(None, description="Filter by region (Asia, Europe, Africa, etc.)"),
    subregion: Optional[str] = Query(None, description="Filter by subregion"),
    search: Optional[str] = Query(None, description="Search by country name"),
    limit: int = Query(250, ge=1, le=250)
):
    """Get all countries with optional filtering."""
    with engine.connect() as conn:
        query = """
            SELECT c.id, c.name, c.iso2, c.iso3, c.phonecode, c.capital,
                   c.currency, c.emoji, c.region, c.subregion,
                   c.latitude, c.longitude
            FROM countries c
            WHERE 1=1
        """
        params = {}
        
        if region:
            query += " AND c.region = :region"
            params["region"] = region
        
        if subregion:
            query += " AND c.subregion = :subregion"
            params["subregion"] = subregion
            
        if search:
            query += " AND c.name LIKE :search"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY c.name LIMIT :limit"
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        rows = result.mappings().all()
        
        return [CountryResponse(**dict(row)) for row in rows]


@router.get("/countries/{country_id}", response_model=CountryResponse)
async def get_country(country_id: int):
    """Get a specific country by ID."""
    with engine.connect() as conn:
        query = """
            SELECT c.id, c.name, c.iso2, c.iso3, c.phonecode, c.capital,
                   c.currency, c.emoji, c.region, c.subregion,
                   c.latitude, c.longitude
            FROM countries c
            WHERE c.id = :country_id
        """
        result = conn.execute(text(query), {"country_id": country_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Country not found")
        
        return CountryResponse(**dict(row))


@router.get("/states", response_model=List[StateResponse])
async def get_states(
    country_id: Optional[int] = Query(None, description="Filter by country ID"),
    search: Optional[str] = Query(None, description="Search by state name"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get states/provinces with optional country filter."""
    with engine.connect() as conn:
        query = """
            SELECT s.id, s.name, s.country_id, s.country_code, s.latitude, s.longitude,
                   c.name as country_name
            FROM states s
            JOIN countries c ON s.country_id = c.id
            WHERE 1=1
        """
        params = {}
        
        if country_id:
            query += " AND s.country_id = :country_id"
            params["country_id"] = country_id
        
        if search:
            query += " AND s.name LIKE :search"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY s.name LIMIT :limit"
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        rows = result.mappings().all()
        
        return [StateResponse(**dict(row)) for row in rows]


@router.get("/states/{state_id}", response_model=StateResponse)
async def get_state(state_id: int):
    """Get a specific state by ID."""
    with engine.connect() as conn:
        query = """
            SELECT s.id, s.name, s.country_id, s.country_code, s.latitude, s.longitude,
                   c.name as country_name
            FROM states s
            JOIN countries c ON s.country_id = c.id
            WHERE s.id = :state_id
        """
        result = conn.execute(text(query), {"state_id": state_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="State not found")
        
        return StateResponse(**dict(row))


@router.get("/cities")
async def get_cities(
    country_id: Optional[int] = Query(None, description="Filter by country ID"),
    state_id: Optional[int] = Query(None, description="Filter by state ID"),
    search: Optional[str] = Query(None, description="Search by city name (min 2 chars)"),
    limit: int = Query(50, ge=1, le=200)
):
    """Get cities with optional filters."""
    with engine.connect() as conn:
        query = """
            SELECT c.id, c.name, c.state_id, c.state_code, c.country_id, c.country_code,
                   c.latitude, c.longitude, c.timezone, c.population,
                   s.name as state_name, co.name as country_name
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE 1=1
        """
        params = {}
        
        if country_id:
            query += " AND c.country_id = :country_id"
            params["country_id"] = country_id
        
        if state_id:
            query += " AND c.state_id = :state_id"
            params["state_id"] = state_id
        
        if search:
            if len(search) < 2:
                raise HTTPException(status_code=400, detail="Search term must be at least 2 characters")
            query += " AND c.name LIKE :search"
            params["search"] = f"%{search}%"
        
        # Order by population for better results when no search term
        if search:
            query += " ORDER BY c.population IS NULL, c.population DESC LIMIT :limit"
        else:
            query += " ORDER BY c.population IS NULL, c.population DESC LIMIT :limit"
        
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        rows = result.mappings().all()
        
        return [dict(row) for row in rows]


@router.get("/cities/{city_id}", response_model=CityResponse)
async def get_city(city_id: int):
    """Get a specific city by ID."""
    with engine.connect() as conn:
        query = """
            SELECT c.id, c.name, c.state_id, c.state_code, c.country_id, c.country_code,
                   c.latitude, c.longitude, c.timezone, c.population,
                   s.name as state_name, co.name as country_name
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE c.id = :city_id
        """
        result = conn.execute(text(query), {"city_id": city_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="City not found")
        
        return CityResponse(**dict(row))


@router.get("/search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(..., min_length=2, description="Search query (min 2 chars)"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search across cities, states, and countries."""
    search_term = f"%{q}%"
    cities = []
    states = []
    countries = []
    
    try:
        with engine.connect() as conn:
            # Search cities (may fail if table doesn't exist)
            try:
                city_query = """
                    SELECT c.id, c.name, c.state_id, c.state_code, c.country_id, c.country_code,
                           c.latitude, c.longitude, c.timezone, c.population,
                           s.name as state_name, co.name as country_name
                    FROM cities c
                    LEFT JOIN states s ON c.state_id = s.id
                    JOIN countries co ON c.country_id = co.id
                    WHERE c.name LIKE :search
                    ORDER BY c.population IS NULL, c.population DESC
                    LIMIT :limit
                """
                city_result = conn.execute(text(city_query), {"search": search_term, "limit": limit})
                cities = [CityResponse(**dict(row)) for row in city_result.mappings().all()]
            except Exception as e:
                # Cities table may not exist - gracefully continue without cities
                print(f"City search unavailable: {e}")
            
            # Search states
            try:
                state_query = """
                    SELECT s.id, s.name, s.country_id, s.country_code, s.latitude, s.longitude,
                           c.name as country_name
                    FROM states s
                    JOIN countries c ON s.country_id = c.id
                    WHERE s.name LIKE :search
                    ORDER BY s.name
                    LIMIT :limit
                """
                state_result = conn.execute(text(state_query), {"search": search_term, "limit": limit})
                states = [StateResponse(**dict(row)) for row in state_result.mappings().all()]
            except Exception as e:
                print(f"State search unavailable: {e}")
            
            # Search countries
            try:
                country_query = """
                    SELECT c.id, c.name, c.iso2, c.iso3, c.phonecode, c.capital,
                           c.currency, c.emoji, c.region, c.subregion,
                           c.latitude, c.longitude
                    FROM countries c
                    WHERE c.name LIKE :search
                    ORDER BY c.name
                    LIMIT :limit
                """
                country_result = conn.execute(text(country_query), {"search": search_term, "limit": limit})
                countries = [CountryResponse(**dict(row)) for row in country_result.mappings().all()]
            except Exception as e:
                print(f"Country search unavailable: {e}")
    except Exception as e:
        print(f"Location search error: {e}")
    
    return LocationSearchResponse(cities=cities, states=states, countries=countries)


@router.get("/nearby")
async def get_nearby_cities(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_km: float = Query(50, ge=1, le=500, description="Search radius in kilometers"),
    limit: int = Query(20, ge=1, le=100)
):
    """Find cities near given coordinates using Haversine formula."""
    with engine.connect() as conn:
        # Haversine formula to calculate distance
        query = """
            SELECT c.id, c.name, c.state_id, c.state_code, c.country_id, c.country_code,
                   c.latitude, c.longitude, c.timezone, c.population,
                   s.name as state_name, co.name as country_name,
                   (6371 * acos(
                       cos(radians(:lat)) * cos(radians(c.latitude)) *
                       cos(radians(c.longitude) - radians(:lng)) +
                       sin(radians(:lat)) * sin(radians(c.latitude))
                   )) AS distance
            FROM cities c
            LEFT JOIN states s ON c.state_id = s.id
            JOIN countries co ON c.country_id = co.id
            WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
            HAVING distance <= :radius
            ORDER BY distance
            LIMIT :limit
        """
        
        result = conn.execute(text(query), {
            "lat": lat,
            "lng": lng,
            "radius": radius_km,
            "limit": limit
        })
        rows = result.mappings().all()
        
        return [{
            **dict(row),
            "distance_km": round(row["distance"], 2)
        } for row in rows]


@router.get("/universities", response_model=List[UniversityResponse])
async def get_universities(
    country_id: Optional[int] = Query(None, description="Filter by country ID"),
    state_id: Optional[int] = Query(None, description="Filter by state ID"),
    search: Optional[str] = Query(None, description="Search by university name"),
    university_type: Optional[str] = Query(None, description="Filter by university type"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get universities with optional filters."""
    with engine.connect() as conn:
        query = """
            SELECT u.id, u.name, u.state_id, u.state_name, u.country_id,
                   u.university_type, u.established_year, u.website, u.email,
                   u.phone, u.latitude, u.longitude,
                   s.name as state_name, c.name as country_name
            FROM universities u
            LEFT JOIN states s ON u.state_id = s.id
            LEFT JOIN countries c ON u.country_id = c.id
            WHERE 1=1
        """
        params = {}
        
        if country_id:
            query += " AND u.country_id = :country_id"
            params["country_id"] = country_id
        
        if state_id:
            query += " AND u.state_id = :state_id"
            params["state_id"] = state_id
        
        if university_type:
            query += " AND u.university_type = :university_type"
            params["university_type"] = university_type
        
        if search:
            query += " AND u.name LIKE :search"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY u.name LIMIT :limit"
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        rows = result.mappings().all()
        
        return [UniversityResponse(**dict(row)) for row in rows]


@router.get("/universities/{university_id}", response_model=UniversityResponse)
async def get_university(university_id: int):
    """Get a specific university by ID."""
    with engine.connect() as conn:
        query = """
            SELECT u.id, u.name, u.state_id, u.state_name, u.country_id,
                   u.university_type, u.established_year, u.website, u.email,
                   u.phone, u.latitude, u.longitude,
                   s.name as state_name, c.name as country_name
            FROM universities u
            LEFT JOIN states s ON u.state_id = s.id
            LEFT JOIN countries c ON u.country_id = c.id
            WHERE u.id = :university_id
        """
        result = conn.execute(text(query), {"university_id": university_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="University not found")
        
        return UniversityResponse(**dict(row))


@router.get("/colleges", response_model=List[CollegeResponse])
async def get_colleges(
    university_id: Optional[int] = Query(None, description="Filter by university ID"),
    country_id: Optional[int] = Query(None, description="Filter by country ID"),
    state_id: Optional[int] = Query(None, description="Filter by state ID"),
    city_id: Optional[int] = Query(None, description="Filter by city ID"),
    search: Optional[str] = Query(None, description="Search by college name"),
    college_type: Optional[str] = Query(None, description="Filter by college type"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get colleges with optional filters."""
    with engine.connect() as conn:
        query = """
            SELECT col.id, col.name, col.university_id, col.university_name,
                   col.city_id, col.city_name, col.state_id, col.state_name,
                   col.country_id, col.college_type, col.established_year,
                   col.affiliation_number, col.website, col.email, col.phone,
                   col.address, col.latitude, col.longitude, col.accreditation_status,
                   u.name as university_name, c.name as city_name,
                   s.name as state_name, co.name as country_name
            FROM colleges col
            LEFT JOIN universities u ON col.university_id = u.id
            LEFT JOIN cities c ON col.city_id = c.id
            LEFT JOIN states s ON col.state_id = s.id
            LEFT JOIN countries co ON col.country_id = co.id
            WHERE 1=1
        """
        params = {}
        
        if university_id:
            query += " AND col.university_id = :university_id"
            params["university_id"] = university_id
        
        if country_id:
            query += " AND col.country_id = :country_id"
            params["country_id"] = country_id
        
        if state_id:
            query += " AND col.state_id = :state_id"
            params["state_id"] = state_id
        
        if city_id:
            query += " AND col.city_id = :city_id"
            params["city_id"] = city_id
        
        if college_type:
            query += " AND col.college_type = :college_type"
            params["college_type"] = college_type
        
        if search:
            query += " AND col.name LIKE :search"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY col.name LIMIT :limit"
        params["limit"] = limit
        
        result = conn.execute(text(query), params)
        rows = result.mappings().all()
        
        return [CollegeResponse(**dict(row)) for row in rows]


@router.get("/colleges/{college_id}", response_model=CollegeResponse)
async def get_college(college_id: int):
    """Get a specific college by ID."""
    with engine.connect() as conn:
        query = """
            SELECT col.id, col.name, col.university_id, col.university_name,
                   col.city_id, col.city_name, col.state_id, col.state_name,
                   col.country_id, col.college_type, col.established_year,
                   col.affiliation_number, col.website, col.email, col.phone,
                   col.address, col.latitude, col.longitude, col.accreditation_status,
                   u.name as university_name, c.name as city_name,
                   s.name as state_name, co.name as country_name
            FROM colleges col
            LEFT JOIN universities u ON col.university_id = u.id
            LEFT JOIN cities c ON col.city_id = c.id
            LEFT JOIN states s ON col.state_id = s.id
            LEFT JOIN countries co ON col.country_id = co.id
            WHERE col.id = :college_id
        """
        result = conn.execute(text(query), {"college_id": college_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="College not found")
        
        return CollegeResponse(**dict(row))
