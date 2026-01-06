# services/stackoverflow_connector.py
"""
Connector Service für StackOverflow Daten in der Hauptdatenbank
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text, or_
from sqlalchemy.orm import Session
from langchain_core.documents import Document

from app.database import SOQuestion, SOAnswer, CollectionQuestion, CollectionConfiguration

logger = logging.getLogger(__name__)


class StackOverflowConnector:
    """Service für Zugriff auf StackOverflow Daten in der Hauptdatenbank"""

    def __init__(self, db: Session):
        """
        Initialize StackOverflow database connector

        Args:
            db: SQLAlchemy database session (injected via DI)
        """
        self.db = db

    def get_questions_with_answers(
            self,
            limit: int = 100,
            min_score: int = 0,
            tags: Optional[List[str]] = None,
            only_accepted_answers: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Holt Fragen mit ihren Antworten aus der StackOverflow DB

        Args:
            limit: Maximale Anzahl Fragen
            min_score: Minimum Score für Fragen
            tags: Liste von Tags zum Filtern (z.B. ["sql", "mysql"])
            only_accepted_answers: Nur Fragen mit akzeptierten Antworten

        Returns:
            Liste von Frage-Antwort Paaren
        """
        try:
            query = self.db.query(SOQuestion).join(
                SOAnswer,
                SOQuestion.stack_overflow_id == SOAnswer.question_stack_overflow_id
            )

            if min_score > 0:
                query = query.filter(SOQuestion.score >= min_score)

            if only_accepted_answers:
                query = query.filter(SOQuestion.accepted_answer_id.isnot(None))

            if tags:
                tag_conditions = [SOQuestion.tags.contains(tag) for tag in tags]
                if tag_conditions:
                    query = query.filter(or_(*tag_conditions))

            questions = query.distinct().limit(limit).all()

            results = []
            for question in questions:
                question_data = {
                    "stack_overflow_id": question.stack_overflow_id,
                    "title": question.title,
                    "body": question.body,
                    "tags": question.tags.split(",") if question.tags else [],
                    "score": question.score,
                    "view_count": question.view_count,
                    "creation_date": question.creation_date,
                    "owner_display_name": question.owner_display_name,
                    "answers": []
                }

                for answer in question.answers:
                    answer_data = {
                        "stack_overflow_id": answer.stack_overflow_id,
                        "body": answer.body,
                        "score": answer.score,
                        "is_accepted": answer.is_accepted,
                        "creation_date": answer.creation_date,
                        "owner_display_name": answer.owner_display_name
                    }
                    question_data["answers"].append(answer_data)

                results.append(question_data)

            logger.info(f"Retrieved {len(results)} questions with answers from StackOverflow DB")
            return results

        except Exception as e:
            logger.error(f"Error retrieving StackOverflow data: {e}")
            return []

    def get_questions_by_ids(self, question_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Holt spezifische Fragen nach IDs mit ihren Antworten

        Args:
            question_ids: Liste von Question IDs

        Returns:
            Liste von Frage-Antwort Paaren
        """
        if not question_ids:
            return []

        try:
            questions = self.db.query(SOQuestion).filter(
                SOQuestion.stack_overflow_id.in_(question_ids)
            ).all()

            results = []
            for question in questions:
                question_data = {
                    "stack_overflow_id": question.stack_overflow_id,
                    "title": question.title,
                    "body": question.body,
                    "tags": question.tags.split(",") if question.tags else [],
                    "score": question.score,
                    "view_count": question.view_count,
                    "creation_date": question.creation_date,
                    "owner_display_name": question.owner_display_name,
                    "answers": []
                }

                for answer in question.answers:
                    answer_data = {
                        "stack_overflow_id": answer.stack_overflow_id,
                        "body": answer.body,
                        "score": answer.score,
                        "is_accepted": answer.is_accepted,
                        "creation_date": answer.creation_date,
                        "owner_display_name": answer.owner_display_name
                    }
                    question_data["answers"].append(answer_data)

                results.append(question_data)

            logger.info(f"Retrieved {len(results)} questions by IDs from StackOverflow DB")
            return results

        except Exception as e:
            logger.error(f"Error retrieving StackOverflow questions by IDs: {e}")
            return []

    def convert_to_documents(
            self,
            qa_pairs: List[Dict[str, Any]],
            include_answers: bool = True,
            combine_qa: bool = True
    ) -> List[Document]:
        """
        Konvertiert StackOverflow Q&A zu LangChain Document Objekten
        Fix: Konvertiert Listen zu Strings für ChromaDB Kompatibilität
        """
        documents = []

        for qa in qa_pairs:
            if combine_qa and include_answers and qa["answers"]:
                best_answer = self._get_best_answer(qa["answers"])

                if best_answer:
                    content = f"""Frage: {qa['title']}

    {qa['body'] if qa['body'] else ''}

    Antwort: {best_answer['body']}"""

                    tags_str = ",".join(qa["tags"]) if qa["tags"] else ""

                    metadata = {
                        "source": "stackoverflow",
                        "type": "question_answer_pair",
                        "question_id": qa["stack_overflow_id"],
                        "answer_id": best_answer["stack_overflow_id"],
                        "question_score": qa["score"],
                        "answer_score": best_answer["score"],
                        "tags": tags_str,
                        "is_accepted_answer": best_answer["is_accepted"],
                        "view_count": qa["view_count"]
                    }

                    documents.append(Document(page_content=content, metadata=metadata))

            else:
                tags_str = ",".join(qa["tags"]) if qa["tags"] else ""

                question_content = f"""Frage: {qa['title']}

    {qa['body'] if qa['body'] else ''}"""

                question_metadata = {
                    "source": "stackoverflow",
                    "type": "question",
                    "question_id": qa["stack_overflow_id"],
                    "question_score": qa["score"],
                    "tags": tags_str,
                    "view_count": qa["view_count"]
                }

                documents.append(Document(page_content=question_content, metadata=question_metadata))

                if include_answers:
                    for answer in qa["answers"]:
                        answer_content = f"""Antwort zu: {qa['title']}

                        {answer['body']}"""

                        answer_metadata = {
                            "source": "stackoverflow",
                            "type": "answer",
                            "question_id": qa["stack_overflow_id"],
                            "answer_id": answer["stack_overflow_id"],
                            "question_title": qa["title"],
                            "answer_score": answer["score"],
                            "is_accepted": answer["is_accepted"],
                            "tags": tags_str
                        }

                        documents.append(Document(page_content=answer_content, metadata=answer_metadata))

        logger.info(f"Converted to {len(documents)} Document objects")
        return documents

    def _get_best_answer(self, answers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Findet die beste Antwort (akzeptiert oder höchster Score)"""
        if not answers:
            return None

        accepted_answers = [a for a in answers if a["is_accepted"]]
        if accepted_answers:
            return accepted_answers[0]

        return max(answers, key=lambda x: x["score"])

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Holt eine spezifische Frage mit Antworten

        Args:
            question_id: StackOverflow ID der Frage

        Returns:
            Question data with answers or None if not found
        """
        try:
            question = self.db.query(SOQuestion).filter(
                SOQuestion.stack_overflow_id == question_id
            ).first()

            if not question:
                return None

            question_data = {
                "stack_overflow_id": question.stack_overflow_id,
                "title": question.title,
                "body": question.body,
                "tags": question.tags.split(",") if question.tags else [],
                "score": question.score,
                "view_count": question.view_count,
                "creation_date": question.creation_date,
                "owner_display_name": question.owner_display_name,
                "answers": []
            }

            for answer in question.answers:
                answer_data = {
                    "stack_overflow_id": answer.stack_overflow_id,
                    "body": answer.body,
                    "score": answer.score,
                    "is_accepted": answer.is_accepted,
                    "creation_date": answer.creation_date,
                    "owner_display_name": answer.owner_display_name
                }
                question_data["answers"].append(answer_data)

            return question_data

        except Exception as e:
            logger.error(f"Error retrieving question {question_id}: {e}")
            return None

    def search_questions(
            self,
            search_term: str,
            limit: int = 10,
            min_score: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Sucht nach Fragen basierend auf Titel oder Body

        Args:
            search_term: Suchbegriff
            limit: Maximale Anzahl Ergebnisse
            min_score: Minimum Score

        Returns:
            Liste von matching Fragen
        """
        try:
            query = self.db.query(SOQuestion).filter(
                or_(
                    SOQuestion.title.contains(search_term),
                    SOQuestion.body.contains(search_term)
                )
            )

            if min_score > 0:
                query = query.filter(SOQuestion.score >= min_score)

            questions = query.order_by(SOQuestion.score.desc()).limit(limit).all()

            results = []
            for question in questions:
                question_data = {
                    "stack_overflow_id": question.stack_overflow_id,
                    "title": question.title,
                    "body": question.body,
                    "tags": question.tags.split(",") if question.tags else [],
                    "score": question.score,
                    "view_count": question.view_count,
                    "creation_date": question.creation_date,
                    "owner_display_name": question.owner_display_name,
                    "answers": []
                }

                for answer in question.answers:
                    answer_data = {
                        "stack_overflow_id": answer.stack_overflow_id,
                        "body": answer.body,
                        "score": answer.score,
                        "is_accepted": answer.is_accepted,
                        "creation_date": answer.creation_date,
                        "owner_display_name": answer.owner_display_name
                    }
                    question_data["answers"].append(answer_data)

                results.append(question_data)

            logger.info(f"Found {len(results)} questions matching '{search_term[:100]}'")
            return results

        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []

    def get_questions_paginated(
            self,
            page: int = 1,
            page_size: int = 20,
            tags: Optional[List[str]] = None,
            min_score: Optional[int] = None,
            sort_by: str = "creation_date",
            sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get questions paginated from database

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            tags: Filter by tags (OR logic)
            min_score: Minimum question score
            sort_by: Sort field (creation_date, score, view_count)
            sort_order: Sort order (asc, desc)

        Returns:
            Dict with items, total, page, page_size, total_pages, has_next, has_prev
        """
        try:
            query = self.db.query(SOQuestion)

            if tags:
                tag_conditions = [SOQuestion.tags.contains(tag) for tag in tags]
                query = query.filter(or_(*tag_conditions))

            if min_score is not None:
                query = query.filter(SOQuestion.score >= min_score)

            total = query.count()

            sort_column = getattr(SOQuestion, sort_by, SOQuestion.creation_date)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            offset = (page - 1) * page_size
            questions = query.offset(offset).limit(page_size).all()

            items = []
            for q in questions:
                items.append({
                    "id": q.stack_overflow_id,
                    "stack_overflow_id": q.stack_overflow_id,
                    "title": q.title,
                    "tags": q.tags.split(",") if q.tags else [],
                    "score": q.score,
                    "view_count": q.view_count,
                    "is_answered": q.is_answered,
                    "answer_count": len(q.answers),
                    "creation_date": q.creation_date,
                    "owner_display_name": q.owner_display_name
                })

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }

        except Exception as e:
            logger.error(f"Error getting paginated questions: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }

    def get_questions_with_collections(
            self,
            page: int = 1,
            page_size: int = 20,
            tags: Optional[List[str]] = None,
            min_score: Optional[int] = None,
            sort_by: str = "creation_date",
            sort_order: str = "desc",
            only_without_collections: bool = False
    ) -> Dict[str, Any]:
        """
        Get paginated questions with their collection membership info.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            tags: Filter by tags (OR logic)
            min_score: Minimum score threshold
            sort_by: Field to sort by (creation_date, score, view_count)
            sort_order: asc or desc
            only_without_collections: If True, only return questions not in any collection

        Returns:
            Dictionary with items (questions with collection info) and pagination metadata
        """
        try:
            from sqlalchemy import and_

            query = self.db.query(SOQuestion)

            if tags:
                tag_conditions = [SOQuestion.tags.contains(tag) for tag in tags]
                query = query.filter(or_(*tag_conditions))

            if min_score is not None:
                query = query.filter(SOQuestion.score >= min_score)

            if only_without_collections:
                in_collections_subquery = self.db.query(
                    CollectionQuestion.question_stack_overflow_id
                ).distinct()

                query = query.filter(
                    ~SOQuestion.stack_overflow_id.in_(in_collections_subquery)
                )

            total = query.count()

            sort_column = getattr(SOQuestion, sort_by, SOQuestion.creation_date)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            offset = (page - 1) * page_size
            questions = query.offset(offset).limit(page_size).all()

            items = []
            for q in questions:
                collections = self.db.query(
                    CollectionConfiguration
                ).join(
                    CollectionQuestion,
                    CollectionConfiguration.id == CollectionQuestion.collection_id
                ).filter(
                    CollectionQuestion.question_stack_overflow_id == q.stack_overflow_id
                ).all()

                collection_info = []
                for c in collections:
                    added_at = self.db.query(
                        CollectionQuestion.added_at
                    ).filter(
                        and_(
                            CollectionQuestion.collection_id == c.id,
                            CollectionQuestion.question_stack_overflow_id == q.stack_overflow_id
                        )
                    ).scalar()

                    collection_info.append({
                        "collection_id": c.id,
                        "collection_name": c.name,
                        "collection_type": c.collection_type,
                        "added_at": added_at.isoformat() if added_at else None
                    })

                items.append({
                    "id": q.stack_overflow_id,
                    "stack_overflow_id": q.stack_overflow_id,
                    "title": q.title,
                    "tags": q.tags.split(",") if q.tags else [],
                    "score": q.score,
                    "view_count": q.view_count,
                    "is_answered": q.is_answered,
                    "creation_date": q.creation_date,
                    "collections": collection_info
                })

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            logger.info(f"Retrieved {len(items)} questions with collections (page {page}/{total_pages})")

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }

        except Exception as e:
            logger.error(f"Error getting questions with collections: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }
