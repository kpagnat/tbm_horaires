
// ===== Card (compact vertical) =====
class TbmHorairesCard extends HTMLElement {

  // Whenever the state changes, a new `hass` object is set. Use this to
  // update your content.
  set hass(hass) {
    
    const cfg = this.config || {};

    // Initialize the content if it's not there yet.
    if (!this.is_template_defined) {
      const pillBg  = cfg.line_bg    || 'var(--primary-color)';
      const pillCol = cfg.line_color || '#fff';
      const rtBg    = cfg.realtime_bg    || 'var(--info-color, #1976d2)';
      const rtColor = cfg.realtime_color || '#fff';
      const isHorizontal = cfg.horizontal || false;

      this.innerHTML = `
      <ha-card>
        <style>
          .wrap{padding:12px}
          .header{display:flex;align-items:center;gap:10px;margin-bottom:8px}
          .pill{
            flex:0 0 auto; display:inline-flex; align-items:center; justify-content:center;
            width:32px; height:32px; border-radius:10px;
            background:${pillBg}; color:${pillCol}; font-weight:700;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
          }
          .head-text{display:flex;flex-direction:column;min-width:0}
          .head-text-horz{display:flex;flex-direction:row;gap:5px;align-items: center;min-width:0}
          .ttl{font-weight:700;font-size:1.05rem;line-height:1.15}
          .sub{opacity:.8;font-size:.95rem}
          .list{display:flex;flex-direction:column;margin-top:8px}
          .list-horz{display:flex;flex-direction:row;}
          .row{
            display:flex;align-items:center;gap:8px;
            padding:4px 8px;  /* très compact */
            min-height:0; line-height:1.1;
          }
          .row:nth-child(even){
            background: var(--secondary-background-color, rgba(0,0,0,0.04));
            border-radius:8px;
          }
          .rt{
            display:inline-flex;align-items:center;justify-content:center;
            width:16px;height:16px;border-radius:50%;
            background: var(--tbm-rt-bg, ${rtBg}); color: var(--tbm-rt-color, ${rtColor});
            flex:0 0 auto;
          }
          .rt ha-icon{ --mdc-icon-size: 12px; }
          .min{font-variant-numeric: tabular-nums; font-weight:600}
          .empty{opacity:.7;padding:6px 0}
        </style>

        <div class="wrap">
          <div class="header">
            <div class="pill" aria-label="Ligne" style="display:none;"></div>
            <div class="${isHorizontal ? "head-text-horz" :"head-text"}">
              <div class="ttl"></div>
              <div class="sub"></div>
            </div>
          </div>

          <div id="list" class="${isHorizontal ? "list-horz" :"list"}"></div>
        </div>
      </ha-card>
    `;

      this.is_template_defined = true;
      this._els = {
        pill: this.querySelector('.pill'),
        ttl:  this.querySelector('.ttl'),
        sub:  this.querySelector('.sub'),
        list: this.querySelector('#list'),
      };

      // Expose realtime colors via CSS vars for incremental updates
      this.style.setProperty('--tbm-rt-bg', rtBg);
      this.style.setProperty('--tbm-rt-color', rtColor);
    }

    // Récupération de l'entité
    const st = hass?.states?.[cfg.entity];
    if (!st) {
      this._els.ttl.textContent = 'Entité introuvable';
      this._els.sub.textContent = '';
      this._els.pill.style.display = 'none';
      this._els.list.innerHTML = `<div class="empty">Vérifiez la configuration de la carte.</div>`;
      return;
    }

    // Mise à jour nécessaire ?
    if(this.last_changed == st["last_changed"])
      return

    // UPDATE
    this.last_changed = st["last_changed"]
    
    // console.log("=== UPDATE ! ===")
    // console.log(cfg);
    // console.log(st);

    // ===== Pour déterminer le numéro de la ligne (Liane 1 > 1) =====
    const formatBadgeTitle = (s) => {
      if (!s) 
        return "";
      return Array.from(String(s).matchAll(/(?:^|[\s-])([\p{L}\p{N}])/gu))
        .map(([, ch]) => ch.toUpperCase())
        .join("");
    };

    const a = st.attributes || {};
    const count = Number(cfg.count ?? 3);
    const deps = (a.departures || []).slice(0, count);

    const rawLine = cfg.line || a.line || a.line_name || "";
    const badgeTitle = cfg.line_title || formatBadgeTitle(rawLine);
    const stop = cfg.stop || a.stop || st.attributes.friendly_name || "TBM";
    const title = `${stop}`.trim();
    const subtitle = a.destination || a.dest_label || "";

    // Styles config (update without rebuilding <style>)
    const pillBg  = cfg.line_bg        || 'var(--primary-color)';
    const pillCol = cfg.line_color     || '#fff';
    const rtBg    = cfg.realtime_bg    || 'var(--info-color, #1976d2)';
    const rtColor = cfg.realtime_color || '#fff';
    this._els.pill.style.background = pillBg;
    this._els.pill.style.color = pillCol;
    this.style.setProperty('--tbm-rt-bg', rtBg);
    this.style.setProperty('--tbm-rt-color', rtColor);

    // Header
    if (badgeTitle) {
      this._els.pill.textContent = badgeTitle;
      this._els.pill.setAttribute('aria-label', `Ligne ${badgeTitle}`);
      this._els.pill.style.display = '';
    } else {
      this._els.pill.style.display = 'none';
    }
    this._els.ttl.textContent = title;
    this._els.sub.textContent = subtitle || '';

    // Body list (replace only when changed)
    const rtIcon  = cfg.realtime_icon  || "mdi:wifi";
    const nextHTML = deps.length
      ? deps.map(d => `
          <div class="row" title="${d.realtime ? "Temps réel" : "Horaire théorique"}">
            <span class="min">${(d.in_min ?? "—")} min</span>
            ${d.realtime ? `<span class="rt" aria-label="temps réel"><ha-icon icon="${rtIcon}"></ha-icon></span>` : ""}
          </div>`).join("")
      : `<div class="empty">Aucun passage à afficher</div>`;

    this._els.list.innerHTML = nextHTML;
  }

