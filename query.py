"""Search the local research library and return citable source passages."""
import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from library import add_public_sources, has_fts, initialize, personal_index

FIELDS = "d.source,d.title,d.date,d.locator,d.channels,d.kind,d.attribution,d.status"
PASSAGE = FIELDS + ",c.location,c.body"

def find(db, args):
    filters = []
    params = []
    if args.kind:
        filters.append("d.kind = ?")
        params.append(args.kind)
    if args.source:
        filters.append("d.source = ?")
        params.append(args.source.upper())
    extra = "".join(" AND "+x for x in filters)
    terms = list(dict.fromkeys(t.strip() for t in args.terms if t.strip()))
    candidates = {}
    use_fts = has_fts(db)
    for term in terms:
        if use_fts and len(term) >= 3:
            sql = f"""SELECT {PASSAGE}, bm25(search,4,1) AS rank
                FROM search JOIN chunks c ON c.id=search.rowid JOIN documents d ON d.source=c.source
                WHERE search MATCH ?{extra} ORDER BY rank LIMIT 160"""
            values = ['"'+term.replace('"','""')+'"',*params]
        else:
            sql = f"""SELECT {PASSAGE}, -1.0 AS rank
                FROM chunks c JOIN documents d ON d.source=c.source
                WHERE (instr(d.title,?)>0 OR instr(c.body,?)>0){extra}
                ORDER BY instr(d.title,?)>0 DESC,d.date DESC,c.id LIMIT 160"""
            values = [term,term,*params,term]
        for row in db.execute(sql,values):
            key = (row["source"],row["location"],row["body"])
            if key not in candidates or row["rank"]<candidates[key]["rank"]:
                candidates[key] = dict(row)
    def rank(row):
        in_title = sum(t in row["title"] for t in terms)
        in_body = sum(t in row["body"] for t in terms)
        priority = row["kind"] in {"primary", "company", "archive", "notes"}
        return (in_title*4+in_body*3, in_body, priority, -row["rank"])
    output = []
    seen = Counter()
    for row in sorted(candidates.values(),key=rank,reverse=True):
        if seen[row["source"]] >= args.per_source:
            continue
        output.append(row)
        seen[row["source"]] += 1
        if len(output) >= args.limit:
            break
    return output

def show(db,args):
    query = f"SELECT {PASSAGE} FROM documents d LEFT JOIN chunks c ON d.source=c.source WHERE d.source=? ORDER BY c.id"
    result = []
    for row in db.execute(query,(args.id.upper(),)):
        if args.where and args.where not in (row["location"] or ""):
            continue
        result.append(dict(row))
        if len(result) >= args.limit:
            break
    return result

def catalog(db,args):
    filters = []
    values = []
    if args.kind:
        filters.append("d.kind=?")
        values.append(args.kind)
    if args.title:
        filters.append("instr(d.title,?)>0")
        values.append(args.title)
    where = " WHERE "+" AND ".join(filters) if filters else ""
    return [dict(r) for r in db.execute(f"SELECT {FIELDS} FROM documents d{where} ORDER BY d.source LIMIT ?",(*values,args.limit))]

def render(rows,args):
    if args.json:
        print(json.dumps(rows,ensure_ascii=False,indent=2))
        return
    if not rows:
        print("无匹配来源。可缩短关键词，或用 catalog 查篇名和来源编号。")
    for row in rows:
        when = " · "+row["date"] if row["date"] else ""
        print(f"[{row['source']}] {row['title']}{when}")
        print(row["channels"]+" · "+row["attribution"]+" · "+row["status"])
        print(row["locator"])
        if row.get("location"):
            print(row["location"])
        body=row.get("body")
        if body:
            starts = [body.find(t) for t in getattr(args,"terms",[]) if t in body]
            start = max(0, min(starts,default=0)-args.chars//4) if len(body)>args.chars else 0
            excerpt=body[start:start+args.chars]
            print(("…" if start else "")+excerpt+("…" if start+len(excerpt)<len(body) else ""))
        print()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    database=parser.add_mutually_exclusive_group()
    database.add_argument("--db", type=Path, help="Use a specified locally generated index.")
    database.add_argument("--public-only", action="store_true", help="Search the bundled public catalog only.")
    commands=parser.add_subparsers(dest="command",required=True)
    find_cmd=commands.add_parser("find")
    find_cmd.add_argument("terms",nargs="+")
    find_cmd.add_argument("--kind")
    find_cmd.add_argument("--source")
    find_cmd.add_argument("--per-source",type=int,choices=range(1,13),default=2)
    show_cmd=commands.add_parser("show")
    show_cmd.add_argument("id")
    show_cmd.add_argument("--where",help="Location substring, such as PDF p.10.")
    catalog_cmd=commands.add_parser("catalog")
    catalog_cmd.add_argument("--kind")
    catalog_cmd.add_argument("--title")
    for command in (find_cmd,show_cmd,catalog_cmd):
        command.add_argument("--limit",type=int,default=8)
        command.add_argument("--chars",type=int,default=800)
        command.add_argument("--json",action="store_true")
    args=parser.parse_args()
    if not 1<=args.limit<=500 or not 100<=args.chars<=5000:
        parser.error("--limit must be 1–500 and --chars 100–5000")
    path = (args.db or personal_index()).expanduser().resolve()
    if args.db and not path.is_file():
        parser.error(f"Local index missing: {path}")
    use_personal = not args.public_only and path.is_file()
    connection = sqlite3.connect(path.as_uri()+"?mode=ro", uri=True) if use_personal else sqlite3.connect(":memory:")
    with closing(connection) as db:
        db.row_factory = sqlite3.Row
        if not use_personal:
            initialize(db)
            add_public_sources(db)
        result = {"find": find, "show": show, "catalog": catalog}[args.command](db,args)
    render(result,args)

if __name__=="__main__":
    main()
