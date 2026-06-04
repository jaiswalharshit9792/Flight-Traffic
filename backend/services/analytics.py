from sqlalchemy.orm import Session
from sqlalchemy import text

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_stats(self):
        routes = self.db.execute(text("SELECT COUNT(*) FROM routes")).first()
        airports = self.db.execute(text("SELECT COUNT(*) FROM airports")).first()
        return {"total_routes": routes[0], "total_airports": airports[0]}
