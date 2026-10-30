from .base import Provider, register
from ..core.http import ProviderError


@register
class Nexar(Provider):
    slug = "nexar"
    modes = {"mpn", "text"}

    def search(self, q):
        if not self.config.key or not self.config.secret:
            raise ProviderError("missing_credentials")
        auth = self.http.json(
            "POST",
            "https://identity.nexar.com/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.key,
                "client_secret": self.config.secret,
                "scope": "supply.domain",
            },
        )
        if not auth.get("access_token"):
            raise ProviderError("authentication_or_access_denied")
        query = "query($q: String!) { supSearch(q: $q, limit: 10) { results { part {\n id name mpn shortDescription manufacturer { name } category { name }\n bestDatasheet { url } specs { attribute { name } displayValue }\n} } } }"
        raw = self.http.json(
            "POST",
            "https://api.nexar.com/graphql",
            headers={"Authorization": "Bearer " + auth["access_token"]},
            json={
                "query": query,
                "variables": {
                    "q": " ".join(filter(None, [q.manufacturer, q.mpn, q.text]))
                },
            },
        )
        if raw.get("errors"):
            raise ProviderError("graphql_access_or_query_error")
        out = []
        for result in ((raw.get("data") or {}).get("supSearch") or {}).get(
            "results", []
        ):
            r = result["part"]
            ds = (r.get("bestDatasheet") or {}).get("url")
            out.append(
                self.product(
                    name=r.get("name") or r.get("mpn", ""),
                    description=r.get("shortDescription", ""),
                    manufacturer=(r.get("manufacturer") or {}).get("name", ""),
                    mpn=r.get("mpn", ""),
                    category=(r.get("category") or {}).get("name", ""),
                    datasheet_urls=[ds] if ds else [],
                    specifications={
                        s["attribute"]["name"]: s.get("displayValue", "")
                        for s in r.get("specs", [])
                    },
                    source_product_id=str(r.get("id", "")),
                    source_url="https://octopart.com",
                    metadata={"provider_data": r},
                )
            )
        return out
