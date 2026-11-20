#!/usr/bin/env python3
"""Maakt losse pagina's voor Google uit de vacaturedata in index.html.

- /vacatures/                 overzicht van alle steden en vakgebieden
- /vacatures/<stad>/          vacatures per stad (vanaf 3 vacatures)
- /vakgebied/<vakgebied>/     vacatures per vakgebied
- /tips/ en /tips/<artikel>/  tips en blog
- sitemap.xml                 alle pagina's

Draai vanuit de map van de repository:  python3 tools/maak_paginas.py
"""
import html
import json
import os
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://valcature.nl"
MIN_STAD = 3

src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
m = re.search(r'<script type="application/json" id="vacaturedata">(.*?)</script>', src, re.S)
DATA = json.loads(m.group(1).replace("<\\/", "</"))
VAC = DATA["vacatures"]
BIJGEWERKT = DATA.get("bijgewerkt") or date.today().isoformat()

def js_obj(naam):
    mm = re.search(r"const " + naam + r"=\{(.*?)\};", src, re.S)
    return dict(re.findall(r'(\w+):"([^"]+)"', mm.group(1))) if mm else {}

VAKKEN = js_obj("VAKKEN")
WERKVORM = {"locatie": "Op locatie", "hybride": "Hybride", "remote": "Thuiswerk"}
CONTRACT = {"vast": "Vast contract", "tijdelijk": "Tijdelijk", "traineeship": "Traineeship",
            "werkstudent": "Werkstudent", "freelance": "Freelance", "project": "Projectbasis"}
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
           "september", "oktober", "november", "december"]

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def datum(d):
    try:
        j, mnd, dag = map(int, d.split("-"))
        return f"{dag} {MAANDEN[mnd-1]} {j}"
    except Exception:
        return d

def euro(n):
    return "€ " + f"{int(n):,}".replace(",", ".")

def salaris(v):
    if v.get("sal"):
        a, b = v["sal"]
        return euro(a) if a == b else f"{euro(a)} – {euro(b)}"
    return v.get("salTekst") or None

def uren(v):
    u = v.get("uren")
    if not u:
        return None
    return f"{u[0]} uur" if u[0] == u[1] else f"{u[0]}–{u[1]} uur"

def sorteer(lst):
    return sorted(lst, key=lambda v: (v.get("sluit") or "9999", v["titel"].lower()))

CSS = """
:root{--cream:#F6F1E7;--paper:#FFFDF8;--ink:#17221D;--muted:#5D6A63;--line:#E3DBCB;--green:#0C5B44;--orange:#FF6A2B;--lime:#D2D63E}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:17px/1.6 "Instrument Sans",system-ui,sans-serif}
a{color:var(--green)}.in{max-width:900px;margin:0 auto;padding:0 20px}
header{background:var(--cream);border-bottom:2px solid var(--ink);padding:14px 0}header .in{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.logo{font:900 24px/1 "Archivo",Impact,sans-serif;letter-spacing:.02em;color:var(--ink);text-decoration:none}.logo i{display:inline-block;width:.55em;height:.55em;border-radius:50%;background:var(--orange);margin:0 .06em}
.btn{display:inline-block;font-weight:700;font-size:14px;text-transform:uppercase;letter-spacing:.04em;border-radius:999px;padding:11px 20px;border:2px solid var(--ink);background:var(--orange);color:#fff;text-decoration:none}
.btn.licht{background:var(--paper);color:var(--ink)}
h1{font:900 clamp(32px,6vw,52px)/1.05 "Archivo",Impact,sans-serif;margin:34px 0 12px}h2{font:800 26px/1.2 "Archivo",Impact,sans-serif;margin:34px 0 10px}
.intro{font-size:19px;max-width:60ch}.meta{color:var(--muted);font-size:14px}
.lijst{display:grid;gap:14px;margin:20px 0;padding:0;list-style:none}
.vac{background:var(--paper);border:2px solid var(--ink);border-radius:20px;padding:16px 18px}
.vac h3{margin:0 0 4px;font-size:19px;line-height:1.3}.vac .org{color:var(--muted);font-size:15px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.tags span{font-size:13px;border:1.5px solid var(--line);border-radius:999px;padding:2px 10px;background:var(--cream)}
.tags .sal{background:var(--lime);border-color:var(--lime)}
.vac a.ga{font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}.chips a{display:inline-block;border:2px solid var(--ink);border-radius:999px;padding:6px 14px;background:var(--paper);text-decoration:none;color:var(--ink);font-weight:600}
.cta{background:var(--green);color:var(--cream);border-radius:24px;padding:22px;margin:30px 0}.cta h2{margin-top:0;color:var(--cream)}.cta p{margin:0 0 14px}
article p,article li{max-width:65ch}
footer{margin-top:50px;border-top:2px solid var(--ink);padding:22px 0 40px;font-size:14px;color:var(--muted)}footer a{margin-right:14px}
"""

