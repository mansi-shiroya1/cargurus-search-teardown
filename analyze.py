"""Turn task scores, interview notes, and the feature proposal into one teardown page.

Usage:  python analyze.py
Reads:  data/task_scores.csv, data/interviews.csv, data/pain_point_effort.csv,
        docs/feature_proposal.md, report/screenshots/*
Writes: report/report.html (open it in a browser)

Pain points are ranked by:
    priority = participants_affected x avg_severity / effort
so a common, painful, cheap-to-fix problem rises to the top.
"""
import csv
import html
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
PROPOSAL = ROOT / "docs" / "feature_proposal.md"
OUT = ROOT / "report" / "report.html"
SITES = [("cargurus", "CarGurus"), ("autotrader", "Autotrader")]
SITE_NAMES = " and ".join(n for _, n in SITES)
DEFAULT_EFFORT = 3
REPO_URL = "https://github.com/mansi-shiroya1/cargurus-search-teardown"
e = html.escape


# ---------- data ----------

def read_csv(name):
    path = DATA / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def to_num(value):
    try:
        return float(value)
    except ValueError:
        return None


def score_tasks(rows):
    tasks, totals = [], defaultdict(list)
    for row in rows:
        scores = {key: to_num(row.get(key, "")) for key, _ in SITES}
        if all(v is None for v in scores.values()):
            continue
        for key, v in scores.items():
            if v is not None:
                totals[key].append(v)
        tasks.append((row["task"], scores, row.get("notes", "")))
    averages = {k: round(sum(v) / len(v), 2) for k, v in totals.items() if v}
    return tasks, averages


def rank_pain_points(interviews, effort_rows):
    effort = {r["pain_point"].lower(): r for r in effort_rows if r.get("pain_point")}
    groups = defaultdict(lambda: {"people": set(), "severity": [], "quotes": []})
    for r in interviews:
        label = r.get("pain_point", "")
        if not label:
            continue
        g = groups[label.lower()]
        g["label"] = label
        g["people"].add(r.get("participant", ""))
        sev = to_num(r.get("severity_1to5", ""))
        if sev is not None:
            g["severity"].append(sev)
        if r.get("quote"):
            g["quotes"].append((r.get("participant", ""), r["quote"]))

    ranked = []
    for key, g in groups.items():
        sev = sum(g["severity"]) / len(g["severity"]) if g["severity"] else 0
        e_row = effort.get(key, {})
        eff = to_num(e_row.get("effort_1to5", "")) or DEFAULT_EFFORT
        ranked.append({
            "label": g["label"],
            "people": len(g["people"]),
            "severity": round(sev, 1),
            "effort": eff,
            "existing": e_row.get("already_on_cargurus", ""),
            "priority": round(len(g["people"]) * sev / eff, 2),
            "quotes": g["quotes"][:2],
        })
    return sorted(ranked, key=lambda p: p["priority"], reverse=True)


def parse_proposal(path):
    """Read '## Heading' sections from the proposal markdown, ignoring <!-- comments -->."""
    if not path.exists():
        return {}
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    sections, current = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current and line:
            sections[current].append(line)
    return sections


class Proposal:
    def __init__(self, sections):
        self.s = sections

    def text(self, key):
        return " ".join(l for l in self.s.get(key, []) if not l.startswith("- "))

    def items(self, key):
        return [l[2:].strip() for l in self.s.get(key, []) if l.startswith("- ")]

    def rows(self, key, cols):
        out = []
        for item in self.items(key):
            parts = [p.strip() for p in item.split("|")]
            out.append((parts + [""] * cols)[:cols])
        return out

    def missing(self):
        return [k for k, v in self.s.items() if not v]


# ---------- page ----------

def score_style(v):
    """Electric Blue at full strength for 5, fading toward charcoal for 1."""
    if v is None:
        return ""
    alpha = {1: 0.08, 2: 0.2, 3: 0.38, 4: 0.62, 5: 1.0}.get(int(v), 0.3)
    return f' style="background:rgba(47,107,255,{alpha})"'


