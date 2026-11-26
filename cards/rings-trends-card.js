const CARD_TAG = 'rings-trends-card';

const PANELS = [
  { id: 'steps', title: 'Steps', icon: 'mdi:walk', period: 'day', type: 'bar', stat: 'change', days: 7 },
  { id: 'sleep', title: 'Sleep', icon: 'mdi:sleep', period: 'day', type: 'bar', stat: 'max', days: 7, format: 'duration' },
  { id: 'sleepScore', title: 'Sleep score', icon: 'mdi:chart-donut', period: 'day', type: 'bar', stat: 'max', days: 7 },
  { id: 'hr', title: 'Heart rate', icon: 'mdi:heart-pulse', unit: 'bpm', period: 'hour', type: 'line', hours: 48 },
  { id: 'hrv', title: 'HRV', icon: 'mdi:chart-timeline-variant', unit: 'ms', period: 'hour', type: 'line', hours: 48 },
  { id: 'spo2', title: 'Blood oxygen', icon: 'mdi:lungs', unit: '%', period: 'hour', type: 'line', hours: 48 },
  { id: 'resp', title: 'Respiration', icon: 'mdi:weather-windy', unit: 'brpm', period: 'hour', type: 'line', hours: 48 },
  { id: 'stress', title: 'Stress', icon: 'mdi:brain', period: 'hour', type: 'line', hours: 48 }
];

const STYLE = `
  :host { display: block; padding: 4px; }
  .wrap { max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 4px 6px 0; }
  .head .title { display: flex; align-items: center; gap: 10px; font-size: 22px; font-weight: 650; color: var(--primary-text-color); letter-spacing: -.01em; }
  .head .title ha-icon { color: var(--secondary-text-color); --mdc-icon-size: 26px; }
  .head .sub { color: var(--secondary-text-color); font-size: 13px; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); align-items: start; }
  .panel {
    position: relative;
    background: var(--card-background-color, #1a1d23);
    border: 1px solid var(--divider-color, rgba(255,255,255,.08));
    border-radius: 20px;
    box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,.2));
    padding: 16px 18px;
    overflow: hidden;
  }
  .panel::before {
    content: '';
    position: absolute; inset: 0 0 auto 0; height: 3px;
    background: linear-gradient(90deg, #6366f1, #ec4899, transparent 88%);
    opacity: .9;
  }
  .ptitle { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 650; color: var(--primary-text-color); }
  .ptitle ha-icon { --mdc-icon-size: 18px; color: var(--secondary-text-color); }
  .ptitle .meta { margin-left: auto; display: flex; gap: 12px; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .chart { height: 98px; margin-top: 10px; display: flex; flex-direction: column; }
  .chart svg { width: 100%; flex: 1 1 auto; display: block; color: var(--primary-text-color); }
  .bars { flex: 1 1 auto; display: flex; align-items: flex-end; gap: 6px; }
  .day { flex: 1 1 0; display: flex; align-items: flex-end; gap: 2px; height: 100%; }
  .day .b { flex: 1 1 0; min-width: 3px; min-height: 2px; border-radius: 3px 3px 1px 1px; }
  .days { display: flex; gap: 6px; margin-top: 4px; font-size: 10px; color: var(--secondary-text-color); }
  .day-l { flex: 1 1 0; text-align: center; }
  .range { margin-top: 6px; font-size: 10.5px; color: var(--secondary-text-color); letter-spacing: .03em; text-transform: uppercase; }
  .empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--secondary-text-color); font-size: 12.5px; }
  .sess-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-top: 10px; }
  .sess-ring h4 { margin: 0 0 4px; font-size: 13px; font-weight: 650; }
  .sess { padding: 8px 0; border-bottom: 1px solid var(--divider-color, rgba(255,255,255,.08)); }
  .sess:last-child { border-bottom: none; }
  .sess-top { display: flex; align-items: center; gap: 10px; font-size: 12.5px; }
  .sess-date { color: var(--secondary-text-color); }
  .sess-dur { margin-left: auto; font-weight: 600; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .sess-score { font-size: 11px; color: var(--secondary-text-color); background: var(--secondary-background-color, rgba(128,128,128,.12)); border-radius: 999px; padding: 2px 8px; }
  .sess-bar { display: flex; height: 6px; margin-top: 6px; border-radius: 3px; overflow: hidden; background: rgba(128,128,128,.18); }
  .sess-bar i { display: block; height: 100%; }
  .note { color: var(--secondary-text-color); font-size: 11.5px; line-height: 1.55; padding: 0 6px 4px; }
  @media (max-width: 700px) {
    .grid { grid-template-columns: 1fr; }
    .head .title { font-size: 19px; }
    .ptitle .meta { gap: 8px; }
  }
`;

class RingsTrendsCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!Array.isArray(this.config.rings) || !this.config.rings.length) {
      throw new Error('Add a `rings` list to the card configuration (see the README).');
    }
    this._rings = this.config.rings;
    this._panels = Array.isArray(this.config.panels) && this.config.panels.length
      ? this.config.panels
      : PANELS;
    this._stats = {};
    this._statsAt = 0;
    this._statsFailedAt = 0;
    this._statsBusy = false;
    this._statsError = null;
    this._built = false;
    this._refs = {};
    if (this._hass) this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._renderValues();
    this._maybeRefreshStats();
  }

  getCardSize() {
    return 16;
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
    root.innerHTML =
      '<style>' + STYLE + '</style>' +
      '<div class="wrap">' +
        '<div class="head"><div class="title"><ha-icon icon="mdi:chart-line"></ha-icon><span>Trends</span></div><div class="sub" id="sub"></div></div>' +
        '<div class="grid" id="grid"></div>' +
        '<section class="panel sessions"><div class="ptitle"><ha-icon icon="mdi:history"></ha-icon><span>Recent sleep sessions</span></div><div class="sess-cols" id="sessions"></div></section>' +
        '<div class="note">Sleep score is the ring&#8217;s own; SparkyFitness recalculates its score from the stage data. HRV scales differ between firmwares &#8212; compare each person with their own history.</div>' +
      '</div>';

    const grid = root.getElementById('grid');
    this._refs = { panels: {}, sessions: root.getElementById('sessions'), sub: root.getElementById('sub') };

    this._panels.forEach((panel) => {
      const el = document.createElement('section');
      el.className = 'panel';
      el.innerHTML =
        '<div class="ptitle"><ha-icon icon="' + panel.icon + '"></ha-icon><span>' + panel.title + '</span><span class="meta" data-vals></span></div>' +
        '<div class="chart" data-chart></div>' +
        '<div class="range" data-range></div>';
      grid.appendChild(el);
      this._refs.panels[panel.id] = {
        chart: el.querySelector('[data-chart]'),
        vals: el.querySelector('[data-vals]'),
        range: el.querySelector('[data-range]')
      };
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

  _fmt(value, panel) {
    if (value === null || value === undefined) return '\u2014';
    const n = Number(value);
    if (!Number.isFinite(n)) return '\u2014';
    if (panel && panel.format === 'duration') return this._fmtDuration(n);
    if (panel && panel.id === 'resp') return n.toFixed(1);
    if (panel && panel.id === 'steps') return Math.round(n).toLocaleString();
    return String(Math.round(n));
  }

  _fmtDuration(minutes) {
    const n = Math.max(0, Math.round(Number(minutes) || 0));
    const h = Math.floor(n / 60);
    const m = n % 60;
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
  }

  _ago(ts) {
    const mins = Math.round((Date.now() - ts) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.round(mins / 60);
    return hrs < 24 ? hrs + 'h ago' : Math.round(hrs / 24) + 'd ago';
  }

  _renderValues() {
    if (!this._built || !this._hass) return;
    this._panels.forEach((panel) => {
      const ref = this._refs.panels[panel.id];
      if (!ref) return;
      ref.vals.innerHTML = '';
      this._rings.forEach((ring) => {
        const value = this._num(ring.entities[panel.id]);
        const span = document.createElement('span');
        span.style.color = ring.color || 'inherit';
        if (value === null) {
          span.textContent = ring.name + ' \u2014';
        } else {
          const suffix = panel.unit ? ' ' + panel.unit : '';
          span.textContent = ring.name + ' ' + this._fmt(value, panel) + suffix;
        }
        ref.vals.appendChild(span);
      });
    });
    this._renderSessions();
    const sub = this._refs.sub;
    if (sub) {
      if (this._statsAt) {
        sub.textContent = 'hourly \u00b7 48h / daily \u00b7 7d \u00b7 updated ' + this._ago(this._statsAt);
      } else if (this._statsError) {
        sub.textContent = 'statistics unavailable';
      } else {
        sub.textContent = 'loading\u2026';
      }
    }
  }

  _renderSessions() {
    const host = this._refs.sessions;
    if (!host) return;
    host.innerHTML = '';
    this._rings.forEach((ring) => {
      const col = document.createElement('div');
      col.className = 'sess-ring';
      const title = document.createElement('h4');
      title.textContent = ring.name;
      title.style.color = ring.color;
      col.appendChild(title);
      const state = this._state(ring.entities.sleep);
      const sessions = state && state.attributes && Array.isArray(state.attributes.sessions)
        ? state.attributes.sessions
        : [];
      if (!sessions.length) {
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.style.height = '40px';
        empty.textContent = 'No sessions retained yet.';
        col.appendChild(empty);
      }
      sessions.slice(0, 5).forEach((session) => col.appendChild(this._sessionRow(session)));
      host.appendChild(col);
    });
  }

  _sessionRow(session) {
    const row = document.createElement('div');
    row.className = 'sess';
    const top = document.createElement('div');
    top.className = 'sess-top';
    const start = session.start ? new Date(session.start) : null;
    const end = session.end ? new Date(session.end) : null;
    const date = document.createElement('span');
    date.className = 'sess-date';
    date.textContent = start
      ? start.toLocaleDateString(undefined, { weekday: 'short' }) + ' ' +
        start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' \u2192 ' +
        (end ? end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '\u2014')
      : '\u2014';
    const dur = document.createElement('span');
    dur.className = 'sess-dur';
    dur.textContent = this._fmtDuration(session.minutes);
    const score = document.createElement('span');
    score.className = 'sess-score';
    score.textContent = session.score === null || session.score === undefined ? 'no score' : 'score ' + session.score;
    top.append(date, dur, score);
    row.appendChild(top);
    const bar = document.createElement('div');
    bar.className = 'sess-bar';
    const parts = [
      ['deep', session.deep, '#48befc'],
      ['light', session.light, '#92ddfc'],
      ['rem', session.rem, '#fd894e'],
      ['awake', session.awake, '#f25230']
    ];
    const total = parts.reduce((sum, part) => sum + (Number(part[1]) || 0), 0);
    parts.forEach((part) => {
      const seg = document.createElement('i');
      const value = Number(part[1]) || 0;
      seg.style.width = total > 0 ? (value / total * 100).toFixed(1) + '%' : '0%';
      seg.style.background = part[2];
      seg.title = part[0] + ' ' + value + 'm';
      bar.appendChild(seg);
    });
    row.appendChild(bar);
    return row;
  }

  _maybeRefreshStats() {
    if (!this._hass || this._statsBusy) return;
    const now = Date.now();
    if (this._statsAt && now - this._statsAt < 15 * 60000) return;
    if (this._statsError && now - this._statsFailedAt < 5 * 60000) return;
    this._statsBusy = true;
    const end = new Date(now).toISOString();
    const dayIds = [];
    const hourIds = [];
    this._panels.forEach((panel) => {
      this._rings.forEach((ring) => {
        const id = ring.entities[panel.id];
        if (!id || !this._hass.states[id]) return;
        (panel.period === 'day' ? dayIds : hourIds).push(id);
      });
    });
    const fetchStats = (ids, period, types, start) => this._hass.callWS({
      type: 'recorder/statistics_during_period',
      start_time: start,
      end_time: end,
      statistic_ids: [...new Set(ids)],
      period,
      types
    });
    Promise.all([
      dayIds.length ? fetchStats(dayIds, 'day', ['change', 'max'], new Date(now - 7 * 864e5).toISOString()) : {},
      hourIds.length ? fetchStats(hourIds, 'hour', ['mean'], new Date(now - 48 * 3600e3).toISOString()) : {}
    ]).then(([day, hour]) => {
      this._stats = { day: day || {}, hour: hour || {} };
      this._statsAt = Date.now();
      this._statsError = null;
      this._renderCharts();
    }).catch((err) => {
      this._statsError = String((err && err.message) || err);
      this._statsFailedAt = Date.now();
    }).finally(() => {
      this._statsBusy = false;
      this._renderValues();
    });
  }

  _renderCharts() {
    if (!this._built) return;
    this._panels.forEach((panel) => {
      const ref = this._refs.panels[panel.id];
      if (!ref) return;
      const rows = this._stats[panel.period === 'day' ? 'day' : 'hour'] || {};
      if (panel.type === 'bar') {
        this._renderBars(panel, ref, rows);
      } else {
        this._renderLine(panel, ref, rows);
      }
    });
  }

  _points(rows, entity, stat) {
    const data = rows[entity] || [];
    return data
      .map((row) => ({
        t: Number(row.start),
        v: row[stat] === null || row[stat] === undefined ? null : Number(row[stat])
      }))
      .filter((point) => Number.isFinite(point.t) && Number.isFinite(point.v));
  }

  _renderBars(panel, ref, rows) {
    const series = this._rings.map((ring) => ({
      ring,
      points: this._points(rows, ring.entities[panel.id], panel.stat)
    }));
    const starts = [...new Set(series.flatMap((s) => s.points.map((p) => p.t)))]
      .sort((a, b) => a - b)
      .slice(-(panel.days || 7));
    if (!starts.length) {
      ref.chart.innerHTML = '<div class="empty">no data yet</div>';
      ref.range.textContent = '';
      return;
    }
    const maps = series.map((s) => new Map(s.points.map((p) => [p.t, p.v])));
    const values = [];
    maps.forEach((map) => starts.forEach((t) => {
      const v = map.get(t);
      if (v !== null && v !== undefined) values.push(v);
    }));
    const max = Math.max(1, ...values);
    const bars = document.createElement('div');
    bars.className = 'bars';
    starts.forEach((t) => {
      const day = document.createElement('div');
      day.className = 'day';
      series.forEach((s, index) => {
        const v = maps[index].get(t);
        const bar = document.createElement('div');
        bar.className = 'b';
        bar.style.background = s.ring.color;
        bar.style.height = v === null || v === undefined ? '0%' : Math.max(2, (Math.max(0, v) / max) * 100).toFixed(1) + '%';
        bar.title = s.ring.name + ': ' + (v === null || v === undefined ? 'no data' : this._fmt(v, panel));
        day.appendChild(bar);
      });
      bars.appendChild(day);
    });
    const labels = document.createElement('div');
    labels.className = 'days';
    starts.forEach((t) => {
      const label = document.createElement('div');
      label.className = 'day-l';
      label.textContent = new Date(t).toLocaleDateString(undefined, { weekday: 'narrow' });
      labels.appendChild(label);
    });
    ref.chart.innerHTML = '';
    ref.chart.appendChild(bars);
    ref.chart.appendChild(labels);
    ref.range.textContent = (panel.days || 7) + ' days \u00b7 max ' + this._fmt(max, panel) + (panel.unit ? ' ' + panel.unit : '');
  }

  _renderLine(panel, ref, rows) {
    const series = this._rings.map((ring) => ({
      ring,
      points: this._points(rows, ring.entities[panel.id], 'mean')
    }));
    const all = series.flatMap((s) => s.points.map((p) => p.v));
    if (!all.length) {
      ref.chart.innerHTML = '<div class="empty">no data yet</div>';
      ref.range.textContent = '';
      return;
    }
    const lo = Math.min(...all);
    const hi = Math.max(...all);
    let min = lo;
    let max = hi;
    if (max - min < 1e-6) {
      min -= 1;
      max += 1;
    }
    const pad = (max - min) * 0.12;
    min -= pad;
    max += pad;
    const now = Date.now();
    const span = (panel.hours || 48) * 3600e3;
    const x = (t) => ((t - (now - span)) / span) * 300;
    const y = (v) => 92 - ((v - min) / (max - min)) * 84;
    const segments = [];
    series.forEach((s) => {
      let current = [];
      const flush = () => {
        if (current.length > 1) segments.push({ color: s.ring.color, points: current.join(' ') });
        current = [];
      };
      s.points.forEach((point, index) => {
        const previous = s.points[index - 1];
        if (previous && point.t - previous.t > 3 * 3600e3) flush();
        current.push(x(point.t).toFixed(1) + ',' + y(point.v).toFixed(1));
      });
      flush();
    });
    const svg = ['<svg viewBox="0 0 300 100" preserveAspectRatio="none">'];
    [25, 50, 75].forEach((gy) => {
      svg.push('<line x1="0" y1="' + gy + '" x2="300" y2="' + gy + '" stroke="currentColor" stroke-opacity=".08" stroke-width="1" vector-effect="non-scaling-stroke"/>');
    });
    segments.forEach((segment) => {
      svg.push('<polyline points="' + segment.points + '" fill="none" stroke="' + segment.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>');
    });
    svg.push('</svg>');
    ref.chart.innerHTML = svg.join('');
    ref.range.textContent = (panel.hours || 48) + 'h \u00b7 ' + this._fmt(lo, panel) + ' \u2013 ' + this._fmt(hi, panel) + (panel.unit ? ' ' + panel.unit : '');
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, RingsTrendsCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: 'Rings Trends',
    description: 'POBOVi ring trends and sleep sessions'
  });
}
