// ===========================================================================
// State
// ===========================================================================
const state = {
  currentView: 'home',
  graphReady: false,
  graphInfo: null,
  searchTimer: null,
  origin: null,        // { id, name, artist, genre, ... }
  target: null,        // { id, name, artist, genre, ... }
  algorithm: 'astar',
  penalize: false,
  path: null,          // array of song objects from API
  player: {
    queue: [],         // array of song objects
    index: -1,
    playing: false,
    progress: 0,       // 0-100
    progressTimer: null,
    elapsed: 0,        // seconds
    duration: 210,     // simulated 3:30
  }
};

// Genre → color (kept for chips)

const GENRE_COLORS = [
  '#1DB954','#3b82f6','#f59e0b','#ec4899','#8b5cf6',
  '#06b6d4','#ef4444','#84cc16','#f97316','#14b8a6',
];

const genreColorMap = {};
let genreColorIdx = 0;
function genreColor(genre) {
  const k = (genre || 'unknown').toLowerCase();
  if (!genreColorMap[k]) {
    genreColorMap[k] = GENRE_COLORS[genreColorIdx++ % GENRE_COLORS.length];
  }
  return genreColorMap[k];
}

// ===========================================================================
// Navigation
// ===========================================================================
function navigate(view) {
  // Update sidebar
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navMap = { home: 0, search: 1, recommend: 2 };
  const navItems = document.querySelectorAll('#sidebar .sidebar-nav .nav-item');
  if (navMap[view] !== undefined) navItems[navMap[view]]?.classList.add('active');

  // Update views
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${view}`)?.classList.add('active');

  // Update header
  const titles = {
    home: 'Bem-vindo ao <span>Musical Graph</span>',
    search: 'Buscar <span>Músicas</span>',
    recommend: 'Gerar <span>Recomendação</span>',
  };
  document.getElementById('header-title').innerHTML = titles[view] || view;

  state.currentView = view;

  if (view === 'search') {
    setTimeout(() => document.getElementById('search-input').focus(), 100);
    if (state.graphReady) loadGenreData();
  }
}

// ===========================================================================
// Status polling
// ===========================================================================
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');

    if (data.status === 'loading') {
      dot.className = 'status-dot';
      txt.textContent = 'Carregando grafo...';
      setTimeout(pollStatus, 1500);
    } else if (data.status === 'ready') {
      dot.className = 'status-dot ready';
      txt.textContent = `${data.nodes.toLocaleString()} músicas`;
      state.graphReady = true;
      state.graphInfo = data;
      onGraphReady(data);
      // Pré-carrega dados de gênero em background
      loadGenreData();
    } else {
      dot.className = 'status-dot error';
      txt.textContent = 'Erro ao carregar';
    }
  } catch {
    setTimeout(pollStatus, 2000);
  }
}

function onGraphReady(info) {
  document.getElementById('header-meta').textContent =
    `${info.nodes.toLocaleString()} músicas · ${info.edges.toLocaleString()} conexões`;

  document.getElementById('home-stats').innerHTML = `
    O grafo musical possui <strong style="color:var(--text-primary)">${info.nodes.toLocaleString()} músicas</strong>
    conectadas por <strong style="color:var(--text-primary)">${info.edges.toLocaleString()} arestas</strong>.
    Cada aresta representa similaridade entre características como energia, dançabilidade, valência e tempo.
    <br><br>
    Use o algoritmo <strong style="color:var(--accent)">A*</strong> para encontrar o caminho mais eficiente,
    ou <strong style="color:var(--accent)">Dijkstra</strong> para uma busca exaustiva garantidamente ótima.
  `;
}

// ===========================================================================
// Search
// ===========================================================================
async function handleSearch(query) {
  clearTimeout(state.searchTimer);
  const browsePanel   = document.getElementById('browse-panel');
  const resultsPanel  = document.getElementById('search-results-panel');
  const count         = document.getElementById('search-results-count');

  if (!query.trim()) {
    browsePanel.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    count.classList.add('hidden');
    return;
  }

  browsePanel.classList.add('hidden');
  resultsPanel.classList.remove('hidden');

  state.searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      renderSearchResults(data.results || []);
    } catch (e) {
      showToast('Erro na busca: ' + e.message, 'error');
    }
  }, 280);
}

function renderSearchResults(songs) {
  const list  = document.getElementById('search-results-list');
  const count = document.getElementById('search-results-count');

  if (!songs.length) {
    list.innerHTML = `<div style="color:var(--text-muted);padding:20px 0;text-align:center">Nenhuma música encontrada</div>`;
    count.classList.add('hidden');
    return;
  }

  count.textContent = `${songs.length} resultado(s)`;
  count.classList.remove('hidden');
  list.innerHTML = songs.map((s, i) => songRowHtml(s, i)).join('');
}

// ===========================================================================
// Browse por gênero
// ===========================================================================
const genreCache = {};
let genreDataLoaded = false;

async function loadGenreData() {
  if (genreDataLoaded) return;
  try {
    let page = 1;
    let fetched = 0;
    let total = Infinity;
    const allSongs = [];

    while (fetched < total) {
      const res = await fetch(`/api/songs/all?page=${page}&per_page=200`);
      const data = await res.json();
      total = data.total;
      allSongs.push(...data.songs);
      fetched += data.songs.length;
      if (data.songs.length < 200) break;
      page++;
    }

    for (const song of allSongs) {
      const g = (song.genre || 'outros').toLowerCase();
      if (!genreCache[g]) genreCache[g] = [];
      genreCache[g].push(song);
    }
    for (const g of Object.keys(genreCache)) {
      genreCache[g].sort((a, b) => a.name.localeCompare(b.name));
    }

    genreDataLoaded = true;
    renderGenreGrid();
  } catch (e) {
    console.error('Erro ao carregar gêneros:', e);
  }
}

function renderGenreGrid() {
  const grid = document.getElementById('genre-grid');
  if (!grid) return;
  const genres = Object.keys(genreCache).sort();

  const TILE_GRADIENTS = [
    'linear-gradient(135deg,#1a6b3a,#1DB954)',
    'linear-gradient(135deg,#1a3a6b,#3b82f6)',
    'linear-gradient(135deg,#6b1a1a,#ef4444)',
    'linear-gradient(135deg,#6b4a1a,#f59e0b)',
    'linear-gradient(135deg,#4a1a6b,#8b5cf6)',
    'linear-gradient(135deg,#1a5a6b,#06b6d4)',
    'linear-gradient(135deg,#6b1a5a,#ec4899)',
    'linear-gradient(135deg,#3a6b1a,#84cc16)',
    'linear-gradient(135deg,#6b3a1a,#f97316)',
    'linear-gradient(135deg,#1a6b5a,#14b8a6)',
    'linear-gradient(135deg,#2a2a4a,#6366f1)',
    'linear-gradient(135deg,#3a1a6b,#7c3aed)',
  ];

  grid.innerHTML = genres.map((genre, i) => {
    const grad = TILE_GRADIENTS[i % TILE_GRADIENTS.length];
    const count = genreCache[genre].length;
    return `
      <div class="genre-tile" style="background:${grad}" onclick="openGenre('${genre.replace(/'/g,"\\'")}')">
        <svg class="genre-tile-icon" width="36" height="36" viewBox="0 0 24 24" fill="none"
          stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
        </svg>
        <div>
          <div style="font-weight:700;font-size:13px;color:#fff;text-shadow:0 1px 4px rgba(0,0,0,.5)">${escHtml(genre)}</div>
          <div style="font-size:11px;color:rgba(255,255,255,.65);margin-top:2px">${count} músicas</div>
        </div>
      </div>
    `;
  }).join('');
}

function openGenre(genre) {
  const songs = genreCache[genre] || [];
  const panel = document.getElementById('genre-songs-panel');
  const grid  = document.getElementById('genre-grid');

  document.getElementById('genre-songs-title').innerHTML = `
    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
      background:${genreColor(genre)};margin-right:6px;flex-shrink:0"></span>
    ${escHtml(genre)}
  `;
  document.getElementById('genre-songs-count').textContent = `${songs.length} músicas`;

  const list = document.getElementById('genre-songs-list');
  list.innerHTML = songs.map((s, i) => songRowHtml(s, i)).join('');

  grid.classList.add('hidden');
  panel.classList.remove('hidden');
}

function backToGenres() {
  document.getElementById('genre-songs-panel').classList.add('hidden');
  document.getElementById('genre-grid').classList.remove('hidden');
}

function songRowHtml(s, i) {
  const sJson = JSON.stringify(s).replace(/"/g, '&quot;');
  const isOrigin = state.origin?.id === s.id;
  const isTarget = state.target?.id === s.id;
  return `
    <div class="song-row" onclick="playSong(${sJson})">
      <div>
        <span class="song-row-num">${i + 1}</span>
        <span class="song-row-play">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
        </span>
      </div>
      <div class="song-row-info">
        <h4>${escHtml(s.name)}</h4>
        <p>${escHtml(s.artist)}</p>
      </div>
      <div>
        <span class="song-row-genre" style="color:${genreColor(s.genre)}">${escHtml(s.genre || 'unknown')}</span>
      </div>
      <div class="song-row-actions">
        <button class="btn-tag ${isOrigin ? 'origin' : ''}"
          onclick="event.stopPropagation();setOrigin(${sJson})">
          ${isOrigin ? '· Origem' : 'Origem'}
        </button>
        <button class="btn-tag ${isTarget ? 'target' : ''}"
          onclick="event.stopPropagation();setTarget(${sJson})">
          ${isTarget ? '· Destino' : 'Destino'}
        </button>
        <a class="btn-tag" style="text-decoration:none;color:var(--accent);border-color:var(--accent)"
          href="${spotifySearchUrl(s.name, s.artist)}" target="_blank"
          onclick="event.stopPropagation()">Spotify</a>
      </div>
    </div>
  `;
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ===========================================================================
// Origin / Target selection
// ===========================================================================
function setOrigin(song) {
  state.origin = song;
  renderSelectionCards();
  updateGenerateButton();
  showToast(`Origem: ${song.name}`, 'success');
  // Re-render search results to update buttons
  const q = document.getElementById('search-input').value;
  if (q) handleSearch(q);
}

function setTarget(song) {
  state.target = song;
  renderSelectionCards();
  updateGenerateButton();
  showToast(`Destino: ${song.name}`, 'info');
  const q = document.getElementById('search-input').value;
  if (q) handleSearch(q);
}

function renderSelectionCards() {
  renderSongCard('origin', state.origin, 'Origem', 'badge-origin', '#f59e0b');
  renderSongCard('target', state.target, 'Destino', 'badge-target', '#3b82f6');
}

function renderSongCard(type, song, label, badgeClass, accentColor) {
  const el = document.getElementById(`${type}-card`);
  if (!song) {
    el.className = 'empty-card';
    el.onclick = () => navigate('search');
    el.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="opacity:0.4">
        <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/>
        <path d="M12 8v8M8 12h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>Clique para selecionar</span>
    `;
    return;
  }

  el.className = 'selected-song-card';
  el.onclick = null;
  el.innerHTML = `
    <div class="badge ${badgeClass}">${label}</div>
    <div class="selected-song-art" style="background:${accentColor}22">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${accentColor}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
      </svg>
    </div>
    <div class="selected-song-info">
      <h4>${escHtml(song.name)}</h4>
      <p>${escHtml(song.artist)}</p>
    </div>
    <button class="clear-btn" onclick="clear${type.charAt(0).toUpperCase()+type.slice(1)}()" title="Remover">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
  `;
}