def pagina(pad, titel, beschrijving, body, crumbs=None):
    url = SITE + pad
    kruim = ""
    if crumbs:
        items = [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(crumbs)]
        kruim = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}, ensure_ascii=False) + "</script>"
    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titel)} | Valcature</title>
<meta name="description" content="{e(beschrijving)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Valcature"><meta property="og:url" content="{url}">
<meta property="og:title" content="{e(titel)}"><meta property="og:description" content="{e(beschrijving)}"><meta property="og:image" content="{SITE}/og2.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0C5B44"><link rel="manifest" href="/manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@800;900&family=Instrument+Sans:wght@400;600;700&display=swap">
<style>{CSS}</style>
{kruim}
</head>
<body>
<header><div class="in"><a class="logo" href="/">VAL<i></i>CATURE</a><a class="btn" href="/#match">Doe de quiz</a></div></header>
<main class="in">
{body}
</main>
<footer><div class="in">
<p><a href="/">Valcature</a><a href="/vacatures/">Vacatures per stad en vakgebied</a><a href="/tips/">Tips</a><a href="/#werkgevers">Voor werkgevers</a><a href="/#privacy">Privacy</a></p>
<p>Elke dag bijgewerkt. Laatst bijgewerkt op {datum(BIJGEWERKT)}. We nemen alleen kerngegevens over; bekijk de actuele vacature altijd bij de werkgever.</p>
</div></footer>
</body>
</html>
"""

def vac_html(v):
    tags = [t for t in [uren(v), WERKVORM.get(v.get("vorm")), v.get("niveau"), CONTRACT.get(v.get("contract"))] if t]
    s = salaris(v)
    t = "".join(f"<span>{e(x)}</span>" for x in tags) + (f'<span class="sal">{e(s)}</span>' if s else "<span>Salaris niet vermeld</span>")
    sluit = f' · sluit {datum(v["sluit"])}' if v.get("sluit") else ""
    return (f'<li class="vac"><h3>{e(v["titel"])}</h3><div class="org">{e(v["org"])} · {e(v["plaats"])}{sluit}</div>'
            f'<div class="tags">{t}</div><a class="ga" href="{e(v["url"])}" target="_blank" rel="noopener">Bekijk bij de werkgever ↗</a></li>')

def cta(tekst="Wil je weten welke vacatures het best bij jou passen? Doe de quiz en zie alles op volgorde van match."):
    return f'<div class="cta"><h2>Vind je match</h2><p>{e(tekst)}</p><a class="btn" href="/#match">Doe de quiz</a></div>'

geschreven = {}

def schrijf(pad, inhoud):
    doel = os.path.join(ROOT, pad.strip("/"), "index.html")
    os.makedirs(os.path.dirname(doel), exist_ok=True)
    open(doel, "w", encoding="utf-8").write(inhoud)
    geschreven[pad] = True

def ruim_op(map_naam, houden):
    basis = os.path.join(ROOT, map_naam)
    if not os.path.isdir(basis):
        return
    for d in os.listdir(basis):
        p = os.path.join(basis, d)
        if os.path.isdir(p) and d not in houden:
            shutil.rmtree(p)

# ---------- Steden ----------
per_stad = defaultdict(list)
for v in VAC:
    if v.get("plaats") and v["plaats"] != "Heel Nederland":
        per_stad[v["plaats"]].append(v)
steden = sorted([s for s, l in per_stad.items() if len(l) >= MIN_STAD], key=lambda s: (-len(per_stad[s]), s))
stad_slugs = set()
for s in steden:
    lst = sorteer(per_stad[s])
    sl = slug(s); stad_slugs.add(sl)
    vk = Counter(VAKKEN.get(v["vak"], v["vak"]) for v in lst).most_common(4)
    vk_tekst = ", ".join(f"{n.lower()} ({c})" for n, c in vk)
    body = (f'<p class="meta"><a href="/vacatures/">Vacatures</a> › {e(s)}</p>'
            f'<h1>Vacatures in {e(s)}</h1>'
            f'<p class="intro">Er staan nu {len(lst)} vacatures in {e(s)} op Valcature, rechtstreeks van de websites van werkgevers. De meeste zijn in {e(vk_tekst)}.</p>'
            + cta(f"Zoek je werk in {s}? Doe de quiz en zie welke van deze {len(lst)} vacatures het best bij jou passen.")
            + '<ul class="lijst">' + "".join(vac_html(v) for v in lst) + "</ul>")
    schrijf(f"/vacatures/{sl}/", pagina(f"/vacatures/{sl}/", f"Vacatures in {s}",
            f"{len(lst)} actuele vacatures in {s}, rechtstreeks van werkgevers. Elke dag bijgewerkt.", body,
            [("Valcature", "/"), ("Vacatures", "/vacatures/"), (s, f"/vacatures/{sl}/")]))
ruim_op("vacatures", stad_slugs)

# ---------- Vakgebieden ----------
per_vak = defaultdict(list)
for v in VAC:
    per_vak[v["vak"]].append(v)
vak_slugs = {}
for k, lst in per_vak.items():
    naam = VAKKEN.get(k, k)
    sl = slug(naam); vak_slugs[k] = sl
    lst = sorteer(lst)
    top_steden = ", ".join(f"{s} ({c})" for s, c in Counter(v["plaats"] for v in lst).most_common(4))
    met_sal = [v for v in lst if v.get("sal")]
    sal_zin = ""
    if len(met_sal) >= 3:
        lo = min(v["sal"][0] for v in met_sal); hi = max(v["sal"][1] for v in met_sal)
        sal_zin = f" Bij de {len(met_sal)} vacatures met een salaris ligt dat tussen {euro(lo)} en {euro(hi)} bruto per maand."
    body = (f'<p class="meta"><a href="/vacatures/">Vacatures</a> › {e(naam)}</p>'
            f'<h1>Vacatures in {e(naam.lower())}</h1>'
            f'<p class="intro">Er staan nu {len(lst)} vacatures in {e(naam.lower())} op Valcature. Vooral in {e(top_steden)}.{e(sal_zin)}</p>'
            + cta() + '<ul class="lijst">' + "".join(vac_html(v) for v in lst) + "</ul>")
    schrijf(f"/vakgebied/{sl}/", pagina(f"/vakgebied/{sl}/", f"Vacatures {naam}",
            f"{len(lst)} actuele vacatures in {naam.lower()}, rechtstreeks van werkgevers. Elke dag bijgewerkt.", body,
            [("Valcature", "/"), ("Vacatures", "/vacatures/"), (naam, f"/vakgebied/{sl}/")]))
ruim_op("vakgebied", set(vak_slugs.values()))

# ---------- Overzicht ----------
body = ('<h1>Vacatures per stad en vakgebied</h1>'
        f'<p class="intro">Alle {len(VAC)} vacatures op Valcature komen van de websites van werkgevers zelf. Kies een stad of vakgebied.</p>'
        '<h2>Per stad</h2><ul class="chips">' + "".join(f'<li><a href="/vacatures/{slug(s)}/">{e(s)} ({len(per_stad[s])})</a></li>' for s in steden) + "</ul>"
        '<h2>Per vakgebied</h2><ul class="chips">' + "".join(f'<li><a href="/vakgebied/{vak_slugs[k]}/">{e(VAKKEN.get(k, k))} ({len(per_vak[k])})</a></li>' for k in sorted(per_vak, key=lambda k: -len(per_vak[k]))) + "</ul>"
        + cta())
schrijf("/vacatures/", pagina("/vacatures/", "Vacatures per stad en vakgebied",
        f"{len(VAC)} actuele vacatures van werkgevers in Amsterdam, de Randstad en daarbuiten, per stad en vakgebied.", body,
        [("Valcature", "/"), ("Vacatures", "/vacatures/")]))

# ---------- Tips ----------
anios = [v for v in VAC if v.get("medrol") == "anios"]
anios_sal = [v for v in anios if v.get("sal")]
if anios_sal:
    lo = min(v["sal"][0] for v in anios_sal); hi = max(v["sal"][1] for v in anios_sal)
    anios_cijfers = (f"<p>Op dit moment staan er {len(anios)} ANIOS-vacatures op Valcature. Bij {len(anios_sal)} daarvan noemt de werkgever een salaris: "
                     f"dat ligt tussen <b>{euro(lo)} en {euro(hi)} bruto per maand</b> (het laagste en hoogste bedrag uit die vacatures). Deze cijfers komen rechtstreeks uit de vacatures en worden elke dag opnieuw berekend.</p>")
else:
    anios_cijfers = f"<p>Op dit moment staan er {len(anios)} ANIOS-vacatures op Valcature, maar geen daarvan noemt een salaris. Kijk in de vacature welke cao en schaal de werkgever gebruikt.</p>"

starters = [v for v in VAC if not v.get("ervaring")]
met_sal = [v for v in VAC if v.get("sal")]

TIPS = [
    {"slug": "zo-schrijf-je-een-motivatiebrief", "titel": "Zo schrijf je een motivatiebrief",
     "kort": "Een motivatiebrief in vijf stappen: van een sterke eerste zin tot een duidelijke afsluiting.",
     "body": """
