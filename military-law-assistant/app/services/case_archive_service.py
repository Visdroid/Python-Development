from typing import Dict, List, Optional
from urllib.parse import quote_plus


class CaseArchiveService:
    """Provides federated public case-archive search links."""

    def __init__(self) -> None:
        self.sources: List[Dict[str, str]] = [
            {
                "id": "saflii",
                "name": "SAFLII (Southern African Legal Information Institute)",
                "domain": "saflii.org",
                "coverage": "South African court judgments and historic case archives",
                "description": "Public legal archive often used for current and historical case law."
            },
            {
                "id": "judiciary",
                "name": "Judiciary of South Africa",
                "domain": "judiciary.org.za",
                "coverage": "Judicial communications, judgments, and court publications",
                "description": "Official judiciary communications and court resources."
            },
            {
                "id": "justice",
                "name": "Department of Justice (DOJ&CD)",
                "domain": "justice.gov.za",
                "coverage": "Justice publications, legal notices, and policy documents",
                "description": "Official justice department publications and legal references."
            },
            {
                "id": "govza",
                "name": "South African Government Publications",
                "domain": "gov.za",
                "coverage": "Gazettes, acts, and departmental public documents",
                "description": "Government document archive for legislation and notices."
            }
        ]

    def get_sources(self) -> List[Dict[str, str]]:
        return self.sources.copy()

    def search_public_cases(
        self,
        query: str,
        source_id: Optional[str] = None
    ) -> Dict[str, object]:
        normalized_query = query.strip()
        if not normalized_query:
            return {"query": "", "results": [], "sources": self.get_sources()}

        selected_sources = self.sources
        if source_id:
            selected_sources = [source for source in self.sources if source["id"] == source_id]

        results: List[Dict[str, str]] = []
        for source in selected_sources:
            site_query = quote_plus(
                f'site:{source["domain"]} "{normalized_query}" (judgment OR case OR v)'
            )
            search_url = f"https://www.google.com/search?q={site_query}"
            results.append({
                "title": f'{source["name"]} results for "{normalized_query}"',
                "source": source["name"],
                "coverage": source["coverage"],
                "description": source["description"],
                "url": search_url
            })

        return {
            "query": normalized_query,
            "results": results,
            "sources": self.get_sources()
        }