function clearorigin() { state.origin = null; renderSelectionCards(); updateGenerateButton(); }
function cleartarget() { state.target = null; renderSelectionCards(); updateGenerateButton(); }

function updateGenerateButton() {
  const btn = document.getElementById('btn-generate');
  btn.disabled = !(state.origin && state.target && state.graphReady);
}

// ===========================================================================
// Algorithm config
// ===========================================================================
function setAlgorithm(algo) {
  state.algorithm = algo;
  document.getElementById('pill-astar').classList.toggle('active', algo === 'astar');
  document.getElementById('pill-dijkstra').classList.toggle('active', algo === 'dijkstra');
}

function togglePenalize() {
  state.penalize = !state.penalize;
  document.getElementById('toggle-penalize').classList.toggle('on', state.penalize);
}

// ===========================================================================
// Generate path
// ===========================================================================
async function generatePath() {
  if (!state.origin || !state.target) return;

  const resultEl = document.getElementById('recommend-result');
  resultEl.innerHTML = `
    <div class="result-empty">
      <div class="spinner"></div>
      <p>Calculando rota com ${state.algorithm === 'astar' ? 'A*' : 'Dijkstra'}...</p>
    </div>
  `;

  navigate('recommend');

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: state.origin.id,
        target: state.target.id,
        algorithm: state.algorithm,
        penalize: state.penalize,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      resultEl.innerHTML = `
        <div class="result-empty">
          <p style="color:#e55353">${escHtml(data.error || 'Erro desconhecido')}</p>
        </div>
      `;
      showToast(data.error || 'Erro', 'error');
      return;
    }

    state.path = data.path;
    renderPathResult(data);
    showToast(`Rota com ${data.path.length} músicas encontrada!`, 'success');

    // Load path into player queue
    playerLoadQueue(data.path);

  } catch (e) {
    resultEl.innerHTML = `
      <div class="result-empty">
        <p style="color:#e55353">Erro de rede: ${e.message}</p>
      </div>
    `;
    showToast('Erro de rede', 'error');
  }
}