  // The user supplied configuration. Throw an exception and Home Assistant
  // will render an error card.
  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
    this.last_changed = "";
    this.is_template_defined = false;
  }

  // The height of your card. Home Assistant uses this to automatically
  // distribute all cards over the available columns in masonry view
  getCardSize() {
    return 2;
  }

  static getStubConfig(hass){
    const anyEntity = Object.keys(hass?.states || {}).find(k => k.startsWith("sensor.tbm"));
    return { entity: anyEntity || "", count: 3 };
  }

  static getConfigForm() {

    const SCHEMA = [
      { name: "entity", required: true, selector: { entity: {} } },
      { name: "horizontal", selector: { boolean: {} } },
      {
        type: "grid",
        name: "",
        schema: [
          { name: "line_title", selector: { text: { } } },
          { name: "line_bg", selector: { text: { } } },
          { name: "line_color", selector: { text: { } } }
        ]
      },
      {
        type: "grid",
        name: "",
        schema: [
          { name: "realtime_icon", selector: { icon: { } } },
          { name: "realtime_bg", selector: { text: { } } },
          { name: "realtime_color", selector: { text: { } } }
        ]
      }
    ];

    const assertConfig = (config) => {
    };

    const computeLabel = (schema) => {
      if (schema.name == "horizontal")
        return "Affichage horizontal";
      if (schema.name == "entity")
        return "Entité (créée par l'intégration)";
      if (schema.name == "line_title")
        return "Nom dans le badge";
      if (schema.name == "line_bg")
        return "Couleur de fond du badge de la ligne";
      if (schema.name == "line_color")
        return "Couleur de texte du badge de la ligne";
      if (schema.name == "realtime_icon")
        return "Icône 'temps réel'";
      if (schema.name == "realtime_bg")
        return "Couleur de fond de l'icône 'temps réel'";
      if (schema.name == "realtime_color")
        return "Couleur de texte de l'icône 'temps réel'";
    };

    return {
      schema: SCHEMA,
      assertConfig: assertConfig,
      computeLabel: computeLabel,
    };
  }
}

customElements.define("tbm-horaires-card", TbmHorairesCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'tbm-horaires-card',
  name: 'TBM Horaires',
  description: 'Prochains passages TBM',
  preview: true
});
