(function () {
    // ── State ────────────────────────────────────────────────────────────
    let allSongs = [];
    let editingSongId = null;   // null = new song
    let songSections = [];      // [{ songPart, lyrics }]
    let activeSectionIndex = 0;
    let songBgImageDataUrl = null;

    const SECTION_COLORS = {
        verse:      { bg: 'bg-blue-600',   text: 'text-white' },
        chorus:     { bg: 'bg-green-600',  text: 'text-white' },
        bridge:     { bg: 'bg-purple-600', text: 'text-white' },
        adlib:      { bg: 'bg-pink-600',   text: 'text-white' },
        intro:      { bg: 'bg-teal-600',   text: 'text-white' },
        outro:      { bg: 'bg-gray-600',   text: 'text-white' },
        prechorus:  { bg: 'bg-indigo-600', text: 'text-white' },
        tag:        { bg: 'bg-amber-500',  text: 'text-white' },
    };

    function sectionColor(part) {
        const key = (part || '').toLowerCase().replace(/\s+/g, '').replace(/\d+$/, '');
        return SECTION_COLORS[key] || { bg: 'bg-gray-500', text: 'text-white' };
    }

    // ── Fetch & render song list ─────────────────────────────────────────
    async function fetchSongs() {
        try {
            const res = await fetch('/api/songs');
            const data = await res.json();
            allSongs = data.songs || [];
            renderSongTable(allSongs);
        } catch (e) {
            console.error('Failed to fetch songs:', e);
        }
    }
    window.fetchSongs = fetchSongs;

    function renderSongTable(songs) {
        const tbody = document.getElementById('songsTbody');
        if (!tbody) return;
        const q = (document.getElementById('songSearch')?.value || '').toLowerCase();
        const filtered = songs.filter(s =>
            (s.title || '').toLowerCase().includes(q) ||
            (s.artist || '').toLowerCase().includes(q) ||
            (s.album || '').toLowerCase().includes(q)
        );
        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-8 text-gray-400">No songs found.</td></tr>';
            return;
        }
        tbody.innerHTML = filtered.map(s => `
            <tr class="border-b hover:bg-orange-50 transition">
                <td class="px-4 py-2 font-semibold">${esc(s.title)}</td>
                <td class="px-4 py-2 text-gray-600">${esc(s.artist)}</td>
                <td class="px-4 py-2 text-gray-600">${esc(s.album)}</td>
                <td class="px-4 py-2 text-gray-600">${esc(s.genre)}</td>
                <td class="px-4 py-2 flex gap-2">
                    <button onclick="openSongEditor(${s.id})" class="bg-orange-500 text-white px-3 py-1 rounded text-xs hover:bg-orange-600 transition font-semibold">Edit</button>
                    <button onclick="confirmDeleteSong(${s.id}, '${esc(s.title)}')" class="bg-red-100 text-red-700 px-3 py-1 rounded text-xs hover:bg-red-200 transition font-semibold">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    function esc(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // ── Search filter ────────────────────────────────────────────────────
    document.getElementById('songSearch')?.addEventListener('input', () => renderSongTable(allSongs));

    // ── Open editor ──────────────────────────────────────────────────────
    window.openSongEditor = async function (songId) {
        editingSongId = songId || null;
        songSections = [];
        songBgImageDataUrl = null;
        activeSectionIndex = 0;

        resetEditorDefaults();

        if (songId) {
            try {
                const res = await fetch(`/api/songs/${songId}`);
                const data = await res.json();
                document.getElementById('songEditorTitle').value = data.song.title || '';
                document.getElementById('songEditorArtist').value = data.song.artist || '';
                document.getElementById('songEditorAlbum').value = data.song.album || '';

                songSections = (data.lyrics || []).map(l => ({ songPart: l.songPart, lyrics: l.lyrics }));

                if (data.settings) {
                    const s = data.settings;
                    if (s.fontSize) document.getElementById('songFontSize').value = s.fontSize;
                    if (s.color) document.getElementById('songTextColor').value = s.color;
                    if (s.family) document.getElementById('songFontFamily').value = s.family;
                    if (s.bgType) {
                        const radio = document.querySelector(`input[name="songBgType"][value="${s.bgType}"]`);
                        if (radio) { radio.checked = true; updateSongBg(); }
                    }
                    if (s.bgImage) { songBgImageDataUrl = s.bgImage; applyBgToPreview(); }
                }
            } catch (e) {
                console.error('Failed to load song:', e);
            }
        } else {
            document.getElementById('songEditorTitle').value = '';
            document.getElementById('songEditorArtist').value = '';
            document.getElementById('songEditorAlbum').value = '';
            songSections = [{ songPart: '', lyrics: '' }];
        }

        renderSectionsList();
        updateSongPreview();
        document.getElementById('songEditorModal').style.display = 'flex';
    };

    function resetEditorDefaults() {
        document.getElementById('songFontSize').value = 80;
        document.getElementById('songTextColor').value = '#ffffff';
        document.getElementById('songFontFamily').value = 'Lexend Deca';
        document.getElementById('songShadowBlur').value = 5;
        document.getElementById('songShadowX').value = 5;
        document.getElementById('songShadowY').value = 5;
        document.getElementById('songStrokeWidth').value = 1;
        document.getElementById('songLineHeight').value = 1.2;
        document.getElementById('songLetterSpacing').value = 0;
        document.getElementById('songWordSpacing').value = 0;
        const blackRadio = document.querySelector('input[name="songBgType"][value="black"]');
        if (blackRadio) { blackRadio.checked = true; updateSongBg(); }
    }

    // ── Add section ──────────────────────────────────────────────────────
    document.getElementById('addSectionBtn')?.addEventListener('click', () => {
        songSections.push({ songPart: '', lyrics: '' });
        activeSectionIndex = songSections.length - 1;
        renderSectionsList();
        updateSongPreview();
    });

    // ── Render sections list ─────────────────────────────────────────────
    function renderSectionsList() {
        const container = document.getElementById('songSectionsList');
        if (!container) return;
        container.innerHTML = '';

        // Build groups: a new group starts whenever songPart is non-empty
        // If the very first section has no name, treat it as its own group
        const groups = []; // [{headerIdx, indices:[]}]
        songSections.forEach((sec, i) => {
            if (sec.songPart.trim() !== '' || groups.length === 0) {
                groups.push({ headerIdx: i, indices: [i] });
            } else {
                groups[groups.length - 1].indices.push(i);
            }
        });

        groups.forEach((group) => {
            const headerIdx = group.headerIdx;
            const headerSec = songSections[headerIdx];
            const col = sectionColor(headerSec.songPart);
            const groupActive = group.indices.includes(activeSectionIndex);

            const card = document.createElement('div');
            card.className = `rounded-xl border bg-white shadow-sm overflow-hidden mb-1 ${groupActive ? 'border-blue-300' : 'border-gray-200'}`;

            // Colored left border for active group
            card.style.borderLeft = groupActive
                ? '3px solid #3b82f6'
                : `3px solid ${getGroupColor(headerSec.songPart)}`;

            // Header row (section name input + ×)
            const header = document.createElement('div');
            header.className = `flex items-center px-3 py-2 gap-2 border-b border-gray-100 ${col.bg} bg-opacity-10`;
            header.innerHTML = `
                <input type="text"
                    class="flex-1 text-xs font-bold uppercase tracking-widest bg-transparent focus:outline-none placeholder-gray-400 text-gray-700"
                    placeholder="Section name (e.g. Verse, Chorus)"
                    value="${esc(headerSec.songPart)}"
                    data-part-idx="${headerIdx}">
                <button class="text-gray-400 hover:text-red-500 text-base font-bold leading-none" onclick="removeSection(${headerIdx})" title="Remove">×</button>
            `;
            header.querySelector('input').addEventListener('change', (e) => {
                songSections[headerIdx].songPart = e.target.value;
                renderSectionsList();
            });
            card.appendChild(header);

            // Each section in the group
            group.indices.forEach((i, pos) => {
                const sec = songSections[i];
                const isActive = i === activeSectionIndex;

                // For non-header sections (pos > 0), show a divider with their section name input
                if (pos > 0) {
                    const divider = document.createElement('div');
                    divider.className = 'flex items-center px-3 py-1.5 gap-2 border-t border-b border-gray-100 bg-gray-50';
                    divider.innerHTML = `
                        <input type="text"
                            class="flex-1 text-xs text-gray-400 placeholder-gray-300 bg-transparent focus:outline-none"
                            placeholder="Section name (e.g. Verse, Chorus)"
                            value="${esc(sec.songPart)}"
                            data-part-idx="${i}">
                        <button class="text-gray-400 hover:text-red-500 text-sm font-bold leading-none" onclick="removeSection(${i})" title="Remove">×</button>
                    `;
                    divider.querySelector('input').addEventListener('change', (e) => {
                        songSections[i].songPart = e.target.value;
                        renderSectionsList();
                    });
                    card.appendChild(divider);
                }

                // Lyrics textarea
                const ta = document.createElement('textarea');
                ta.rows = 3;
                ta.className = `w-full text-sm px-3 py-2 focus:outline-none resize-none bg-white placeholder-gray-300 ${isActive ? 'bg-blue-50' : ''}`;
                ta.placeholder = 'Enter lyrics...';
                ta.value = sec.lyrics;

                ta.addEventListener('focus', () => {
                    activeSectionIndex = i;
                    updateSongPreview();
                    // Highlight active card border without full re-render
                    container.querySelectorAll(':scope > div').forEach(el => {
                        el.style.borderLeft = `3px solid ${getGroupColor(songSections[el._headerIdx]?.songPart || '')}`;
                        el.classList.remove('border-blue-300');
                    });
                    card.style.borderLeft = '3px solid #3b82f6';
                    card._headerIdx = headerIdx;
                });

                ta.addEventListener('input', (e) => {
                    songSections[i].lyrics = e.target.value;
                    if (i === activeSectionIndex) updateSongPreview();
                });

                ta.addEventListener('keydown', (e) => {
                    // Backspace on empty → delete section
                    if (e.key === 'Backspace' && ta.value === '' && songSections.length > 1) {
                        e.preventDefault();
                        songSections.splice(i, 1);
                        activeSectionIndex = Math.max(0, i - 1);
                        renderSectionsList();
                        updateSongPreview();
                        focusSectionTextarea(activeSectionIndex, true);
                        return;
                    }
                    // Enter at end → add new section
                    if (e.key === 'Enter' && ta.selectionStart === ta.value.length) {
                        e.preventDefault();
                        songSections.splice(i + 1, 0, { songPart: '', lyrics: '' });
                        activeSectionIndex = i + 1;
                        renderSectionsList();
                        updateSongPreview();
                        focusSectionTextarea(activeSectionIndex, false);
                    }
                });

                card._headerIdx = headerIdx;
                card.appendChild(ta);
            });

            container.appendChild(card);
        });
    }

    function focusSectionTextarea(sectionIdx, atEnd) {
        // Find textarea matching sectionIdx by scanning rendered textareas in order
        const allTa = document.querySelectorAll('#songSectionsList textarea');
        // Map by order of songSections
        const order = [];
        const groups2 = [];
        songSections.forEach((sec, i) => {
            if (sec.songPart.trim() !== '' || groups2.length === 0) groups2.push({ headerIdx: i, indices: [i] });
            else groups2[groups2.length - 1].indices.push(i);
        });
        groups2.forEach(g => g.indices.forEach(i => order.push(i)));
        const pos = order.indexOf(sectionIdx);
        if (pos >= 0 && allTa[pos]) {
            const ta = allTa[pos];
            ta.focus();
            if (atEnd) ta.setSelectionRange(ta.value.length, ta.value.length);
        }
    }

    function getGroupColor(songPart) {
        const key = (songPart || '').toLowerCase().replace(/\s+/g, '').replace(/\d+$/, '');
        const colorMap = {
            verse:     '#3b82f6',
            chorus:    '#22c55e',
            bridge:    '#a855f7',
            adlib:     '#ec4899',
            intro:     '#14b8a6',
            outro:     '#6b7280',
            prechorus: '#6366f1',
            tag:       '#f59e0b',
        };
        return colorMap[key] || '#9ca3af';
    }

    window.moveSectionUp = function (i) {
        if (i === 0) return;
        [songSections[i - 1], songSections[i]] = [songSections[i], songSections[i - 1]];
        activeSectionIndex = i - 1;
        renderSectionsList();
    };

    window.moveSectionDown = function (i) {
        if (i >= songSections.length - 1) return;
        [songSections[i], songSections[i + 1]] = [songSections[i + 1], songSections[i]];
        activeSectionIndex = i + 1;
        renderSectionsList();
    };

    window.removeSection = function (i) {
        songSections.splice(i, 1);
        activeSectionIndex = Math.max(0, Math.min(activeSectionIndex, songSections.length - 1));
        renderSectionsList();
        updateSongPreview();
    };

    // ── Preview ──────────────────────────────────────────────────────────
    window.updateSongPreview = function () {
        const previewText = document.getElementById('songPreviewText');
        const previewArea = document.getElementById('songPreviewArea');
        if (!previewText || !previewArea) return;

        const sec = songSections[activeSectionIndex];
        const text = sec ? sec.lyrics || sec.songPart : 'Song Preview';
        const fontFamily = document.getElementById('songFontFamily').value;
        const fontSize = parseInt(document.getElementById('songFontSize').value) || 80;
        const color = document.getElementById('songTextColor').value;
        const blur = document.getElementById('songShadowBlur').value;
        const sx = document.getElementById('songShadowX').value;
        const sy = document.getElementById('songShadowY').value;
        const lineHeight = document.getElementById('songLineHeight').value;
        const letterSpacing = document.getElementById('songLetterSpacing').value;
        const wordSpacing = document.getElementById('songWordSpacing').value;

        previewText.textContent = text;
        previewText.style.fontFamily = `'${fontFamily}', sans-serif`;
        // Scale font size relative to preview container width (design base: 1920px)
        const containerW = previewArea.offsetWidth || 640;
        const scale = containerW / 1920;
        previewText.style.fontSize = (fontSize * scale) + 'px';
        previewText.style.color = color;
        previewText.style.lineHeight = lineHeight;
        previewText.style.letterSpacing = letterSpacing + 'px';
        previewText.style.wordSpacing = wordSpacing + 'px';
        previewText.style.textShadow = `${sx}px ${sy}px ${blur}px rgba(0,0,0,0.8)`;
    };

    window.setSongAlign = function (align) {
        const previewText = document.getElementById('songPreviewText');
        if (previewText) previewText.style.textAlign = align;
    };

    window.songApplyStyle = function (style) {
        // Toggle bold/italic/underline on previewText (visual only; stored in formattingJson)
        const el = document.getElementById('songPreviewText');
        if (!el) return;
        if (style === 'bold') el.style.fontWeight = el.style.fontWeight === 'bold' ? 'normal' : 'bold';
        if (style === 'italic') el.style.fontStyle = el.style.fontStyle === 'italic' ? 'normal' : 'italic';
        if (style === 'underline') el.style.textDecoration = el.style.textDecoration === 'underline' ? 'none' : 'underline';
    };

    window.updateSongBg = function () {
        const bgType = document.querySelector('input[name="songBgType"]:checked')?.value || 'black';
        const uploadArea = document.getElementById('bgImageUploadArea');
        const previewArea = document.getElementById('songPreviewArea');
        if (!previewArea) return;

        if (bgType === 'black') {
            previewArea.style.background = '#000';
            previewArea.style.backgroundImage = 'none';
            if (uploadArea) uploadArea.style.display = 'none';
        } else if (bgType === 'image') {
            if (uploadArea) uploadArea.style.display = 'block';
            applyBgToPreview();
        } else {
            previewArea.style.background = '#111';
            previewArea.style.backgroundImage = 'none';
            if (uploadArea) uploadArea.style.display = 'none';
        }
    };

    window.handleSongBgImage = function (input) {
        const file = input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            songBgImageDataUrl = e.target.result;
            applyBgToPreview();
            const thumb = document.getElementById('bgImagePreviewThumb');
            if (thumb) thumb.innerHTML = `<img src="${songBgImageDataUrl}" class="w-full rounded mt-1 max-h-20 object-cover">`;
        };
        reader.readAsDataURL(file);
    };

    function applyBgToPreview() {
        const previewArea = document.getElementById('songPreviewArea');
        if (!previewArea || !songBgImageDataUrl) return;
        previewArea.style.backgroundImage = `url('${songBgImageDataUrl}')`;
        previewArea.style.backgroundSize = 'cover';
        previewArea.style.backgroundPosition = 'center';
    }

    // ── Save song ────────────────────────────────────────────────────────
    async function saveSong() {
        const title = document.getElementById('songEditorTitle').value.trim();
        if (!title) { alert('Song title is required.'); return false; }

        const payload = {
            title,
            artist: document.getElementById('songEditorArtist').value.trim(),
            album: document.getElementById('songEditorAlbum').value.trim(),
            genre: '',
            lyrics: songSections.map(s => ({ songPart: s.songPart, lyrics: s.lyrics })),
            settings: {
                fontSize: document.getElementById('songFontSize').value,
                color: document.getElementById('songTextColor').value,
                family: document.getElementById('songFontFamily').value,
                bgType: document.querySelector('input[name="songBgType"]:checked')?.value || 'black',
                bgImage: songBgImageDataUrl || null,
                formattingJson: JSON.stringify({
                    shadowBlur: document.getElementById('songShadowBlur').value,
                    shadowX: document.getElementById('songShadowX').value,
                    shadowY: document.getElementById('songShadowY').value,
                    strokeWidth: document.getElementById('songStrokeWidth').value,
                    lineHeight: document.getElementById('songLineHeight').value,
                    letterSpacing: document.getElementById('songLetterSpacing').value,
                    wordSpacing: document.getElementById('songWordSpacing').value,
                })
            }
        };

        const url = editingSongId ? `/api/songs/${editingSongId}` : '/api/songs';
        const method = editingSongId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        return data.success;
    }

    // ── Editor buttons ───────────────────────────────────────────────────
    document.getElementById('songEditorOk')?.addEventListener('click', async () => {
        const ok = await saveSong();
        if (ok) {
            document.getElementById('songEditorModal').style.display = 'none';
            fetchSongs();
        }
    });

    document.getElementById('songEditorApply')?.addEventListener('click', async () => {
        await saveSong();
        fetchSongs();
    });

    document.getElementById('songEditorCancel')?.addEventListener('click', () => {
        document.getElementById('songEditorModal').style.display = 'none';
    });

    // ── Add song button ──────────────────────────────────────────────────
    document.getElementById('addSongBtn')?.addEventListener('click', () => {
        openSongEditor(null);
    });

    // ── Delete song ──────────────────────────────────────────────────────
    let deleteSongId = null;

    window.confirmDeleteSong = function (id, name) {
        deleteSongId = id;
        document.getElementById('deleteSongName').textContent = name;
        document.getElementById('deleteSongModal').style.display = 'flex';
    };

    document.getElementById('confirmDeleteSong')?.addEventListener('click', async () => {
        if (!deleteSongId) return;
        await fetch(`/api/songs/${deleteSongId}`, { method: 'DELETE' });
        document.getElementById('deleteSongModal').style.display = 'none';
        deleteSongId = null;
        fetchSongs();
    });

    document.getElementById('cancelDeleteSong')?.addEventListener('click', () => {
        document.getElementById('deleteSongModal').style.display = 'none';
        deleteSongId = null;
    });

    // Recalculate preview font size when window resizes
    window.addEventListener('resize', updateSongPreview);
})();
