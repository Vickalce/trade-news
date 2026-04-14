from apscheduler.schedulers.blocking import BlockingScheduler

from api.db.session import SessionLocal
from api.services.pipeline import run_ingestion_only, run_signal_pipeline



def scheduled_cycle() -> None:
    db = SessionLocal()
    try:
        run_ingestion_only(db)
        run_signal_pipeline(db, limit=20)
    finally:
        db.close()



def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(scheduled_cycle, "interval", minutes=5, id="trade_news_cycle", max_instances=1)
    scheduler.start()


if __name__ == "__main__":
    main()