def para(text):
    return f'<p class="body">{e(text)}</p>' if text else ""


def ul(items, cls="list"):
    return f'<ul class="{cls}">' + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>" if items else ""


def section(num, eyebrow, title_html, body, anchor=""):
    if not body.strip():
        return ""
    aid = f' id="{anchor}"' if anchor else ""
    return (f'<section{aid}><div class="eyebrow">{num} · {eyebrow}</div>'
            f"<h2>{title_html}</h2>{body}</section>")


def pain_card(i, p, n_people, max_pri):
    quotes = "".join(
        '<p class="quote">“' + e(q) + '” <span>- ' + e(who) + "</span></p>" for who, q in p["quotes"]
    )
    existing = ("<span>On CarGurus: " + e(p["existing"]) + "</span>") if p["existing"] else ""
    width = round(p["priority"] / max_pri * 100)
    return (
        '<div class="pain"><div class="rank">' + str(i).zfill(2) + "</div><div>"
        + '<div class="ptitle">' + e(p["label"]) + "</div>" + quotes
        + '<div class="meta"><span>' + str(p["people"]) + "/" + str(n_people) + " participants</span>"
        + "<span>Severity " + str(p["severity"]) + "</span>"
        + "<span>Effort " + str(int(p["effort"])) + "</span>" + existing + "</div>"
        + '<div class="bar"><i style="width:' + str(width) + '%"></i></div></div>'
        + '<div class="pri"><b>' + str(p["priority"]) + "</b><small>priority</small></div></div>"
    )


