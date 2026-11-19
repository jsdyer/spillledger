"""Extract incident and claim rows from the fund's general claims table."""
from datetime import date
import re
import pymupdf
from source_io import archives, archived, publish

DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
PROVINCES = {"British Columbia","Nova Scotia"}
def lines(cell):
    return [s.strip() for s in (cell or "").splitlines() if s.strip()]


def assemble(pdf):
    incidents = []
    current = None
    province = None
    with pymupdf.open(stream=pdf,filetype="pdf") as document:
        for page_number in range(63,77):
            for table in document[page_number-1].find_tables().tables:
                header,*rows = table.extract()
                if len(header)!=6 or "Amount recovered" not in (header[4] or ""):
                    continue
                for incident,spacer,claim,decision,recovery,status in rows:
                    if incident and not any((spacer,claim,decision,recovery,status)):
                        province = incident.strip()
                        current = None
                        continue
                    if province not in PROVINCES:
                        continue
                    if spacer:
                        raise ValueError(f"Unexpected table layout on page {page_number}")
                    if incident:
                        details = lines(incident)
                        ix = next(i for i,s in enumerate(details) if DATE.fullmatch(s))
                        date.fromisoformat(details[ix])
                        current = dict(name=" ".join(details[:ix]), date=details[ix], place=details[ix+1],
                                       description=details[ix+1:], province=province, page=page_number,
                                       claims=[], recovery=lines(recovery))
                        incidents.append(current)
                    if current is None:
                        raise ValueError("Claim without an associated incident")
                    # Empty incident cells continue the same printed incident and shared recovery.
                    current["claims"].append(dict(submission=lines(claim),decision=lines(decision),status=status.strip(),page=page_number))
                    if not incident and recovery and lines(recovery)!=current["recovery"]:
                        raise ValueError("Additional recovery cell requires review")
    if {r["province"] for r in incidents} != PROVINCES or len(incidents)<60:
        raise ValueError("Incomplete incident table")
    merged = {}
    for record in incidents:
        key = (record["province"], record["name"], record["date"], record["place"])
        if key in merged:
            prior = merged[key]
            if key != ("Nova Scotia","Farley Mowat","2015-06-24","Shelburne") or any(prior[k]!=record[k] for k in ("description","recovery")):
                raise ValueError("Review repeated incident identities")
            prior["claims"].extend(record["claims"])
        else:
            merged[key] = record
    incidents = list(merged.values())
    return dict(start=2024,end=2024,coverage="BC and Nova Scotia · 2023–24 report",
                count=len(incidents), records=incidents, source=archives()[0]["url"])


if __name__ == "__main__":
    publish(assemble(archived(archives()[0])))