<p>Een goede motivatiebrief is kort, persoonlijk en laat zien dat je de vacature echt hebt gelezen. Een werkgever leest vaak tientallen brieven. Met deze vijf stappen val je op.</p>
<h2>1. Begin met waarom deze baan</h2>
<p>Sla "Hierbij solliciteer ik naar…" over. Begin met wat je aantrekt in deze functie of organisatie. Eén concrete reden is sterker dan drie algemene.</p>
<h2>2. Koppel je ervaring aan hun eisen</h2>
<p>Pak de twee of drie belangrijkste eisen uit de vacature. Laat per eis met een kort voorbeeld zien dat je die beheerst: wat deed je, en wat leverde het op?</p>
<h2>3. Laat zien wie je bent</h2>
<p>Werkgevers zoeken ook iemand die in het team past. Vertel kort hoe je werkt of wat collega's aan je waarderen.</p>
<h2>4. Houd het kort</h2>
<p>Eén A4 is genoeg. Gebruik korte alinea's en schrijf actief: "Ik heb… opgezet" in plaats van "Er werd door mij…".</p>
<h2>5. Sluit duidelijk af</h2>
<p>Zeg dat je graag op gesprek komt en bedank de lezer. Controleer daarna de naam van de contactpersoon, de functietitel en je spelling.</p>
<p><b>Tip:</b> op Valcature staat bij elke vacature de knop <i>Opzet motivatiebrief</i>. Die maakt een eerste opzet op basis van jouw antwoorden, die je daarna zelf aanvult.</p>"""},
    {"slug": "wat-verdien-je-als-anios", "titel": "Wat verdien je als ANIOS?",
     "kort": "Wat een arts niet in opleiding tot specialist verdient, op basis van de vacatures die nu openstaan.",
     "body": """
