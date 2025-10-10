# app/services/database_service.py

import logging
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import pool
from contextlib import contextmanager

try:
    from utils.config import DATABASE_CONFIG
except ImportError:
    logging.critical("Database configuration not found.")
    DATABASE_CONFIG = {}

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for all interactions with the PostgreSQL database."""
    _connection_pool = None

    def __init__(self):
        if not DatabaseService._connection_pool:
            if not DATABASE_CONFIG:
                raise ValueError("Database configuration is missing.")
            try:
                DatabaseService._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=2,
                    maxconn=30,
                    options="-c search_path=hunter_agent,public",
                    **DATABASE_CONFIG
                )
                logging.info("Database connection pool created successfully.")
            except psycopg2.OperationalError as e:
                logging.critical(f"Failed to create database connection pool: {e}")
                raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections - ensures proper release."""
        conn = self._connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO hunter_agent, public;")
            conn.commit()
            yield conn
        except Exception as e:
            logging.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            self._connection_pool.putconn(conn)

    def batch_insert_headlines(self, headlines_data):
        """
        Batch inserts a list of headlines into the database.
        
        Args:
            headlines_data (list of tuples): A list where each tuple is
                                             (headline, url, source, ticker, score, ai_provider).
        """
        if not headlines_data:
            return 0
            
        sql = """
            INSERT INTO hunter_agent.headlines (headline, url, source, ticker, score, ai_provider)
            VALUES %s
            ON CONFLICT (url) DO NOTHING;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    execute_values(cursor, sql, headlines_data, page_size=100)
                    inserted_count = cursor.rowcount
                conn.commit()
                logging.info(f"Batch insert complete. Inserted {inserted_count} new headlines.")
                return inserted_count
            except Exception as e:
                logging.error(f"Error during batch headline insert: {e}")
                conn.rollback()
                return 0

    def fetch_unscored_headlines(self, limit=100):
        """Fetches headlines from the database that have not yet been scored."""
        sql = "SELECT id, headline, ticker FROM hunter_agent.headlines WHERE score IS NULL LIMIT %s;"
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (limit,))
                    return cursor.fetchall()
            except Exception as e:
                logging.error(f"Error fetching unscored headlines: {e}")
                return []

    def batch_update_scores(self, scored_data):
        """
        Batch updates scores for multiple headlines.
        
        Args:
            scored_data (list of tuples): A list where each tuple is
                                          (score, ai_provider, headline_id).
        """
        if not scored_data:
            return 0
            
        sql = """
            UPDATE hunter_agent.headlines SET
                score = data.score,
                ai_provider = data.ai_provider
            FROM (VALUES %s) AS data(score, ai_provider, id)
            WHERE hunter_agent.headlines.id = data.id;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    execute_values(cursor, sql, scored_data, page_size=100)
                    updated_count = cursor.rowcount
                conn.commit()
                logging.info(f"Batch score update complete. Updated {updated_count} headlines.")
                return updated_count
            except Exception as e:
                logging.error(f"Error during batch score update: {e}")
                conn.rollback()
                return 0
  
    def get_top_headlines(self, count=3, days=1):
        """
        Fetches the top N highest-scoring, unused headlines from the last N days.
    
        Args:
            count (int): The number of headlines to fetch.
            days (int): How many days back to look for headlines.
        """
        sql = """
            SELECT id, headline, url FROM hunter_agent.headlines
            WHERE created_at >= NOW() - INTERVAL %s
            AND used_in_thread = FALSE
            AND score IS NOT NULL
            ORDER BY score DESC
            LIMIT %s;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (f'{days} days', count))
                    results = cursor.fetchall()
                    if results:
                        return [{"id": r[0], "headline": r[1], "url": r[2]} for r in results]
                    return []
            except Exception as e:
                logging.error(f"Error fetching top {count} headlines: {e}")
                return []

    def get_top_headline(self, days=1):
        """
        Fetches the single highest-scoring, unused headline from the last N days.
        This is a convenience wrapper around get_top_headlines() for jobs that need
        only one headline (e.g., opinion threads).
    
        Args:
            days (int): How many days back to look for headlines.
    
        Returns:
            dict or None: A dictionary with keys 'id', 'headline', 'url' if found,
                        otherwise None.
        """
        try:
            headlines = self.get_top_headlines(count=1, days=days)
        
            if headlines:
                logging.info(f"Retrieved top headline from last {days} day(s): ID {headlines[0]['id']}")
                return headlines[0]
            else:
                logging.warning(f"No unused headlines found in the last {days} day(s) for single headline fetch.")
                return None
            
        except Exception as e:
            logging.error(f"Error fetching top headline from last {days} day(s): {e}", exc_info=True)
            return None

    def mark_headline_as_used(self, headline_id: int):
        """
        Marks a headline as used in a thread to prevent reuse.
        
        Args:
            headline_id (int): The ID of the headline to mark as used.
        """
        sql = """
            UPDATE hunter_agent.headlines
            SET used_in_thread = TRUE
            WHERE id = %s;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (headline_id,))
                conn.commit()
                logging.info(f"Marked headline {headline_id} as used")
                return True
            except Exception as e:
                logging.error(f"Error marking headline {headline_id} as used: {e}")
                conn.rollback()
                return False

    def get_top_xrp_headline_for_today(self, threshold=7):
        """
        Fetches the highest-scoring, unused XRP headline from the last 24 hours.
        """
        sql = """
            SELECT id, headline, url FROM hunter_agent.headlines
            WHERE (headline ILIKE '%%XRP%%' OR ticker = 'XRP')
            AND created_at >= NOW() - INTERVAL '24 hours'
            AND used_in_thread = FALSE
            AND score >= %s
            ORDER BY score DESC
            LIMIT 1;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (threshold,))
                    result = cursor.fetchone()
                    if result:
                        return {"id": result[0], "headline": result[1], "url": result[2]}
                    return None
            except Exception as e:
                logging.error(f"Error fetching top XRP headline: {e}")
                return None

    def check_if_content_posted_today(self, content_type: str):
        """
        Checks the content_log to see if a specific type of content was posted today.
        This replaces the need for flag files.
        """
        sql = """
            SELECT 1 FROM hunter_agent.content_log
            WHERE content_type = %s
            AND created_at >= NOW() - INTERVAL '24 hours'
            LIMIT 1;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (content_type,))
                    return cursor.fetchone() is not None
            except Exception as e:
                logging.error(f"Error checking for recent content of type {content_type}: {e}")
                return False

    def get_latest_ta_for_token(self, token: str):
        """
        Fetches the most recent TA data entry for a given token to use as "memory".
        """
        sql = """
            SELECT close_price, rsi, ai_summary
            FROM hunter_agent.ta_data
            WHERE token = %s
            ORDER BY date DESC
            LIMIT 1;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (token.upper(),))
                    result = cursor.fetchone()
                    if result:
                        return {"close": result[0], "rsi": result[1], "gpt_summary": result[2]}
                    return None
            except Exception as e:
                logging.error(f"Error fetching latest TA for token {token}: {e}")
                return None

    def batch_upsert_ta_data(self, ta_entry_data: dict):
        """
        Inserts or updates a TA data entry for a specific token and date.
    
        Args:
            ta_entry_data (dict): Dictionary containing:
                - token: str (e.g., 'BTC', 'ETH')
                - date: str (ISO date)
                - close_price: float
                - sma_10: float
                - sma_50: float
                - sma_200: float
                - rsi: float
                - macd: float
                - macd_signal: float
                - ai_summary: str
                - ai_provider: str
        """
        sql = """
            INSERT INTO hunter_agent.ta_data 
            (token, date, close_price, sma_10, sma_50, sma_200, rsi, macd, macd_signal, ai_summary, ai_provider)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (token, date) 
            DO UPDATE SET
                close_price = EXCLUDED.close_price,
                sma_10 = EXCLUDED.sma_10,
                sma_50 = EXCLUDED.sma_50,
                sma_200 = EXCLUDED.sma_200,
                rsi = EXCLUDED.rsi,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                ai_summary = EXCLUDED.ai_summary,
                ai_provider = EXCLUDED.ai_provider;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        ta_entry_data.get('token', '').upper(),
                        ta_entry_data.get('date'),
                        ta_entry_data.get('close_price'),
                        ta_entry_data.get('sma_10'),
                        ta_entry_data.get('sma_50'),
                        ta_entry_data.get('sma_200'),
                        ta_entry_data.get('rsi'),
                        ta_entry_data.get('macd'),
                        ta_entry_data.get('macd_signal'),
                        ta_entry_data.get('ai_summary'),
                        ta_entry_data.get('ai_provider', 'gemini')
                    ))
                conn.commit()
                logging.info(f"Upserted TA data for {ta_entry_data.get('token')} on {ta_entry_data.get('date')}")
                return True
            except Exception as e:
                logging.error(f"Error upserting TA data: {e}")
                conn.rollback()
                return False

    def purge_old_records(self, table_name: str, days_to_keep: int):
        """
        Deletes records from a specified table that are older than N days.
    
        Args:
            table_name (str): The name of the table to clean (e.g., 'headlines').
            days_to_keep (int): How many days of recent data to keep.
        """
        if not table_name.isalnum():
            logging.error(f"Invalid table name provided for purging: {table_name}")
            return 0
        
        sql = f"""
            DELETE FROM hunter_agent.{table_name}
            WHERE created_at < NOW() - INTERVAL '%s days';
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (days_to_keep,))
                    deleted_count = cursor.rowcount
                conn.commit()
                logging.info(f"Purged {deleted_count} records older than {days_to_keep} days from '{table_name}'.")
                return deleted_count
            except Exception as e:
                logging.error(f"Error purging old records from {table_name}: {e}")
                conn.rollback()
                return 0

    def log_content(self, content_type: str, details: str, tweet_id: str = None, 
                    headline_id: int = None, ai_provider: str = None, notion_url: str = None):
        """
        Inserts a new record into the content_log table. This is the new
        primary logging mechanism for all generated content.
        """
        sql = """
            INSERT INTO hunter_agent.content_log
            (content_type, tweet_id, success, details, headline_id, ai_provider, notion_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        content_type,
                        tweet_id,
                        True,
                        details,
                        headline_id,
                        ai_provider,
                        notion_url
                    ))
                    log_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"Successfully logged content to content_log with ID: {log_id}")
                return log_id
            except Exception as e:
                logging.error(f"Error logging content to database: {e}")
                conn.rollback()
                return None

    def get_recent_headlines_for_display(self, count=4, hours=1):
        """
        Fetches the top N highest-scoring headlines from recent hours for display purposes.
        """
        sql = f"""
            SELECT id, headline, url FROM hunter_agent.headlines
            WHERE created_at >= NOW() - INTERVAL '{hours} hours'
            AND score IS NOT NULL
            ORDER BY score DESC, created_at DESC
            LIMIT %s;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (count,))
                    results = cursor.fetchall()
                    if results:
                        return [{"id": r[0], "headline": r[1], "url": r[2]} for r in results]
                    return []
            except Exception as e:
                logging.error(f"Error fetching recent headlines for display: {e}")
                return []

    # ========================================
    # Job execution tracking operations
    # ========================================

    def start_job_execution(self, job_name: str, category: str = None, metadata: dict = None):
        """
        Records the start of a job execution.
        Returns the execution_id for tracking.
        
        Args:
            job_name: Name of the job being executed
            category: Job category (from JobCategory enum)
            metadata: Optional dict of job-specific data
        
        Returns:
            int: execution_id if successful, None if failed
        """
        import json
        
        sql = """
            INSERT INTO hunter_agent.job_executions 
            (job_name, category, started_at, status, metadata)
            VALUES (%s, %s, NOW(), 'running', %s)
            RETURNING id;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        job_name,
                        category,
                        json.dumps(metadata) if metadata else None
                    ))
                    execution_id = cursor.fetchone()[0]
                conn.commit()
                logging.debug(f"Started job execution tracking: {job_name} (ID: {execution_id})")
                return execution_id
            except Exception as e:
                logging.error(f"Failed to start job execution tracking for {job_name}: {e}")
                conn.rollback()
                return None

    def complete_job_execution(self, execution_id: int, status: str, 
                            error_message: str = None, error_traceback: str = None,
                            duration_seconds: float = None, metadata: dict = None):
        """
        Updates a job execution record with completion details.
        
        Args:
            execution_id: ID returned from start_job_execution()
            status: 'success' or 'failed'
            error_message: Brief error description if failed
            error_traceback: Full traceback if failed
            duration_seconds: How long the job took
            metadata: Additional job-specific data to merge
        
        Returns:
            bool: True if successful, False if failed
        """
        import json
        
        sql = """
            UPDATE hunter_agent.job_executions
            SET completed_at = NOW(),
                status = %s,
                error_message = %s,
                error_traceback = %s,
                duration_seconds = %s,
                metadata = COALESCE(%s::jsonb, metadata)
            WHERE id = %s;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        status,
                        error_message,
                        error_traceback,
                        duration_seconds,
                        json.dumps(metadata) if metadata else None,
                        execution_id
                    ))
                conn.commit()
                logging.debug(f"Completed job execution tracking: ID {execution_id} - {status}")
                return True
            except Exception as e:
                logging.error(f"Failed to complete job execution tracking for ID {execution_id}: {e}")
                conn.rollback()
                return False

    def get_recent_job_executions(self, job_name: str = None, limit: int = 10, status: str = None):
        """
        Retrieves recent job executions, optionally filtered.
        
        Args:
            job_name: Filter by specific job name (optional)
            limit: Maximum number of results
            status: Filter by status: 'success', 'failed', 'running' (optional)
        
        Returns:
            list: List of tuples with job execution data
        """
        conditions = []
        params = []
        
        if job_name:
            conditions.append("job_name = %s")
            params.append(job_name)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
            SELECT id, job_name, category, started_at, completed_at, 
                status, duration_seconds, error_message
            FROM hunter_agent.job_executions
            {where_clause}
            ORDER BY started_at DESC
            LIMIT %s;
        """
        params.append(limit)
        
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchall()
            except Exception as e:
                logging.error(f"Failed to fetch job executions: {e}")
                return []

    def get_failed_jobs(self, hours: int = 24):
        """
        Get all failed job executions within the last N hours.
        Useful for monitoring and alerting.
        
        Args:
            hours: Look back this many hours
        
        Returns:
            list: List of tuples (id, job_name, started_at, error_message)
        """
        sql = """
            SELECT id, job_name, started_at, error_message
            FROM hunter_agent.job_executions
            WHERE status = 'failed'
            AND started_at >= NOW() - INTERVAL '%s hours'
            ORDER BY started_at DESC;
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (hours,))
                    return cursor.fetchall()
            except Exception as e:
                logging.error(f"Failed to fetch failed jobs: {e}")
                return []

    def get_job_statistics(self, job_name: str, days: int = 7):
        """
        Get success rate and performance stats for a specific job.
        
        Args:
            job_name: Name of the job to analyze
            days: Look back this many days
        
        Returns:
            dict: Statistics including success rate, avg duration, etc.
        """
        sql = """
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                AVG(duration_seconds) as avg_duration,
                MAX(duration_seconds) as max_duration,
                MIN(duration_seconds) as min_duration
            FROM hunter_agent.job_executions
            WHERE job_name = %s
            AND started_at >= NOW() - INTERVAL '%s days'
            AND status IN ('success', 'failed');
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (job_name, days))
                    result = cursor.fetchone()
                    if result and result[0] > 0:
                        total, success, avg_dur, max_dur, min_dur = result
                        return {
                            'total_runs': total,
                            'successful_runs': success,
                            'success_rate': round((success / total * 100), 2) if total > 0 else 0,
                            'avg_duration': round(float(avg_dur), 2) if avg_dur else 0,
                            'max_duration': round(float(max_dur), 2) if max_dur else 0,
                            'min_duration': round(float(min_dur), 2) if min_dur else 0
                        }
                    return None
            except Exception as e:
                logging.error(f"Failed to fetch job statistics for {job_name}: {e}")
                return None
    
    def check_connection(self):
        """
        Performs a simple query to verify that the database connection is live.
        Returns True if successful, False otherwise.
        """
        try:
            # Use the 'get_connection' context manager correctly
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
            return True
        except Exception as e:
            # The logger will now be correctly defined
            logger.error(f"Database health check failed: {e}")
            return False