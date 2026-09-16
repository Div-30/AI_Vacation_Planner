import logging
import sys
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.knowledge_base.pipeline import run_indexing_pipeline

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def scheduled_pipeline_run():
    logger.info("Scheduler triggered — starting indexing pipeline...")
    try:
        run_indexing_pipeline()
        logger.info("Scheduled pipeline run completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline run failed {e}")
if __name__ == "__main__":
    logger.info("Starting AI Vacation Planner — Knowledge Base Scheduler")
    logger.info("Pipeline will run automatically every Saturday at midnight.")
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func = scheduled_pipeline_run,
        trigger=CronTrigger(day_of_week="sat", hour=0, minute=0),
        id="knowledge_base_refresh",
        name="Weekly Knowledge Base Refresh",
        misfire_grace_time=3600
    )
    logger.info("Scheduler is running")
    try:
        scheduler.start()
    except(KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped gracefully.")