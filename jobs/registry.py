# job_registry.py - Enhanced Job Registry with Categories
import time
import threading
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, List, Callable, Optional, Any
from enum import Enum

# Set up logger for this module
logger = logging.getLogger(__name__)

class JobCategory(Enum):
    """Job categories for organization and monitoring"""
    DATA_INGESTION = "data_ingestion"
    CONTENT_GENERATION = "content_generation"
    SOCIAL_POSTING = "social_posting"
    WEBSITE_GENERATION = "website_generation"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"

class JobPriority(Enum):
    """Job priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class JobRegistry:
    """
    Centralized job registry with categorization, proper decoration handling, and monitoring
    """
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.job_stats: Dict[str, Dict] = {}
        self.categories: Dict[JobCategory, List[str]] = {cat: [] for cat in JobCategory}
        self._stats_lock = threading.RLock()
    
    def register_job(self, 
                    name: str, 
                    func: Callable, 
                    schedule_config: Dict[str, Any],
                    category: JobCategory,
                    priority: JobPriority = JobPriority.MEDIUM,
                    description: str = "",
                    dependencies: Optional[List[str]] = None,
                    **kwargs) -> Callable:
        """
        Register a job with the scheduler
        
        Args:
            name: Unique job name
            func: Function to execute
            schedule_config: Schedule configuration
            category: Job category
            priority: Job priority
            description: Human-readable description
            dependencies: List of job names this job depends on
            **kwargs: Additional metadata
        """
        if name in self.jobs:
            raise ValueError(f"Job '{name}' already registered")
        
        # Create properly wrapped job
        wrapped_job = self._create_wrapped_job(func, name, category, priority)
        
        # Store job info
        self.jobs[name] = {
            'function': wrapped_job,
            'original_function': func,
            'schedule_config': schedule_config,
            'category': category,
            'priority': priority,
            'description': description,
            'dependencies': dependencies or [],
            'metadata': kwargs,
            'registered_at': datetime.now(),
            'enabled': True
        }
        
        # Add to category
        self.categories[category].append(name)
        
        # Initialize stats
        with self._stats_lock:
            self.job_stats[name] = {
                'executions': 0,
                'failures': 0,
                'last_run': None,
                'last_success': None,
                'last_failure': None,
                'total_duration': 0,
                'average_duration': 0,
                'last_error': None
            }
        
        return wrapped_job
    
    def _create_wrapped_job(self, func: Callable, name: str, category: JobCategory, priority: JobPriority) -> Callable:
        """Create a properly wrapped job function with enhanced monitoring and database tracking"""
        
        # Import here to avoid circular imports
        from scheduler import telegram_job_wrapper, run_in_thread
        from services.database_service import DatabaseService
        
        @telegram_job_wrapper(name)
        @wraps(func)
        def job_wrapper():
            # Check if job is enabled
            if not self.jobs[name].get('enabled', True):
                logger.info(f"⏸️ Job {name} is disabled, skipping")
                return None
            
            # Check dependencies
            if not self._check_dependencies(name):
                logger.warning(f"⚠️ Job {name} dependencies not met, skipping")
                return None
            
            # Initialize database service
            db_service = DatabaseService()
            execution_id = None
            start_time = time.time()
            
            # Start database tracking
            try:
                execution_id = db_service.start_job_execution(
                    job_name=name,
                    category=category.value,
                    metadata={
                        'priority': priority.value,
                        'description': self.jobs[name].get('description', '')
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to start database tracking for {name}: {e}")
                # Continue execution even if tracking fails
            
            try:
                # Execute the actual function
                logger.info(f"🚀 Starting job: {name}")
                result = func()
                duration = time.time() - start_time
                
                # Update in-memory stats (backward compatibility)
                self._update_success_stats(name, duration)
                
                # Complete database tracking
                if execution_id:
                    try:
                        db_service.complete_job_execution(
                            execution_id=execution_id,
                            status='success',
                            duration_seconds=duration
                        )
                    except Exception as e:
                        logger.warning(f"Failed to complete database tracking for {name}: {e}")
                
                logger.info(f"✅ Job {name} completed successfully in {duration:.2f}s")
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Update in-memory stats (backward compatibility)
                self._update_failure_stats(name, duration, str(e))
                
                # Get full traceback for database
                import traceback
                error_traceback = traceback.format_exc()
                
                # Complete database tracking with failure
                if execution_id:
                    try:
                        db_service.complete_job_execution(
                            execution_id=execution_id,
                            status='failed',
                            error_message=str(e),
                            error_traceback=error_traceback,
                            duration_seconds=duration
                        )
                    except Exception as db_error:
                        logger.warning(f"Failed to complete database tracking for {name}: {db_error}")
                
                logger.error(f"❌ Job {name} failed after {duration:.2f}s: {str(e)}")
                logger.debug(f"Full traceback:\n{error_traceback}")
                
                # Don't re-raise to allow other jobs to continue
                return None
        
        return job_wrapper
    
    def _check_dependencies(self, job_name: str) -> bool:
        """Check if job dependencies have been met"""
        job_info = self.jobs[job_name]
        dependencies = job_info.get('dependencies', [])
        
        if not dependencies:
            return True
        
        with self._stats_lock:
            for dep_name in dependencies:
                dep_stats = self.job_stats.get(dep_name)
                if not dep_stats:
                    logger.warning(f"Dependency {dep_name} not found for job {job_name}")
                    return False
                
                # Check if dependency ran successfully recently (within last 2 hours)
                last_success = dep_stats.get('last_success')
                if not last_success or (time.time() - last_success) > 7200:
                    logger.warning(f"Dependency {dep_name} hasn't run successfully recently")
                    return False
        
        return True
    
    def _update_success_stats(self, job_name: str, duration: float):
        """Update job statistics after successful execution"""
        with self._stats_lock:
            stats = self.job_stats[job_name]
            stats['executions'] += 1
            stats['last_run'] = time.time()
            stats['last_success'] = time.time()
            stats['total_duration'] += duration
            stats['average_duration'] = stats['total_duration'] / stats['executions']
    
    def _update_failure_stats(self, job_name: str, duration: float, error: str):
        """Update job statistics after failed execution"""
        with self._stats_lock:
            stats = self.job_stats[job_name]
            stats['executions'] += 1
            stats['failures'] += 1
            stats['last_run'] = time.time()
            stats['last_failure'] = time.time()
            stats['last_error'] = error
            stats['total_duration'] += duration
            stats['average_duration'] = stats['total_duration'] / stats['executions']
    
    def schedule_all_jobs(self, scheduler):
        """Schedule all registered and enabled jobs"""
        scheduled_count = 0
        
        for name, job_info in self.jobs.items():
            if not job_info.get('enabled', True):
                logger.info(f"⏸️ Skipping disabled job: {name}")
                continue
            
            config = job_info['schedule_config']
            wrapped_func = job_info['function']
            
            try:
                self._apply_schedule(scheduler, config, wrapped_func, name)
                scheduled_count += 1
                logger.info(f"✅ Scheduled {job_info['category'].value} job: {name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to schedule job {name}: {e}")
        
        logger.info(f"📅 Scheduled {scheduled_count}/{len(self.jobs)} jobs")
        return scheduled_count
    
    def _apply_schedule(self, scheduler, config: Dict, func: Callable, job_name: str):
        """Apply schedule configuration to a job"""
        schedule_type = config['type']
        
        if schedule_type == 'hourly':
            scheduler.every().hour.at(config['minute']).do(self._run_in_thread, func)
            
        elif schedule_type == 'daily':
            scheduler.every().day.at(config['time']).do(self._run_in_thread, func)
            
        elif schedule_type == 'weekly':
            day_attr = getattr(scheduler.every(), config['day'].lower())
            day_attr.at(config['time']).do(self._run_in_thread, func)
            
        elif schedule_type == 'weekdays':
            # Special handling for weekday-only jobs
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                day_attr = getattr(scheduler.every(), day)
                day_attr.at(config['time']).do(self._run_in_thread, func)
                
        elif schedule_type == 'interval':
            interval_obj = scheduler.every(config['value'])
            unit_attr = getattr(interval_obj, config['unit'])
            unit_attr.do(func)  # No threading for frequent jobs like heartbeat
            
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
    
    def _run_in_thread(self, func: Callable):
        """Run job in a separate thread"""
        # Import here to avoid circular imports
        from scheduler import run_in_thread
        run_in_thread(func)()
    
    def get_category_jobs(self, category: JobCategory) -> List[str]:
        """Get all jobs in a specific category"""
        return self.categories.get(category, [])
    
    def get_job_stats(self, job_name: str) -> Optional[Dict]:
        """Get statistics for a specific job"""
        with self._stats_lock:
            return self.job_stats.get(job_name, {}).copy()
    
    def get_category_stats(self, category: JobCategory) -> Dict:
        """Get aggregated statistics for a job category"""
        category_jobs = self.get_category_jobs(category)
        
        if not category_jobs:
            return {}
        
        with self._stats_lock:
            total_executions = sum(self.job_stats[job]['executions'] for job in category_jobs)
            total_failures = sum(self.job_stats[job]['failures'] for job in category_jobs)
            
            return {
                'total_jobs': len(category_jobs),
                'total_executions': total_executions,
                'total_failures': total_failures,
                'success_rate': ((total_executions - total_failures) / total_executions * 100) if total_executions > 0 else 0,
                'jobs': category_jobs
            }
    
    def enable_job(self, job_name: str):
        """Enable a job"""
        if job_name in self.jobs:
            self.jobs[job_name]['enabled'] = True
            logger.info(f"✅ Enabled job: {job_name}")
        else:
            logger.warning(f"Job not found: {job_name}")
    
    def disable_job(self, job_name: str):
        """Disable a job"""
        if job_name in self.jobs:
            self.jobs[job_name]['enabled'] = False
            logger.info(f"⏸️ Disabled job: {job_name}")
        else:
            logger.warning(f"Job not found: {job_name}")
    
    def list_jobs(self, category: Optional[JobCategory] = None) -> List[Dict]:
        """List all jobs or jobs in a specific category"""
        if category:
            job_names = self.get_category_jobs(category)
        else:
            job_names = list(self.jobs.keys())
        
        result = []
        for name in job_names:
            job_info = self.jobs[name]
            stats = self.get_job_stats(name)
            
            result.append({
                'name': name,
                'category': job_info['category'].value,
                'priority': job_info['priority'].value,
                'description': job_info['description'],
                'enabled': job_info['enabled'],
                'schedule': job_info['schedule_config'],
                'stats': stats
            })
        
        return result