class TbmHorairesCard extends HTMLElement {
  setConfig(config){ this._config = config; }
  set hass(hass){
    const st = hass.states[this._config.entity];
    if(!st){
      this.innerHTML = `<ha-card><div style="padding:12px">Entité introuvable</div></ha-card>`;
      return;
    }
    const a = st.attributes || {};
    const title = this._config.title || a.stop || st.attributes.friendly_name || "TBM";
    const subtitle = this._config.subtitle
      || `${a.line || a.line_name || ""}${(a.destination||a.dest_label) ? " → " : ""}${a.destination || a.dest_label || ""}`.trim();
    const deps = (a.departures || []).slice(0, this._config.count || 3);

    const rtIcon  = this._config.realtime_icon  || "mdi:wifi";
    const rtBg    = this._config.realtime_bg    || "var(--info-color, #1976d2)";
    const rtColor = this._config.realtime_color || "#fff";

    this.innerHTML = `
      <ha-card>
         <style>
          .hdr{padding:12px 12px 0 12px;}
          .sub{opacity:.8;margin-top:2px;}
          .chips{padding:12px;display:flex;flex-wrap:wrap;gap:8px}
          .chip{padding:6px 10px;border-radius:999px;border:1px solid var(--divider-color);display:inline-flex;align-items:center;gap:8px}
          .rt{
            display:inline-flex;align-items:center;justify-content:center;
            width:18px;height:18px;border-radius:50%;
            background:${rtBg}; color:${rtColor};
          }
          .rt ha-icon{ --mdc-icon-size: 12px; }
        </style>
        <div class="hdr">
          <div class="sub">${title} - ${subtitle}</div>
        </div>
        <div class="chips">
          ${
            deps.length
              ? deps.map(d => `
                <span class="chip" title="${d.realtime ? "Temps réel" : "Horaire théorique"}">
                  ${d.realtime ? `<span class="rt" aria-label="temps réel"><ha-icon icon="${rtIcon}"></ha-icon></span>` : ""}
                  ${(d.in_min ?? "—")} min
                </span>`).join("")
              : `<span style="opacity:.7">Aucun passage à afficher</span>`
          }
        </div>
      </ha-card>`;
  }
  getCardSize(){ return 1; }
}
customElements.define('tbm-horaires-card', TbmHorairesCard);