<p>Een ANIOS is een arts niet in opleiding tot specialist. Veel basisartsen werken eerst een paar jaar als ANIOS voordat ze aan een specialisatie beginnen. Het salaris hangt af van de cao van de werkgever (bijvoorbeeld een umc, een algemeen ziekenhuis of de ggz) en van je ervaring.</p>
<h2>Wat zeggen de vacatures van nu?</h2>
""" + anios_cijfers + """
<h2>Waar let je op?</h2>
<ul><li>Het bedrag is bruto per maand; vakantiegeld en een eindejaarsuitkering komen daar vaak bovenop.</li>
<li>Diensten in de avond, nacht en het weekend leveren meestal een toeslag op.</li>
<li>Werk je minder uren, dan krijg je naar verhouding minder.</li></ul>
<p>Op Valcature zie je bij elke artsenvacature het salaris als de werkgever dat noemt. Doe de quiz en kies bij geneeskunde voor ANIOS om alle open plekken op volgorde van match te zien.</p>"""},
    {"slug": "sollicitatiegesprek-voorbereiden", "titel": "Zo bereid je een sollicitatiegesprek voor",
     "kort": "Met deze voorbereiding ga je rustig en zelfverzekerd je sollicitatiegesprek in.",
     "body": """
<p>Een goede voorbereiding maakt het verschil. Neem er een avond voor en loop deze punten door.</p>
<h2>Ken de organisatie</h2>
<p>Lees de website, recent nieuws en de vacature nog een keer. Bedenk waarom je juist hier wilt werken.</p>
<h2>Bereid voorbeelden voor</h2>
<p>Kies drie situaties uit je werk, studie of bijbaan waarin je iets voor elkaar kreeg. Vertel ze kort: wat was de situatie, wat deed jij, wat was het resultaat?</p>
<h2>Verwacht deze vragen</h2>
<ul><li>Vertel eens wat over jezelf.</li><li>Waarom wil je deze baan?</li><li>Wat zijn je sterke en zwakke punten?</li><li>Vertel over een keer dat iets niet goed ging.</li></ul>
<h2>Stel zelf vragen</h2>
<p>Vraag bijvoorbeeld hoe een gewone werkweek eruitziet, met wie je samenwerkt en wat ze in het eerste halfjaar van je verwachten.</p>
<h2>Praktisch</h2>
<p>Check de route of de link voor een videogesprek, zorg dat je op tijd bent en neem je cv mee.</p>"""},
    {"slug": "salaris-onderhandelen", "titel": "Zo onderhandel je over je salaris",
     "kort": "Praktische tips om rustig en goed voorbereid over je salaris te praten.",
     "body": """
