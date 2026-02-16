import streamlit as st
import feedparser
import requests
import re
from bs4 import BeautifulSoup
from mistralai import Mistral

# ==============================
# CONFIGURATION MISTRAL
# ==============================

client = Mistral(api_key="yLoE1iD8DZpbusRDpVQ44wmyc2uIqaTx")

MAX_CHARS = 12000  # Limite envoyée à Mistral


# ==============================
# FONCTION : EXTRACTION ARTICLE COMPLET
# ==============================

@st.cache_data(show_spinner=False)
def extraire_texte_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Supprimer éléments inutiles
        for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        texte = "\n".join(p.get_text() for p in paragraphs)

        texte = re.sub(r'\s+', ' ', texte)

        return texte.strip()

    except Exception:
        return ""


# ==============================
# FONCTION : NETTOYAGE HTML SIMPLE (fallback)
# ==============================

def nettoyer_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)


# ==============================
# FONCTION : GENERATION RESUME
# ==============================

def generer_resume(texte):
    try:
        texte_utilise = texte[:MAX_CHARS]

        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Fais un résumé de l'article suivant en 5 points majeurs.

Le résumé commencera par une problématique générale formulée sous forme de question paradoxale.

Ensuite :
- 5 points différenciés par des emojis adaptés
- Chaque point contient, au format bullet point :
    • un titre court
    • une explication synthétique
    • si présent dans l'article : un chiffre ou exemple précis

Article :
{texte_utilise}
"""
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Erreur Mistral : {str(e)}"


# ==============================
# INTERFACE STREAMLIT
# ==============================

st.set_page_config(page_title=" News AI ", layout="wide")
st.title("🗞️ Plateforme médiatique multiscalaire 🗞️")

RSS_FEEDS = {
    "🧠 La Vie des Idées": "https://laviedesidees.fr/spip.php?page=backend",
    "🌍 Diploweb": "https://www.diploweb.com/spip.php?page=backend",
    "📚 Telos": "https://www.telos-eu.com/fr/rss.xml",
    "📰 Institut Montaigne": "https://www.institutmontaigne.org/rss.xml",
    "👁 Les Yeux du Monde": "https://les-yeux-du-monde.fr/feed"
}

# ==============================
# TRAITEMENT DES FLUX
# ==============================

for nom_flux, url_flux in RSS_FEEDS.items():

    st.header(nom_flux)
    flux = feedparser.parse(url_flux)

    if not flux.entries:
        st.error(f"Flux vide ou invalide pour {nom_flux}")
        continue

    key_affichage = f"show_all_{nom_flux}"

    if key_affichage not in st.session_state:
        st.session_state[key_affichage] = False

    if st.session_state[key_affichage]:
        articles_a_afficher = flux.entries
    else:
        articles_a_afficher = flux.entries[:5]

    for article in articles_a_afficher:

        with st.expander(f"📌 {article.title}"):

            st.write(f"**Auteur** : {article.get('author', 'Inconnu')}")
            st.write(f"**Source** : {flux.feed.get('title', nom_flux)}")

            # --- EXTRACTION TEXTE COMPLET ---
            texte_complet = extraire_texte_article(article.link)

            # Fallback si extraction échoue
            if len(texte_complet) < 800:
                texte_complet = nettoyer_html(article.get('summary', ''))

            st.write(f"**Aperçu :** {texte_complet[:500]}...")

            key_resume = f"resume_{nom_flux}_{article.link}"

            if key_resume not in st.session_state:
                st.session_state[key_resume] = None

            if st.button("✨ Résumé L2", key=f"btn_{key_resume}"):

                with st.spinner("Analyse en cours..."):
                    resume = generer_resume(texte_complet)
                    st.session_state[key_resume] = resume

            if st.session_state[key_resume]:
                st.info(st.session_state[key_resume])

            st.markdown(f"🧐 [Lire l'article complet]({article.link})")

            # ==============================
            # BOUTON NOTEBOOKLM (TEXTE COMPLET)
            # ==============================

            if st.button("💬 Poser des questions à l'article", key=f"ask_{key_resume}"):

                st.text_area(
                    "Texte prêt à être copié dans NotebookLM :",
                    texte_complet,
                    height=300
                )

                st.link_button(
                    "Ouvrir NotebookLM",
                    "https://notebooklm.google.com/notebook/6c5a02cc-b53e-4247-895d-501b4b938951?addSource=true"
                )

    # ==============================
    # BOUTON AFFICHER PLUS / REDUIRE
    # ==============================

    if not st.session_state[key_affichage] and len(flux.entries) > 5:

        if st.button("⬇️ Afficher plus", key=f"more_{nom_flux}"):
            st.session_state[key_affichage] = True
            st.rerun()

    elif st.session_state[key_affichage]:

        if st.button("⬆️ Réduire", key=f"less_{nom_flux}"):
            st.session_state[key_affichage] = False
            st.rerun()
