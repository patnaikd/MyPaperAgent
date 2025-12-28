"""Agent for gathering author background information from web sources."""
import json
import logging
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import requests

from src.agents.base import BaseAgent
from src.utils.database import Author, PaperAuthor, PaperSemanticScholar, get_session


logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1"
DBLP_AUTHOR_SEARCH_URL = "https://dblp.org/search/author/api"
SEMANTIC_SCHOLAR_PAPER_FIELDS = (
    "paperId,corpusId,externalIds,url,title,abstract,venue,publicationVenue,year,"
    "referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,"
    "fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationDate,journal,"
    "citationStyles,authors,citations,references,tldr,textAvailability"
)


class AuthorInfoAgent(BaseAgent):
    """Agent for collecting author information from public sources."""

    def __init__(self) -> None:
        super().__init__(temperature=0.2, max_tokens=512)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MyPaperAgent/1.0"})
        if self.config.semantic_scholar_api_key:
            self.session.headers.update({"x-api-key": self.config.semantic_scholar_api_key})

    def fetch_authors_info(self, authors: list[Any]) -> list[dict[str, Any]]:
        """Fetch author info in parallel for a list of author entries."""
        author_entries = self._normalize_authors(authors)
        if not author_entries:
            return []

        max_workers = 4 #min(4, len(author_entries))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            base_infos = list(executor.map(self._fetch_author_profile, author_entries))

        for info in base_infos:
            info["introduction"] = self._generate_introduction(info)

        return base_infos

    def fetch_paper_metadata(self, paper_id: str) -> Optional[dict[str, Any]]:
        """Fetch paper metadata from Semantic Scholar by ID (e.g., ARXIV:2106.15928)."""
        if not paper_id:
            return None

        logger.info("Requesting Semantic Scholar paper batch for %s", paper_id)
        response = self.session.post(
            f"{SEMANTIC_SCHOLAR_API_URL}/paper/batch",
            params={"fields": SEMANTIC_SCHOLAR_PAPER_FIELDS},
            json={"ids": [paper_id]},
            timeout=20,
        )
        self._log_response("Semantic Scholar paper batch", response)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or not data:
            return None
        paper = data[0]
        if isinstance(paper, dict) and paper.get("error"):
            return None
        return paper if isinstance(paper, dict) else None

    def store_paper_metadata(self, paper_id: int, paper_meta: dict[str, Any]) -> None:
        """Store raw Semantic Scholar paper metadata for a paper."""
        if not paper_id or not paper_meta:
            return

        session = get_session()
        try:
            payload = json.dumps(paper_meta, ensure_ascii=True)
            record = (
                session.query(PaperSemanticScholar)
                .filter(PaperSemanticScholar.paper_id == paper_id)
                .first()
            )
            if record:
                record.response_json = payload
            else:
                session.add(
                    PaperSemanticScholar(paper_id=paper_id, response_json=payload)
                )
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.warning(
                "Failed to store Semantic Scholar metadata for paper %s: %s",
                paper_id,
                exc,
            )
        finally:
            session.close()

    def store_author_infos(self, paper_id: int, author_infos: list[dict[str, Any]]) -> None:
        """Store author information and link to the paper."""
        if not paper_id or not author_infos:
            return

        session = get_session()
        try:
            stored_authors: list[Author] = []
            for info in author_infos:
                author = self._upsert_author(session, info)
                if author:
                    stored_authors.append(author)

            session.flush()
            session.query(PaperAuthor).filter(PaperAuthor.paper_id == paper_id).delete()
            for order, author in enumerate(stored_authors, start=1):
                session.add(
                    PaperAuthor(
                        paper_id=paper_id,
                        author_id=author.id,
                        author_order=order,
                    )
                )

            session.commit()
        except Exception as exc:
            session.rollback()
            logger.warning("Failed to store author info for paper %s: %s", paper_id, exc)
        finally:
            session.close()

    @staticmethod
    def load_paper_metadata_with_timestamp(
        paper_id: int,
    ) -> tuple[Optional[dict[str, Any]], Optional[datetime]]:
        if not paper_id:
            return None, None
        session = get_session()
        try:
            record = (
                session.query(PaperSemanticScholar)
                .filter(PaperSemanticScholar.paper_id == paper_id)
                .first()
            )
            if not record or not record.response_json:
                return None, None
            try:
                payload = json.loads(record.response_json)
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid JSON stored for paper %s Semantic Scholar metadata", paper_id
                )
                return None, None
            timestamp = record.updated_at or record.created_at
            return payload, timestamp
        finally:
            session.close()

    @staticmethod
    def load_paper_metadata_from_db(paper_id: int) -> Optional[dict[str, Any]]:
        payload, _timestamp = AuthorInfoAgent.load_paper_metadata_with_timestamp(paper_id)
        return payload

    @staticmethod
    def load_author_infos_with_timestamp(
        paper_id: int,
    ) -> tuple[list[dict[str, Any]], Optional[datetime]]:
        if not paper_id:
            return [], None
        session = get_session()
        try:
            rows = (
                session.query(Author, PaperAuthor)
                .join(PaperAuthor, Author.id == PaperAuthor.author_id)
                .filter(PaperAuthor.paper_id == paper_id)
                .order_by(
                    PaperAuthor.author_order.is_(None),
                    PaperAuthor.author_order,
                    PaperAuthor.id,
                )
                .all()
            )
            results: list[dict[str, Any]] = []
            timestamps: list[datetime] = []
            for author, link in rows:
                results.append(
                    {
                        "name": author.name,
                        "author_id": author.semantic_scholar_id,
                        "introduction": author.introduction,
                        "homepage": author.homepage,
                        "semantic_scholar_url": author.semantic_scholar_url,
                        "dblp_url": author.dblp_url,
                        "affiliation": author.affiliation,
                        "top_cited_papers": AuthorInfoAgent._parse_json(author.top_cited_papers),
                        "coauthors": AuthorInfoAgent._parse_json(author.coauthors),
                        "research_interests": AuthorInfoAgent._parse_json(
                            author.research_interests
                        ),
                        "sources": AuthorInfoAgent._parse_json(author.sources),
                        "error": author.error,
                    }
                )
                timestamps.append(author.updated_at or author.created_at)
            latest = max(timestamps) if timestamps else None
            return results, latest
        finally:
            session.close()

    @staticmethod
    def load_author_infos_from_db(paper_id: int) -> list[dict[str, Any]]:
        infos, _timestamp = AuthorInfoAgent.load_author_infos_with_timestamp(paper_id)
        return infos

    def _fetch_author_profile(self, author_entry: dict[str, Any]) -> dict[str, Any]:
        """Fetch author info from public APIs."""
        author_name = author_entry.get("name") or "Unknown author"
        author_id = author_entry.get("author_id")
        info: dict[str, Any] = {
            "name": author_name,
            "author_id": author_id,
            "introduction": "",
            "homepage": None,
            "semantic_scholar_url": None,
            "dblp_url": None,
            "affiliation": None,
            "top_cited_papers": [],
            "coauthors": [],
            "research_interests": [],
            "sources": [],
            "error": None,
        }

        try:
            semantic_info = None
            if author_id:
                semantic_info = self._fetch_semantic_scholar_by_id(author_id)
            if not semantic_info:
                semantic_info = self._fetch_semantic_scholar(author_name)
            if semantic_info:
                info.update(semantic_info)
                info["sources"].append("Semantic Scholar")

            dblp_url = self._fetch_dblp_url(author_name)
            if dblp_url:
                info["dblp_url"] = dblp_url
                info["sources"].append("DBLP")

        except Exception as exc:
            logger.warning("Failed to fetch author info for %s: %s", author_name, exc)
            info["error"] = str(exc)

        return info

    def _fetch_semantic_scholar(self, author_name: str) -> dict[str, Any]:
        """Fetch author details from Semantic Scholar using name search."""
        search_params = {
            "query": author_name,
            "limit": 1,
            "fields": "name,affiliations,homepage,url,paperCount,citationCount,hIndex",
        }
        search_response = self.session.get(
            f"{SEMANTIC_SCHOLAR_API_URL}/author/search",
            params=search_params,
            timeout=20,
        )
        self._log_response("Semantic Scholar author search", search_response)
        search_response.raise_for_status()
        search_data = search_response.json()
        matches = search_data.get("data", [])
        if not matches:
            return {}

        author_id = matches[0].get("authorId")
        if not author_id:
            return {}

        return self._fetch_semantic_scholar_by_id(author_id)

    def _fetch_semantic_scholar_by_id(self, author_id: str) -> dict[str, Any]:
        """Fetch author details from Semantic Scholar by ID."""
        detail_params = {
            "fields": (
                "name,affiliations,homepage,url,papers.title,papers.citationCount,papers.url,"
                "papers.year,papers.authors,papers.fieldsOfStudy"
            )
        }
        detail_response = self.session.get(
            f"{SEMANTIC_SCHOLAR_API_URL}/author/{author_id}",
            params=detail_params,
            timeout=20,
        )
        self._log_response("Semantic Scholar author detail", detail_response)
        detail_response.raise_for_status()
        detail = detail_response.json()

        papers = detail.get("papers", []) or []
        top_papers = self._extract_top_papers(papers)
        coauthors = self._extract_top_coauthors(papers, detail.get("name") or "")
        interests = self._extract_research_interests(papers)

        homepage = detail.get("homepage")
        if isinstance(homepage, list):
            homepage = homepage[0] if homepage else None

        affiliation = detail.get("affiliations")
        if isinstance(affiliation, list):
            affiliation = ", ".join([item for item in affiliation if item])

        semantic_url = detail.get("url") or self._build_semantic_scholar_url(author_id)

        return {
            "author_id": author_id,
            "homepage": homepage,
            "semantic_scholar_url": semantic_url,
            "affiliation": affiliation,
            "top_cited_papers": top_papers,
            "coauthors": coauthors,
            "research_interests": interests,
            "name": detail.get("name"),
        }

    def _fetch_dblp_url(self, author_name: str) -> Optional[str]:
        """Fetch the DBLP profile URL for an author."""
        params = {"q": author_name, "format": "json"}
        response = self.session.get(DBLP_AUTHOR_SEARCH_URL, params=params, timeout=20)
        self._log_response("DBLP author search", response)
        response.raise_for_status()
        data = response.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if not hits:
            return None
        hit = hits[0]
        if isinstance(hit, dict):
            info = hit.get("info", {})
            return info.get("url")
        return None

    def _extract_top_papers(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        papers_sorted = sorted(
            papers,
            key=lambda p: p.get("citationCount") or 0,
            reverse=True,
        )
        top_papers = []
        for paper in papers_sorted[:3]:
            title = paper.get("title")
            if not title:
                continue
            top_papers.append(
                {
                    "title": title,
                    "citation_count": paper.get("citationCount"),
                    "url": paper.get("url"),
                    "year": paper.get("year"),
                }
            )
        return top_papers

    def _extract_top_coauthors(self, papers: list[dict[str, Any]], author_name: str) -> list[str]:
        author_key = author_name.strip().lower()
        coauthor_counts: Counter[str] = Counter()
        for paper in papers[:20]:
            for author in paper.get("authors", []) or []:
                name = author.get("name")
                if not name:
                    continue
                if name.strip().lower() == author_key:
                    continue
                coauthor_counts[name] += 1
        return [name for name, _ in coauthor_counts.most_common(3)]

    def _extract_research_interests(self, papers: list[dict[str, Any]]) -> list[str]:
        interest_counts: Counter[str] = Counter()
        for paper in papers[:20]:
            fields = paper.get("fieldsOfStudy") or []
            for field in fields:
                if isinstance(field, str):
                    interest_counts[field] += 1
            topics = paper.get("topics") or []
            for topic in topics:
                if isinstance(topic, dict):
                    name = topic.get("topic") or topic.get("name")
                else:
                    name = topic
                if isinstance(name, str):
                    interest_counts[name] += 1
        return [name for name, _ in interest_counts.most_common(5)]

    def _generate_introduction(self, info: dict[str, Any]) -> str:
        name = info.get("name") or "This author"
        affiliation = info.get("affiliation")
        interests = info.get("research_interests") or []
        top_papers = info.get("top_cited_papers") or []
        top_titles = [paper.get("title") for paper in top_papers if paper.get("title")]

        if not affiliation and not interests and not top_titles:
            return f"{name} is an academic researcher with published work in the field."

        prompt_parts = [
            f"Name: {name}",
            f"Affiliation: {affiliation or 'Unknown'}",
            f"Research interests: {', '.join(interests) if interests else 'Unknown'}",
            f"Notable papers: {', '.join(top_titles) if top_titles else 'Unknown'}",
        ]
        prompt = (
            "Write a concise 2-3 sentence introduction for this author using only the facts "
            "provided. If a field is unknown, omit it. Do not use markdown or bullets.\n\n"
            + "\n".join(prompt_parts)
        )

        try:
            return self.generate(prompt=prompt, system="You write concise academic bios.")
        except Exception as exc:
            logger.warning("Failed to generate introduction for %s: %s", name, exc)
            return f"{name} is an academic researcher with published work in the field."

    def _log_response(self, label: str, response: requests.Response) -> None:
        request = response.request
        method = request.method if request else "UNKNOWN"
        url = response.url
        status = response.status_code
        body_preview = response.text or ""
        if len(body_preview) > 2000:
            body_preview = f"{body_preview[:2000]}... (truncated)"
        logger.info("%s %s %s -> %s", label, method, url, status)
        logger.debug("%s response: %s", label, body_preview)

    def _normalize_authors(self, authors: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for author in authors:
            if isinstance(author, str):
                name = author.strip()
                if name:
                    normalized.append({"name": name, "author_id": None})
                continue
            if isinstance(author, dict):
                name = author.get("name") or author.get("authorName")
                author_id = author.get("author_id") or author.get("authorId")
                if isinstance(name, str):
                    name = name.strip()
                if name or author_id:
                    normalized.append({"name": name or "Unknown author", "author_id": author_id})
        return normalized

    def _build_semantic_scholar_url(self, author_id: str) -> str:
        return f"https://www.semanticscholar.org/author/{author_id}"

    def _upsert_author(self, session, info: dict[str, Any]) -> Optional[Author]:
        author_id = info.get("author_id")
        name = info.get("name")
        query = session.query(Author)
        if author_id:
            author = (
                query.filter(Author.semantic_scholar_id == str(author_id)).first()
            )
        else:
            author = (
                query.filter(Author.semantic_scholar_id.is_(None), Author.name == name)
                .first()
            )

        if author is None:
            author = Author(semantic_scholar_id=str(author_id) if author_id else None)
            session.add(author)

        author.name = name
        author.homepage = info.get("homepage")
        author.semantic_scholar_url = info.get("semantic_scholar_url")
        author.dblp_url = info.get("dblp_url")
        author.affiliation = info.get("affiliation")
        author.introduction = info.get("introduction")
        author.top_cited_papers = self._dump_json(info.get("top_cited_papers"))
        author.coauthors = self._dump_json(info.get("coauthors"))
        author.research_interests = self._dump_json(info.get("research_interests"))
        author.sources = self._dump_json(info.get("sources"))
        author.error = info.get("error")

        return author

    def _dump_json(self, value: Any) -> Optional[str]:
        if value in (None, [], {}):
            return None
        return json.dumps(value, ensure_ascii=True)

    @staticmethod
    def _parse_json(value: Optional[str]) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
