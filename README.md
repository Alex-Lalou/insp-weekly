# 🎓 Revue INSP Hebdomadaire — GitHub Actions

Génère automatiquement une revue d'actualité pour l'oral INSP chaque lundi matin et l'envoie par email.

---

## 🚀 Setup en 5 étapes

### 1. Crée le dépôt GitHub
```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/TON_PSEUDO/insp-weekly.git
git push -u origin main
```

### 2. Ajoute les Secrets GitHub
Dans ton dépôt → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Nom | Valeur |
|-----|--------|
| `ANTHROPIC_API_KEY` | Ta clé sur console.anthropic.com |
| `GMAIL_ADDRESS` | ton.adresse@gmail.com |
| `GMAIL_APP_PASSWORD` | Mot de passe d'application Gmail (voir étape 3) |
| `EMAIL_TO` | L'adresse qui reçoit la revue (peut être la même) |

### 3. Crée un mot de passe d'application Gmail
1. Va sur [myaccount.google.com/security](https://myaccount.google.com/security)
2. Active la **validation en 2 étapes** si ce n'est pas fait
3. Cherche **"Mots de passe des applications"**
4. Crée un mot de passe → copie le code à 16 caractères
5. C'est ce code à mettre dans `GMAIL_APP_PASSWORD`

### 4. Vérifie la structure du dépôt
```
insp-weekly/
├── revue_insp.py
├── .github/
│   └── workflows/
│       └── revue_hebdo.yml
└── README.md
```

### 5. Lance un test manuel
Dans ton dépôt GitHub → onglet **Actions** → **Revue INSP Hebdomadaire** → **Run workflow**

---

## ⏰ Fréquence
Le script tourne automatiquement **chaque lundi à 7h00** (heure de Paris).
Pour changer la fréquence, modifie le cron dans `.github/workflows/revue_hebdo.yml` :
```yaml
- cron: "0 6 * * 1"   # lundi 7h Paris
- cron: "0 6 * * 1,3" # lundi + mercredi
- cron: "0 6 * * *"   # tous les jours
```

## ✏️ Personnalisation
- **Thèmes** : modifie la liste `THEMES` dans `revue_insp.py`
- **Période** : par défaut = semaine passée. Change `get_week_range()` pour adapter
- **Prompt** : modifie `SYSTEM_PROMPT` pour affiner le style de la revue
