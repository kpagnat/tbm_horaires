(() => {
  "use strict";

  // ===== Helpers =====
  const lineCodeOf = (s) => {
    if (!s) return "";
    const m = String(s).trim().match(/([A-Z]{1,3}|\d{1,3})$/i);
    return (m ? m[1] : String(s)).toUpperCase();
  };

  // ===== Card (compact vertical) =====
  class TbmHorairesCard extends HTMLElement {
    setConfig(config) { this._config = config || {}; }

    set hass(hass) {
      const cfg = this._config || {};
      const st = hass?.states?.[cfg.entity];
      if (!st) {
        this.innerHTML = `<ha-card><div style="padding:12px">Entité introuvable</div></ha-card>`;
        return;
      }

      const a = st.attributes || {};
      const count = Number(cfg.count ?? 3);
      const deps = (a.departures || []).slice(0, count);

      const rawLine = cfg.line || a.line || a.line_name || "";
      const code = lineCodeOf(rawLine);
      const stop = cfg.stop || a.stop || st.attributes.friendly_name || "TBM";
      const title = `${stop}`.trim();
      const subtitle = a.destination || a.dest_label || "";

      // Styles config
      const rtIcon  = cfg.realtime_icon  || "mdi:wifi";
      const rtBg    = cfg.realtime_bg    || "var(--info-color, #1976d2)";
      const rtColor = cfg.realtime_color || "#fff";
      const pillBg  = cfg.line_bg        || "var(--primary-color)";
      const pillCol = cfg.line_color     || "#fff";

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
            .ttl{font-weight:700;font-size:1.05rem;line-height:1.15}
            .sub{opacity:.8;font-size:.95rem}
            .list{display:flex;flex-direction:column;margin-top:8px}
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
              background:${rtBg}; color:${rtColor};
              flex:0 0 auto;
            }
            .rt ha-icon{ --mdc-icon-size: 12px; }
            .min{font-variant-numeric: tabular-nums; font-weight:600}
            .empty{opacity:.7;padding:6px 0}
          </style>

          <div class="wrap">
            <div class="header">
              ${code ? `<div class="pill" aria-label="Ligne ${code}">${code}</div>` : ""}
              <div class="head-text">
                <div class="ttl">${title}</div>
                <div class="sub">${subtitle}</div>
              </div>
            </div>

            <div class="list">
              ${
                deps.length
                  ? deps.map(d => `
                    <div class="row" title="${d.realtime ? "Temps réel" : "Horaire théorique"}">
                      <span class="min">${(d.in_min ?? "—")} min</span>
                      ${d.realtime ? `<span class="rt" aria-label="temps réel"><ha-icon icon="${rtIcon}"></ha-icon></span>` : ""}
                    </div>`).join("")
                  : `<div class="empty">Aucun passage à afficher</div>`
              }
            </div>
          </div>
        </ha-card>
      `;
    }

    getCardSize(){ return 1 + Math.max(0, Number(this._config?.count ?? 3)); }

    static getConfigElement() { return document.createElement("tbm-horaires-card-editor"); }
    static getStubConfig(hass){
      const any = Object.keys(hass?.states || {}).find(k => k.startsWith("sensor."));
      return { entity: any || "", count: 3 };
    }
  }

  // ===== Editor (no-Lit fallback, reliable in HA GUI) =====
  class TbmHorairesCardEditor extends HTMLElement {
    setConfig(config){ this._config = { count: 3, ...config }; this._render(); }
    set hass(hass){ this._hass = hass; this._render(); }

    connectedCallback(){ this._render(); }

    _emit(cfg){
      this._config = cfg;
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }}));
    }

    _render(){
      // Avoid rendering before HA injects the editor
      if (!this.isConnected) return;

      const c = this._config || {};
      this.innerHTML = `
        <div class="card-config" style="display:grid;gap:12px;padding:12px">
          <ha-entity-picker id="entity" label="Entité (sensor)" .includeDomains='["sensor"]'></ha-entity-picker>

          <ha-textfield id="count" label="Nombre de passages (max 3)" type="number" min="1" max="3"></ha-textfield>

          <ha-textfield id="realtime_icon" label="Icône temps réel (ex: mdi:wifi)"></ha-textfield>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <ha-textfield id="realtime_bg"   label="Fond temps réel (CSS var/hex)"></ha-textfield>
            <ha-textfield id="realtime_color" label="Couleur icône (hex)"></ha-textfield>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <ha-textfield id="line_bg"   label="Fond médaillon ligne (CSS var/hex)"></ha-textfield>
            <ha-textfield id="line_color" label="Couleur médaillon (hex)"></ha-textfield>
          </div>
        </div>
      `;

      // Wire props
      const $ = (id) => this.querySelector(`#${id}`);
      if ($("entity")) {
        $("entity").hass = this._hass;
        $("entity").value = c.entity || "";
        $("entity").addEventListener("value-changed", (e)=>{
          const v = e.detail?.value ?? e.target?.value;
          this._emit({ ...this._config, entity: v });
        });
      }
      if ($("count")) {
        $("count").value = String(c.count ?? 3);
        $("count").addEventListener("change", (e)=> this._emit({ ...c, count: Number(e.target.value) }));
      }
      ["realtime_icon","realtime_bg","realtime_color","line_bg","line_color"]
        .forEach(k=>{
          if($(k)){
            $(k).value = c[k] || "";
            $(k).addEventListener("change",(e)=> this._emit({ ...this._config, [k]: e.target.value }));
          }
        });
    }
  }

  // ===== Define elements (guard if reloaded) =====
  if (!customElements.get("tbm-horaires-card")) customElements.define("tbm-horaires-card", TbmHorairesCard);
  if (!customElements.get("tbm-horaires-card-editor")) customElements.define("tbm-horaires-card-editor", TbmHorairesCardEditor);

  // Show in “Add Card” dialog
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "tbm-horaires-card",
    name: "TBM Horaires (vertical compact)",
    description: "Prochains passages TBM – liste compacte, médaillon de ligne, badge temps réel.",
  });
})();
