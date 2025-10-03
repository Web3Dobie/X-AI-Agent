# job_definitions.py - Define and register all scheduled jobs with proper logging
import logging
from datetime import datetime
from .registry import JobRegistry, JobCategory, JobPriority

# Import your job functions
# from content.reply_handler import reply_to_comments
from jobs.maintenance import run_weekly_maintenance_job
from jobs.data_ingestion import run_headline_ingestion_job
from jobs.market_summary import run_market_summary_job
from jobs.news_recap import run_news_thread_job
from jobs.opinion_thread import run_opinion_thread_job
from jobs.random_post import run_random_post_job
from jobs.ta_thread import run_ta_thread_job
from jobs.explainer_thread import run_explainer_thread_job
from jobs.ta_article import run_ta_article_job

logger = logging.getLogger(__name__)

def run_daily_ta_thread_wrapper():
    """Determines which token to analyze based on the day of the week."""
    # Monday=0, Tuesday=1, ..., Friday=4
    weekday = datetime.utcnow().weekday()
    token_map = {
        0: "BTC", # Monday
        1: "ETH", # Tuesday
        2: "SOL", # Wednesday
        3: "XRP", # Thursday
        4: "DOGE"  # Friday
    }
    token_to_analyze = token_map.get(weekday)
    if token_to_analyze:
        run_ta_thread_job(token_to_analyze)
    else:
        logging.info("Not a weekday for TA threads. Skipping.")


