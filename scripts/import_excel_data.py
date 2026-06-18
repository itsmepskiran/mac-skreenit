"""
Import Excel data into MySQL database.
Run: python backend/scripts/import_excel_data.py
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text
import uuid
import unicodedata

EXCEL_PATH = "f:/Skreenit_App/database/dpts_dsgnts.xlsx"
COUNTRIES_PATH = "f:/Skreenit_App/database/Skreenit_Global_Countries.xlsx"
STATES_PATH = "f:/Skreenit_App/database/Skreenit_Global_States.xlsx"
CITIES_PATH = "f:/Skreenit_App/database/worldcities.xlsx"
UNIVERSITIES_PATH = "f:/Skreenit_App/database/Universities.xlsx"
COLLEGES_PATH = "f:/Skreenit_App/database/Colleges.xlsx"

def normalize_string(s):
    """Normalize string by removing diacritical marks."""
    if not s:
        return None
    # Normalize to NFD form (decompose characters) and remove combining marks
    normalized = unicodedata.normalize('NFD', str(s))
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn').lower()

def import_departments():
    """Import departments from Excel."""
    df = pd.read_excel(EXCEL_PATH, sheet_name='Departments')
    print(f"Found {len(df)} departments")
    
    with engine.connect() as conn:
        for _, row in df.iterrows():
            dept_id = str(row.get('Department ID', '')).strip()
            dept_name = str(row.get('Department Name', '')).strip()
            
            if not dept_name:
                continue
            
            # Generate UUID if not provided
            if not dept_id or dept_id == 'nan':
                dept_id = str(uuid.uuid4())
            
            # Create slug from name
            slug = dept_name.lower().replace(' ', '-').replace('&', 'and')
            
            try:
                conn.execute(text("""
                    INSERT INTO departments (id, name, slug, is_active, sort_order)
                    VALUES (:id, :name, :slug, TRUE, 0)
                    ON DUPLICATE KEY UPDATE name = :name, slug = :slug
                """), {"id": dept_id, "name": dept_name, "slug": slug})
                print(f"  ✓ {dept_name}")
            except Exception as e:
                print(f"  ✗ {dept_name}: {e}")
        
        conn.commit()
    print("Departments imported successfully!\n")

def import_designations():
    """Import designations/roles from Excel."""
    df = pd.read_excel(EXCEL_PATH, sheet_name='Designations')
    print(f"Found {len(df)} designations")
    
    with engine.connect() as conn:
        for _, row in df.iterrows():
            desig_id = str(row.get('Designation ID', '')).strip()
            dept_id = str(row.get('Department ID', '')).strip()
            level_val = row.get('Level', 0)
            
            # Handle level - could be string like 'E01' or integer
            if pd.notna(level_val):
                try:
                    level = int(level_val) if isinstance(level_val, (int, float)) else 0
                except (ValueError, TypeError):
                    level = 0
            else:
                level = 0
            
            desig_name = str(row.get('Designation Name', '')).strip()
            
            if not desig_name:
                continue
            
            # Generate UUID if not provided
            if not desig_id or desig_id == 'nan':
                desig_id = str(uuid.uuid4())
            
            # Create slug from name
            slug = desig_name.lower().replace(' ', '-').replace('&', 'and').replace('/', '-')
            
            # Handle department_id - could be None if not linked
            dept_fk = dept_id if dept_id and dept_id != 'nan' else None
            
            try:
                conn.execute(text("""
                    INSERT INTO roles (id, name, slug, department_id, level, is_active, sort_order)
                    VALUES (:id, :name, :slug, :dept_id, :level, TRUE, 0)
                    ON DUPLICATE KEY UPDATE name = :name, slug = :slug, level = :level
                """), {"id": desig_id, "name": desig_name, "slug": slug, "dept_id": dept_fk, "level": level})
                print(f"  ✓ {desig_name} (Level {level})")
            except Exception as e:
                print(f"  ✗ {desig_name}: {e}")
        
        conn.commit()
    print("Designations imported successfully!\n")

def import_countries():
    """Import countries from Excel."""
    df = pd.read_excel(COUNTRIES_PATH)
    print(f"Found {len(df)} countries")
    
    # Ensure proper encoding by converting to string with UTF-8
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.encode('utf-8', errors='ignore').str.decode('utf-8')
    
    # Create table if not exists
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS countries (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                iso2 VARCHAR(2),
                iso3 VARCHAR(3),
                phonecode VARCHAR(20),
                capital VARCHAR(100),
                currency VARCHAR(50),
                emoji VARCHAR(10),
                region VARCHAR(50),
                subregion VARCHAR(100),
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                INDEX idx_countries_name (name),
                INDEX idx_countries_iso2 (iso2)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        conn.commit()
    
    with engine.connect() as conn:
        count = 0
        for _, row in df.iterrows():
            name = str(row.get('Common Name', '')).strip()
            official_name = str(row.get('Official Name', '')).strip()
            iso2 = str(row.get('ISO Alpha-2', '')).strip()
            iso3 = str(row.get('ISO Alpha-3', '')).strip()
            continent = str(row.get('Continent', '')).strip()
            
            if not name or name == 'nan':
                continue
            
            # Skip invalid ISO codes
            if iso2 == 'nan' or len(iso2) != 2:
                iso2 = None
            if iso3 == 'nan' or len(iso3) != 3:
                iso3 = None
            if continent == 'nan':
                continent = None
            
            try:
                conn.execute(text("""
                    INSERT INTO countries (name, iso2, iso3, region)
                    VALUES (:name, :iso2, :iso3, :region)
                    ON DUPLICATE KEY UPDATE name = :name, region = :region
                """), {"name": name, "iso2": iso2, "iso3": iso3, "region": continent})
                count += 1
                if count % 50 == 0:
                    print(f"  Imported {count} countries...")
            except Exception as e:
                print(f"  ✗ {name}: {e}")
        
        conn.commit()
    print(f"Countries imported successfully! ({count} records)\n")

def import_states():
    """Import states from Excel."""
    df = pd.read_excel(STATES_PATH)
    print(f"Found {len(df)} states")
    
    # Create table if not exists
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS states (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                country_id INT,
                country_code VARCHAR(2),
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                INDEX idx_states_country (country_id),
                INDEX idx_states_name (name),
                FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        conn.commit()
    
    # Get country ISO to ID mapping
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, iso2 FROM countries WHERE iso2 IS NOT NULL"))
        country_map = {row.iso2: row.id for row in result}
    
    with engine.connect() as conn:
        count = 0
        for _, row in df.iterrows():
            country_name = str(row.get('Country', '')).strip()
            country_iso = str(row.get('Country ISO', '')).strip()
            state_name = str(row.get('State/Province Name', '')).strip()
            subdivision = str(row.get('Subdivision Code', '')).strip()
            
            if not state_name or state_name == 'nan':
                continue
            
            # Get country_id from ISO code
            country_id = country_map.get(country_iso if country_iso != 'nan' else None)
            
            if country_iso == 'nan':
                country_iso = None
            
            try:
                conn.execute(text("""
                    INSERT INTO states (name, country_id, country_code)
                    VALUES (:name, :country_id, :country_code)
                    ON DUPLICATE KEY UPDATE name = :name
                """), {"name": state_name, "country_id": country_id, "country_code": country_iso})
                count += 1
                if count % 500 == 0:
                    print(f"  Imported {count} states...")
            except Exception as e:
                print(f"  ✗ {state_name}: {e}")
        
        conn.commit()
    print(f"States imported successfully! ({count} records)\n")

def import_cities():
    """Import cities from worldcities.xlsx."""
    df = pd.read_excel(CITIES_PATH)
    print(f"Found {len(df)} cities")
    
    # Create table if not exists
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cities (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                state_id INT,
                state_code VARCHAR(10),
                country_id INT,
                country_code VARCHAR(2),
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                timezone VARCHAR(50),
                population INT,
                INDEX idx_cities_state (state_id),
                INDEX idx_cities_country (country_id),
                INDEX idx_cities_name (name),
                FOREIGN KEY (state_id) REFERENCES states(id) ON DELETE CASCADE,
                FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        conn.commit()
    
    # Get country ISO to ID mapping
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, iso2 FROM countries WHERE iso2 IS NOT NULL"))
        country_map = {row.iso2: row.id for row in result}
    
    # Get state name to ID mapping with normalization
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM states WHERE name IS NOT NULL"))
        state_map = {normalize_string(row.name): row.id for row in result}
    
    with engine.connect() as conn:
        count = 0
        for _, row in df.iterrows():
            city_name = str(row.get('city_ascii', '')).strip()
            admin_name = str(row.get('admin_name', '')).strip()
            country_iso = str(row.get('iso2', '')).strip()
            lat = row.get('lat')
            lng = row.get('lng')
            population = row.get('population')
            
            if not city_name or city_name == 'nan':
                continue
            
            # Get country_id from ISO code
            country_id = country_map.get(country_iso if country_iso != 'nan' else None)
            
            # Get state_id from admin_name (match by normalized state name)
            state_id = None
            if admin_name and admin_name != 'nan':
                state_id = state_map.get(normalize_string(admin_name))
            
            # Handle country_iso
            if country_iso == 'nan':
                country_iso = None
            
            # Handle population
            if pd.isna(population):
                population = None
            else:
                population = int(population)
            
            # Handle lat/lng
            if pd.isna(lat):
                lat = None
            if pd.isna(lng):
                lng = None
            
            try:
                conn.execute(text("""
                    INSERT INTO cities (name, state_id, country_id, country_code, latitude, longitude, population)
                    VALUES (:name, :state_id, :country_id, :country_code, :latitude, :longitude, :population)
                    ON DUPLICATE KEY UPDATE name = :name
                """), {
                    "name": city_name,
                    "state_id": state_id,
                    "country_id": country_id,
                    "country_code": country_iso,
                    "latitude": lat,
                    "longitude": lng,
                    "population": population
                })
                count += 1
                if count % 1000 == 0:
                    print(f"  Imported {count} cities...")
            except Exception as e:
                print(f"  ✗ {city_name}: {e}")
        
        conn.commit()
    print(f"Cities imported successfully! ({count} records)\n")

def import_universities():
    """Import universities from UGC Excel."""
    try:
        # UGC Excel has header in row 1 (skip row 0 which is a title row)
        df = pd.read_excel(UNIVERSITIES_PATH, header=1)
        print(f"Found {len(df)} universities")
        print(f"Columns: {list(df.columns)}")
    except FileNotFoundError:
        print(f"Universities file not found at {UNIVERSITIES_PATH}")
        return
    except Exception as e:
        print(f"Error reading universities file: {e}")
        return
    
    # Get country name to ID mapping
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM countries WHERE name IS NOT NULL"))
        country_name_map = {normalize_string(row.name): row.id for row in result}
    
    # Get state name to ID mapping with normalization (India country_id = 101)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, country_id FROM states WHERE name IS NOT NULL"))
        state_map = {}
        for row in result:
            key = f"{normalize_string(row.name)}_{row.country_id}"
            state_map[key] = row.id
    
    with engine.connect() as conn:
        count = 0
        for _, row in df.iterrows():
            # UGC Excel columns: Sr.No, Type, Name of the University, Address, Zip, state, Status
            university_name = str(row.get('Name of the University', '')).strip().strip('"')
            state_name = str(row.get('state', '')).strip()
            university_type = str(row.get('Type', '')).strip() if pd.notna(row.get('Type')) else None
            address = str(row.get('Address', '')).strip() if pd.notna(row.get('Address')) else None
            zip_code = str(row.get('Zip', '')).strip() if pd.notna(row.get('Zip')) else None
            status = str(row.get('Status', '')).strip() if pd.notna(row.get('Status')) else None
            
            if not university_name or university_name == 'nan':
                continue
            
            # All UGC universities are in India
            country_id = 105  # India (id in countries table)
            
            # Get state_id from state name and country_id
            state_id = None
            if state_name and state_name != 'nan':
                state_key = f"{normalize_string(state_name)}_{country_id}"
                state_id = state_map.get(state_key)
            
            # Clean up values
            if university_type == 'nan':
                university_type = None
            if address == 'nan':
                address = None
            if zip_code == 'nan':
                zip_code = None
            if status == 'nan':
                status = None
            
            try:
                conn.execute(text("""
                    INSERT INTO universities (name, state_id, state_name, country_id, university_type)
                    VALUES (:name, :state_id, :state_name, :country_id, :university_type)
                    ON DUPLICATE KEY UPDATE name = :name, state_id = :state_id, university_type = :university_type
                """), {
                    "name": university_name,
                    "state_id": state_id,
                    "state_name": state_name if state_name != 'nan' else None,
                    "country_id": country_id,
                    "university_type": university_type
                })
                count += 1
                if count % 100 == 0:
                    print(f"  Imported {count} universities...")
            except Exception as e:
                print(f"  ✗ {university_name}: {e}")
        
        conn.commit()
    print(f"Universities imported successfully! ({count} records)\n")

def import_colleges():
    """Import colleges from UGC Excel."""
    try:
        # UGC Excel has header in row 1 (skip row 0 which is a title row)
        df = pd.read_excel(COLLEGES_PATH, header=1)
        print(f"Found {len(df)} colleges")
        print(f"Columns: {list(df.columns)}")
    except FileNotFoundError:
        print(f"Colleges file not found at {COLLEGES_PATH}")
        return
    except Exception as e:
        print(f"Error reading colleges file: {e}")
        return
    
    # Get university name to ID mapping (with multiple match strategies)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM universities WHERE name IS NOT NULL"))
        university_map = {}
        for row in result:
            # Full name match
            university_map[normalize_string(row.name)] = row.id
            # Also match without trailing city (e.g. "University of Delhi, Delhi" -> "University of Delhi")
            name_parts = row.name.split(',')
            if len(name_parts) > 1:
                stripped = name_parts[0].strip()
                university_map[normalize_string(stripped)] = row.id
    
    # Get state name to ID mapping with normalization
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, country_id FROM states WHERE name IS NOT NULL"))
        state_map = {}
        for row in result:
            key = f"{normalize_string(row.name)}_{row.country_id}"
            state_map[key] = row.id
    
    with engine.connect() as conn:
        count = 0
        skip_count = 0
        for _, row in df.iterrows():
            # UGC Excel columns: (Sr.No), Name of the college, Affiliated To University,
            # College address, District, State, Status, Year of Estb., Teaching Upto,
            # Govt or Non Govt, Aided or Unaided
            college_name = str(row.get('Name of the college', '')).strip().strip('"')
            university_name = str(row.get('Affiliated To University', '')).strip().strip('"')
            address = str(row.get('College address', '')).strip() if pd.notna(row.get('College address')) else None
            district = str(row.get('District', '')).strip() if pd.notna(row.get('District')) else None
            state_name = str(row.get('State', '')).strip() if pd.notna(row.get('State')) else None
            status = str(row.get('Status', '')).strip() if pd.notna(row.get('Status')) else None
            established_year = row.get('Year of Estb.')
            teaching_upto = str(row.get('Teaching Upto', '')).strip() if pd.notna(row.get('Teaching Upto')) else None
            govt_or_non = str(row.get('Govt or Non Govt', '')).strip() if pd.notna(row.get('Govt or Non Govt')) else None
            aided_or_unaided = str(row.get('Aided or Unaided', '')).strip() if pd.notna(row.get('Aided or Unaided')) else None
            
            if not college_name or college_name == 'nan':
                skip_count += 1
                continue
            
            # Get university_id from university name (try multiple matching strategies)
            university_id = None
            if university_name and university_name != 'nan':
                # Try full match first
                university_id = university_map.get(normalize_string(university_name))
                # If no match, try stripping city suffix (e.g. "University of Mumbai, Mumbai" -> "University of Mumbai")
                if not university_id and ',' in university_name:
                    stripped_name = university_name.split(',')[0].strip()
                    university_id = university_map.get(normalize_string(stripped_name))
            
            # All UGC colleges are in India
            country_id = 105  # India (id in countries table)
            
            # Get state_id from state name and country_id
            state_id = None
            if state_name and state_name != 'nan':
                state_key = f"{normalize_string(state_name)}_{country_id}"
                state_id = state_map.get(state_key)
            
            # Combine Govt/Non-Govt and Aided/Unaided into college_type
            college_type_parts = []
            if govt_or_non and govt_or_non != 'nan':
                college_type_parts.append(govt_or_non)
            if aided_or_unaided and aided_or_unaided != 'nan':
                college_type_parts.append(aided_or_unaided)
            college_type = ' - '.join(college_type_parts) if college_type_parts else None
            
            # Handle established_year
            if pd.isna(established_year) or established_year == 'nan':
                established_year = None
            else:
                try:
                    established_year = int(float(established_year))
                except (ValueError, TypeError):
                    established_year = None
            
            # Clean up values
            if address == 'nan':
                address = None
            if district == 'nan':
                district = None
            if state_name == 'nan':
                state_name = None
            if status == 'nan':
                status = None
            if university_name == 'nan':
                university_name = None
            
            try:
                conn.execute(text("""
                    INSERT INTO colleges (name, university_id, university_name, city_name, state_id, state_name, country_id, college_type, established_year, address)
                    VALUES (:name, :university_id, :university_name, :city_name, :state_id, :state_name, :country_id, :college_type, :established_year, :address)
                    ON DUPLICATE KEY UPDATE name = :name, university_id = :university_id, college_type = :college_type
                """), {
                    "name": college_name,
                    "university_id": university_id,
                    "university_name": university_name,
                    "city_name": district,
                    "state_id": state_id,
                    "state_name": state_name,
                    "country_id": country_id,
                    "college_type": college_type,
                    "established_year": established_year,
                    "address": address
                })
                count += 1
                if count % 500 == 0:
                    print(f"  Imported {count} colleges...")
            except Exception as e:
                print(f"  ✗ {college_name}: {e}")

        conn.commit()
    print(f"Colleges imported successfully! ({count} records, {skip_count} skipped)\n")

def import_education_data():
    """Import universities and colleges from Excel."""
    print("=" * 50)
    print("Importing Education Data (Universities & Colleges)")
    print("=" * 50 + "\n")
    
    try:
        import_universities()
        import_colleges()
        print("Education data imported successfully!")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("=" * 50)
    print("Importing Excel Data to MySQL")
    print("=" * 50 + "\n")
    
    try:
        import_departments()
        import_designations()
        import_countries()
        import_states()
        import_cities()
        import_universities()
        import_colleges()
        print("All data imported successfully!")
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")

def import_only_countries():
    """Import only countries (for fixing encoding issues)."""
    print("=" * 50)
    print("Importing Countries Only (Encoding Fix)")
    print("=" * 50 + "\n")
    
    try:
        import_countries()
        print("Countries imported successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
