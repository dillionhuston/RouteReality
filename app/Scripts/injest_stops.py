import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.Stop import Stop
from app.models.BusRoute import Route
from app.models.RouteStop import RouteStop 
from app.models.Database import engine, SessionLocal
from app.models.base import Base

def populate_stops():
 
    db = SessionLocal()
    try:
        csv_path = Path(__file__).parent / "stops.csv"
        print(f"Loading stops from: {csv_path}")
        
        stops_df = pd.read_csv(csv_path)
        
        stops_list = []
        for _, row in stops_df.iterrows():
            stop = Stop(
                id=row['AtcoCode'],
                name=row['CommonName'],
                latitude=float(row['Latitude']),  
                longitude=float(row['Longitude']),
            )
            stops_list.append(stop)
        
        # Bulk insert rather than inserting one by one
        db.bulk_save_objects(stops_list)
        db.commit()
        
        print(f"Added {len(stops_list)} stops!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_stops()