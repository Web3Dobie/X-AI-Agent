# job_definitions.py - Define and register all scheduled jobs  
import logging
from .registry import JobRegistry, JobCategory, JobPriority

# Import your job functions
from content.market_summary import post_market_summary_thread
from content.news_recap import post_news_thread
from content.random_post import post_random_content
from content.reply_handler import reply_to_comments
from content.ta_poster import post_ta_thread
from content.top_news_or_explainer import post_top_news_or_skip
from content.explainer_writer import generate_substack_explainer
from content.ta_substack_generator import generate_ta_substack_article
from crypto_news_bridge import generate_crypto_news_for_website
from utils import fetch_and_score_headlines, rotate_logs

logger = logging.getLogger(__name__)

def setup_all_jobs(job_registry: JobRegistry):
    """
    Register all jobs with the job registry system
    """
    
    # ===== DATA INGESTION JOBS =====
    job_registry.register_job(
        name="fetch_headlines",
        func=fetch_and_score_headlines,
        schedule_config={'type': 'hourly', 'minute': ':55'},
        category=JobCategory.DATA_INGESTION,
        priority=JobPriority.CRITICAL,
        description="Fetch and score cryptocurrency news headlines"
    )
    
    # ===== WEBSITE GENERATION JOBS =====
    job_registry.register_job(
        name="crypto_news_website",
        func=generate_crypto_news_for_website,
        schedule_config={'type': 'hourly', 'minute': ':15'},
        category=JobCategory.WEBSITE_GENERATION,
        priority=JobPriority.HIGH,
        description="Generate crypto news content for website",
        dependencies=["fetch_headlines"]  # Depends on fresh headlines
    )
    
    # ===== SOCIAL MEDIA POSTING JOBS =====
    
    # Daily news thread
    job_registry.register_job(
        name="news_thread",
        func=post_news_thread,
        schedule_config={'type': 'daily', 'time': '13:00'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.HIGH,
        description="Post daily news thread to social media",
        dependencies=["fetch_headlines"]
    )
    
    # Daily market summary
    job_registry.register_job(
        name="market_summary",
        func=post_market_summary_thread,
        schedule_config={'type': 'daily', 'time': '14:00'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.HIGH,
        description="Post daily market summary thread"
    )
    
    # Weekday TA threads (Monday-Friday at 16:00)
    job_registry.register_job(
        name="ta_thread_weekdays",
        func=post_ta_thread,
        schedule_config={'type': 'weekdays', 'time': '16:00'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.MEDIUM,
        description="Post technical analysis threads on weekdays"
    )
    
    # Evening top news
    job_registry.register_job(
        name="top_news_or_skip",
        func=post_top_news_or_skip,
        schedule_config={'type': 'daily', 'time': '23:45'},
        category=JobCategory.SOCIAL_POSTING,
        priority=JobPriority.MEDIUM,
        description="Post top news of the day or skip if no major news",
        dependencies=["fetch_headlines"]
    )
    
    # ===== CONTENT GENERATION JOBS =====
    
    # Weekly Substack explainer (Fridays)
    job_registry.register_job(
        name="substack_explainer",
        func=generate_substack_explainer,
        schedule_config={'type': 'weekly', 'day': 'friday', 'time': '23:45'},
        category=JobCategory.CONTENT_GENERATION,
        priority=JobPriority.MEDIUM,
        description="Generate weekly Substack explainer article"
    )
    
    # Weekly TA Substack article (Sundays)
    job_registry.register_job(
        name="ta_substack_article",
        func=generate_ta_substack_article,
        schedule_config={'type': 'weekly', 'day': 'sunday', 'time': '18:00'},
        category=JobCategory.CONTENT_GENERATION,
        priority=JobPriority.MEDIUM,
        description="Generate weekly technical analysis Substack article"
    )
    
    # ===== MAINTENANCE JOBS =====
    
    # Weekly log rotation (Sundays)
    job_registry.register_job(
        name="log_rotation",
        func=rotate_logs,
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
    """Print a nice summary of all registered jobs using logger"""
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