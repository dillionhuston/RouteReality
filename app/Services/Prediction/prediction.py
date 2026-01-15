"""I know the name "preduiction is vague, this will all probaly need renamed beofre prod release

    Again some code is unfinished and some is skeleton. Baby steps...


"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.Journey import Journey

class PredictionService():
    def  __init__(self):
        pass


    def predict_journey(db: Session, route_id: str, start_time: timedelta):
        
        completed_journeys = db.query(Journey).filter(
            Journey.status =="STOP_REACHED",
            Journey.route_id == route_id,
            Journey.end_time.isnot(None),
            Journey.start_time.isnot(None)
        ).all()


        # This is the simplest/accurate way od predicting using averages
        # This is not the final version. Dont worry,

        durations = [(Journey.end_time - Journey.start_time).total_seconds()for j in completed_journeys]
        avrg_duration = sum(durations)/len(durations) if durations else 30*60 #fallback 30 mins, unrealistic i know


        predicted_arrival = start_time + timedelta(seconds=avrg_duration)
        predicted_status = "on_time"
        if durations and max(durations) > avrg_duration * 1.2:
            predicted_status = "DELAYED"

        return predicted_status, predicted_arrival