def build_html(tasks, averages, pains, n_people, prop, screenshots, funnel):
    names = dict(SITES)
    best_key = max(averages, key=averages.get) if averages else None
    top = pains[0] if pains else None
    max_pri = max((p["priority"] for p in pains), default=1) or 1
    feature = prop.text("feature name") or "Feature proposal"

    # 01 scorecard
    rows = "".join(
        f"<tr><td class='task'>{e(t)}" + (f"<span class='note'>{e(n)}</span>" if n else "") + "</td>"
        + "".join(f"<td class='s'{score_style(s[k])}>{'' if s[k] is None else int(s[k])}</td>" for k, _ in SITES)
        + "</tr>"
        for t, s, n in tasks
    )
    avg_row = "<tr class='avg'><td>Average</td>" + "".join(
        f"<td class='s'>{averages.get(k, '-')}</td>" for k, _ in SITES) + "</tr>"
    head = "".join(f"<th class='s'>{name}</th>" for _, name in SITES)
    scorecard = (
        '<p class="hint">Each task scored from 1 (painful) to 5 (easy). Darker blue means smoother.</p>'
        f"<div class='panel'><table><tr><th>Shopper task</th>{head}</tr>{rows}{avg_row}</table></div>"
        '<div class="legend">Painful <i style="background:rgba(47,107,255,.08)"></i>'
        '<i style="background:rgba(47,107,255,.38)"></i><i style="background:rgba(47,107,255,1)"></i> Easy</div>'
    ) if tasks else ""

    # evidence
    shots = "".join(
        f'<figure><a href="screenshots/{e(f)}"><img src="screenshots/{e(f)}" alt="{e(c)}" loading="lazy"></a><figcaption>{e(c)}</figcaption></figure>'
        for f, c in screenshots
    )
    evidence = f'<div class="shots">{shots}</div>' if shots else ""

    # 02 pain points
    pain_cards = "".join(pain_card(i, p, n_people, max_pri) for i, p in enumerate(pains, 1))
    pains_html = ('<p class="hint">Priority = participants affected × average severity ÷ effort to fix.</p>'
                  + pain_cards) if pains else ""

    # 03 proposal + mock-up
    chips = "".join(f'<span class="chip">+ {e(c)}</span>' for c in prop.items("suggested filters"))
    mock = (f'<div class="mock"><div class="mbar"><span></span><span></span><span></span></div>'
            f'<div class="mq">{e(prop.text("mockup search"))}</div>'
            f'<div class="mlabel">Shoppers like you usually narrow by</div><div>{chips}</div>'
            '<div class="mhint">One tap applies a filter and updates the result count.</div>'
            '<div class="mcaption">Concept mock-up</div><div class="mhint">Counts come from the CarGurus test search.</div></div>') if chips else ""
    left = "".join(
        f'<div class="block"><h3>{lbl}</h3>{para(prop.text(k))}</div>'
        for lbl, k in [("The problem", "problem"), ("Why this problem first", "why this problem"),
                       ("The proposal", "proposal")] if prop.text(k)
    )
    proposal_html = f'<div class="split"><div>{left}</div>{mock}</div>' if (left or mock) else ""

    # 04 landscape
    land = prop.rows("what exists today", 3)
    land_html = ("<div class='panel'><table><tr><th>Feature</th><th>What it does</th>"
                 "<th>Gap for this problem</th></tr>"
                 + "".join(f"<tr><td class='task'>{e(a)}</td><td>{e(b)}</td><td class='gap'>{e(c)}</td></tr>"
                           for a, b, c in land)
                 + "</table></div>") if land else ""

    # 05 dealer tradeoff
    trade_txt, limits = prop.text("dealer tradeoff"), prop.items("how i'd limit it")
    trade_html = (f'<div class="two"><div class="card">{"<h3>The risk</h3>" + para(trade_txt) if trade_txt else ""}</div>'
                  f'<div class="card">{"<h3>How I would limit it</h3>" + ul(limits, "list check") if limits else ""}</div></div>'
                  ) if (trade_txt or limits) else ""

    # 06 scope
    v_in, v_out = prop.items("v1 in"), prop.items("v1 out")
    scope_html = (f'<div class="two"><div class="card in"><h3>In V1</h3>{ul(v_in, "list check")}</div>'
                  f'<div class="card out"><h3>Later, not V1</h3>{ul(v_out, "list cross")}</div></div>'
                  ) if (v_in or v_out) else ""

    # 07 metrics
    primary = prop.text("primary metric")
    metrics_html = (f'<div class="metrics"><div class="card primary"><small>Primary metric</small>'
                    f'<b>{e(primary)}</b></div>'
                    f'<div class="card"><small>Secondary</small>{ul(prop.items("secondary metrics"))}</div>'
                    f'<div class="card"><small>Guardrails</small>{ul(prop.items("guardrails"))}</div></div>'
                    ) if primary else ""

    # 08 launch
    steps = prop.rows("test and launch", 2)
    launch_html = ('<ol class="timeline">' + "".join(
        f'<li><span class="dot">{i}</span><b>{e(a)}</b><p>{e(b)}</p></li>' for i, (a, b) in enumerate(steps, 1)
    ) + "</ol>") if steps else ""

    # 09 risks
    risks_html = ul(prop.items("risks"), "list risk")

    # method, findings, funnel, next steps
    method_html = ul(prop.items("method"), "list check")
    findings = prop.rows("findings", 2)
    findings_html = ('<div class="finds">' + "".join(
        '<div class="card find"><div class="rank">' + str(i).zfill(2) + "</div><div><h4>" + e(t) + "</h4>"
        + '<p class="body">' + e(d) + "</p></div></div>" for i, (t, d) in enumerate(findings, 1)
    ) + "</div>") if findings else ""
    next_html = ul(prop.items("next steps"), "list check")

    funnel_html, last_left = "", None
    frows = [(r["step"], [(k, to_num(r.get(k, ""))) for k, _ in SITES]) for r in funnel if r.get("step")]
    if frows:
        fmax = max(v for _, vals in frows for _, v in vals if v) or 1
        blocks = []
        for step, vals in frows:
            bars = "".join(
                '<div class="frow"><span class="fname">' + names[k] + '</span><div class="ftrack"><i class="f-' + k
                + '" style="width:' + str(max(2, round(v / fmax * 100))) + '%"></i></div><b>'
                + format(int(v), ",") + "</b></div>" for k, v in vals if v is not None)
            blocks.append('<div class="fstep"><div class="flabel">' + e(step) + "</div>" + bars + "</div>")
        funnel_html = ('<p class="hint">Cars left after each step of the same search.</p><div class="panel funnel">'
                       + "".join(blocks) + "</div>")
        last_left = frows[-1][1][0][1]

    if n_people:
        stats = [
            (str(len(tasks)), "shopper tasks tested<br>on " + str(len(SITES)) + " marketplaces"),
            (str(n_people), "car buyers<br>interviewed"),
            (str(top["people"]) + "/" + str(n_people) if top else "-",
             "hit the top pain point<br>(" + e(top["label"].lower()) + ")" if top else "hit the top pain point"),
            (str(averages.get(best_key, "-")),
             "best avg task score<br>(" + names[best_key] + ")" if best_key else "best avg task score"),
        ]
    else:
        stats = [
            (str(len(tasks)), "shopper tasks run<br>on each site"),
            (str(len(SITES)), "car marketplaces<br>compared"),
            (format(int(last_left), ",") if last_left else "-", "cars still left on CarGurus<br>after two must-have filters"),
            (str(len(land)), "existing features<br>reviewed"),
        ]
    stat_html = "".join("<div class='stat'><b>" + v + "</b><span>" + l + "</span></div>" for v, l in stats)

    if not tasks and not n_people:
        stats = [
            (str(len(land)), "existing CarGurus<br>features reviewed"),
            (str(len(v_in)), "things in<br>V1 scope"),
            (str(len(prop.items("guardrails"))), "guardrail metrics<br>protecting dealers and shoppers"),
            (str(len(steps)), "stages in the<br>test and launch plan"),
        ]
        stat_html = "".join("<div class='stat'><b>" + v + "</b><span>" + l + "</span></div>" for v, l in stats)
        strip = "<b>CASE STUDY</b>A feature proposal for CarGurus used-car search"
        eyebrow = "Feature proposal · CarGurus used-car search"
        second_cta = '<a class="btn" href="#landscape">See what exists today</a>'
        end_lede = "The proposal source and the script that builds this page are on GitHub."
        lede = ("I reviewed what CarGurus offers shoppers today, found the biggest gap in getting from a broad search "
                "to a shortlist, and scoped a feature to close it, with success metrics and a launch plan.")
    else:
        strip = "<b>CASE STUDY</b>Product teardown of used-car search on " + SITE_NAMES
        eyebrow = "Product teardown · " + " vs. ".join(n for _, n in SITES)
        second_cta = '<a class="btn" href="#scorecard">See the research</a>'
        end_lede = "Task scores, result counts, screenshots, and the script that builds this page are on GitHub."
        if n_people:
            lede = ("I tested real shopper tasks on three car marketplaces and interviewed recent car buyers to find "
                    "where narrowing down the right car gets hard, then decided what CarGurus should build first and how to measure it.")
        else:
            lede = ("Six shopper tasks, run on " + SITE_NAMES + " with the same search, show where getting from a broad "
                    "search to a shortlist gets hard. The second half turns the biggest gap into a scoped feature for "
                    "CarGurus, with success metrics and a launch plan.")

    parts = [
        ("Method", "How the test <em>was run</em>", method_html, "method"),
        ("Task testing", "Friction <em>scorecard</em>", scorecard, "scorecard"),
        ("Narrowing", "How fast the list <em>shrinks</em>", funnel_html, ""),
        ("Findings", "What the test <em>showed</em>", findings_html, "findings"),
        ("Evidence", "Findings, <em>in screenshots</em>", evidence, ""),
        ("Interviews", "Pain points, <em>ranked</em>", pains_html, "pain"),
        ("Recommendation", "Proposal: <em>" + e(feature.lower()) + "</em>", proposal_html, "proposal"),
        ("Landscape", "What exists <em>today</em>", land_html, "landscape"),
        ("Two-sided marketplace", "The <em>dealer</em> tradeoff", trade_html, ""),
        ("Scope", "What ships <em>first</em>", scope_html, ""),
        ("Measurement", "How I'd know it <em>worked</em>", metrics_html, "metrics"),
        ("Rollout", "Test &amp; <em>launch</em> plan", launch_html, "launch"),
        ("Risks", "What could <em>go wrong</em>", risks_html, ""),
        ("Next steps", "What I'd do <em>next</em>", next_html, ""),
    ]
    parts = [x for x in parts if x[2].strip()]
    body = "".join(section(str(i).zfill(2), eb, t, b, a) for i, (eb, t, b, a) in enumerate(parts, 1))
    nav = "".join('<a href="#' + a + '">' + lbl + "</a>" for lbl, a in
                  [("Scorecard", "scorecard"), ("Findings", "findings"), ("Pain points", "pain"), ("Proposal", "proposal"),
                   ("Metrics", "metrics"), ("Launch", "launch")] if any(x[3] == a for x in parts))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Car Search Teardown</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@1&display=swap" rel="stylesheet">