function renderPathResult(data) {
  const resultEl = document.getElementById('recommend-result');
  const algoLabel = data.algorithm === 'astar' ? 'A* (Weighted A*)' : 'Dijkstra';

  let html = `
    <div class="result-meta">
      <div class="result-stat">
        <div class="result-stat-val">${data.path.length}</div>
        <div class="result-stat-label">Músicas</div>
      </div>
      <div class="result-stat">
        <div class="result-stat-val">${data.transitions}</div>
        <div class="result-stat-label">Transições</div>
      </div>
      <div class="result-stat">
        <div class="result-stat-val">${data.cost.toFixed(4)}</div>
        <div class="result-stat-label">Custo Total</div>
      </div>
      <div class="result-stat">
        <div class="result-stat-val" style="font-size:13px">${algoLabel}</div>
        <div class="result-stat-label">Algoritmo</div>
      </div>
    </div>
    <div class="path-list">
  `;

  data.path.forEach((song, i) => {
    const isOrigin = i === 0;
    const isTarget = i === data.path.length - 1;
    const cls = isOrigin ? 'is-origin' : isTarget ? 'is-target' : '';

    html += `
      <div class="path-node ${cls}" id="path-node-${i}">
        <div class="path-connector">
          <div class="path-dot"></div>
          <div class="path-line"></div>
        </div>
        <div class="path-card" onclick="playerJumpTo(${i})">
          <div class="path-card-header">
            <div style="display:flex;align-items:center;gap:8px">
              <div style="width:10px;height:10px;border-radius:50%;background:${genreColor(song.genre)};flex-shrink:0"></div>
              <span class="path-index">#${i + 1}</span>
            </div>
            ${isOrigin ? '<span class="path-badge path-badge-origin">ORIGEM</span>' : ''}
            ${isTarget ? '<span class="path-badge path-badge-target">DESTINO</span>' : ''}
          </div>
          <h4>${escHtml(song.name)}</h4>
          <p>${escHtml(song.artist)}</p>
          <div class="path-features">
            <span class="feature-chip">Energia ${(song.energy * 100).toFixed(0)}%</span>
            <span class="feature-chip">Dança ${(song.danceability * 100).toFixed(0)}%</span>
            <span class="feature-chip">Valência ${(song.valence * 100).toFixed(0)}%</span>
            <span class="feature-chip">${song.tempo} BPM</span>
            <span class="feature-chip" style="color:${genreColor(song.genre)}">${escHtml(song.genre || '—')}</span>
            <a class="feature-chip" style="color:var(--accent);text-decoration:none;cursor:pointer"
              href="${spotifySearchUrl(song.name, song.artist)}" target="_blank"
              onclick="event.stopPropagation()">Spotify</a>
          </div>
        </div>
      </div>
    `;
  });

  html += '</div>';
  resultEl.innerHTML = html;
}

