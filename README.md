# TBM Horaires – Intégration Home Assistant + Carte Lovelace

Affiche les **prochains passages** (temps réel) des lignes TBM (tram / bus / bat³) pour un arrêt donné, via l’API **SIRI-Lite** de Bordeaux Métropole. Aucune page web n’est "scrapée" : on interroge directement l’API temps réel officielle.

---

## ✨ Fonctionnalités

- Recherche d’arrêt par nom (**config flow**).
- Sélection du **quai** (StopPoint) avec libellé **`<Code de ligne> – <Destination>`** (ex. `B – France Alouette`, `27 – Bordeaux Ravezies`).
- Sélection **Ligne** et **Destination** (listes déroulantes).
- **Temps réel** détecté (si `ExpectedTime ≠ AimedTime`).
- Rafraîchissement périodique (par défaut toutes **60–120 s**, configurable).
- Attributs riches : liste `departures` (minutes, destination, realtime…)
- Carte Lovelace dédiée (chips minutes, badge *wifi* bleu pour le temps réel).
- (Option) 2ᵉ et 3ᵉ passages sous forme de **capteurs séparés**.

---

## 📦 Intégration

```text
tbm_horaires_integration/
├─ __init__.py
├─ api.py
├─ config_flow.py
├─ const.py
├─ coordinator.py
├─ manifest.json
├─ sensor.py
├─ strings.json                # base en (obligatoire)
└─ translations/
   └─ fr.json                  # traductions FR
```

## 🖼️ Carte Lovelace (frontend)

```text
tbm_horaires_card/tbm-horaires-card.js
```

---

## 🔧 Pré-requis

- Home Assistant (Core / OS / Supervised).
- Accès Internet vers l’API SIRI-Lite (domaine Bordeaux Métropole).
- Droits d’écriture sur `config/` (pour déposer les fichiers).

---

## 🚀 Installation (manuelle)

### 1) Intégration (`custom_components`)

1. Copier le dossier **`tbm-horaires-integration`** dans le répertoire `config/custom_components/` de votre instance.
2. **Redémarrer Home Assistant**.
3. Aller dans **Paramètres → Appareils & services → + Ajouter une intégration → TBM Horaires**.
4. Étapes de configuration :
   - **Rechercher un arrêt** — saisissez par ex. `La Cité du Vin`.
   - **Choisir le quai (StopPoint)** — la liste affiche des libellés **`<Code> – <Destination>`**; s’il n’y a pas de passage imminent, un fallback `Nom [id]` peut apparaître (normal tard le soir).
   - **Choisir Ligne et Destination** — listes déroulantes.
   - **Nom de l’entité** proposé par défaut : `Nom arrêt – Destination`.

> **Nom du capteur créé** : `TBM [Ligne] [Nom arrêt] [Destination]` (friendly_name).

### 2) Carte Lovelace (fichier JS)

1. Copier **`tbm-horaires-card/tbm-horaires-card.js`** dans `config/www/tbm-horaires-card`.
2. Déclarer la ressource : **Paramètres → Tableaux de bord → Ressources → Ajouter**
   - **URL** : `/local/tbm-horaires-card/tbm-horaires-card.js?v=1.0.0`
   - **Type** : *JavaScript Module*
3. Ajouter la carte (Carte **Manuelle**) :

```yaml
type: custom:tbm-horaires-card
entity: sensor.tbm_b_la_cite_du_vin_france_alouette
count: 3
title: La Cité du Vin
subtitle: Tram B → France Alouette
# Personnalisation optionnelle du badge temps réel
realtime_icon: mdi:wifi
realtime_bg: var(--info-color)
realtime_color: '#ffffff'
```

> **Astuce cache** : si vous modifiez le JS, incrémentez `?v=` ou forcez le rafraîchissement du navigateur.

---

## 🧠 Utilisation & données exposées

- **État** du capteur = minutes du **prochain passage** (ex. `4 min`).
- **Attributs** principaux :
  - `stop`, `line`, `destination`
  - `departures`: tableau des prochaines visites (jusqu’à 8), avec :
    - `in_min` (minutes), `line_name`, `destination`, `realtime` (bool), `time_expected` (ISO).

### (Option) 2ᵉ et 3ᵉ passages en capteurs dédiés

Deux approches :

1. **Variante intégration** (si activée dans `sensor.py`) : deux entités supplémentaires sont créées automatiquement, suffixées **`- 2e`** et **`- 3e`**.
2. **Capteurs Template** :

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "TBM B La Cité du Vin France Alouette - 2e"
        unit_of_measurement: "min"
        state: >
          {% set deps = state_attr('sensor.tbm_b_la_cite_du_vin_france_alouette','departures') or [] %}
          {% if deps|length > 1 %}{{ (deps[1].in_min)|int(0) }}{% endif %}
      - name: "TBM B La Cité du Vin France Alouette - 3e"
        unit_of_measurement: "min"
        state: >
          {% set deps = state_attr('sensor.tbm_b_la_cite_du_vin_france_alouette','departures') or [] %}
          {% if deps|length > 2 %}{{ (deps[2].in_min)|int(0) }}{% endif %}
```

---

## ⚙️ Réglages utiles

- `const.py` :
  - `DEFAULT_INTERVAL_SEC` — intervalle de rafraîchissement (ex. `60` ou `120`).
  - `DEFAULT_PREVIEW` — fenêtre des prochains passages demandés à l’API (ex. `PT40M`, `PT90M`).
- **Labels lors du choix du quai** : la sonde essaie successivement `PT10M`, `PT90M`, puis `PT20H` pour couvrir la nuit (permet d’afficher `Code – Destination` même en l’absence de passage immédiat).

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

## 💡 Idées d’amélioration

- Couleurs/icônes par ligne (via `lines-discovery`) dans la carte.
- Options flow : choisir combien de passages publier (1/2/3).
- Multi-entités depuis un même arrêt (plusieurs lignes/destinations).
