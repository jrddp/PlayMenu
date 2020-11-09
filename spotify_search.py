from util import get_uri_from_url


def search(query: str, type="track"):
    from googlesearch import search

    query = query.replace(' ', '+')
    query = f"{query}+site:open.spotify.com"
    if type: query += f"/{type}"
    return next(search(query, num=1, start=0, stop=0))


def play_search(query: str, type="track"):
    from util import play_uri

    url = search(query, type)
    uri = get_uri_from_url(url)
    play_uri(uri)
