/* ===== Init MediaElement + Enhanced UI ===== */
var audioEnhancer = (function () {
  let audioEl, player, ctx, analyser, dataArray, rafId;
  let currentLyricIndex = -1;
  let lyricsData = [];
  let lyricsListEl, lyricsContainerEl;
  let isLyricsFetching = false;
  const seekStep = 5; // seconds

  function initMediaElement() {
    const media = $('audio.fc-media', 'body');
    if (media.length) {
      media.mediaelementplayer({
        audioHeight: 40,
        features: ['playpause', 'current', 'duration', 'progress', 'volume', 'tracks', 'fullscreen'],
        alwaysShowControls: true,
        timeAndDurationSeparator: '<span></span>',
        iPadUseNativeControls: true,
        iPhoneUseNativeControls: true,
        AndroidUseNativeControls: true,
        success: function (mediaEl/*, originalNode, instance */) {
          audioEl = mediaEl; // HTMLAudioElement
          wireCustomControls();
          prepAudioContext();
          mountLyrics();
          bindKeyboardShortcuts();
          applySavedTheme();
        }
      });
    }
  }

  /* ===== Custom Controls ===== */
  function wireCustomControls() {
    const $btnPlayPause = $('#btnPlayPause');
    const $btnBack = $('#btnBack');
    const $btnFwd = $('#btnFwd');
    const $vol = $('#volRange');
    const $curr = $('#currTime');
    const $dur = $('#durTime');

    // duration on metadata load
    audioEl.addEventListener('loadedmetadata', () => {
      $dur.text(formatTime(audioEl.duration));
      $vol.val(audioEl.volume);
      startWave();
    });

    // time updates - THIS IS WHERE LYRICS SYNC HAPPENS
    audioEl.addEventListener('timeupdate', () => {
      $curr.text(formatTime(audioEl.currentTime));
      syncLyrics(audioEl.currentTime);
    });

    // play/pause UI + fade
    function fade(target, cb) {
      const step = 0.05;
      if (target > audioEl.volume) {
        let i = audioEl.volume;
        const up = setInterval(() => {
          i = Math.min(1, i + step);
          audioEl.volume = i;
          if (i >= target) { clearInterval(up); cb && cb(); }
        }, 20);
      } else {
        let i = audioEl.volume;
        const down = setInterval(() => {
          i = Math.max(0, i - step);
          audioEl.volume = i;
          if (i <= target) { clearInterval(down); cb && cb(); }
        }, 20);
      }
    }

    $btnPlayPause.on('click', () => {
      if (audioEl.paused) {
        fade(Math.max($vol.val(), 0.6), () => audioEl.play());
      } else {
        fade(0.0, () => audioEl.pause());
      }
    });

    audioEl.addEventListener('play', () => {
      $btnPlayPause.find('i').removeClass('fa-play').addClass('fa-pause');
      startWave();
    });
    audioEl.addEventListener('pause', () => {
      $btnPlayPause.find('i').removeClass('fa-pause').addClass('fa-play');
      stopWave();
    });

    // seek buttons
    $btnBack.on('click', () => { audioEl.currentTime = Math.max(0, audioEl.currentTime - seekStep); });
    $btnFwd.on('click', () => { audioEl.currentTime = Math.min(audioEl.duration || 0, audioEl.currentTime + seekStep); });

    // volume
    $vol.on('input', () => { audioEl.volume = parseFloat($vol.val()); });

    // Lyrics fetch button handler
    $('#btnFetchLyrics').on('click', function() {
      if (isLyricsFetching) return;
      
      const artist = $(this).data('artist') || $('.titre h3').text().trim();
      const title = $(this).data('title') || $('.titre h1').text().trim();
      const songId = $('.Melophile').data('song-id');
      
      fetchLyricsFromBackend(artist, title, songId);
    });
  }

  /* ===== Theme Toggle ===== */
  function applySavedTheme() {
    const html = document.documentElement;
    const stored = html.getAttribute('data-theme') || 'dark';
    html.setAttribute('data-theme', stored);
  }
  function toggleTheme() {
    const html = document.documentElement;
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
  }
  document.addEventListener('click', (e) => {
    if (e.target.closest('#themeToggle')) toggleTheme();
  });

  /* ===== Web Audio Waveform ===== */
  function prepAudioContext() {
    try {
      const ACtx = window.AudioContext || window.webkitAudioContext;
      ctx = new ACtx();
      const source = ctx.createMediaElementSource(audioEl);
      analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      const bufferLength = analyser.frequencyBinCount;
      dataArray = new Uint8Array(bufferLength);
      source.connect(analyser);
      analyser.connect(ctx.destination);
    } catch (e) {
      console.warn('AudioContext not available', e);
    }
  }

  function startWave() {
    const canvas = document.getElementById('waveform');
    if (!canvas || !analyser) return;
    const c = canvas.getContext('2d');

    function draw() {
      rafId = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);
      c.clearRect(0, 0, canvas.width, canvas.height);

      const w = canvas.width;
      const h = canvas.height;
      const barCount = 64;
      const step = Math.floor(dataArray.length / barCount);
      const barW = (w / barCount) * 0.7;

      for (let i = 0; i < barCount; i++) {
        const v = dataArray[i * step] / 255;
        const barH = Math.max(6, v * (h - 8));
        const x = i * (w / barCount) + 6;
        const y = h - barH - 4;

        const grad = c.createLinearGradient(x, y, x, y + barH);
        grad.addColorStop(0, '#8a5cff');
        grad.addColorStop(0.5, '#00e3ff');
        grad.addColorStop(1, '#00d0ffff');

        c.fillStyle = grad;
        c.fillRect(x, y, barW, barH);
        c.shadowColor = '#00e3ff';
        c.shadowBlur = 8;
      }
    }
    cancelAnimationFrame(rafId);
    draw();
  }
  function stopWave() { cancelAnimationFrame(rafId); }

  /* ===== Lyrics Fetching Functions ===== */
  function fetchLyricsFromBackend(artist, title, songId) {
    if (!artist || !title) {
      showLyricsMessage('❌ Artist and title required', 'error');
      return;
    }

    console.log(`Fetching lyrics for: ${artist} - ${title}`);
    isLyricsFetching = true;
    
    // Update button state
    const fetchBtn = $('#btnFetchLyrics');
    const originalIcon = fetchBtn.find('i').attr('class');
    fetchBtn.find('i').attr('class', 'fa fa-spinner fa-spin');
    fetchBtn.prop('disabled', true);

    // Show loading state
    showLyricsMessage('🎵 Fetching synced lyrics...', 'loading');

    const requestData = {
      artist: artist,
      title: title
    };
    
    if (songId) {
      requestData.song_id = songId;
    }

    return fetch('fetch-lyrics/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
        console.log('Lyrics response:', data);
        
        if (data.success && data.lyrics && data.lyrics.length > 0) {
            lyricsData = data.lyrics;
            
            // Ensure all lyrics have timestamp field for precise syncing
            lyricsData.forEach(item => {
              if (typeof item.timestamp === 'undefined') {
                item.timestamp = timeToSeconds(item.time);
              }
            });
            
            // Sort by timestamp to ensure correct order
            lyricsData.sort((a, b) => a.timestamp - b.timestamp);
            
            console.log(`Loaded ${lyricsData.length} synced lyrics lines`);
            console.log('First line:', lyricsData[0]);
            console.log('Last line:', lyricsData[lyricsData.length - 1]);
            
            renderLyrics();
            showLyricsMessage(`✅ ${data.message || 'Synced lyrics loaded!'}`, 'success');
            
            // Hide the fetch button since we now have lyrics
            fetchBtn.fadeOut();
            
        } else {
            throw new Error(data.message || 'No synced lyrics found');
        }
    })
    .catch(error => {
        console.error('Failed to fetch lyrics:', error);
        showLyricsMessage(`❌ ${error.message}`, 'error');
    })
    .finally(() => {
        isLyricsFetching = false;
        // Restore button state
        fetchBtn.find('i').attr('class', originalIcon);
        fetchBtn.prop('disabled', false);
    });
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
  }

  /* ===== Lyrics Display Functions ===== */
  function mountLyrics() {
    lyricsListEl = document.getElementById('lyricsList');
    lyricsContainerEl = document.getElementById('lyricsContainer');
    
    console.log('Mounting lyrics, elements found:', {
      lyricsListEl: !!lyricsListEl,
      lyricsContainerEl: !!lyricsContainerEl
    });
    
    if (!lyricsListEl) {
      console.warn('Lyrics container not found!');
      return;
    }

    // Get lyrics data from data attribute
    const lyricsAttr = lyricsListEl.getAttribute('data-lyrics');
    console.log('Raw lyrics data from HTML:', lyricsAttr);
    
    if (!lyricsAttr || lyricsAttr.trim() === '' || lyricsAttr === 'null' || lyricsAttr === '[]') {
      console.log('No lyrics data found in HTML');
      lyricsData = [];
      showLyricsMessage('No lyrics available • Click 🎵 to fetch', 'info');
    } else {
      try {
        const parsed = JSON.parse(lyricsAttr);
        if (Array.isArray(parsed) && parsed.length > 0) {
          lyricsData = parsed;
          
          // Ensure all lyrics have timestamp field
          lyricsData.forEach(item => {
            if (typeof item.timestamp === 'undefined') {
              item.timestamp = timeToSeconds(item.time);
            }
          });
          
          // Sort by timestamp
          lyricsData.sort((a, b) => a.timestamp - b.timestamp);
          
          console.log(`Loaded ${lyricsData.length} lyrics from HTML`);
          renderLyrics();
        } else {
          console.log('Empty lyrics array');
          lyricsData = [];
          showLyricsMessage('No lyrics available • Click 🎵 to fetch', 'info');
        }
      } catch (e) {
        console.error('Error parsing lyrics JSON:', e);
        lyricsData = [];
        showLyricsMessage('Lyrics format error • Click 🎵 to fetch', 'error');
      }
    }
  }

  function renderLyrics() {
    if (!lyricsListEl) return;

    if (!lyricsData || lyricsData.length === 0) {
      showLyricsMessage('No lyrics available • Click 🎵 to fetch', 'info');
      return;
    }

    console.log('Rendering lyrics...');
    
    // Clear container
    lyricsListEl.innerHTML = '';
    
    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    lyricsData.forEach((lyric, index) => {
      const lineDiv = document.createElement('div');
      lineDiv.className = 'line';
      lineDiv.dataset.index = index;
      lineDiv.dataset.time = lyric.time || '0:00';
      lineDiv.dataset.timestamp = lyric.timestamp || timeToSeconds(lyric.time);
      
      // Add timing indicator (hidden by default, for debugging)
      const timingSpan = document.createElement('span');
      timingSpan.className = 'timing-indicator';
      timingSpan.textContent = lyric.time;
      timingSpan.style.cssText = 'opacity: 0.3; font-size: 11px; margin-right: 8px; display: none; color: #666;';
      
      // Add lyrics text
      const textSpan = document.createElement('span');
      textSpan.textContent = lyric.lyrics || '';
      
      lineDiv.appendChild(timingSpan);
      lineDiv.appendChild(textSpan);
      fragment.appendChild(lineDiv);
    });
    
    lyricsListEl.appendChild(fragment);
    
    console.log(`Rendered ${lyricsData.length} lyric lines`);

    // Add click-to-seek functionality
    lyricsListEl.addEventListener('click', handleLyricClick);
  }

  function handleLyricClick(e) {
    const line = e.target.closest('.line');
    if (!line || !audioEl) return;
    
    const timestamp = parseFloat(line.dataset.timestamp);
    if (!isNaN(timestamp)) {
      console.log(`Seeking to timestamp: ${timestamp}s`);
      audioEl.currentTime = timestamp;
      
      // Visual feedback
      line.style.transform = 'scale(1.02)';
      setTimeout(() => {
        line.style.transform = '';
      }, 150);
    }
  }

  function syncLyrics(currentTime) {
    if (!lyricsData || lyricsData.length === 0 || !lyricsListEl) return;
    
    // Find the current lyric line based on precise timing
    let newIndex = -1;
    
    for (let i = 0; i < lyricsData.length; i++) {
      const lyricTime = lyricsData[i].timestamp;
      
      // Check if current time is past this lyric's time
      if (currentTime >= lyricTime) {
        newIndex = i;
      } else {
        break; // We've found the active line
      }
    }
    
    // Only update if the index actually changed
    if (newIndex !== currentLyricIndex) {
      // Remove active class from all lines
      const lines = lyricsListEl.querySelectorAll('.line');
      lines.forEach(line => line.classList.remove('active'));
      
      // Update current index
      currentLyricIndex = newIndex;
      
      // Add active class to current line
      if (currentLyricIndex >= 0) {
        const activeLine = lines[currentLyricIndex];
        if (activeLine) {
          activeLine.classList.add('active');
          
          // Auto-scroll to keep active line visible
          scrollToActiveLine(activeLine);
        }
      }
    }
  }

  function scrollToActiveLine(activeLine) {
    if (!lyricsContainerEl || !activeLine) return;
    
    const container = lyricsContainerEl;
    const containerHeight = container.clientHeight;
    const lineHeight = activeLine.offsetHeight;
    const lineTop = activeLine.offsetTop;
    
    // Calculate the ideal scroll position (center the active line)
    const idealScrollTop = lineTop - (containerHeight / 2) + (lineHeight / 2);
    
    // Smooth scroll to the calculated position
    container.scrollTo({
      top: Math.max(0, idealScrollTop),
      behavior: 'smooth'
    });
  }

  function showLyricsMessage(message, type = 'info') {
    if (!lyricsListEl) return;
    
    const iconMap = {
      'success': 'fa-check-circle',
      'error': 'fa-exclamation-triangle', 
      'loading': 'fa-spinner fa-spin',
      'info': 'fa-info-circle'
    };
    
    const colorMap = {
      'success': '#4CAF50',
      'error': '#f44336',
      'loading': '#2196F3',
      'info': '#607D8B'
    };
    
    const icon = iconMap[type] || iconMap.info;
    const color = colorMap[type] || colorMap.info;
    
    lyricsListEl.innerHTML = `
      <div class="line lyrics-message" style="
        opacity: 0.7; 
        text-align: center; 
        padding: 60px 20px; 
        color: ${color};
        font-size: 16px;
        line-height: 1.5;
      ">
        <i class="fa ${icon}" style="margin-right: 8px;"></i>
        ${message}
      </div>`;
    
    // Auto-hide success messages
    if (type === 'success') {
      setTimeout(() => {
        const msgEl = lyricsListEl.querySelector('.lyrics-message');
        if (msgEl) {
          msgEl.style.opacity = '0';
          setTimeout(() => {
            if (lyricsData && lyricsData.length > 0) {
              renderLyrics();
            }
          }, 500);
        }
      }, 2000);
    }
  }

  /* ===== Keyboard Shortcuts ===== */
  function bindKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      if (e.code === 'Space') {
        e.preventDefault();
        $('#btnPlayPause').click();
      } else if (e.key === 'ArrowRight') {
        audioEl.currentTime = Math.min(audioEl.duration || 0, audioEl.currentTime + 5);
      } else if (e.key === 'ArrowLeft') {
        audioEl.currentTime = Math.max(0, audioEl.currentTime - 5);
      } else if (e.key === 'ArrowUp') {
        audioEl.volume = Math.min(1, (audioEl.volume || 0) + 0.05);
        $('#volRange').val(audioEl.volume);
      } else if (e.key === 'ArrowDown') {
        audioEl.volume = Math.max(0, (audioEl.volume || 0) - 0.05);
        $('#volRange').val(audioEl.volume);
      } else if (e.key.toLowerCase() === 'n') {
        const next = document.querySelector('header .header-actions a[title="Next"]');
        if (next && next.getAttribute('href') && next.getAttribute('href') !== '#') {
          window.location = next.getAttribute('href');
        }
      } else if (e.key.toLowerCase() === 'p') {
        const prev = document.querySelector('header .header-actions a[title="Previous"]');
        if (prev && prev.getAttribute('href') && prev.getAttribute('href') !== '#') {
          window.location = prev.getAttribute('href');
        }
      } else if (e.ctrlKey && e.key.toLowerCase() === 'l') {
        e.preventDefault();
        $('#btnFetchLyrics').click();
      } else if (e.key.toLowerCase() === 'd') {
        // Debug: toggle timing indicators
        toggleTimingDebug();
      }
    });
  }

  /* ===== Utility Functions ===== */
  function timeToSeconds(time) {
    if (!time) return 0;
    if (typeof time === 'number') return time;
    
    const parts = time.split(':');
    if (parts.length === 3) {
      return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
    }
    if (parts.length === 2) {
      return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    }
    return parseFloat(time) || 0;
  }

  function formatTime(sec) {
    if (!isFinite(sec)) return '0:00';
    sec = Math.max(0, Math.floor(sec));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m + ':' + (s < 10 ? '0' + s : s);
  }

  // Debug function to show/hide timing indicators
  function toggleTimingDebug() {
    const timingElements = document.querySelectorAll('.timing-indicator');
    timingElements.forEach(el => {
      el.style.display = el.style.display === 'none' ? 'inline' : 'none';
    });
    console.log('Timing debug toggled');
  }

  // Public API
  return {
    init: function () {
      $(function () {
        initMediaElement();
      });
    },
    
    // Expose some functions for debugging
    debug: {
      showTimings: toggleTimingDebug,
      getLyricsData: () => lyricsData,
      getCurrentIndex: () => currentLyricIndex,
      syncLyrics: syncLyrics
    }
  };
})();

// Initialize the audio enhancer
audioEnhancer.init();

// Debug helper - type audioEnhancer.debug.showTimings() in console to see timing
console.log('Audio enhancer loaded. Debug functions available at audioEnhancer.debug');