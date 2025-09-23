# TBM Horaires – Intégration Home Assistant + Carte Lovelace

Affiche les **prochains passages** (temps réel) des lignes TBM (tram / bus / bat³) pour un arrêt donné, via l’API **SIRI-Lite** de Bordeaux Métropole. Aucune page web n’est "scrapée" : on interroge directement l’API temps réel officielle.

---

## ✨ Fonctionnalités

- Recherche de la **ligne** par nom (Liane 1, EXPRESS G, etc.)
- Sélection de **l'arrêt+destination** avec libellé **`<Code de ligne> – <Destination>`** (ex. `B – France Alouette`, `27 – Bordeaux Ravezies`).
- **Temps réel** détecté
- Rafraîchissement périodique (par défaut **toutes les minutes**, configurable).
- Carte Lovelace dédiée

---

## 📦 Intégration

```text
custom_components\tbm_horaires\*.*
```

## 🖼️ Carte Lovelace (frontend)

```text
www\tbm_horaires_card\tbm-horaires-card.js
```

---

## 🔧 Pré-requis

- Home Assistant (Core / OS / Supervised).
- Accès Internet vers l’API SIRI-Lite (domaine Bordeaux Métropole).

---

## 🚀 Intégration

### Installation automatique

- Ajouter l'adresse https://github.com/kpagnat/tbm_horaires dans les ressources HACS
- Dans Paramètres > Appareils et services > Ajouter une intégration et chercher "TBM"

### Installation manuelle

- Copier le dossier **`custom_components/tbm-horaires`** dans le répertoire `config/custom_components/` de votre instance.
- **Redémarrer Home Assistant**.
- Aller dans **Paramètres → Appareils & services → + Ajouter une intégration → TBM Horaires**.

### Création d'un 1er capteur (=une ligne+une direction+un arrêt)

Depuis l'intégration :

- **Sélectionner une ligne** — ex. `Liane 1`.
- **Choisir l'arrêt**
- **Valider l’entité**

> **Nom du capteur créé** : `TBM [Ligne] [Nom arrêt] [Destination]` (friendly_name).

## Carte Lovelace (fichier JS)

1. Copier le dossier **`www/tbm-horaires-card`** dans `config/www/`.
2. Déclarer la ressource : **Paramètres → Tableaux de bord → Ressources → Ajouter**
   - **URL** : `/local/tbm-horaires-card/tbm-horaires-card.js?v=1.0.0`
   - **Type** : *JavaScript Module*
3. Ajouter la carte (Carte **Manuelle**) (avec éditeur) :

```yaml
type: custom:tbm-horaires-card
entity: sensor.tbm_1_goillot_pessac_cap_de_bos
count: 3
line_bg: "#00B1EB"
# Personnalisation optionnelle du badge temps réel
realtime_icon: mdi:wifi
realtime_bg: var(--info-color)
realtime_color: '#ffffff'
```

![Example de carte](card.png)

---

### Logs de debug (configuration)

```yaml
logger:
  default: info
  logs:
    custom_components.tbm_horaires: debug
```

---

## 🔒 Respect des données

- Source : **API SIRI-Lite** de Bordeaux Métropole (clé publique).
- Aucune donnée personnelle n’est collectée.

---
