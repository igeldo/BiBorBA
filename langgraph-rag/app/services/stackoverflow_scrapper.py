# app / services / stackoverflow_scraper.py
"""
Stack Overflow Scraper Service
Handles fetching and storing questions and answers from Stack Overflow API
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, SOQuestion, SOAnswer
from app.utils.text_cleaning import clean_html

logger = logging.getLogger(__name__)


class StackOverflowScraper:
    """Service for scraping Stack Overflow data"""

    BASE_URL = "https://api.stackexchange.com/2.3"

    API_TIMEOUT = 30  # seconds
    RATE_LIMIT_DELAY = 0.5  # seconds between requests
    RETRY_DELAY = 1.0  # seconds before retry after error

    def __init__(self):
        self.api_key = None  # API only needed if more then 300 request per day
        self.session = requests.Session()
        if self.api_key:
            logger.info("StackOverflow scraper initialized with API key (using main database)")
        else:
            logger.info("StackOverflow scraper initialized without API key (using main database, rate limits apply)")

    def _get_so_db(self) -> Session:
        """Get database session from main database"""
        return SessionLocal()

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make API request with error handling and rate limiting"""
        url = f"{self.BASE_URL}/{endpoint}"

        # Default parameters
        default_params = {
            "site": "stackoverflow",
            "order": "desc",
            "sort": "votes"
        }

        if self.api_key:
            default_params["key"] = self.api_key

        params = {**default_params, **params}

        try:
            response = self.session.get(url, params=params, timeout=self.API_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            if "quota_remaining" in data:
                logger.info(f"API Quota remaining: {data['quota_remaining']}")

            if "backoff" in data:
                backoff_seconds = data["backoff"]
                logger.warning(f"API backoff requested: {backoff_seconds} seconds")
                time.sleep(backoff_seconds)

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"items": [], "error": str(e)}

    def scrape_and_store(
            self,
            count: int = 100,
            days_back: int = 365,
            tags: Optional[List[str]] = None,
            min_score: int = 1,
            only_accepted_answers: bool = True,
            start_page: int = 1,
            job_id: Optional[str] = None,
            progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Scrape questions and answers from Stack Overflow and store in database

        Args:
            start_page: Start from this API page (for continuation of previous scraping jobs)

        Returns:
            Dictionary with statistics about the scraping job
        """

        logger.info(f"Starting scraping job {job_id}: count={count}, tags={tags}")

        from_date = datetime.utcnow() - timedelta(days=days_back)
        from_timestamp = int(from_date.timestamp())

        if not tags:
            tags = ["sql"]

        params = {
            "tagged": ";".join(tags),
            "fromdate": from_timestamp,
            "pagesize": min(count, 100),  # API limit is 100 per page
            "filter": "withbody",
            "min": min_score
        }

        if only_accepted_answers:
            params["accepted"] = True

        stats = {
            "questions_fetched": 0,
            "questions_stored": 0,
            "questions_skipped": 0,
            "answers_fetched": 0,
            "answers_stored": 0,
            "answers_skipped": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat()
        }

        db = self._get_so_db()

        try:
            questions_data = self._fetch_questions(params, count, only_accepted_answers, start_page)
            stats["questions_fetched"] = len(questions_data)

            if progress_callback:
                progress_callback({"questions_fetched": len(questions_data)})

            logger.info(f"Fetched {len(questions_data)} questions from API")

            question_ids = []
            questions_to_store = []
            for question_raw in questions_data:
                try:
                    question_data = self._parse_question_data(question_raw)
                    questions_to_store.append(question_data)

                    # Store question using ORM (handles UPSERT automatically)
                    stored_question = self._store_question_orm(db, question_data, stats)

                    if stored_question:
                        question_ids.append(question_data["stack_overflow_id"])
                        logger.debug(f"Stored question: {question_data['title'][:50]}...")

                        if progress_callback:
                            progress_callback({"questions_stored": stats["questions_stored"]})
                    else:
                        stats["questions_skipped"] += 1

                except Exception as e:
                    logger.error(f"Error processing question: {e}")
                    stats["errors"] += 1

            logger.info(f"Stored {stats['questions_stored']} questions")

            # Extract accepted_answer_ids from stored questions
            accepted_answer_ids = [
                q["accepted_answer_id"] for q in questions_to_store
                if q.get("accepted_answer_id")
            ]

            if accepted_answer_ids:
                logger.info(f"Found {len(accepted_answer_ids)} questions with accepted answers")

                # Fetch accepted answers specifically
                accepted_answers_data = self._fetch_accepted_answers(accepted_answer_ids)
                logger.info(f"Fetched {len(accepted_answers_data)} accepted answers from API")

                # Store accepted answers FIRST (before fetching all answers)
                for answer_raw in accepted_answers_data:
                    try:
                        answer_data = self._parse_answer_data(answer_raw)
                        self._store_answer_orm(db, answer_raw, answer_data, stats)

                        if progress_callback:
                            progress_callback({"answers_stored": stats["answers_stored"]})

                    except Exception as e:
                        logger.error(f"Error processing accepted answer: {e}")
                        stats["errors"] += 1

            # Fetch and store all other answers
            if question_ids:
                logger.info(f"Fetching answers for {len(question_ids)} questions")

                answers_data = self._fetch_answers(question_ids)
                stats["answers_fetched"] = len(answers_data)

                if progress_callback:
                    progress_callback({"answers_fetched": len(answers_data)})

                for answer_raw in answers_data:
                    try:
                        answer_data = self._parse_answer_data(answer_raw)
                        # Store answer using ORM (handles UPSERT automatically)
                        self._store_answer_orm(db, answer_raw, answer_data, stats)

                        if progress_callback:
                            progress_callback({"answers_stored": stats["answers_stored"]})

                    except Exception as e:
                        logger.error(f"Error processing answer: {e}")
                        stats["errors"] += 1

            stats["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Scraping job {job_id} completed: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Scraping job {job_id} failed: {e}")
            stats["error"] = str(e)
            stats["completed_at"] = datetime.utcnow().isoformat()
            raise

        finally:
            db.close()

    def _fetch_questions(
            self,
            params: Dict,
            count: int,
            only_accepted_answers: bool,
            start_page: int = 1
    ) -> List[Dict]:
        """Fetch questions from Stack Overflow API

        Args:
            start_page: Start from this page number (for batch continuation)
        """

        all_questions = []
        page = start_page
        pages_fetched = 0
        max_pages = 10  # Safety limit: max 10 pages per scraping job

        while len(all_questions) < count:
            params["page"] = page
            params["pagesize"] = min(100, count - len(all_questions))

            data = self._make_request("search/advanced", params)

            if "error" in data or not data.get("items"):
                logger.warning(f"No more questions available or API error")
                break

            questions = data["items"]

            all_questions.extend(questions)
            pages_fetched += 1

            logger.info(f"Fetched page {page}: {len(questions)} questions (total: {len(all_questions)})")

            # Check if we have more pages
            if not data.get("has_more", False):
                break

            page += 1
            time.sleep(self.RATE_LIMIT_DELAY)  # Rate limiting

            if pages_fetched >= max_pages:
                logger.warning(f"Reached page limit ({max_pages}). Fetched {len(all_questions)} of {count} requested questions.")
                break

        return all_questions[:count]

    def _fetch_answers(self, question_ids: List[int]) -> List[Dict]:
        """Fetch answers for given question IDs"""

        all_answers = []

        # Process in batches of 100 (API limit)
        for i in range(0, len(question_ids), 100):
            batch = question_ids[i:i + 100]
            ids_string = ";".join(map(str, batch))

            params = {
                "pagesize": 100,
                "filter": "withbody"
            }

            endpoint = f"questions/{ids_string}/answers"
            data = self._make_request(endpoint, params)

            if "error" not in data and data.get("items"):
                answers = data["items"]
                all_answers.extend(answers)
                logger.info(f"Fetched {len(answers)} answers for batch of {len(batch)} questions")

            if len(question_ids) > 100:
                time.sleep(self.RETRY_DELAY)  # Rate limiting between batches

        return all_answers

    def _parse_question_data(self, question_data: Dict) -> Dict:
        """Parse Stack Overflow API question data to database format"""
        return {
            "stack_overflow_id": question_data.get("question_id"),
            "title": question_data.get("title", ""),
            "body": clean_html(question_data.get("body", "")),
            "tags": ",".join(question_data.get("tags", [])),
            "score": question_data.get("score", 0),
            "view_count": question_data.get("view_count", 0),
            "creation_date": datetime.fromtimestamp(question_data.get("creation_date", 0)),
            "last_activity_date": datetime.fromtimestamp(question_data.get("last_activity_date", 0)),
            "owner_user_id": question_data.get("owner", {}).get("user_id"),
            "owner_display_name": question_data.get("owner", {}).get("display_name"),
            "is_answered": question_data.get("is_answered", False),
            "accepted_answer_id": question_data.get("accepted_answer_id")
        }

    def _parse_answer_data(self, answer_data: Dict) -> Dict:
        """Parse Stack Overflow API answer data to database format"""
        return {
            "stack_overflow_id": answer_data.get("answer_id"),
            "body": clean_html(answer_data.get("body", "")),
            "score": answer_data.get("score", 0),
            "creation_date": datetime.fromtimestamp(answer_data.get("creation_date", 0)),
            "last_activity_date": datetime.fromtimestamp(answer_data.get("last_activity_date", 0)),
            "owner_user_id": answer_data.get("owner", {}).get("user_id"),
            "owner_display_name": answer_data.get("owner", {}).get("display_name"),
            "is_accepted": answer_data.get("is_accepted", False)
        }

    def _fetch_accepted_answers(self, accepted_answer_ids: List[int]) -> List[Dict]:
        """Fetch specific accepted answers by their IDs

        Args:
            accepted_answer_ids: List of StackOverflow answer IDs

        Returns:
            List of answer data dicts from API
        """
        if not accepted_answer_ids:
            return []

        all_answers = []

        # Process in batches of 100 (API limit)
        for i in range(0, len(accepted_answer_ids), 100):
            batch = accepted_answer_ids[i:i + 100]
            ids_string = ";".join(map(str, batch))

            params = {
                "pagesize": 100,
                "filter": "withbody"
            }

            endpoint = f"answers/{ids_string}"
            data = self._make_request(endpoint, params)

            if "error" not in data and data.get("items"):
                answers = data["items"]
                all_answers.extend(answers)
                logger.info(f"Fetched {len(answers)} accepted answers for batch of {len(batch)} IDs")

            if len(accepted_answer_ids) > 100:
                time.sleep(self.RETRY_DELAY)  # Rate limiting between batches

        logger.info(f"Total accepted answers fetched: {len(all_answers)}")
        return all_answers

    def _store_question_orm(
        self,
        db: Session,
        question_data: Dict,
        stats: Dict
    ) -> Optional[SOQuestion]:
        """Store question using SQLAlchemy ORM with merge()

        Now works correctly because stack_overflow_id is PRIMARY KEY!

        Args:
            db: SQLAlchemy session
            question_data: Parsed question data
            stats: Statistics dict to update

        Returns:
            SOQuestion object if stored successfully, None otherwise
        """
        try:
            # Create question object
            question = SOQuestion(**question_data)

            # Merge: SQLAlchemy checks PRIMARY KEY (stack_overflow_id)
            # - If exists: UPDATE
            # - If new: INSERT
            merged_question = db.merge(question)
            db.commit()
            db.refresh(merged_question)

            stats["questions_stored"] += 1
            logger.debug(f"Stored question {merged_question.stack_overflow_id}")
            return merged_question

        except Exception as e:
            logger.error(f"Error storing question {question_data.get('stack_overflow_id')}: {e}")
            db.rollback()
            stats["errors"] += 1
            return None

    def _store_answer_orm(
        self,
        db: Session,
        answer_raw: Dict,
        answer_data: Dict,
        stats: Dict
    ) -> bool:
        """Store answer using SQLAlchemy ORM with merge()

        Now works correctly because stack_overflow_id is PRIMARY KEY!

        Args:
            db: SQLAlchemy session
            answer_raw: Raw API response dict
            answer_data: Parsed answer data
            stats: Statistics dict to update

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Find question using ORM
            question = db.query(SOQuestion).filter(
                SOQuestion.stack_overflow_id == answer_raw.get("question_id")
            ).first()

            if not question:
                logger.warning(
                    f"Question {answer_raw.get('question_id')} not found for "
                    f"answer {answer_data.get('stack_overflow_id')}"
                )
                stats["answers_skipped"] += 1
                return False

            # Create answer object with FK to question
            answer = SOAnswer(
                stack_overflow_id=answer_data["stack_overflow_id"],
                question_stack_overflow_id=question.stack_overflow_id,  # NEW FK name!
                body=answer_data["body"],
                score=answer_data["score"],
                creation_date=answer_data["creation_date"],
                last_activity_date=answer_data["last_activity_date"],
                owner_user_id=answer_data["owner_user_id"],
                owner_display_name=answer_data["owner_display_name"],
                is_accepted=answer_data["is_accepted"]
            )

            # Merge: SQLAlchemy checks PRIMARY KEY (stack_overflow_id)
            # - If exists: UPDATE
            # - If new: INSERT
            merged_answer = db.merge(answer)
            db.commit()
            db.refresh(merged_answer)

            stats["answers_stored"] += 1
            logger.debug(f"Stored answer {merged_answer.stack_overflow_id} for question {question.stack_overflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing answer {answer_data.get('stack_overflow_id')}: {e}")
            db.rollback()
            stats["errors"] += 1
            return False

    def test_api_connection(self) -> Dict[str, Any]:
        """Test Stack Overflow API connection"""

        try:
            params = {
                "pagesize": 1,
                "tagged": "sql"
            }

            data = self._make_request("questions", params)

            if "error" in data:
                return {
                    "success": False,
                    "error": data["error"]
                }

            return {
                "success": True,
                "quota_remaining": data.get("quota_remaining"),
                "result": f"Successfully fetched {len(data.get('items', []))} test question(s)"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get statistics about scraped data using ORM queries"""
        db = self._get_so_db()

        try:
            # Count queries using ORM
            total_questions = db.query(SOQuestion).count()
            total_answers = db.query(SOAnswer).count()
            accepted_answers = db.query(SOAnswer).filter(SOAnswer.is_accepted == True).count()

            # Recent activity (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_questions = db.query(SOQuestion).filter(
                SOQuestion.created_at >= seven_days_ago
            ).count()

            # Average scores using ORM
            avg_question_score = db.query(func.avg(SOQuestion.score)).scalar()
            avg_answer_score = db.query(func.avg(SOAnswer.score)).scalar()

            # Top tags - processed in Python to avoid PostgreSQL-specific functions
            top_tags_dict: Dict[str, int] = {}
            all_tags = db.query(SOQuestion.tags).filter(SOQuestion.tags.isnot(None)).all()

            for (tags,) in all_tags:
                if tags:
                    for tag in tags.split(','):
                        tag = tag.strip()
                        if tag:
                            top_tags_dict[tag] = top_tags_dict.get(tag, 0) + 1

            # Sort by count and take top 10
            top_tags = [
                {"tag": tag, "count": count}
                for tag, count in sorted(
                    top_tags_dict.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ]

            return {
                "total_questions": total_questions,
                "total_answers": total_answers,
                "accepted_answers": accepted_answers,
                "recent_questions_7d": recent_questions,
                "avg_question_score": float(avg_question_score or 0),
                "avg_answer_score": float(avg_answer_score or 0),
                "top_tags": top_tags,
                "database_url": "main_database"
            }

        except Exception as e:
            logger.error(f"Error getting scraping stats: {e}")
            return {"error": str(e)}

        finally:
            db.close()


# Global instance
_stackoverflow_scraper = None


def get_stackoverflow_scraper() -> StackOverflowScraper:
    """Get global Stack Overflow scraper instance"""
    global _stackoverflow_scraper
    if _stackoverflow_scraper is None:
        _stackoverflow_scraper = StackOverflowScraper()
    return _stackoverflow_scraper