// ===========================================================================
// Player (simulated)
// ===========================================================================
function playerLoadQueue(songs) {
  const p = state.player;
  clearInterval(p.progressTimer);
  p.queue = songs;
  p.index = 0;
  p.playing = false;
  p.progress = 0;
  p.elapsed = 0;
  playerRenderCurrent();
  document.getElementById('btn-play').disabled = false;
  document.getElementById('btn-next').disabled = songs.length <= 1;
  document.getElementById('btn-prev').disabled = true;
}

function playerRenderCurrent() {
  const p = state.player;
  const song = p.queue[p.index];
  if (!song) return;

  document.getElementById('player-name').textContent = song.name;
  document.getElementById('player-artist').textContent = song.artist;
  const artEl = document.getElementById('player-art');
  artEl.style.background = genreColor(song.genre) + '22';
  artEl.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none"
    stroke="${genreColor(song.genre)}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
  </svg>`;

  // Simulate different durations by tempo
  p.duration = song.tempo ? Math.round(180 + (song.tempo / 200) * 60) : 210;

  updateProgressDisplay();
  updateSpotifyButton(song);

  // Highlight path node
  document.querySelectorAll('.path-node').forEach(el => el.classList.remove('is-playing'));
  document.getElementById(`path-node-${p.index}`)?.classList.add('is-playing');
  document.getElementById(`path-node-${p.index}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function playerToggle() {
  const p = state.player;
  if (p.queue.length === 0) return;

  p.playing = !p.playing;
  updatePlayPauseIcon();

  const art = document.getElementById('player-art');
  if (p.playing) {
    art.classList.add('playing');
    p.progressTimer = setInterval(() => {
      p.elapsed += 1;
      p.progress = Math.min((p.elapsed / p.duration) * 100, 100);
      updateProgressDisplay();
      if (p.elapsed >= p.duration) {
        playerNext();
      }
    }, 1000);
  } else {
    art.classList.remove('playing');
    clearInterval(p.progressTimer);
  }
}

function playerNext() {
  const p = state.player;
  if (p.index >= p.queue.length - 1) return;
  clearInterval(p.progressTimer);
  p.index++;
  p.progress = 0;
  p.elapsed = 0;
  p.playing = false;
  playerRenderCurrent();
  document.getElementById('btn-prev').disabled = false;
  document.getElementById('btn-next').disabled = p.index >= p.queue.length - 1;
  updatePlayPauseIcon();
  playerToggle(); // auto-play next
}

function playerPrev() {
  const p = state.player;
  if (p.index <= 0) return;
  clearInterval(p.progressTimer);
  p.index--;
  p.progress = 0;
  p.elapsed = 0;
  p.playing = false;
  playerRenderCurrent();
  document.getElementById('btn-prev').disabled = p.index <= 0;
  document.getElementById('btn-next').disabled = false;
  updatePlayPauseIcon();
  playerToggle();
}

function playerJumpTo(idx) {
  const p = state.player;
  if (idx < 0 || idx >= p.queue.length) return;
  clearInterval(p.progressTimer);
  p.index = idx;
  p.progress = 0;
  p.elapsed = 0;
  p.playing = false;
  playerRenderCurrent();
  document.getElementById('btn-prev').disabled = idx <= 0;
  document.getElementById('btn-next').disabled = idx >= p.queue.length - 1;
  updatePlayPauseIcon();
  playerToggle();
}

function updatePlayPauseIcon() {
  const playing = state.player.playing;
  document.getElementById('icon-play').style.display = playing ? 'none' : 'block';
  document.getElementById('icon-pause').style.display = playing ? 'block' : 'none';
}

function updateProgressDisplay() {
  const p = state.player;
  document.getElementById('progress-fill').style.width = p.progress + '%';
  document.getElementById('time-current').textContent = formatTime(p.elapsed);
  document.getElementById('time-total').textContent = formatTime(p.duration);
}

function seekProgress(event) {
  const p = state.player;
  if (!p.queue.length) return;
  const bar = document.getElementById('progress-bar');
  const rect = bar.getBoundingClientRect();
  const ratio = (event.clientX - rect.left) / rect.width;
  p.progress = Math.max(0, Math.min(100, ratio * 100));
  p.elapsed = Math.round((p.progress / 100) * p.duration);
  updateProgressDisplay();
}

function setVolume(event) {
  const bar = document.querySelector('.volume-bar');
  const rect = bar.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  document.getElementById('volume-fill').style.width = (ratio * 100) + '%';
}

function formatTime(s) {
  s = Math.floor(s);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function playSong(song) {
  playerLoadQueue([song]);
  document.getElementById('btn-next').disabled = true;
  document.getElementById('btn-prev').disabled = true;
  updateSpotifyButton(song);
  playerToggle();
}

// ===========================================================================
// Spotify integration
// ===========================================================================
function spotifySearchUrl(name, artist) {
  const query = encodeURIComponent(`${name} ${artist}`);
  return `https://open.spotify.com/search/${query}`;
}

function openInSpotify(event) {
  const p = state.player;
  const song = p.queue[p.index];
  if (!song) return false;
  window.open(spotifySearchUrl(song.name, song.artist), '_blank');
  return false;
}

function updateSpotifyButton(song) {
  const btn = document.getElementById('btn-spotify-open');
  if (!btn || !song) return;
  btn.href = spotifySearchUrl(song.name, song.artist);
}

// ===========================================================================
// Toast notifications
// ===========================================================================
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const icon = { success: '✓', error: '✕', info: 'i' }[type] || 'i';
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span style="font-weight:700;color:${type === 'success' ? 'var(--accent)' : type === 'error' ? '#e55353' : '#3b82f6'}">${icon}</span> <span>${escHtml(msg)}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ===========================================================================
// Boot
// ===========================================================================
document.addEventListener('DOMContentLoaded', () => {
  pollStatus();
});