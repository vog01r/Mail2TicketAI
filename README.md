# Mail Support Bot

Ce projet permet d'automatiser le support utilisateur via une boîte mail dédiée. Le bot lit les nouveaux messages entrants, tente de résoudre les problèmes en dialoguant avec l'utilisateur par e-mail (grâce à l'IA OpenAI), et propose des solutions directement par mail. Si le problème est trop complexe à résoudre automatiquement, ou si l'utilisateur formule une demande explicite d'escalade (par exemple avec des phrases comme « merci d'escalader », « je souhaite un support humain », ou des synonymes), le script prend lui-même la décision de créer un ticket sur GitLab et informe l'utilisateur de l'escalade et de la création du ticket.

Ce système permet de gagner énormément de temps de traitement pour l'équipe support : il gère automatiquement 80 à 90% des demandes, notamment en filtrant les messages inutiles ou sans suite (ex : « hello », « salut », « ça va » sans question réelle). Seules les demandes nécessitant une intervention humaine ou une escalade sont transmises à l'équipe via GitLab et une notification webhook.

## Fonctionnalités principales
- Lecture automatique des nouveaux e-mails non lus
- Réponse automatique à l'utilisateur avec l'aide de l'API OpenAI
- Tentative de résolution des problèmes par mail, avec relance pour obtenir plus de détails si besoin
- Détection linguistique des demandes d'escalade (synonymes, formulations variées)
- Création automatique d'un ticket GitLab si besoin
- Notification d'escalade via un webhook (ex : Google Chat)
- Filtrage automatique des messages non pertinents ou sans suite

## Prérequis
- Python 3.8 ou supérieur
- Un compte OpenAI avec une clé API
- Un compte e-mail compatible IMAP/SMTP
- Un projet GitLab (pour la création d'issues)
- Un webhook (optionnel, pour notifications)

## Installation
1. **Clonez le dépôt**
   ```bash
   git clone <url-du-repo>
   cd <nom-du-repo>
   ```
2. **Installez les dépendances**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configurez les variables d'environnement**
   - Copiez le fichier `.env.example` en `.env` :
     ```bash
     cp .env.example .env
     ```
   - Modifiez le fichier `.env` avec vos propres informations (voir section suivante).

## Configuration
Le fichier `.env` doit contenir toutes les informations nécessaires (voir `.env.example`).

**Exemple de configuration :**
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_ACCOUNT=adresse-support@domaine.com
EMAIL_PASSWORD=motdepasseapplication
IMAP_SERVER=imap.exemple.com
IMAP_PORT=993
SMTP_SERVER=smtp.exemple.com
SMTP_PORT=587
PROGRESS_THRESHOLD=0.8
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_PROJECT_ID=123
GITLAB_BASE_URL=https://gitlab.exemple.com
WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/xxxx/messages?key=xxxx&token=xxxx
SUPPORT_EMAIL=adresse-support@domaine.com
```

## Lancement du bot
```bash
python app.py
```

Le bot tourne en continu et surveille la boîte mail.

## Personnalisation
- Modifiez le prompt dans `app.py` pour changer le ton ou la signature des réponses.
- Adaptez le seuil d'escalade (`PROGRESS_THRESHOLD`) selon vos besoins.

## Sécurité
- **Ne partagez jamais votre fichier `.env` en public !**
- Utilisez des mots de passe d'application pour les comptes e-mail.

## Licence
Ce projet est fourni sans garantie. À adapter selon vos besoins. 