"""
revue_insp.py
Génère une revue d'actualité INSP hebdomadaire via l'API Anthropic
et l'envoie par email via Gmail SMTP.

Variables d'environnement requises (GitHub Secrets) :
  ANTHROPIC_API_KEY   → clé API Anthropic
  GMAIL_ADDRESS       → adresse Gmail expéditrice
  GMAIL_APP_PASSWORD  → mot de passe d'application Gmail
  EMAIL_TO            → adresse(s) destinataire(s), séparées par des virgules
"""

import os
import datetime
import smtplib
import anthropic
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── PROMPT ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un préparateur expert du concours externe de l'INSP. Tu rédiges une revue de l'actualité hebdomadaire pour aider les candidats à préparer l'épreuve orale.

Pour chaque thématique, rédige 2 faits marquants avec ce format exact :

---
THÉMATIQUE : Politique intérieure 🏛️
FAIT 1 : [titre du fait]
Résumé : [2-3 phrases de contexte]
Enjeux : [1 phrase sur les enjeux]
Questions oral : [1-2 questions type jury]

FAIT 2 : [titre du fait]
Résumé : [2-3 phrases de contexte]
Enjeux : [1 phrase sur les enjeux]
Questions oral : [1-2 questions type jury]

---
THÉMATIQUE : Économie & Finances 📈
[même structure]

---
[et ainsi de suite pour les 6 thématiques]

CONSEIL ORAL DE LA SEMAINE : [1 conseil général]
---

Couvre ces 6 thématiques dans cet ordre :
1. Politique intérieure
2. Économie & Finances
3. International & Géopolitique
4. Social & Société
5. Environnement & Transition
6. Droit & Institutions"""


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_week_range():
    """Retourne (lundi, dimanche) de la semaine passée."""
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + datetime.timedelta(days=6)
    return last_monday, last_sunday


def format_date_fr(d: datetime.date) -> str:
    months = ["janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{d.day} {months[d.month - 1]} {d.year}"


# ── GÉNÉRATION ────────────────────────────────────────────────────────────────

def generate_review(date_debut: str, date_fin: str) -> str:
    """Appelle l'API Anthropic et retourne le texte brut de la revue."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Génère la revue de l'actualité du {date_debut} au {date_fin} pour l'oral INSP."
        }]
    )

    for block in response.content:
        if hasattr(block, "text"):
            return block.text


# ── EMAIL BUILDER ─────────────────────────────────────────────────────────────

def text_to_html(texte: str, date_debut: str, date_fin: str) -> str:
    """Convertit le texte structuré en HTML pour l'email."""
    lignes = texte.strip().split("\n")
    html_body = ""

    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne or ligne == "---":
            continue
        elif ligne.startswith("THÉMATIQUE :"):
            html_body += f'<h3 style="color:#1a2d42;border-left:4px solid #b8960c;padding-left:10px;margin:24px 0 8px;font-size:14px;text-transform:uppercase">{ligne.replace("THÉMATIQUE : ", "")}</h3>'
        elif ligne.startswith("FAIT "):
            html_body += f'<p style="font-weight:bold;color:#1a2d42;margin:12px 0 4px">{ligne}</p>'
        elif ligne.startswith("Résumé :"):
            html_body += f'<p style="font-size:13px;color:#333;margin:4px 0;line-height:1.6">{ligne}</p>'
        elif ligne.startswith("Enjeux :"):
            html_body += f'<p style="font-size:12px;color:#555;border-left:3px solid #b8960c;padding-left:8px;margin:6px 0">{ligne}</p>'
        elif ligne.startswith("Questions oral :"):
            html_body += f'<p style="font-size:12px;color:#444;font-style:italic;margin:4px 0">❓ {ligne}</p>'
        elif ligne.startswith("CONSEIL ORAL"):
            html_body += f'<div style="background:#fffbe6;border:1px solid #d4af37;padding:10px 16px;border-radius:5px;font-size:13px;margin:20px 0">💡 {ligne}</div>'
        else:
            html_body += f'<p style="font-size:13px;color:#333;margin:3px 0">{ligne}</p>'

    return f"""
    <div style="font-family:Georgia,serif;max-width:680px;margin:0 auto;color:#111">
      <div style="background:#1a2d42;color:#f0e6c8;padding:22px 28px;border-radius:8px 8px 0 0">
        <h1 style="margin:0;font-size:20px">🎓 Revue de l'Actualité — INSP</h1>
        <p style="margin:5px 0 0;font-size:11px;opacity:.65;letter-spacing:.07em">PRÉPARATION À L'ÉPREUVE ORALE · CONCOURS EXTERNE</p>
      </div>
      <div style="border:1px solid #ddd;border-top:none;padding:22px 28px;border-radius:0 0 8px 8px;background:#fafafa">
        <div style="background:#e8f0e8;border:1px solid #7ab87a;padding:10px 16px;border-radius:5px;font-size:13px;margin-bottom:20px">
          📅 <strong>Semaine du {date_debut} au {date_fin}</strong>
        </div>
        {html_body}
        <hr style="margin:28px 0;border:none;border-top:1px solid #eee"/>
        <p style="font-size:11px;color:#aaa;text-align:center;margin:0">
          Revue générée automatiquement · INSP Oral Prep · GitHub Actions
        </p>
      </div>
    </div>"""


# ── ENVOI EMAIL ───────────────────────────────────────────────────────────────

def send_email(html_body: str, subject: str):
    """Envoie l'email via Gmail SMTP."""
    gmail_address  = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    email_to       = os.environ["EMAIL_TO"]

    destinataires = [e.strip() for e in email_to.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = ", ".join(destinataires)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, destinataires, msg.as_string())

    print(f"✅ Email envoyé à {email_to}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    lundi, dimanche = get_week_range()
    date_debut = format_date_fr(lundi)
    date_fin   = format_date_fr(dimanche)

    print(f"📰 Génération de la revue du {date_debut} au {date_fin}…")

    texte = generate_review(date_debut, date_fin)
    print("✅ Revue générée")

    html = text_to_html(texte, date_debut, date_fin)
    subj = f"Revue INSP — semaine du {date_debut} au {date_fin}"
    send_email(html, subj)
    print("✅ Email envoyé")


if __name__ == "__main__":
    main()
