import csv
import sys

import httpx

OPENALEX_BASE = "https://api.openalex.org"
MAILTO = "your@email.com"


def search_author(client: httpx.Client, name: str) -> dict:
    resp = client.get(
        f"{OPENALEX_BASE}/authors",
        params={"search": name, "mailto": MAILTO},
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise SystemExit(f"No author found for '{name}'")

    author = results[0]
    print(
        f"Matched author: {author['display_name']}  "
        f"(ID: {author['id']}, works: {author['works_count']})"
    )
    return author


def fetch_last_author_works(
    client: httpx.Client, author_id: str
) -> list[dict]:
    """Return works where *author_id* is the last author.

    Each dict includes the first author's OpenAlex ID and name so we can
    later compute mentee scores.
    """
    short_id = author_id.replace("https://openalex.org/", "")
    cursor = "*"
    works: list[dict] = []

    while cursor:
        resp = client.get(
            f"{OPENALEX_BASE}/works",
            params={
                "filter": f"authorships.author.id:{short_id}",
                "per_page": 200,
                "cursor": cursor,
                "mailto": MAILTO,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        for work in data.get("results", []):
            authorships = work.get("authorships", [])
            is_last = any(
                a["author"]["id"] == author_id
                and a.get("author_position") == "last"
                for a in authorships
            )
            if not is_last:
                continue

            first_author = next(
                (a for a in authorships if a.get("author_position") == "first"),
                None,
            )
            first_author_id = first_author["author"]["id"] if first_author else None
            first_author_name = (
                first_author["author"].get("display_name", "") if first_author else ""
            )

            works.append(
                {
                    "title": work.get("display_name", ""),
                    "year": work.get("publication_year"),
                    "first_author_id": first_author_id,
                    "first_author_name": first_author_name,
                }
            )

        cursor = data.get("meta", {}).get("next_cursor")

    works.sort(key=lambda w: w["year"] or 0, reverse=True)
    return works


def count_prior_works(
    client: httpx.Client, author_id: str, before_year: int
) -> int:
    """Return the number of works *author_id* published before *before_year*."""
    short_id = author_id.replace("https://openalex.org/", "")
    resp = client.get(
        f"{OPENALEX_BASE}/works",
        params={
            "filter": (
                f"authorships.author.id:{short_id},"
                f"publication_year:<{before_year}"
            ),
            "per_page": 1,
            "mailto": MAILTO,
        },
    )
    resp.raise_for_status()
    return resp.json().get("meta", {}).get("count", 0)


def build_mentorship_rows(
    client: httpx.Client, works: list[dict]
) -> list[dict]:
    rows: list[dict] = []
    cache: dict[tuple[str, int], int] = {}

    for i, w in enumerate(works, 1):
        first_id = w["first_author_id"]
        year = w["year"]

        if first_id and year:
            key = (first_id, year)
            if key not in cache:
                cache[key] = count_prior_works(client, first_id, year)
            mentee_score = cache[key]
        else:
            mentee_score = None

        rows.append(
            {
                "title": w["title"],
                "year": year,
                "mentee_score": mentee_score,
            }
        )
        print(
            f"  [{i}/{len(works)}] {w['first_author_name']}: "
            f"mentee_score={mentee_score}"
        )

    return rows


def compute_mentorship_indices(rows: list[dict]) -> dict[str, int]:
    scores = [r["mentee_score"] for r in rows if r["mentee_score"] is not None]
    return {
        "M10": sum(1 for s in scores if s < 10),
        "M25": sum(1 for s in scores if s < 25),
    }


def write_csv(rows: list[dict], indices: dict[str, int], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "year", "mentee_score"])
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow({})
        for label, value in indices.items():
            writer.writerow({"title": label, "mentee_score": value})
    print(f"\nWrote {len(rows)} rows to {path}")


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "Steven A Cholewiak"

    with httpx.Client(timeout=30) as client:
        author = search_author(client, name)
        works = fetch_last_author_works(client, author["id"])

        if not works:
            print("No last-author publications found.")
            return

        print(f"\nFound {len(works)} last-author papers. Computing mentee scores…")
        rows = build_mentorship_rows(client, works)

    indices = compute_mentorship_indices(rows)

    out_path = "mentorship_index.csv"
    write_csv(rows, indices, out_path)

    print(f"\n{'Title':<70} {'Year':>4}  {'Mentee Score':>12}")
    print("-" * 92)
    for r in rows:
        score = r["mentee_score"] if r["mentee_score"] is not None else "N/A"
        print(f"{r['title'][:70]:<70} {r['year']:>4}  {score:>12}")

    print()
    for label, value in indices.items():
        print(f"{label}: {value}")


if __name__ == "__main__":
    main()