def setup_all_jobs(job_registry: JobRegistry):
    """
    Register all jobs with the job registry system
    """
    
    # ===== DATA INGESTION JOBS =====
    job_registry.register_job(
        name="fetch_headlines",
        func=run_headline_ingestion_job,
        schedule_config={'type': 'hourly', 'minute': ':55'},
        category=JobCategory.DATA_INGESTION,
        priority=JobPriority.CRITICAL,
        description="Fetch and score cryptocurrency news headlines"
    )
    
    # ===== SOCIAL MEDIA POSTING JOBS =====
    
    # Daily news thread
    job_registry.register_job(
        name="news_thread",
        func=run_news_thread_job,
        schedule_config={'type': 'daily', 'time': '13:00'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.HIGH,
        description="Post daily news thread to social media",
        dependencies=["fetch_headlines"]
    )
    
    # Daily market summary
    job_registry.register_job(
        name="market_summary",
        func=run_market_summary_job,
        schedule_config={'type': 'daily', 'time': '14:00'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.HIGH,
        description="Post daily market summary thread"
    )
    
    # Weekday TA threads (Monday-Friday at 16:00)
    job_registry.register_job(
    name="ta_thread_weekdays",
    func=run_daily_ta_thread_wrapper,
    schedule_config={'type': 'weekdays', 'time': '16:00'},
    category=JobCategory.SOCIAL_POSTING,
    priority=JobPriority.MEDIUM,
    description="Post technical analysis threads on weekdays"
    )
    
    # Evening top news
    for day in ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
        job_registry.register_job(
            name=f"opinion_thread_{day}",
            func=run_opinion_thread_job,
            schedule_config={'type': 'weekly', 'day': day, 'time': '23:45'}, # Uses the supported 'weekly' type
            category=JobCategory.SOCIAL_POSTING,
            priority=JobPriority.MEDIUM,
            description=f"Posts 'Hunter Reacts' opinion thread on {day.capitalize()}."
        )

    # Hunter Explainer on Fridays
    job_registry.register_job(
        name="explainer_thread_weekly", # Renamed from "substack_explainer" for clarity
        func=run_explainer_thread_job,
        schedule_config={'type': 'weekly', 'day': 'friday', 'time': '23:45'},
        category=JobCategory.CONTENT_GENERATION,
        priority=JobPriority.MEDIUM,
        description="Generate weekly explainer thread from the week's top headline"
    )

    # ===== WEEKEND ENGAGEMENT JOBS =====
    # We now create separate jobs for Saturday and Sunday for each time slot.
    for day in ['saturday', 'sunday']:
        job_registry.register_job(
            name=f"random_post_{day}_morning",
            func=run_random_post_job,
            schedule_config={'type': 'weekly', 'day': day, 'time': '10:00'}, # Uses 'weekly' type
            category=JobCategory.SOCIAL_POSTING,
            priority=JobPriority.LOW,
            description=f"Posts random engagement content on {day.capitalize()} morning."
        )
        job_registry.register_job(
            name=f"random_post_{day}_afternoon",
            func=run_random_post_job,
            schedule_config={'type': 'weekly', 'day': day, 'time': '17:00'}, # Uses 'weekly' type
            category=JobCategory.SOCIAL_POSTING,
            priority=JobPriority.LOW,
            description=f"Posts random engagement content on {day.capitalize()} afternoon."
        )
        job_registry.register_job(
            name=f"random_post_{day}_evening",
            func=run_random_post_job,
            schedule_config={'type': 'weekly', 'day': day, 'time': '21:00'}, # Uses 'weekly' type
            category=JobCategory.SOCIAL_POSTING,
            priority=JobPriority.LOW,
            description=f"Posts random engagement content on {day.capitalize()} evening."
        )
    
    # ===== CONTENT GENERATION JOBS =====
    
    # Weekly TA Substack article (Sundays)
    job_registry.register_job(
        name="ta_substack_article",
        func=run_ta_article_job,
        schedule_config={'type': 'weekly', 'day': 'sunday', 'time': '18:00'},
        category=JobCategory.CONTENT_GENERATION,
        priority=JobPriority.MEDIUM,
        description="Generate weekly technical analysis Substack article"
    )
    
    # ===== MAINTENANCE JOBS =====
    
    # Weekly log rotation (Sundays)
    job_registry.register_job(
        name="log_rotation",
        func=run_weekly_maintenance_job,
        schedule_config={'type': 'weekly', 'day': 'sunday', 'time': '23:50'},
        category=JobCategory.MAINTENANCE,
        priority=JobPriority.LOW,
        description="Rotate and archive log files"
    )
    
    # ===== MONITORING JOBS =====
    
    # System heartbeat (every 15 minutes)
    # Note: This will be added separately in the main scheduler
    # since it uses a different function from the scheduler module
    
    logger.info("✅ All jobs registered successfully")
    
    # Print summary by category
    for category in JobCategory:
        jobs = job_registry.get_category_jobs(category)
        if jobs:
            logger.info(f"📁 {category.value.title()}: {len(jobs)} jobs - {', '.join(jobs)}")

def print_job_summary(job_registry: JobRegistry):
    """FIXED: Print a nice summary of all registered jobs using logger instead of print"""
    logger.info("="*80)
    logger.info("🔧 JOB REGISTRY SUMMARY")
    logger.info("="*80)
    
    total_jobs = len(job_registry.jobs)
    enabled_jobs = sum(1 for job in job_registry.jobs.values() if job['enabled'])
    
    logger.info(f"📊 Total Jobs: {total_jobs} | Enabled: {enabled_jobs} | Disabled: {total_jobs - enabled_jobs}")
    
    for category in JobCategory:
        jobs = job_registry.get_category_jobs(category)
        if not jobs:
            continue
            
        logger.info(f"📁 {category.value.upper().replace('_', ' ')}")
        logger.info("-" * 40)
        
        for job_name in jobs:
            job_info = job_registry.jobs[job_name]
            schedule = job_info['schedule_config']
            status = "✅" if job_info['enabled'] else "⏸️"
            
            # Format schedule info
            if schedule['type'] == 'hourly':
                schedule_str = f"Every hour at {schedule['minute']}"
            elif schedule['type'] == 'daily':
                schedule_str = f"Daily at {schedule['time']}"
            elif schedule['type'] == 'weekly':
                schedule_str = f"Every {schedule['day']} at {schedule['time']}"
            elif schedule['type'] == 'weekdays':
                schedule_str = f"Weekdays at {schedule['time']}"
            elif schedule['type'] == 'interval':
                schedule_str = f"Every {schedule['value']} {schedule['unit']}"
            else:
                schedule_str = str(schedule)
            
            priority_emoji = {
                JobPriority.CRITICAL: "🔴",
                JobPriority.HIGH: "🟡", 
                JobPriority.MEDIUM: "🟢",
                JobPriority.LOW: "🔵"
            }
            
            logger.info(f"  {status} {job_name}")
            logger.info(f"     {priority_emoji[job_info['priority']]} {schedule_str}")
            if job_info['description']:
                logger.info(f"     💬 {job_info['description']}")
            if job_info['dependencies']:
                logger.info(f"     🔗 Depends on: {', '.join(job_info['dependencies'])}")
    
    logger.info("="*80)

# Example usage for testing
if __name__ == "__main__":
    # Test the job registry setup
    registry = JobRegistry()
    setup_all_jobs(registry)
    print_job_summary(registry)