<p>Veel mensen vinden onderhandelen spannend. Met een goede voorbereiding is het gewoon een gesprek.</p>
<h2>Weet wat gebruikelijk is</h2>
<p>Kijk of de werkgever een cao of salarisschaal noemt. Vergelijk vacatures voor vergelijkbare functies: op Valcature staat bij """ + str(len(met_sal)) + """ van de """ + str(len(VAC)) + """ vacatures een salaris.</p>
<h2>Noem een bedrag met een reden</h2>
<p>Onderbouw je wens met je ervaring, je opleiding of wat je in je huidige baan verdient. Een bandbreedte geeft ruimte voor het gesprek.</p>
<h2>Kijk verder dan het brutoloon</h2>
<p>Denk aan thuiswerken, opleidingsbudget, reiskosten, pensioen, extra vrije dagen of een eindejaarsuitkering. Daar is soms meer ruimte.</p>
<h2>Neem bedenktijd</h2>
<p>Je hoeft niet meteen ja te zeggen. Vraag het aanbod op papier en neem een dag om erover na te denken.</p>"""},
    {"slug": "eerste-baan-na-je-studie", "titel": "Je eerste baan na je studie vinden",
     "kort": "Net afgestudeerd? Zo vind je een baan die past bij je studie.",
     "body": """
<p>Net klaar met je studie en geen idee waar te beginnen? Dat is heel normaal. Deze stappen helpen je op weg.</p>
<h2>Zoek op je studie, niet alleen op functietitel</h2>
<p>Functietitels verschillen per werkgever. Kijk vooral welke opleiding een werkgever vraagt. In de Valcature-quiz vul je je studie in, en vacatures die daar echt bij passen komen bovenaan.</p>
<h2>Kijk naar starterfuncties</h2>
<p>Bij """ + str(len(starters)) + """ vacatures op Valcature vraagt de werkgever geen minimaal aantal jaren ervaring. Ook traineeships en werkstudentbanen zijn een goede opstap.</p>
<h2>Gebruik je netwerk</h2>
<p>Vertel docenten, oud-studiegenoten en je stagebegeleider dat je zoekt. Veel banen komen via via.</p>
<h2>Solliciteer gericht</h2>
<p>Tien goede sollicitaties werken beter dan vijftig snelle. Pas je brief en cv per vacature aan.</p>"""},
]

for t in TIPS:
    body = (f'<p class="meta"><a href="/tips/">Tips</a> › {e(t["titel"])}</p><article><h1>{e(t["titel"])}</h1>'
            f'<p class="intro">{e(t["kort"])}</p>{t["body"]}</article>' + cta())
    art = {"@context": "https://schema.org", "@type": "Article", "headline": t["titel"], "description": t["kort"],
           "inLanguage": "nl", "dateModified": BIJGEWERKT, "author": {"@type": "Person", "name": "Valerie Jorissen"},
           "publisher": {"@type": "Organization", "name": "Valcature", "url": SITE}}
    body = f'<script type="application/ld+json">{json.dumps(art, ensure_ascii=False)}</script>' + body
    schrijf(f"/tips/{t['slug']}/", pagina(f"/tips/{t['slug']}/", t["titel"], t["kort"], body,
            [("Valcature", "/"), ("Tips", "/tips/"), (t["titel"], f"/tips/{t['slug']}/")]))
ruim_op("tips", {t["slug"] for t in TIPS})
body = ('<h1>Tips voor je zoektocht</h1><p class="intro">Korte, praktische tips over solliciteren, salaris en je eerste baan.</p><ul class="lijst">'
        + "".join(f'<li class="vac"><h3><a href="/tips/{t["slug"]}/">{e(t["titel"])}</a></h3><p>{e(t["kort"])}</p></li>' for t in TIPS) + "</ul>" + cta())
schrijf("/tips/", pagina("/tips/", "Tips voor solliciteren en je loopbaan", "Praktische tips over motivatiebrieven, sollicitatiegesprekken, salaris en je eerste baan.", body,
        [("Valcature", "/"), ("Tips", "/tips/")]))

# ---------- Sitemap ----------
urls = ["/"] + sorted(geschreven)
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    sm.append(f"  <url><loc>{SITE}{u}</loc><lastmod>{BIJGEWERKT}</lastmod><changefreq>daily</changefreq></url>")
sm.append("</urlset>")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm) + "\n")
print(f"{len(geschreven)} pagina's gemaakt ({len(steden)} steden, {len(vak_slugs)} vakgebieden, {len(TIPS)} tips)")
