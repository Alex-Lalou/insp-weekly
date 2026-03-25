"""
revue_insp.py
Génère une revue d'actualité INSP hebdomadaire via l'API Anthropic
et l'envoie par email via Gmail SMTP.

Variables d'environnement requises (à définir dans GitHub Secrets) :
  ANTHROPIC_API_KEY   → ta clé API Anthropic
  GMAIL_ADDRESS       → ton adresse Gmail expéditrice
  GMAIL_APP_PASSWORD  → mot de passe d'application Gmail (pas ton mdp principal)
  EMAIL_TO            → adresse destinataire (peut être la même)
"""

import os
import json
import datetime
import smtplib
import anthropic
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ────────────────────────────────────────────────────────────────────

THEMES = [
    {"id": "politique",     "label": "Politique intérieure",        "icon": "🏛️"},
    {"id": "economie",      "label": "Économie & Finances",          "icon": "📈"},
    {"id": "international", "label": "International & Géopolitique", "icon": "🌍"},
    {"id": "social",        "label": "Social & Société",             "icon": "🤝"},
    {"id": "environnement", "label": "Environnement & Transition",   "icon": "🌿"},
    {"id": "droit",         "label": "Droit & Institutions",         "icon": "⚖️"},
]

SYSTEM_PROMPT = """Tu es un préparateur expert du concours externe de l'INSP. Tu structures l'actualité en revue thématique pour l'oral.

Pour la période demandée, identifie les faits marquants dans chaque thématique.
- 2 faits max par thématique
- Résumé en 2-3 phrases, enjeux en 1 phrase, 1-2 questions pour l'oral
- Indique la source (titre + URL) pour chaque fait si disponible

Format de réponse : JSON uniquement, sans balises markdown :
{
  "periode": "...",
  "themes": {
    "politique":      { "faits": [{"titre":"...","resume":"...","enjeux":"...","questions_oral":["..."],"sources":[{"titre":"...","url":"..."}]}], "point_chaud": false },
    "economie":       { "faits": [], "point_chaud": false },
    "international":  { "faits": [], "point_chaud": false },
    "social":         { "faits": [], "point_chaud": false },
    "environnement":  { "faits": [], "point_chaud": false },
    "droit":          { "faits": [], "point_chaud": false }
  },
  "conseil_oral": "..."
}"""


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_week_range():
    """Retourne (lundi, dimanche) de la semaine passée."""
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + datetime.timedelta(days=6)
    return last_monday, last_sunday


def format_date_fr(d: datetime.date) -> str:
    months = ["janvier","février","mars","avril","mai","juin",
              "juillet","août","septembre","octobre","novembre","décembre"]
    return f"{d.day} {months[d.month - 1]} {d.year}"


def generate_review(date_debut: str, date_fin: str) -> dict:
    """Appelle l'API Anthropic et retourne le JSON parsé."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Génère la revue de l'actualité française et internationale "
                f"du {date_debut} au {date_fin} pour l'oral INSP. "
                f"Réponds UNIQUEMENT avec le JSON demandé, rien d'autre."
            )
        }]
    )

    full_text = ""
    for block in response.content:
        if block.type == "text":
            full_text += block.text

    import re
    from json_repair import repair_json

    # Nettoie les balises markdown
    full_text = re.sub(r"```(?:json)?", "", full_text).replace("```", "").strip()

    # Extrait le JSON entre { et }
    j0 = full_text.index("{")
    j1 = full_text.rindex("}") + 1
    json_str = full_text[j0:j1]

    # json_repair corrige automatiquement tout JSON malformé
    return json.loads(repair_json(json_str))


# ── EMAIL BUILDER ─────────────────────────────────────────────────────────────

def build_html_email(revue: dict, date_debut: str, date_fin: str) -> str:
    themes_html = ""
    for t in THEMES:
        td = revue.get("themes", {}).get(t["id"], {})
        faits = td.get("faits", [])
        if not faits:
            continue
        hot = td.get("point_chaud", False)
        faits_html = ""
        for f in faits:
            sources_html = ""
            for s in f.get("sources", []):
                sources_html += f'<a href="{s["url"]}" style="color:#1a5296;font-size:11px">{s.get("titre", s["url"])}</a> '
            questions_html = "".join(
                f'<div style="font-size:12px;color:#555;font-style:italic;margin:2px 0">→ {q}</div>'
                for q in f.get("questions_oral", [])
            )
            faits_html += f"""
            <div style="margin-bottom:14px;padding:12px 14px;border:1px solid {'#e08080' if hot else '#ddd'};border-radius:5px;background:{'#fff8f8' if hot else '#fff'}">
              <strong style="color:#1a2d42;font-size:14px">{f['titre']}</strong><br/>
              <span style="font-size:13px;color:#333;line-height:1.6">{f['resume']}</span>
              {f'<div style="margin-top:8px;font-size:12px;color:#555;border-left:3px solid #b8960c;padding-left:8px"><strong>Enjeux :</strong> {f["enjeux"]}</div>' if f.get('enjeux') else ''}
              {f'<div style="margin-top:8px">{questions_html}</div>' if questions_html else ''}
              {f'<div style="margin-top:8px">{sources_html}</div>' if sources_html else ''}
            </div>"""

        themes_html += f"""
        <h3 style="color:#1a2d42;border-left:4px solid #b8960c;padding-left:10px;margin:24px 0 12px;font-size:14px;text-transform:uppercase;letter-spacing:.04em">
          {t['icon']} {t['label']}{' 🔴' if hot else ''}
        </h3>
        {faits_html}"""

    conseil = revue.get("conseil_oral", "")

    return f"""
    <div style="font-family:Georgia,serif;max-width:680px;margin:0 auto;color:#111">
      <div style="background:#1a2d42;color:#f0e6c8;padding:22px 28px;border-radius:8px 8px 0 0">
        <h1 style="margin:0;font-size:20px">🎓 Revue de l'Actualité — INSP</h1>
        <p style="margin:5px 0 0;font-size:11px;opacity:.65;letter-spacing:.07em">PRÉPARATION À L'ÉPREUVE ORALE · CONCOURS EXTERNE</p>
      </div>
      <div style="border:1px solid #ddd;border-top:none;padding:22px 28px;border-radius:0 0 8px 8px;background:#fafafa">
        <div style="background:#fffbe6;border:1px solid #d4af37;padding:10px 16px;border-radius:5px;font-size:13px;margin-bottom:20px">
          📅 <strong>Période :</strong> du {date_debut} au {date_fin}<br/>
          {f'💡 <em>{conseil}</em>' if conseil else ''}
        </div>
        {themes_html}
        <hr style="margin:28px 0;border:none;border-top:1px solid #eee"/>
        <p style="font-size:11px;color:#aaa;text-align:center;margin:0">
          Revue générée automatiquement · INSP Oral Prep · GitHub Actions
        </p>
      </div>
    </div>"""


def send_email(html_body: str, subject: str):
    """Envoie l'email via Gmail SMTP."""
    gmail_address  = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    email_to       = os.environ["EMAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = email_to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, email_to, msg.as_string())

    print(f"✅ Email envoyé à {email_to}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    lundi, dimanche = get_week_range()
    date_debut = format_date_fr(lundi)
    date_fin   = format_date_fr(dimanche)

    print(f"📰 Génération de la revue du {date_debut} au {date_fin}…")

    revue = generate_review(date_debut, date_fin)
    print("✅ Revue générée")

    html  = build_html_email(revue, date_debut, date_fin)
    subj  = f"Revue INSP — semaine du {date_debut} au {date_fin}"
    send_email(html, subj)


if __name__ == "__main__":
    main()
