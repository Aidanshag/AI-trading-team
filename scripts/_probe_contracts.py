"""Debug: why does Contract/search return nothing for ES, CL, GC?"""

from tools.projectx_client import get_client

c = get_client()
c.authenticate()

for q in ["ES", "/ES", "E-mini", "EP", "ESM5", "ESM25", "ESZ25", "CL", "GC", "NQ"]:
    for live in (True, False):
        try:
            r = c.search_contracts(q, live=live)
            n = len(r)
            first = (r[0] if r else {})
            first_id = first.get("id") or first.get("contractId") or "-"
            first_name = first.get("name") or first.get("productName") or "-"
            print(f"  search({q!r:<10} live={live}) -> {n:>3} contracts   "
                  f"first: id={first_id} name={first_name}")
        except Exception as e:
            print(f"  search({q!r:<10} live={live}) -> error: {e}")