<style>
:root{{--charcoal:#1E1E1C;--panel:#262624;--line:#3a3935;--sand:#D8CBB3;--muted:#9c9282;--blue:#2F6BFF;--hi:#f1e9da}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--charcoal);color:var(--sand);font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:inherit;text-decoration:none}}
.strip{{background:var(--blue);color:#fff;font-size:12.5px;text-align:center;padding:8px 16px}}
.strip b{{border:1px solid rgba(255,255,255,.6);border-radius:10px;padding:1px 7px;font-size:10.5px;margin-right:8px;letter-spacing:.06em}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 24px}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:22px 0;border-bottom:1px solid var(--line)}}
.logo{{font-weight:700;letter-spacing:.14em;font-size:14px}} .logo i{{color:var(--blue);font-style:normal;margin-right:6px}}
.links{{display:flex;gap:26px;font-size:13.5px;color:var(--muted)}} .links a:hover{{color:var(--sand)}}
.btn{{display:inline-block;padding:11px 18px;border-radius:7px;font-size:13.5px;font-weight:600;border:1px solid var(--line)}}
.btn.primary{{background:var(--blue);border-color:var(--blue);color:#fff}}
.btn:hover{{border-color:var(--sand)}} .btn.primary:hover{{filter:brightness(1.1)}}
.hero{{padding:72px 0 40px}}
.eyebrow{{font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;gap:12px}}
.eyebrow:before{{content:"";width:26px;height:1px;background:var(--muted)}}
h1{{font-size:clamp(40px,6.4vw,76px);line-height:1.02;letter-spacing:-.035em;font-weight:600;margin:22px 0;max-width:860px}}
h1 em,h2 em{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;letter-spacing:-.01em}}
.lede{{font-size:17px;line-height:1.6;color:var(--muted);max-width:600px;margin:0 0 30px}}
.ctas{{display:flex;gap:12px;flex-wrap:wrap}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:56px 0 0}}
.stat{{padding:26px 22px 26px 0}} .stat+.stat{{border-left:1px solid var(--line);padding-left:22px}}
.stat b{{display:block;font-size:40px;font-weight:600;letter-spacing:-.03em;margin-bottom:6px}}
.stat span{{font-size:12.5px;color:var(--muted);line-height:1.45}}
section{{padding:64px 0 8px}}
h2{{font-size:30px;font-weight:600;letter-spacing:-.025em;margin:10px 0 22px}}
h3{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:500;margin:0 0 10px}}
.hint{{color:var(--muted);font-size:14px;margin:-12px 0 24px}}
.body{{font-size:16px;line-height:1.65;color:var(--sand);margin:0}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 22px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:14.5px;min-width:560px}}
th{{font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:500;text-align:left;padding:16px 8px}}
td{{padding:14px 8px;border-top:1px solid var(--line);vertical-align:top;line-height:1.5}}
.s{{text-align:center;width:120px}} td.s{{font-weight:600;color:#fff;border-radius:6px;border:4px solid var(--panel)}}
.task{{color:var(--hi)}} .task .note{{display:block;color:var(--muted);font-size:12.5px;margin-top:3px}}
.gap{{color:var(--hi)}} .gap:before{{content:"→ ";color:var(--blue)}}
.avg td{{font-weight:600;border-top:1px solid var(--muted)}} .avg td.s{{color:var(--sand);background:none}}
.legend{{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);margin:14px 2px 0}}
.legend i{{width:22px;height:12px;border-radius:3px;display:inline-block}}
.shots{{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}}
figure{{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
figure img{{display:block;width:100%;height:auto}}
figcaption{{padding:12px 14px;font-size:13px;color:var(--muted)}}
.pain{{display:grid;grid-template-columns:56px 1fr 90px;gap:20px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:14px}}
.rank{{font-size:28px;font-weight:600;color:var(--blue)}}
.ptitle{{font-size:19px;font-weight:600;color:var(--hi);margin-bottom:6px}}
.quote{{font-family:"Instrument Serif",Georgia,serif;font-style:italic;font-size:19px;margin:4px 0}}
.quote span{{font-family:Inter,sans-serif;font-style:normal;font-size:12px;color:var(--muted)}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}}
.meta span{{font-size:12px;border:1px solid var(--line);border-radius:20px;padding:3px 10px;color:var(--muted)}}
.bar{{height:4px;background:var(--line);border-radius:4px}} .bar i{{display:block;height:100%;background:var(--blue);border-radius:4px}}
.pri{{text-align:right}} .pri b{{font-size:30px;font-weight:600;display:block}} .pri small{{color:var(--muted);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase}}
.finds{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.find{{display:grid;grid-template-columns:44px 1fr;gap:14px}} .find .rank{{font-size:22px}}
h4{{font-size:18px;line-height:1.3;color:var(--hi);margin:0 0 8px;font-weight:600}}
.find .body{{font-size:14.5px;color:var(--sand)}}
.funnel{{padding:22px}} .fstep+.fstep{{margin-top:22px;padding-top:22px;border-top:1px solid var(--line)}}
.flabel{{font-size:15px;color:var(--hi);font-weight:600;margin-bottom:10px}}
.frow{{display:grid;grid-template-columns:96px 1fr 64px;gap:12px;align-items:center;margin:6px 0;font-size:13px;color:var(--muted)}}
.frow b{{color:var(--sand);font-weight:600;text-align:right;font-variant-numeric:tabular-nums}}
.ftrack{{height:14px;background:rgba(255,255,255,.04);border-radius:4px}} .ftrack i{{display:block;height:100%;border-radius:4px}}
.f-cargurus{{background:var(--blue)}} .f-autotrader{{background:var(--sand)}}
figure a{{display:block}}
.split{{display:grid;grid-template-columns:1.1fr 1fr;gap:36px;align-items:start}}
.block+.block{{margin-top:26px}}
.mock{{background:#f6f2ea;color:#1E1E1C;border-radius:14px;padding:18px 20px 16px;box-shadow:0 20px 50px rgba(0,0,0,.35);position:relative}}
.mbar{{display:flex;gap:6px;margin-bottom:16px}} .mbar span{{width:9px;height:9px;border-radius:50%;background:#cfc6b6}}
.mq{{font-weight:600;font-size:16px;padding:12px 14px;border:1px solid #ddd3c2;border-radius:8px;background:#fff}}
.mlabel{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#7d7466;margin:18px 0 8px}}
.chip{{display:inline-block;border:1.5px solid var(--blue);color:var(--blue);border-radius:20px;padding:6px 12px;margin:0 6px 8px 0;font-size:13.5px;font-weight:600;background:#fff}}
.chip:first-child{{background:var(--blue);color:#fff}}
.mhint{{font-size:13px;color:#7d7466;margin-top:6px}}
.mcaption{{position:absolute;top:14px;right:18px;font-size:11px;color:#9b917f;letter-spacing:.08em;text-transform:uppercase}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px}}
.card.in{{border-top:3px solid var(--blue)}} .card.out{{border-top:3px solid var(--line)}}
.list{{margin:0;padding:0;list-style:none}} .list li{{padding:9px 0;border-top:1px solid var(--line);font-size:15px;line-height:1.5}}
.list li:first-child{{border-top:none}}
.check li:before{{content:"✓";color:var(--blue);font-weight:700;margin-right:10px}}
.cross li{{color:var(--muted)}} .cross li:before{{content:"-";margin-right:10px}}
.risk li:before{{content:"!";display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1px solid var(--blue);color:var(--blue);font-size:11px;font-weight:700;margin-right:10px}}
.metrics{{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:16px}}
.metrics small{{display:block;font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.primary{{background:linear-gradient(135deg,rgba(47,107,255,.22),var(--panel) 70%)}}
.primary b{{font-size:24px;line-height:1.3;color:var(--hi);font-weight:600}}
.timeline{{list-style:none;padding:0;margin:0;display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:16px;position:relative}}
.timeline li{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;position:relative}}
.timeline b{{display:block;font-size:17px;color:var(--hi);margin:12px 0 6px}}
.timeline p{{margin:0;font-size:14px;line-height:1.55;color:var(--muted)}}
.dot{{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--blue);color:#fff;font-weight:700;font-size:13px}}
.end{{margin:72px 0 0;padding:44px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(47,107,255,.16),transparent 60%)}}
footer{{color:var(--muted);font-size:12.5px;padding:40px 0;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}}
@media(max-width:820px){{
 .links{{display:none}} .hero{{padding-top:48px}}
 .stats{{grid-template-columns:1fr 1fr}} .stat:nth-child(3){{border-left:none;padding-left:0}} .stat:nth-child(n+3){{border-top:1px solid var(--line)}}
 .pain{{grid-template-columns:1fr}} .pri{{text-align:left}}
 .split,.two,.metrics,.finds,.shots{{grid-template-columns:1fr}} .timeline{{grid-auto-flow:row}} .end{{padding:28px}}
}}
</style></head><body>
<div class="strip">{strip}</div>
<div class="wrap">
<nav><a class="logo" href="#"><i>◆</i>SEARCH TEARDOWN</a>
<div class="links">{nav}</div>
<a class="btn" href="{REPO_URL}">View on GitHub</a></nav>

<header class="hero">
<div class="eyebrow">{eyebrow}</div>
<h1>Where car search <em>breaks down.</em></h1>
<p class="lede">{e(lede)}</p>
<div class="ctas"><a class="btn primary" href="#proposal">See the proposal</a>{second_cta}</div>
<div class="stats">{stat_html}</div>
</header>
{body}
<div class="end"><div class="eyebrow">Method &amp; data</div>
<h2>Everything here is <em>reproducible.</em></h2>
<p class="lede">{end_lede}</p>
<div class="ctas"><a class="btn primary" href="{REPO_URL}">View the repository</a></div></div>
<footer><span>Built by Mansi Shiroya</span><span>Independent analysis, not affiliated with {SITE_NAMES}.</span></footer>
</div></body></html>"""


# ---------- main ----------

def main():
    tasks, averages = score_tasks(read_csv("task_scores.csv"))
    interviews = read_csv("interviews.csv")
    pains = rank_pain_points(interviews, read_csv("pain_point_effort.csv"))
    n_people = len({r["participant"] for r in interviews if r.get("pain_point")})
    prop = Proposal(parse_proposal(PROPOSAL))
    screenshots = [tuple((p.strip() for p in (i.split("|") + [""])[:2])) for i in prop.items("evidence")]
    screenshots = [(f, c) for f, c in screenshots if (OUT.parent / "screenshots" / f).exists()]

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build_html(tasks, averages, pains, n_people, prop, screenshots, read_csv("funnel.csv")), encoding="utf-8")

    if tasks:
        print("Average task score by site:")
        for key, name in SITES:
            print(f"  {name:<11} {averages.get(key, '-')}")
    if pains:
        print("\nTop pain points:")
        for i, p in enumerate(pains[:3], 1):
            print(f"  {i}. {p['label']}  (priority {p['priority']}: {p['people']} people, severity {p['severity']})")

    todo = []
    todo += [f'docs/feature_proposal.md -> "## {k}"' for k in prop.missing()]
    if todo:
        print("\nStill empty (hidden on the page until filled):")
        for t in todo:
            print("  -", t)
    print(f"\nReport written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
