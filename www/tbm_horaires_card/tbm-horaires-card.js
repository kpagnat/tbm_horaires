/*
  TBM Horaires Card – compact vertical list
  Fixes included:
  - No full innerHTML rebuild on each hass update (prevents focus loss & memory bloat)
  - Editor renders once; fields update imperatively; preserves input focus
  - window.customCards guarded against duplicates
*/

(function(){
  const TAG_CARD = "tbm-horaires-card";
  const TAG_EDITOR = "tbm-horaires-card-editor";
  const VERSION = "1.1.0";

  // ---- helper ----
  function lineCodeOf(raw){
    if (!raw) return "";
    const s = String(raw).trim();
    const m = s.match(/([A-Za-zÀ-ÿ]*?)\s*(\d+[A-Za-z]?)$/);
    if (m) return m[2];
    return s.length <= 4 ? s.toUpperCase() : s.slice(0,4).toUpperCase();
  }

  // Throttle utility (optional)
  function throttle(fn, wait){
    let last = 0, timer = null, lastArgs;
    return function(...args){
      const now = Date.now();
      lastArgs = args;
      const later = () => { last = Date.now(); timer = null; fn.apply(this, lastArgs); };
      if (!last || (now - last) >= wait){
        last = now; fn.apply(this, args);
      } else if (!timer){
        timer = setTimeout(later, wait - (now - last));
      }
    };
  }

  // ---- Card ----
  class TbmHorairesCard extends HTMLElement {
    constructor(){
      super();
      this._built = false;
      this._config = {};
      this._lastListHTML = undefined;
      this._updateThrottled = throttle(() => this._update(), 250);
    }

    setConfig(config){
      this._config = { count: 3, ...config };
      if (this._built) this._refreshStaticBits();
    }

    connectedCallback(){
      // Nothing until we have hass and config
    }

    set hass(hass){
      this._hass = hass;
      // Use throttled updates to avoid excessive DOM churn
      this._updateThrottled();
    }

    _ensureBuilt(){
      if (this._built) return;
      this.innerHTML = `
        <ha-card>
          <style>
            :host { display:block; }
            .wrap{ padding: 12px; }
            .header{ display:flex; align-items:center; gap:12px; margin-bottom: 8px; }
            .pill{ display:inline-flex; align-items:center; justify-content:center; min-width:36px; height:28px; padding:0 10px; border-radius:999px; font-weight:600; font-size:14px; }
            .head-text{ display:flex; flex-direction:column; min-width:0; }
            .ttl{ font-weight:600; font-size:16px; line-height:1.1; }
            .sub{ opacity:0.8; font-size:13px; }
            .list{ display:flex; flex-direction:column; gap:8px; margin-top: 8px; }
            .row{ display:flex; align-items:center; justify-content:space-between; }
            .min{ font-variant-numeric: tabular-nums; font-size:16px; }
            .empty{ opacity:.7; font-size:13px; }
            .rt{ display:inline-flex; align-items:center; gap:6px; padding:2px 6px; border-radius:8px; background: var(--tbm-rt-bg, #1976d2); color: var(--tbm-rt-color, #fff); }
            ha-icon{ width:18px; height:18px; }
          </style>
          <div class="wrap">
            <div class="header">
              <div class="pill" aria-label="Ligne"></div>
              <div class="head-text">
                <div class="ttl"></div>
                <div class="sub"></div>
              </div>
            </div>
            <div class="list"></div>
          </div>
        </ha-card>`;
      this._els = {
        pill: this.querySelector('.pill'),
        ttl:  this.querySelector('.ttl'),
        sub:  this.querySelector('.sub'),
        list: this.querySelector('.list'),
      };
      this._built = true;
    }

    _refreshStaticBits(){
      if (!this._built) return;
      const cfg = this._config;
      const pillBg  = cfg.line_bg        || 'var(--primary-color)';
      const pillCol = cfg.line_color     || '#fff';
      const rtBg    = cfg.realtime_bg    || 'var(--info-color, #1976d2)';
      const rtColor = cfg.realtime_color || '#fff';
      this._els.pill.style.background = pillBg;
      this._els.pill.style.color = pillCol;
      this.style.setProperty('--tbm-rt-bg', rtBg);
      this.style.setProperty('--tbm-rt-color', rtColor);
    }

    _update(){
      const hass = this._hass; if (!hass) return;
      const cfg = this._config || {};
      const st = hass.states?.[cfg.entity];
      this._ensureBuilt();

      if (!st){
        this._els.ttl.textContent = 'Entité introuvable';
        this._els.sub.textContent = '';
        this._els.pill.style.display = 'none';
        this._els.list.innerHTML = `<div class="empty">Vérifiez la configuration de la carte.</div>`;
        return;
      }

      const a = st.attributes || {};
      const count = Number(cfg.count ?? 3);
      const departures = Array.isArray(a.departures) ? a.departures.slice(0, count) : [];

      const rawLine = cfg.line || a.line || a.line_name || '';
      const code    = lineCodeOf(rawLine);
      const stop    = cfg.stop || a.stop || st.attributes.friendly_name || 'TBM';
      const title   = `${stop}`.trim();
      const subtitle= a.destination || a.dest_label || '';

      this._refreshStaticBits();

      // Header
      if (code) {
        this._els.pill.textContent = code;
        this._els.pill.setAttribute('aria-label', `Ligne ${code}`);
        this._els.pill.style.display = '';
      } else {
        this._els.pill.style.display = 'none';
      }
      this._els.ttl.textContent = title;
      this._els.sub.textContent = subtitle || '';

      // List (render only if changed)
      const rtIcon  = cfg.realtime_icon  || 'mdi:wifi';
      const nextHTML = departures.length
        ? departures.map(d => `
            <div class="row" title="${d.realtime ? 'Temps réel' : 'Horaire théorique'}">
              <span class="min">${(d.in_min ?? '—')} min</span>
              ${d.realtime ? `<span class="rt" aria-label="temps réel"><ha-icon icon="${rtIcon}"></ha-icon></span>` : ''}
            </div>`).join('')
        : `<div class="empty">Aucun passage à afficher</div>`;

      if (nextHTML !== this._lastListHTML){
        this._els.list.innerHTML = nextHTML;
        this._lastListHTML = nextHTML;
      }
    }

    getCardSize(){ return 1 + Math.max(0, Number(this._config?.count ?? 3)); }

    static getConfigElement(){ return document.createElement(TAG_EDITOR); }

    static getStubConfig(hass){
      const any = Object.keys(hass?.states || {}).find(k => k.startsWith('sensor.'));
      return { entity: any || '', count: 3 };
    }
  }

  // ---- Editor ----
  class TbmHorairesCardEditor extends HTMLElement {
    constructor(){ super(); this._rendered = false; this._config = { count: 3 }; }

    setConfig(config){
      this._config = { count: 3, ...config };
      this._ensureRender();
      this._updateFields();
    }

    set hass(hass){
      this._hass = hass;
      const ent = this.querySelector('#entity');
      if (ent) ent.hass = hass; // imperative update only; no re-render
    }

    connectedCallback(){ this._ensureRender(); }

    _ensureRender(){ if (!this._rendered) { this._render(); this._rendered = true; } }

    _updateFields(){
      const c = this._config || {};
      const setVal = (id, v) => {
        const el = this.querySelector('#'+id);
        if (!el) return;
        const val = v == null ? '' : String(v);
        if (String(el.value ?? '') !== val) el.value = val;
      };
      setVal('entity', c.entity || '');
      setVal('count',  c.count ?? 3);
      ['realtime_icon','realtime_bg','realtime_color','line_bg','line_color','stop','line'].forEach(k=> setVal(k, c[k] || ''));
    }

    _render(){
      this.innerHTML = `
        <div class="card-config" style="display:block;padding:8px 2px;">
          <div class="form-row">
            <ha-entity-picker id="entity" label="Entité (sensor.*)" allow-custom-entity></ha-entity-picker>
          </div>
          <div class="form-row">
            <paper-input id="count" label="Nombre de départs" type="number" min="1"></paper-input>
          </div>
          <div class="form-row">
            <paper-input id="stop" label="Nom arrêt (override)"></paper-input>
            <paper-input id="line" label="Ligne (override)"></paper-input>
          </div>
          <div class="form-row" style="margin-top:6px; font-weight:600">Temps réel</div>
          <div class="form-row">
            <paper-input id="realtime_icon" label="Icône (ex: mdi:wifi)"></paper-input>
            <paper-input id="realtime_bg" label="Fond (CSS)"></paper-input>
            <paper-input id="realtime_color" label="Texte (CSS)"></paper-input>
          </div>
          <div class="form-row" style="margin-top:6px; font-weight:600">Ligne</div>
          <div class="form-row">
            <paper-input id="line_bg" label="Fond (CSS)"></paper-input>
            <paper-input id="line_color" label="Texte (CSS)"></paper-input>
          </div>
        </div>`;

      const $ = (id) => this.querySelector('#'+id);

      if ($('entity')){
        $('entity').hass = this._hass;
        $('entity').addEventListener('value-changed', (e)=>{
          const v = e.detail?.value ?? e.target?.value;
          this._config = { ...this._config, entity: v };
          this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._config } }));
        });
      }

      const bindChange = (id, map = v => v) => {
        const el = $(id); if (!el) return;
        const handler = (e) => {
          const val = map(e.target.value);
          this._config = { ...this._config, [id]: val };
          this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._config } }));
        };
        el.addEventListener('change', handler);
        el.addEventListener('keyup', (e)=>{ if (e.key === 'Enter') handler(e); });
      };

      bindChange('count', v => Number(v));
      ['realtime_icon','realtime_bg','realtime_color','line_bg','line_color','stop','line'].forEach(bindChange);

      // initial fill
      this._updateFields();
    }
  }

  // ---- Registry guards ----
  if (!customElements.get(TAG_CARD))   customElements.define(TAG_CARD, TbmHorairesCard);
  if (!customElements.get(TAG_EDITOR)) customElements.define(TAG_EDITOR, TbmHorairesCardEditor);

  // ---- window.customCards (guarded) ----
  try {
    window.customCards = window.customCards || [];
    if (!window.customCards.some(c => c.type === TAG_CARD)){
      window.customCards.push({
        type: TAG_CARD,
        name: 'TBM Horaires (compact)',
        description: 'Prochains passages TBM – liste compacte, médaillon de ligne, badge temps réel.'
      });
    }
  } catch(e) {}

  if (!window.__TBM_HORAIRES_CARD_LOGGED){
    window.__TBM_HORAIRES_CARD_LOGGED = true;
    // eslint-disable-next-line no-console
    console.info(`%c${TAG_CARD}%c v${VERSION} loaded`, 'font-weight:700', '');
  }
})();
