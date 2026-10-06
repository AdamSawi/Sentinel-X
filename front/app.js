const $ = id => document.getElementById(id);
let measures = [];
const time = seconds => new Date(seconds * 1000).toLocaleTimeString('fr-FR');
function node(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
function card(title, value, detail, good) {
  const n = node('div', '', 'card'); n.append(node('small', title), node('strong', value, good ? 'ok' : 'bad'), node('small', detail)); return n;
}
function chart() {
  const canvas = $('chart'), c = canvas.getContext('2d');
  const points = measures.filter(x => x.device_id === $('device').value).reverse();
  c.clearRect(0, 0, canvas.width, canvas.height);
  if (!points.length) { $('chart-caption').textContent = 'En attente de mesures.'; return; }
  const values = points.map(x => x.temperature_c), lo = Math.min(...values) - 1, hi = Math.max(...values) + 1;
  const t0 = points[0].received_at, dt = Math.max(1, points.at(-1).received_at - t0);
  c.strokeStyle = '#63dac1'; c.lineWidth = 2; c.beginPath();
  points.forEach((p, i) => { const x = 60 + (p.received_at - t0) / dt * 920, y = 205 - (p.temperature_c - lo) / (hi - lo) * 185; if (i) c.lineTo(x, y); else c.moveTo(x, y); }); c.stroke();
  c.fillStyle = '#99adc4'; c.font = '14px sans-serif'; c.fillText(hi.toFixed(1) + ' °C', 0, 20); c.fillText(lo.toFixed(1) + ' °C', 0, 205);
  $('chart-caption').textContent = `${points.length} mesures · ${time(t0)} — ${time(points.at(-1).received_at)} · axe temporel : réception serveur`;
}
$('device').addEventListener('change', chart);
async function get(path) { const r = await fetch(path, {cache:'no-store'}); if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }
async function refresh() {
  try {
    const [health, telemetry, events] = await Promise.all([get('/api/health'), get('/api/telemetry'), get('/api/events')]);
    const now = Date.parse(health.server_time) / 1000;
    $('connection').textContent = 'Dernière actualisation : ' + time(now); $('connection').className = 'ok';
    $('health').replaceChildren(card('API', health.api, 'Contrôle HTTP réel', true), card('SQLite', health.database, 'Stockage persistant interne', true), card('MQTT / TLS', health.mqtt, 'Connexion du backend au broker', health.mqtt === 'connected'), card('Messages rejetés', health.rejected_since_start, 'Validation/authentification API et ingestion, depuis démarrage', health.rejected_since_start === 0));
    measures = telemetry;
    const latest = new Map(); for (const p of measures) if (!latest.has(p.device_id)) latest.set(p.device_id, p);
    const cards = [...latest.values()].map(p => card(p.device_id + (p.simulated ? ' · SIMULÉ' : ' · DÉCLARÉ NON SIMULÉ'), p.temperature_c.toFixed(1) + ' °C', `${now-p.received_at > 15 ? 'PÉRIMÉ · ' : ''}humidité ${p.humidity_pct ?? '—'} % · gaz ${p.gas_index ?? '—'} (indice) · reçu ${time(p.received_at)}`, now-p.received_at <= 15));
    $('devices').replaceChildren(...(cards.length ? cards : [node('p', 'Aucun capteur connecté. En attente du composant de votre équipe via MQTT ou API.')]));
    const selected = $('device').value; $('device').replaceChildren(...[...latest.keys()].map(id => {const o = node('option', id); o.value=id; return o;})); if (latest.has(selected)) $('device').value=selected; chart();
    const beat = events.find(e => e.event_type === 'heartbeat');
    $('vision').textContent = beat ? `Dernier heartbeat : ${beat.device_id}, ${time(beat.received_at)}${now-beat.received_at > 15 ? ' · PÉRIMÉ' : ' · récent'}` : 'Santé du modèle inconnue : aucun heartbeat reçu. Une absence d’intrusion ne prouve pas son arrêt.';
    $('events').replaceChildren(...events.filter(e => e.event_type !== 'heartbeat').map(e => { const tr=node('tr',''); [time(e.received_at),e.device_id,e.zone,e.event_type,e.confidence == null ? '—' : `${Math.round(e.confidence*100)} %`,e.simulated?'SIMULÉ / REJOUÉ':'Déclaré non simulé'].forEach(v=>tr.append(node('td',v))); return tr; }));
  } catch (e) { $('connection').textContent = 'Backend inaccessible — affichage non actualisé. ' + e.message; $('connection').className='bad'; }
  setTimeout(refresh, 2000);
}
refresh();
