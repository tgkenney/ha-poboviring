const CARD_TAG = 'rings-dashboard-card';

const STYLE = `
  :host {
    --ring-bg: var(--card-background-color, #1a1d23);
    --ring-inner: var(--secondary-background-color, rgba(128,128,128,.10));
    --ring-text: var(--primary-text-color, #e9ecf1);
    --ring-muted: var(--secondary-text-color, #9aa3af);
    --ring-border: var(--divider-color, rgba(255,255,255,.08));
    --ring-track: rgba(128,128,128,.18);
    --ring-green: #22c55e;
    --ring-amber: #f59e0b;
    --ring-red: #ef4444;
    --ring-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,.2));
    display: block;
    padding: 4px;
  }
  .wrap { display: flex; flex-direction: column; gap: 16px; }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 4px 6px 0; }
  .head .title { display: flex; align-items: center; gap: 10px; font-size: 22px; font-weight: 650; color: var(--ring-text); letter-spacing: -.01em; }
  .head .title ha-icon { color: var(--ring-muted); --mdc-icon-size: 26px; }
  .head .sub { color: var(--ring-muted); font-size: 13px; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); align-items: start; }

  .ring {
    position: relative;
    background: var(--ring-bg);
    border: 1px solid var(--ring-border);
    border-radius: 20px;
    box-shadow: var(--ring-shadow);
    padding: 18px;
    overflow: hidden;
  }
  .ring::before {
    content: '';
    position: absolute; inset: 0 0 auto 0; height: 3px;
    background: linear-gradient(90deg, var(--accent), transparent 85%);
    opacity: .9;
  }
  .top { display: flex; align-items: center; gap: 14px; }
  .batt { position: relative; width: 56px; height: 56px; flex: 0 0 56px; }
  .batt svg { width: 56px; height: 56px; transform: rotate(-90deg); }
  .batt .t { fill: none; stroke: var(--ring-track); stroke-width: 5; }
  .batt .p { fill: none; stroke: var(--accent); stroke-width: 5; stroke-linecap: round; transition: stroke-dashoffset .6s ease; }
  .batt .n { position: absolute; inset: 0; display: grid; place-items: center; font-size: 13px; font-weight: 650; color: var(--ring-text); }
  .ident { min-width: 0; flex: 1 1 auto; }
  .ident h2 { margin: 0; font-size: 18px; font-weight: 650; color: var(--ring-text); letter-spacing: -.01em; }
  .status { display: flex; align-items: center; gap: 7px; margin-top: 4px; font-size: 12.5px; color: var(--ring-muted); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ring-muted); }
  .dot.ok { background: var(--ring-green); box-shadow: 0 0 0 3px rgba(34,197,94,.18); }
  .dot.stale { background: var(--ring-amber); box-shadow: 0 0 0 3px rgba(245,158,11,.18); }
  .dot.bad { background: var(--ring-red); box-shadow: 0 0 0 3px rgba(239,68,68,.18); }
  .find {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--ring-inner); color: var(--ring-text);
    border: 1px solid var(--ring-border); border-radius: 999px;
    padding: 7px 12px; font: inherit; font-size: 12.5px; cursor: pointer;
    transition: transform .12s ease, background .2s ease;
  }
  .find:hover { background: color-mix(in srgb, var(--accent) 16%, transparent); }
  @supports not (background: color-mix(in srgb, red 10%, transparent)) {
    .find:hover { background: var(--ring-inner); }
    .spark .bar { background: var(--accent); opacity: .42; }
    .spark .bar.today { opacity: 1; }
    .tile.warn { border-color: var(--ring-amber); }
  }
  .find:active { transform: scale(.97); }
  .find ha-icon { --mdc-icon-size: 17px; color: var(--accent); }

  .chip { display: inline-flex; align-items: center; margin-top: 6px; padding: 2px 8px; border-radius: 999px; background: var(--ring-inner); color: var(--ring-muted); font-size: 10.5px; letter-spacing: .02em; }
  .hrrow { display: flex; align-items: center; gap: 10px; margin-top: 12px; color: var(--ring-muted); font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; }
  .hrsvg { flex: 1 1 auto; height: 30px; width: 100%; overflow: visible; }
  .hrsvg polyline { fill: none; stroke: var(--accent); stroke-width: 1.8; stroke-linejoin: round; stroke-linecap: round; opacity: .85; }
  .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; margin-top: 16px; }
  .hero .num { font-size: 40px; line-height: 1; font-weight: 700; color: var(--ring-text); letter-spacing: -.03em; font-variant-numeric: tabular-nums; }
  .hero .lbl { color: var(--ring-muted); font-size: 12.5px; margin-top: 5px; }
  .spark { display: flex; align-items: flex-end; gap: 4px; height: 46px; min-width: 110px; }
  .spark .bar { flex: 1 1 0; min-width: 4px; border-radius: 3px 3px 1px 1px; background: color-mix(in srgb, var(--accent) 42%, transparent); }
  .spark .bar { background: var(--accent); opacity: .42; }
  .spark .bar.today { background: var(--accent); opacity: 1; }

  .tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 16px; }
  .tile {
    background: var(--ring-inner); border: 1px solid transparent; border-radius: 13px;
    padding: 10px 9px; display: flex; flex-direction: column; align-items: flex-start; gap: 3px;
    min-width: 0;
  }
  .tile ha-icon { --mdc-icon-size: 18px; color: var(--ring-muted); }
  .tile .v { font-size: 17px; font-weight: 650; color: var(--ring-text); font-variant-numeric: tabular-nums; line-height: 1.1; }
  .tile .k { font-size: 10.5px; color: var(--ring-muted); text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .tile.low .v { color: var(--ring-green); }
  .tile.mid .v { color: var(--ring-amber); }
  .tile.high .v { color: var(--ring-red); }
  .tile.warn { border-color: color-mix(in srgb, var(--ring-amber) 40%, transparent); }

  .sleeprow { display: none; align-items: center; gap: 8px; margin-top: 10px; font-size: 10.5px; color: var(--ring-muted); text-transform: uppercase; letter-spacing: .04em; }
  .sleeprow .sl { white-space: nowrap; }
  .sleeprow .sbar { flex: 1 1 auto; display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--ring-track); }
  .sleeprow .sbar i { display: block; height: 100%; width: 0; }
  .sleeprow .sbar .d { background: #48befc; }
  .sleeprow .sbar .l { background: #92ddfc; }
  .sleeprow .sbar .r { background: #fd894e; }
  .sleeprow .sbar .a { background: #f25230; }
  .sleeprow .ss { white-space: nowrap; font-variant-numeric: tabular-nums; }

  @media (max-width: 420px) {
    .tiles { grid-template-columns: repeat(3, 1fr); }
    .hero .num { font-size: 34px; }
  }
`;

class RingsDashboardCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!Array.isArray(this.config.rings) || !this.config.rings.length) {
      throw new Error('Add a `rings` list to the card configuration (see the README).');
    }
    this._rings = this.config.rings;
    this._refs = {};
    this._stats = {};
    this._built = false;
    if (this._hass) this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
    this._maybeRefreshStats();
  }

  getCardSize() {
    return 11;
  }

  connectedCallback() {
    if (this._hass && !this._built) this._build();
  }

  _build() {
    if (!this._built) {
      this.attachShadow({ mode: 'open' });
      this._built = true;
    }
    const root = this.shadowRoot;
    root.innerHTML = '<style>' + STYLE + '</style><div class="wrap"><div class="head"><div class="title"><ha-icon icon="mdi:ring"></ha-icon><span>Rings</span></div><div class="sub" id="sub"></div></div><div class="grid" id="grid"></div></div>';

    const grid = root.getElementById('grid');
    this._refs = {};

    this._rings.forEach((ring) => {
      const card = document.createElement('section');
      card.className = 'ring';
      card.style.setProperty('--accent', ring.accent || '#6366f1');
      card.innerHTML =
        '<div class="top">' +
          '<div class="batt"><svg viewBox="0 0 56 56"><circle class="t" cx="28" cy="28" r="24"/><circle class="p" cx="28" cy="28" r="24"/></svg><div class="n">--</div></div>' +
          '<div class="ident"><h2></h2><div class="status"><span class="dot"></span><span class="st"></span></div><div class="chip"></div></div>' +
          '<button class="find" type="button"><ha-icon icon="mdi:vibrate"></ha-icon>Find</button>' +
        '</div>' +
        '<div class="hero"><div><div class="num">--</div><div class="lbl">steps today</div></div><div class="spark"></div></div>' +
        '<div class="hrrow"><span>hr 24h</span><svg class="hrsvg" viewBox="0 0 120 28" preserveAspectRatio="none"><polyline points=""></polyline></svg></div>' +
        '<div class="tiles">' +
          '<div class="tile" data-m="hr"><ha-icon icon="mdi:heart-pulse"></ha-icon><span class="v">--</span><span class="k">bpm</span></div>' +
          '<div class="tile" data-m="hrv"><ha-icon icon="mdi:chart-timeline-variant"></ha-icon><span class="v">--</span><span class="k">hrv ms</span></div>' +
          '<div class="tile" data-m="spo2"><ha-icon icon="mdi:lungs"></ha-icon><span class="v">--</span><span class="k">spo2 %</span></div>' +
          '<div class="tile" data-m="resp"><ha-icon icon="mdi:weather-windy"></ha-icon><span class="v">--</span><span class="k">brpm</span></div>' +
          '<div class="tile" data-m="stress"><ha-icon icon="mdi:brain"></ha-icon><span class="v">--</span><span class="k">stress</span></div>' +
          '<div class="tile" data-m="calories"><ha-icon icon="mdi:fire"></ha-icon><span class="v">--</span><span class="k">kcal</span></div>' +
          '<div class="tile" data-m="active"><ha-icon icon="mdi:run"></ha-icon><span class="v">--</span><span class="k">active min</span></div>' +
          '<div class="tile" data-m="sleep"><ha-icon icon="mdi:sleep"></ha-icon><span class="v">--</span><span class="k">sleep today</span></div>' +
          '<div class="tile" data-m="score"><ha-icon icon="mdi:chart-donut"></ha-icon><span class="v">--</span><span class="k">score</span></div>' +
          '<div class="tile" data-m="temp"><ha-icon icon="mdi:thermometer"></ha-icon><span class="v">--</span><span class="k">temp</span></div>' +
        '</div>' +
        '<div class="sleeprow"><span class="sl">stages</span><div class="sbar"><i class="d"></i><i class="l"></i><i class="r"></i><i class="a"></i></div><span class="ss">--</span></div>';

      card.querySelector('h2').textContent = ring.name;
      const findBtn = card.querySelector('.find');
      findBtn.addEventListener('click', () => {
        if (!ring.entities.find || !this._hass) return;
        findBtn.disabled = true;
        this._hass.callService('button', 'press', { entity_id: ring.entities.find })
          .catch(() => {})
          .finally(() => { setTimeout(() => { findBtn.disabled = false; }, 4000); });
      });

      grid.appendChild(card);
      this._refs[ring.key] = {
        card,
        pct: card.querySelector('.batt .n'),
        arc: card.querySelector('.batt .p'),
        dot: card.querySelector('.dot'),
        status: card.querySelector('.st'),
        num: card.querySelector('.num'),
        spark: card.querySelector('.spark'),
        chip: card.querySelector('.chip'),
        sleeprow: card.querySelector('.sleeprow'),
        sbar: card.querySelector('.sbar'),
        ss: card.querySelector('.ss'),
        hrline: card.querySelector('.hrsvg polyline'),
        tiles: {}
      };
      card.querySelectorAll('.tile').forEach((el) => {
        this._refs[ring.key].tiles[el.dataset.m] = el;
      });
    });
  }

  _state(entity) {
    return entity && this._hass ? this._hass.states[entity] : undefined;
  }

  _num(entity) {
    const st = this._state(entity);
    if (!st || st.state === 'unknown' || st.state === 'unavailable' || st.state === '') return null;
    const n = Number(st.state);
    return Number.isFinite(n) ? n : null;
  }

  _setTile(ref, value, unit, cls) {
    if (!ref) return;
    ref.querySelector('.v').textContent = value === null ? '--' : String(value);
    ref.classList.remove('low', 'mid', 'high', 'warn');
    if (cls) ref.classList.add(cls);
  }

  _fmtMin(mins) {
    const n = Math.max(0, Math.round(Number(mins) || 0));
    const h = Math.floor(n / 60);
    const m = n % 60;
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
  }

  _agoText(iso) {
    if (!iso) return 'no sync yet';
    const t = Date.parse(iso);
    if (!Number.isFinite(t)) return 'no sync yet';
    const mins = Math.round((Date.now() - t) / 60000);
    if (mins < 1) return 'synced just now';
    if (mins < 60) return 'synced ' + mins + 'm ago';
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return 'synced ' + hrs + 'h ago';
    return 'synced ' + Math.round(hrs / 24) + 'd ago';
  }

  _update() {
    if (!this._built || !this._refs) return;
    let freshest = null;

    this._rings.forEach((ring) => {
      const ref = this._refs[ring.key];
      if (!ref) return;

      const batt = this._num(ring.entities.battery);
      ref.pct.textContent = batt === null ? '--' : Math.round(batt) + '%';
      const circ = 2 * Math.PI * 24;
      ref.arc.style.strokeDasharray = String(circ);
      ref.arc.style.strokeDashoffset = String(circ * (1 - Math.max(0, Math.min(100, batt || 0)) / 100));

      const syncState = this._state(ring.entities.sync);
      const iso = syncState ? syncState.state : null;
      ref.status.textContent = this._agoText(iso);
      const t = iso ? Date.parse(iso) : NaN;
      ref.dot.className = 'dot ' + (!Number.isFinite(t) ? 'bad' : (Date.now() - t < 90 * 60000 ? 'ok' : 'stale'));
      if (Number.isFinite(t) && (!freshest || t > freshest)) freshest = t;

      const fwState = this._state(ring.entities.firmware);
      const rssi = this._num(ring.entities.rssi);
      const chipParts = [];
      if (fwState && fwState.state !== 'unknown' && fwState.state !== 'unavailable') chipParts.push(fwState.state);
      if (rssi !== null) chipParts.push(Math.round(rssi) + ' dBm');
      ref.chip.textContent = chipParts.length ? chipParts.join('  ·  ') : 'no link yet';
      const rssiState = this._state(ring.entities.rssi);
      ref.chip.title = (rssiState && rssiState.attributes && rssiState.attributes.proxy) || '';

      const steps = this._num(ring.entities.steps);
      ref.num.textContent = steps === null ? '--' : Math.round(steps).toLocaleString();

      const hr = this._num(ring.entities.hr);
      this._setTile(ref.tiles.hr, hr === null ? null : Math.round(hr), 'bpm');

      const hrv = this._num(ring.entities.hrv);
      this._setTile(ref.tiles.hrv, hrv === null ? null : Math.round(hrv), 'ms');

      const spo2 = this._num(ring.entities.spo2);
      this._setTile(ref.tiles.spo2, spo2 === null ? null : Math.round(spo2), '%', spo2 !== null && spo2 < 94 ? 'warn' : null);

      const resp = this._num(ring.entities.resp);
      this._setTile(ref.tiles.resp, resp === null ? null : resp.toFixed(1), 'brpm');

      const stress = this._num(ring.entities.stress);
      this._setTile(ref.tiles.stress, stress === null ? null : Math.round(stress), '',
        stress === null ? null : (stress < 34 ? 'low' : stress < 67 ? 'mid' : 'high'));

      const kcal = this._num(ring.entities.calories);
      this._setTile(ref.tiles.calories, kcal === null ? null : Math.round(kcal), 'kcal');

      const active = this._num(ring.entities.active);
      this._setTile(ref.tiles.active, active === null ? null : Math.round(active), 'min');

      const sleepState = this._state(ring.entities.sleep);
      const attrs = sleepState && sleepState.attributes ? sleepState.attributes : null;
      const sessions = attrs && Array.isArray(attrs.sessions) ? attrs.sessions : [];
      let sleep = this._num(ring.entities.sleep);
      let dayStages = null;
      if (sessions.length) {
        const today = new Date().toDateString();
        dayStages = { deep: 0, light: 0, rem: 0, awake: 0 };
        let total = 0;
        sessions.forEach((session) => {
          const end = session.end || session.start;
          if (!end || new Date(end).toDateString() !== today) return;
          total += Number(session.minutes) || 0;
          dayStages.deep += Number(session.deep) || 0;
          dayStages.light += Number(session.light) || 0;
          dayStages.rem += Number(session.rem) || 0;
          dayStages.awake += Number(session.awake) || 0;
        });
        sleep = total;
      }
      let sleepText = null;
      if (sleep !== null) {
        const h = Math.floor(sleep / 60);
        const m = Math.round(sleep % 60);
        sleepText = h > 0 ? h + 'h ' + m + 'm' : m + 'm';
      }
      this._setTile(ref.tiles.sleep, sleepText, '');

      const score = this._num(ring.entities.sleepScore);
      this._setTile(ref.tiles.score, score === null ? null : Math.round(score), '');

      const temp = this._num(ring.entities.temp);
      this._setTile(ref.tiles.temp, temp === null ? null : temp.toFixed(1), '°C');

      const parts = dayStages ? [
        ['d', dayStages.deep, 'deep'],
        ['l', dayStages.light, 'light'],
        ['r', dayStages.rem, 'rem'],
        ['a', dayStages.awake, 'awake'],
      ] : attrs ? [
        ['d', Number(attrs.deep_minutes) || 0, 'deep'],
        ['l', Number(attrs.light_minutes) || 0, 'light'],
        ['r', Number(attrs.rem_minutes) || 0, 'rem'],
        ['a', Number(attrs.awake_minutes) || 0, 'awake'],
      ] : [];
      const stageTotal = parts.reduce((sum, part) => sum + part[1], 0);
      if (ref.sleeprow && stageTotal > 0) {
        ref.sleeprow.style.display = '';
        for (const [cls, mins, label] of parts) {
          const bar = ref.sbar.querySelector('.' + cls);
          bar.style.width = (100 * mins / stageTotal).toFixed(1) + '%';
          bar.title = label + ' ' + this._fmtMin(mins);
        }
        ref.ss.textContent = this._fmtMin(stageTotal);
      } else if (ref.sleeprow) {
        ref.sleeprow.style.display = 'none';
      }
    });

    const sub = this.shadowRoot.getElementById('sub');
    if (sub) {
      sub.textContent = freshest
        ? 'last activity ' + this._agoText(new Date(freshest).toISOString()).replace('synced ', '')
        : 'waiting for first sync';
    }
  }

  _maybeRefreshStats() {
    if (!this._hass || this._statsBusy) return;
    const now = Date.now();
    if (this._statsAt && now - this._statsAt < 15 * 60000) return;
    this._statsAt = now;
    this._statsBusy = true;
    const stepIds = this._rings.map((r) => r.entities.steps).filter(Boolean);
    const hrIds = this._rings.map((r) => r.entities.hr).filter(Boolean);
    const fetchStats = (ids, period, fromMs, types) => this._hass.callWS({
      type: 'recorder/statistics_during_period',
      start_time: new Date(fromMs).toISOString(),
      end_time: new Date(now).toISOString(),
      statistic_ids: ids,
      period,
      types
    }).catch(() => ({}));
    Promise.all([
      fetchStats(stepIds, 'day', now - 7 * 864e5, ['change']),
      fetchStats(hrIds, 'hour', now - 24 * 36e5, ['mean'])
    ]).then(([steps, hr]) => {
      this._stats = steps || {};
      this._statsHr = hr || {};
      this._renderSparks();
    }).finally(() => { this._statsBusy = false; });
  }

  _renderSparks() {
    if (!this._built) return;
    this._rings.forEach((ring) => {
      const ref = this._refs[ring.key];
      if (!ref) return;
      const rows = (this._stats && this._stats[ring.entities.steps]) || [];
      ref.spark.innerHTML = '';
      if (!rows.length) {
        const empty = document.createElement('div');
        empty.style.cssText = 'width:100%;text-align:right;font-size:11.5px;color:var(--ring-muted)';
        empty.textContent = 'no history yet';
        ref.spark.appendChild(empty);
        return;
      }
      const hrRows = (this._statsHr && this._statsHr[ring.entities.hr]) || [];
      const vals = hrRows.map((r) => Number(r.mean)).filter((v) => Number.isFinite(v));
      if (ref.hrline) {
        if (vals.length > 1) {
          const lo = Math.min(...vals);
          const hi = Math.max(...vals);
          const span = Math.max(1, hi - lo);
          ref.hrline.setAttribute('points', vals.map((v, i) => (i / (vals.length - 1) * 120).toFixed(1) + ',' + (25 - ((v - lo) / span) * 20).toFixed(1)).join(' '));
        } else {
          ref.hrline.setAttribute('points', '');
        }
      }

      const shown = rows.slice(-7);
      const max = Math.max(1, ...shown.map((r) => Number(r.change) || 0));
      shown.forEach((r, i) => {
        const bar = document.createElement('div');
        bar.className = 'bar' + (i === shown.length - 1 ? ' today' : '');
        const v = Math.max(0, Number(r.change) || 0);
        bar.style.height = Math.max(6, (v / max) * 100) + '%';
        bar.title = Math.round(v).toLocaleString() + ' steps';
        ref.spark.appendChild(bar);
      });
    });
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, RingsDashboardCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: 'Rings Dashboard',
    description: 'POBOVi ring overview for multiple wearers'
  });
}
