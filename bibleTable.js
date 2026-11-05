// Import shadcn/ui dropdown components (assume shadcn/ui is available)
// If not, user must install shadcn/ui and its dependencies
import { addBibleToSchedule } from './groupTable.js';
import { showDownloadTranslationsModal, handleDownloadTranslationsDropdown } from './downloadBibleTranslations.js';

let _notesEditorHasFocus = false;
let savedNotesSelection = null;
let savedNotesRange = null;
// Context menu logic above here...

export async function renderTranslationDropdown(containerId = 'translationSelect', onChange, selectedTranslation = null) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Replace <select> with a custom dropdown for bold abbreviation
  container.innerHTML = `
    <label for="translationSelect" class="block font-medium text-gray-700 mb-2">Select Bible Translation:</label>
    <div id="custom-translation-dropdown" style="position:relative;">
      <button class="translation-select-dropdown w-100" id="dropdownToggle" style="display:flex;align-items:center;justify-content:space-between;padding:0.5em 1em;border:1px solid #ccc;background:#fff;border-radius:6px;box-shadow:0 1px 2px #0001;min-height:40px;cursor:pointer;">
        <span id="dropdownSelected">Select translation...</span>
        <span style="margin-left:auto;transition:transform 0.2s;" id="dropdownArrow"><img src="libs/svg/arrow_drop_down.svg" alt="Arrow Down"></span>
      </button>
      <div class="dropdown-menu w-100" id="dropdownMenu"></div>
    </div>
  `;
  const dropdownToggle = container.querySelector('#dropdownToggle');
  const dropdownMenu = container.querySelector('#dropdownMenu');
  const dropdownSelected = container.querySelector('#dropdownSelected');
  const dropdownArrow = container.querySelector('#dropdownArrow');

  // Prepare translation options using new JSON format
  const installedFiles = await window.api.listFiles?.('db/bible_json') || [];
  const installedTranslationsByLang = {};
  const translationAbbrs = {};
  for (const f of installedFiles.filter(f => f.endsWith('.json'))) {
    try {
      const data = await window.api.loadJson(`db/bible_json/${f}`);
      let lang = '';
      let name = '';
      let abbr = '';
      // New format: { translation: { name, language, abbreviation, ... }, verses: [...] }
      if (data && data.translation) {
        lang = (data.translation.language || '').toUpperCase();
        name = data.translation.name || f.replace(/\.json$/, '').replace(/_/g, ' ');
        abbr = data.translation.abbreviation || '';
      } else if (Array.isArray(data) && data.length > 0) {
        // Fallback for old format
        lang = (data[0].Language || '').toUpperCase();
        name = data[0].Translation || f.replace(/\.json$/, '').replace(/_/g, ' ');
        abbr = data[0].Abbreviation || data[0].abbreviation || '';
      } else if (data && Array.isArray(data.verses) && data.verses.length > 0) {
        lang = (data.verses[0].Language || '').toUpperCase();
        name = data.verses[0].Translation || f.replace(/\.json$/, '').replace(/_/g, ' ');
        abbr = data.verses[0].Abbreviation || data.verses[0].abbreviation || '';
      } else {
        lang = '';
        name = f.replace(/\.json$/, '').replace(/_/g, ' ');
      }
      if (!installedTranslationsByLang[lang]) installedTranslationsByLang[lang] = [];
      installedTranslationsByLang[lang].push(name);
      if (abbr) translationAbbrs[name] = abbr;
    } catch {
      if (!installedTranslationsByLang['']) installedTranslationsByLang[''] = [];
      const name = f.replace(/\.json$/, '').replace(/_/g, ' ');
      installedTranslationsByLang[''].push(name);
    }
  }

  // Build dropdown menu HTML
  let menuHtml = '';
  const languageNames = {
    EN: 'English', 
    ES: 'Spanish', 
    FR: 'French', 
    DE: 'German', 
    IT: 'Italian', 
    PT: 'Portuguese', 
    RU: 'Russian', 
    ZH: 'Chinese', 
    KO: 'Korean', 
    JA: 'Japanese', 
    AR: 'Arabic', 
    HI: 'Hindi', 
    TL: 'Filipino',
    ILOKO: 'Ilokano',
    CEB: 'Cebuano',
};
  const langs = Object.keys(installedTranslationsByLang).filter(l => installedTranslationsByLang[l].length);
  if (!langs.length) {
    menuHtml = '<div class="dropdown-item text-muted" style="padding:0.7em 1em;">No translations found</div>';
  } else {
    langs.forEach(lang => {
      menuHtml += `<div class='dropdown-header dropdown-header-language' style='padding:0.5em 1em 0.2em 1em;font-weight:600;'>${languageNames[lang] || lang || 'Other'}</div>`;
      installedTranslationsByLang[lang].forEach(tr => {
        const abbr = translationAbbrs[tr];
        menuHtml += `<div class='dropdown-item' data-value="${tr}" style="cursor:pointer;transition:background 0.2s;">${tr}${abbr ? ` <b>(${abbr})</b>` : ''}</div>`;
      });
    });
  }
  menuHtml += `<div class='dropdown-divider' style='height:1px;background:#eee;margin:0.3em 0;'></div><div class='dropdown-item dropdown-item-download' data-value='__download__' style="padding:0.7em 1em;cursor:pointer;font-weight:600;">Download Bible Translations</div>`;
  dropdownMenu.innerHTML = menuHtml;

  // Dropdown toggle logic
  dropdownToggle.onclick = () => {
    const isOpen = dropdownMenu.style.display === 'none';
    dropdownMenu.style.display = isOpen ? 'block' : 'none';
    dropdownArrow.querySelector('img').src = isOpen ? 'libs/svg/arrow_drop_up.svg' : 'libs/svg/arrow_drop_down.svg';
    // Highlight selected item
    if (isOpen) {
      // Use selected translation from localStorage or argument
      let selectedValue = selectedTranslation || localStorage.getItem('selected_bible_translation');
      dropdownMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.classList.remove('selected');
        if (item.getAttribute('data-value') === selectedValue) {
          item.classList.add('selected');
        }
      });
    }
  };
  document.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      dropdownMenu.style.display = 'none';
      dropdownArrow.querySelector('img').src = 'libs/svg/arrow_drop_down.svg';
    }
  });

  // Dropdown item click logic
  dropdownMenu.querySelectorAll('.dropdown-item').forEach(item => {
    item.onmouseenter = () => { item.style.background = '#f5f5f5'; };
    item.onmouseleave = () => { item.style.background = ''; };
    item.onclick = async () => {
      const value = item.getAttribute('data-value');
      dropdownMenu.style.display = 'none';
      dropdownMenu.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('selected'));
      item.classList.add('selected');
      if (value === '__download__') {
        // Directly show the modal
        await showDownloadTranslationsModal();
        return;
      }
      dropdownSelected.innerHTML = item.innerHTML;
      await renderBibleTable(value);
      if (onChange) onChange(value);
      // Save selected translation to localStorage for persistence
      localStorage.setItem('selected_bible_translation', value);
    };
  });

  // Restore previous selection or select first available translation
  let selectedValue = selectedTranslation || localStorage.getItem('selected_bible_translation');
  let selectedItem = null;
  if (selectedValue) {
    selectedItem = dropdownMenu.querySelector(`.dropdown-item[data-value="${selectedValue}"]`);
  }
  if (!selectedItem) {
    selectedItem = dropdownMenu.querySelector('.dropdown-item[data-value]:not([data-value="__download__"])');
    selectedValue = selectedItem ? selectedItem.getAttribute('data-value') : null;
  }
  if (selectedItem) {
    dropdownSelected.innerHTML = selectedItem.innerHTML;
    // --- PATCH: Pass selectedValue to renderBibleTable for NT-only logic ---
    await renderBibleTable(selectedValue);
    if (onChange) onChange(selectedValue);
    localStorage.setItem('selected_bible_translation', selectedValue);
  }
}

// Expose a global function to re-render the dropdown and handle selection after download/update/uninstall
window.renderTranslationDropdown = async function(containerId = 'translationSelect', onChange) {
  // Get current selected translation before re-render
  const container = document.getElementById(containerId);
  let prevSelected = null;
  if (container) {
    const selectedSpan = container.querySelector('#dropdownSelected');
    if (selectedSpan) {
      // Extract translation name from innerHTML (remove abbreviation in parentheses)
      prevSelected = selectedSpan.textContent.replace(/\s*\(.+\)\s*$/, '').trim();
    }
  }
  // Re-render dropdown and try to keep selection if still available
  await renderTranslationDropdown(containerId, onChange, prevSelected);
};

// --- Global Download Translations Modal ---
let downloadTranslationsModal = null;

window.showDownloadTranslationsModal = showDownloadTranslationsModal;

function normalizeBibleData(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.verses)) return data.verses;
  return [];
}

// Helper function to detect empty verses and update references with ranges
function updateReferencesWithEmptyVerseRanges(verses) {
  if (!verses || !verses.length) return verses;
  
  const updated = [...verses];
  
  for (let i = 0; i < updated.length; i++) {
    const current = updated[i];
    if (!current || !current.Reference || !current.Verse) continue;
    
    // Parse current reference
    const currentMatch = current.Reference.match(/^(.+?)\s(\d+):(\d+)(?:-(\d+))?$/);
    if (!currentMatch) continue;
    
    const book = currentMatch[1].trim();
    const chapter = currentMatch[2];
    const verseStart = currentMatch[3];
    
    // Skip if already a range
    if (currentMatch[4]) continue;
    
    // Look ahead for consecutive empty verses
    let lastEmptyVerse = verseStart;
    let j = i + 1;
    
    while (j < updated.length) {
      const next = updated[j];
      if (!next || !next.Reference) break;
      
      const nextMatch = next.Reference.match(/^(.+?)\s(\d+):(\d+)(?:-(\d+))?$/);
      if (!nextMatch) break;
      
      const nextBook = nextMatch[1].trim();
      const nextChapter = nextMatch[2];
      const nextVerse = nextMatch[3];
      
      // Stop if book or chapter changed
      if (nextBook !== book || nextChapter !== chapter) break;
      
      // Check if this verse is empty (no Verse content or whitespace only)
      const isNextEmpty = !next.Verse || (typeof next.Verse === 'string' && !next.Verse.trim());
      
      if (isNextEmpty && Number(nextVerse) === Number(lastEmptyVerse) + 1) {
        lastEmptyVerse = nextVerse;
        j++;
      } else {
        break;
      }
    }
    
    // If we found empty verses after current verse, update the reference
    if (lastEmptyVerse !== verseStart) {
      current.Reference = `${book} ${chapter}:${verseStart}-${lastEmptyVerse}`;
    }
  }
  
  return updated;
}

export async function renderBibleTable(translation, containerId = 'table-container') {
  const container = document.getElementById(containerId);
  if (!container) return;
  const tableDiv = document.getElementById('bible-table');
  if (!tableDiv) return;
  if (!translation) {
    tableDiv.innerHTML = `<div class="text-center py-4 text-muted-foreground">No translation selected</div>`;
    return;
  }
  
  // Select the #bible-table div globally
  if (!tableDiv) {
    // console.error('No #bible-table div found in document');
    return;
  }
tableDiv.innerHTML = `
  <div class="tabulator-header"></div>
  <div class="tabulator-tableholder>
    <div class="skeleton-loader">
      <div class="skeleton-line full"></div>
      <div class="skeleton-line medium"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-line full"></div>
      <div class="skeleton-line medium"></div>
    </div>
  </div>
`;
  tableDiv.tabIndex = 0;

  // Remove previous keydown event listener if it exists
  tableDiv.replaceWith(tableDiv.cloneNode(true));
  const newTableDiv = document.getElementById('bible-table');
  
  // Show loading skeleton
  newTableDiv.innerHTML = `
    <div class="tabulator-header"></div>
    <div class="tabulator-tableholder">
      <div class="skeleton-loader">
        <div class="skeleton-line full"></div>
        <div class="skeleton-line medium"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line full"></div>
        <div class="skeleton-line medium"></div>
      </div>
    </div>
  `;

  // Wait for Tabulator to be loaded
  async function waitForTabulator() {
    while (!window.Tabulator) {
      await new Promise(r => setTimeout(r, 50));
    }
  }
  await waitForTabulator();

  // Load data from downloaded JSON file in db/bible_json only
  let verses = [];
  let data = null;
  let safeFilename = translation.replace(/[\\\/]/g, '_') + '.json';
  try {
    if (window.api.loadJson) {
      data = await window.api.loadJson(`db/bible_json/${safeFilename}`);
      verses = normalizeBibleData(data);
      if (!verses?.length) {
        console.log(`[BibleTable] No verses loaded from JSON file: db/bible_json/${safeFilename}. Raw data:`, data);
      }
    } else {
      console.log('[BibleTable] window.api.loadJson is not available');
    }
  } catch (err) {
    console.log(`[BibleTable] Error loading JSON file: db/bible_json/${safeFilename}`, err);
    verses = [];
  }

  // --- PATCH: Update references to include ranges for empty verses ---
  verses = updateReferencesWithEmptyVerseRanges(verses);

  // --- PATCH: Remove rows with empty verses ---
  verses = verses.filter(verse => verse.Verse && (typeof verse.Verse === 'string' ? verse.Verse.trim() : verse.Verse));

  window._lastLoadedBibleData = verses;
  // console.log('[DEBUG] _lastLoadedBibleData populated:', window._lastLoadedBibleData);
  if (!verses?.length) {
    newTableDiv.innerHTML = `<div class="text-center py-4 text-muted-foreground">No verses found in ${translation} translation</div>`;
    return;
  }
  newTableDiv.innerHTML = '';

  // --- PATCH: Detect NT-only translation and update bookSuggestions accordingly ---
  // List of NT books
  const NT_BOOKS = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
  ];
  // List of all books (OT+NT)
  const ALL_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", ...NT_BOOKS
  ];

  // Get unique books in loaded data
  const loadedBooks = Array.from(new Set(verses.map(v => {
    const m = v.Reference.match(/^(.+?)\s\d+:\d+$/);
    return m ? m[1].trim() : null;
  }).filter(Boolean)));

  // If all loaded books are NT books and no OT books, set NT-only mode
  const isNTOnly = loadedBooks.length > 0 &&
    loadedBooks.every(b => NT_BOOKS.includes(b)) &&
    !loadedBooks.some(b => !NT_BOOKS.includes(b));

  // Patch: update bookSuggestions for autocomplete
  window._currentBookSuggestions = isNTOnly ? NT_BOOKS : ALL_BOOKS;

  // --- PATCH: Update reference if previous is not available in NT-only ---
  const refArea = document.getElementById('referenceTextArea');
  let prevRef = window._lastSelectedReference;
  let selectRef = null;
  if (isNTOnly) {
    // If previous reference is not in NT, select Matthew 1:1
    let prevBook = null, prevChapter = null, prevVerse = null;
    if (prevRef && typeof prevRef === 'object') {
      prevBook = prevRef.book;
      prevChapter = prevRef.chapter;
      prevVerse = prevRef.verse;
    } else if (refArea) {
      prevBook = refArea.querySelector('.book-part')?.innerText.trim();
      prevChapter = refArea.querySelector('.chapter-part')?.innerText.trim();
      prevVerse = refArea.querySelector('.verse-part')?.innerText.trim();
    }
    if (!NT_BOOKS.includes(prevBook)) {
      selectRef = { book: "Matthew", chapter: "1", verse: "1" };
    } else {
      selectRef = { book: prevBook, chapter: prevChapter, verse: prevVerse };
    }
  } else {
    // Use previous reference if available, else first row
    if (refArea) {
      selectRef = {
        book: refArea.querySelector('.book-part')?.innerText.trim(),
        chapter: refArea.querySelector('.chapter-part')?.innerText.trim(),
        verse: refArea.querySelector('.verse-part')?.innerText.trim()
      };
    }
  }
  // Save for next time
  window._lastSelectedReference = selectRef;

  // Setup Tabulator
  const table = new window.Tabulator(newTableDiv, {
    height: '100%',
    layout: 'fitDataStretch',
    virtualDom: true,
    renderVertical: 'virtual', // Improved virtual rendering
    // rowHeight: 30, // Fixed row height helps performance
    dataLoader: false, // Disable built-in loader since we handle it
    progressiveLoad: 'load', // Only load visible data
    selectable: true,
    selectableRangeMode: "click", // only one row at a time
    index: 'Reference', // use Reference as the unique row index
    data: verses, // data from the downloaded JSON file
    columns: [
      { title: 'Translation', field: 'Translation', resizable:false, headerSort:false, width: 200 },
      { title: 'Reference', field: 'Reference', resizable:false, headerSort:false, width: 160 },
      { title: 'Verse', field: 'Verse', resizable:false, headerSort:false},
    ],
    rowClick: function (e, row) {
      // 1) Select the clicked row
      row.select();
      const rowData = row.getData();
      // 2) Scroll it fully into view
      table.scrollToRow(rowData.Reference, 'center');
      // 3) Refocus the tableDiv so Arrow keys still work
      tableDiv.focus();
      // 4) Dispatch selection event
      const selectedRows = table.getSelectedRows();
      const selectedData = selectedRows.map(r => r.getData());
      window.dispatchEvent(new CustomEvent('bible-rows-selected', {
        detail: { bibleData: selectedData }
      }));
      // --- PATCH: Save last selected reference ---
      const d = row.getData();
      if (d && d.Reference) {
        const m = d.Reference.match(/^(.+?)\s(\d+):(\d+)$/);
        if (m) {
          window._lastSelectedReference = { book: m[1].trim(), chapter: m[2], verse: m[3] };
        }
      }
    },
  });

  window.bibleTableInstance = table;

  table.on('renderComplete', () => {
    // console.log('[Tabulator event] renderComplete triggered');

    const refArea = document.getElementById('referenceTextArea');
    if (!refArea) {
      // console.warn('[renderComplete] No referenceTextArea found.');
      return;
    }

    const book = refArea.querySelector('.book-part')?.innerText.trim();
    const chapter = refArea.querySelector('.chapter-part')?.innerText.trim();
    const verse = refArea.querySelector('.verse-part')?.innerText.trim();
    const targetRef = `${book} ${chapter}:${verse}`;
    // console.log('[renderComplete] Target reference:', targetRef);

    const targetRow = window._lastLoadedBibleData?.find(row =>
      row.Reference.replace(/\s+/g, ' ').trim().toLowerCase() ===
      targetRef.replace(/\s+/g, ' ').trim().toLowerCase()
    );

    if (!targetRow) {
      // fallback to Matthew 1:1 for NT-only
      if (isNTOnly) {
        const mattRow = window._lastLoadedBibleData?.find(row =>
          row.Reference.replace(/\s+/g, ' ').trim().toLowerCase() ===
          'Matthew 1:1'.toLowerCase()
        );
        if (mattRow) {
          table.scrollToRow(mattRow.Reference, 'top');
          let attempts = 0;
          const MAX_ATTEMPTS = 20;
          const CHECK_INTERVAL = 50;
          function trySelect() {
            const rowComponent = table.getRow(mattRow.Reference);
            if (rowComponent) {
              rowComponent.select();
              newTableDiv.focus();
              window.dispatchEvent(new CustomEvent('bible-rows-selected', {
                detail: { bibleData: [rowComponent.getData()] }
              }));
            } else if (attempts < MAX_ATTEMPTS) {
              attempts++;
              setTimeout(trySelect, CHECK_INTERVAL);
            }
          }
          trySelect();
        }
      }
      return;
    }

    table.scrollToRow(targetRow.Reference, 'top');
    let attempts = 0;
    const MAX_ATTEMPTS = 20;
    const CHECK_INTERVAL = 50;
    function trySelect() {
      const rowComponent = table.getRow(targetRow.Reference);
      if (rowComponent) {
        rowComponent.select();
        newTableDiv.focus();
        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [rowComponent.getData()] }
        }));
      } else if (attempts < MAX_ATTEMPTS) {
        attempts++;
        setTimeout(trySelect, CHECK_INTERVAL);
      }
    }
    trySelect();
  });

  window.bibleTableInstance = table;

  // Add arrow key navigation
  newTableDiv.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const bookPart = document.querySelector('#referenceTextArea .book-part');
      if (bookPart) {
        bookPart.focus();
        // Optional: select all text inside
        setTimeout(() => {
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(bookPart);
          sel.removeAllRanges();
          sel.addRange(range);
        }, 0);
      }
    }
    
    if (e.key === 'Enter') {
      const selectedRows = table.getSelectedRows();
      const selectedData = selectedRows.map(r => r.getData());
      // console.log('[keydown Enter] selectedData:', selectedData);

      window.dispatchEvent(new CustomEvent('bible-rows-enter', {
        detail: { bibleData: selectedData }
      }));

      if (typeof window.updateLiveTextArea === 'function') {
        window.updateLiveTextArea(selectedData, null);
      } else {
        // console.warn('[keydown] updateLiveTextArea not defined');
      }
    }


    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

    const selectedRows = table.getSelectedRows();
    if (!selectedRows.length) return;

    const currentRow = selectedRows[0];
    const nextRow = (e.key === 'ArrowDown')
                    ? currentRow.getNextRow()
                    : currentRow.getPrevRow();
    if (!nextRow) return;

    e.preventDefault();
    currentRow.deselect();
    nextRow.select();

    const newId = nextRow.getData().Reference;

    // Defer expensive DOM reads to next animation frame
    requestAnimationFrame(() => {
      const rowComponent = table.getRow(newId);
      if (rowComponent) {
        const tableHolder = newTableDiv.querySelector('.tabulator-tableholder');
        if (tableHolder) {
          const holderRect = tableHolder.getBoundingClientRect();
          const rowRect = rowComponent.getElement().getBoundingClientRect();
          if (rowRect.top < holderRect.top) {
            table.scrollToRow(newId, "top");
          } else if (rowRect.bottom > holderRect.bottom) {
            table.scrollToRow(newId, "bottom");
          }
        }
      }
    });

    newTableDiv.focus();
    window.dispatchEvent(new CustomEvent('bible-rows-selected', {
      detail: { bibleData: [ nextRow.getData() ] }
    }));
  });

  // Then modify the click handler to use _lastSearchMatchedRow when available:
  newTableDiv.addEventListener('click', (e) => {
    const rowElement = e.target.closest('.tabulator-row');
    if (!rowElement) {
      table.deselectRow();
      return;
    }

    const row = table.getRow(rowElement);
    if (row) {
      const rowData = row.getData();
      const selectedRows = table.getSelectedRows();

      if (e.shiftKey) {
        // Use last search-matched row as anchor if available, otherwise first selected row
        const anchorRow = _lastSearchMatchedRow || (selectedRows.length > 0 ? selectedRows[0] : null);
        
        if (anchorRow) {
          const allRows = table.getRows();
          const anchorIndex = allRows.indexOf(anchorRow);
          const currentIndex = allRows.indexOf(row);
          
          // Determine range
          const start = Math.min(anchorIndex, currentIndex);
          const end = Math.max(anchorIndex, currentIndex);
          
          // Select all rows in range
          table.deselectRow();
          for (let i = start; i <= end; i++) {
            allRows[i].select();
          }
          
          // Dispatch event with all selected rows
          window.dispatchEvent(new CustomEvent('bible-rows-selected', {
            detail: { bibleData: table.getSelectedData() }
          }));
        }
      } else {
        // Regular click - clear search anchor and select single row
        _lastSearchMatchedRow = null;
        if (!e.ctrlKey && !e.metaKey) {
          table.deselectRow();
        }
        row.select();
        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [rowData] }
        }));
      }

      // Scroll and focus logic remains the same
      const rowTop = rowElement.offsetTop;
      const rowBottom = rowTop + rowElement.offsetHeight;
      const tableTop = newTableDiv.querySelector('.tabulator-tableholder').scrollTop;
      const tableBottom = tableTop + newTableDiv.querySelector('.tabulator-tableholder').offsetHeight;

      if (rowTop < tableTop || rowBottom > tableBottom) {
        table.scrollToRow(rowData.Reference, 'center');
      }
      newTableDiv.focus();
    }
  });

  newTableDiv.addEventListener('dblclick', (e) => {
    const rowElement = e.target.closest('.tabulator-row');
    if (!rowElement) {
      // console.warn('[dblclick] No row element found');
      return;
    }

    const row = table.getRow(rowElement);
    if (!row) {
      // console.warn('[dblclick] No Tabulator row found');
      return;
    }

    const rowData = row.getData();
    // console.log('[dblclick] Selected rowData:', rowData);

    if (typeof window.updateLiveTextArea === 'function') {
      window.updateLiveTextArea([rowData], null);
    } else {
      // console.warn('[dblclick] window.updateLiveTextArea is not defined');
    }
  });

  // Add context menu to bible-table rows
  newTableDiv.addEventListener('contextmenu', (e) => {
    const rowElement = e.target.closest('.tabulator-row');
    if (!rowElement) return;
    e.preventDefault();

    const row = table.getRow(rowElement);
    if (!row) return;

    // Retain multi-selection if right-clicked row is already selected
    const selectedRows = table.getSelectedRows();
    const isAlreadySelected = selectedRows.some(r => r === row);
    if (!isAlreadySelected) {
      table.deselectRow();
      row.select();
    }

    // Build custom context menu
    const menu = document.createElement('div');
    menu.className = 'context-menu-container absolute bg-white border rounded shadow z-50';
    menu.style.position = 'absolute';
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;

    // Begin with base menu
    let menuHTML = `
      <div class="px-4 py-2 hover:bg-gray-100 cursor-pointer whitespace-nowrap flex items-center" id="add-bible-to-schedule">
        <span class="context-menu-icons icons align-middle mr-2"><img src="libs/svg/more_time.svg" alt="Add to Schedule"></span> Add to Schedule
      </div>
    `;

    const notesModal = document.getElementById('notes-modal');
    const notesEditor = document.getElementById('notes-editor');
    if (notesEditor) {
      notesEditor.addEventListener('focusin', () => {
        _notesEditorHasFocus = true;
        // console.log('[Focus] #notes-editor got focus');
      });
      notesEditor.addEventListener('focusout', () => {
        setTimeout(() => {
          const active = document.activeElement;
          const isContextMenuOpen = document.querySelector('.context-menu-container');

          if (!notesEditor.contains(active) && !isContextMenuOpen) {
            _notesEditorHasFocus = false;
            // console.log('[Focus] #notes-editor lost focus (confirmed)');
          } else {
            // console.log('[Focus] #notes-editor blur ignored due to context menu');
          }
        }, 100); // ← slight delay is key
      });
    }

    const isNotesVisible = notesModal && !notesModal.classList.contains('hidden');
    const isNotesEditorFocused = window._notesEditorHasFocus;

    // console.log('[ContextMenu] #notes-modal exists:', !!notesModal);
    // console.log('[ContextMenu] #notes-modal is visible:', isNotesVisible);
    // console.log('[ContextMenu] #notes-editor exists:', !!notesEditor);
    // console.log('[ContextMenu] #notes-editor is focused:', isNotesEditorFocused);

    if (isNotesVisible && isNotesEditorFocused) {
      // console.log('[ContextMenu] ✅ Showing Add to Notes option');
      notesEditor.focus(); // ensure caret remains active

      menuHTML += `
        <div class="px-4 py-2 hover:bg-gray-100 cursor-pointer whitespace-nowrap flex items-center" id="add-bible-to-notes">
          <span class="context-menu-icons icons align-middle mr-2">add_notes</span> Add to Notes
        </div>
      `;
    } else {
      // console.warn('[ContextMenu] ❌ Not showing Add to Notes (conditions failed)');
    }

    menu.innerHTML = menuHTML;
    document.body.appendChild(menu);

    // Cleanup menu on next click/contextmenu
    const cleanup = () => {
      if (menu && menu.parentNode) menu.parentNode.removeChild(menu);
    };
    setTimeout(() => {
      document.addEventListener('click', cleanup, { once: true });
      document.addEventListener('contextmenu', cleanup, { once: true });
    }, 0);

    // ✅ Attach Add to Schedule handler
    const addToScheduleBtn = menu.querySelector('#add-bible-to-schedule');
    if (addToScheduleBtn) {
      addToScheduleBtn.onclick = () => {
        const selectedRows = table.getSelectedRows();
        const selectedData = selectedRows.length > 1
          ? selectedRows.map(r => r.getData())
          : selectedRows[0]?.getData();

        if (typeof addBibleToSchedule === 'function') {
          addBibleToSchedule(selectedData);
        }

        cleanup();
      };
    }

    // ✅ Attach Add to Notes handler
    const addToNotesBtn = menu.querySelector('#add-bible-to-notes');
    if (addToNotesBtn) {
      addToNotesBtn.onclick = async () => {
        const selectedRows = table.getSelectedRows();
        const selectedData = selectedRows.map(r => r.getData());
        if (!selectedData.length) return;

        const first = selectedData[0];
        const last = selectedData[selectedData.length - 1];
        const translation = first.Translation;
        const [book, ...refParts] = first.Reference.split(' ');
        const chapterVerseStart = refParts.join('');
        const chapterVerseEnd = last.Reference.split(' ').slice(1).join('');

        const [chapterStart, verseStart] = chapterVerseStart.split(':');
        const [chapterEnd, verseEnd] = chapterVerseEnd.split(':');

        // Build reference title using separated components
        let referenceTitle = '';
        if (chapterStart === chapterEnd && verseStart === verseEnd) {
          referenceTitle = `<span class="preview-book">${book}</span> <span class="preview-chapter-verse">${chapterStart}:${verseStart}</span> <span class="preview-translation">(${translation})</span>`;
        } else if (chapterStart === chapterEnd) {
          referenceTitle = `<span class="preview-book">${book}</span> <span class="preview-chapter-verse">${chapterStart}:${verseStart}–${verseEnd}</span> <span class="preview-translation">(${translation})</span>`;
        } else {
          referenceTitle = `<span class="preview-book">${book}</span> <span class="preview-chapter-verse">${chapterStart}:${verseStart}–${chapterEnd}:${verseEnd}</span> <span class="preview-translation">(${translation})</span>`;
        }

        const formattedVerses = selectedData.map(d => {
          const verseNumber = d.Reference.split(':')[1];
          return `<sup>${verseNumber}</sup> ${d.Verse}`;
        }).join('<br><br>');

        const fullInsert = `<strong>${referenceTitle}</strong><br>${formattedVerses}<br><br>`;

        const notesModal = document.getElementById('notes-modal');
        const notesEditor = document.getElementById('notes-editor');

        // ✅ Show notes-modal if it's hidden
        const isHidden = notesModal?.classList.contains('hidden');
        if (isHidden) {
          notesModal.classList.remove('hidden');
          await new Promise(resolve => setTimeout(resolve, 50)); s// wait briefly to ensure DOM is ready
        }

        // ✅ Focus editor and insert content
        if (notesEditor) {
          let savedRange = null;

          const sel = window.getSelection();
          if (sel.rangeCount > 0) {
            const range = sel.getRangeAt(0);
            if (notesEditor.contains(range.commonAncestorContainer)) {
              savedRange = range.cloneRange();
            }
          }

          notesEditor.focus();

          if (savedNotesRange) {
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(savedNotesRange);
          } else {
            // console.warn('[Caret Restore] No saved caret — will insert at end');
          }

          insertHTMLAtCaret(notesEditor, fullInsert);
          // console.log('[Insert] Content inserted at caret');
        }

        // console.log('[ContextMenu] 📥 Inserted verse into notes (with modal open)');
        cleanup();
      };
    }
    });

    function insertHTMLAtCaret(editableDiv, html) {
      const selection = window.getSelection();
      let range = null;

      if (selection.rangeCount) {
        range = selection.getRangeAt(0);
        if (!editableDiv.contains(range.commonAncestorContainer)) {
          range = null;
        }
      }

      if (!range) {
        // Move caret to end if not inside editor
        // console.log('[insertHTMLAtCaret] Inserting at end of notes-editor');
        editableDiv.focus();
        selection.removeAllRanges();
        range = document.createRange();
        range.selectNodeContents(editableDiv);
        range.collapse(false);
        selection.addRange(range);
      } else {
        // console.log('[insertHTMLAtCaret] Inserting at caret position in notes-editor');
      }

      range.deleteContents();

      // ✅ Use contextual fragment for correct order
      const fragment = range.createContextualFragment(html);
      const lastNode = fragment.lastChild;

      range.insertNode(fragment);

      // ✅ Move caret after inserted content
      if (lastNode) {
        range.setStartAfter(lastNode);
        range.setEndAfter(lastNode);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }

  // --- Live reference search from #referenceTextArea on keyup ---
  // const refArea = document.getElementById('referenceTextArea');
  let _lastSearchMatchedRow = null;

  if (refArea) {
    refArea.addEventListener('keyup', (e) => {
      // console.log(`[DEBUG] Keyup detected: ${e.key}`);
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        return;
      }

      const bookEl = refArea.querySelector('.book-part');
      const chapterEl = refArea.querySelector('.chapter-part');
      const verseEl = refArea.querySelector('.verse-part');

      if (!bookEl || !chapterEl || !verseEl) {
        // console.warn('[DEBUG] Missing one or more reference parts');
        return;
      }

      const book = bookEl.innerText.trim();
      const chapter = chapterEl.innerText.trim();
      const verse = verseEl.innerText.trim();

      if (!book || !chapter || !verse) {
        // console.log('[DEBUG] Incomplete reference:', { book, chapter, verse });
        return;
      }

      const reference = `${book} ${chapter}:${verse}`;
      // console.log(`[DEBUG] Trying to find row: "${reference}"`);

      const row = table.getRow(reference);
      if (row) {
        // Deselect all first
        table.deselectRow();
        // Scroll and select the new row
        table.scrollToRow(reference, 'top');
        row.select();
        _lastSearchMatchedRow = row;
        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [ row.getData() ] }
        }));
      } else {
        // console.warn(`[DEBUG] No row found for "${reference}"`);
      }
    });
  }


  // Arrow-key navigation: attached once (outside renderComplete)
  // Optimized arrow-key navigation for Tabulator
  tableDiv.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

    const selectedRows = table.getSelectedRows();
    if (!selectedRows.length) return;

    const currentRow = selectedRows[0];
    const nextRow = (e.key === 'ArrowDown')
                    ? currentRow.getNextRow()
                    : currentRow.getPrevRow();
    if (!nextRow) return;

    e.preventDefault();
    currentRow.deselect();
    nextRow.select();

    const newId = nextRow.getData().Reference;

    // Defer expensive DOM reads to next animation frame
    requestAnimationFrame(() => {
      const rowComponent = table.getRow(newId);
      if (rowComponent) {
        const tableHolder = tableDiv.querySelector('.tabulator-tableholder');
        if (tableHolder) {
          const holderRect = tableHolder.getBoundingClientRect();
          const rowRect = rowComponent.getElement().getBoundingClientRect();
          if (rowRect.top < holderRect.top) {
            table.scrollToRow(newId, "top");
          } else if (rowRect.bottom > holderRect.bottom) {
            table.scrollToRow(newId, "bottom");
          }
        }
      }
    });

    tableDiv.focus();
    window.dispatchEvent(new CustomEvent('bible-rows-selected', {
      detail: { bibleData: [ nextRow.getData() ] }
    }));
  });

  window._lastLoadedBibleData = verses;

  document.addEventListener('selectionchange', () => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;

    const range = sel.getRangeAt(0);
    const notesEditor = document.getElementById('notes-editor');
    if (!notesEditor || !notesEditor.contains(range.commonAncestorContainer)) return;

    savedNotesRange = range.cloneRange();
  });
}

// === Caret tracking for #notes-editor ===
function saveNotesCaret() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return;

  const range = sel.getRangeAt(0);
  const notesEditor = document.getElementById('notes-editor');
  if (notesEditor && notesEditor.contains(range.commonAncestorContainer)) {
    savedNotesRange = range.cloneRange();
    savedNotesSelection = {
      anchorNode: sel.anchorNode,
      anchorOffset: sel.anchorOffset,
      focusNode: sel.focusNode,
      focusOffset: sel.focusOffset,
    };

    console.log('[Caret Saved]', {
      anchorNode: sel.anchorNode,
      anchorOffset: sel.anchorOffset,
      focusNode: sel.focusNode,
      focusOffset: sel.focusOffset,
      range: savedNotesRange.toString(),
    });
  }
}

const notesEditor = document.getElementById('notes-editor');
if (notesEditor) {
  notesEditor.addEventListener('mouseup', saveNotesCaret);
  notesEditor.addEventListener('keyup', saveNotesCaret);
}

// Store last selected bible row for editable-part fallback
let _lastSelectedBibleRow = null;
// Store loaded bible data for chapter/verse lookup - now only stores current book
// Use window._lastLoadedBibleData globally
window._lastLoadedBibleData = null;
let _lastLoadedTranslation = null;
let _currentLoadPromise = null; // Track pending load operations

// Debounced event listener for bible row selection
window.addEventListener('bible-rows-selected', (function() {
  let debounceTimer;
  const DEBOUNCE_DELAY = 100; // ms
  
  return function(e) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const selected = e.detail?.bibleData?.[0] || null;
      _lastSelectedBibleRow = selected;
      
      const translation = selected?.Translation;
      if (!translation || translation === _lastLoadedTranslation) return;
      
      // Cancel any pending load operation
      if (_currentLoadPromise && typeof _currentLoadPromise.cancel === 'function') {
        _currentLoadPromise.cancel();
      }
      
      _lastLoadedTranslation = translation;
      // Remove _lastLoadedBibleData = null; to prevent clearing loaded data
      
      // Create a cancelable promise
      _currentLoadPromise = makeCancelable(window.api.loadBible(translation));
      _currentLoadPromise.promise
        .then(data => {
          _lastLoadedBibleData = data;
          _currentLoadPromise = null;
        })
        .catch(err => {
          if (!err.isCanceled) {
            // console.error('Error loading bible data:', err);
          }
          _currentLoadPromise = null;
        });
    }, DEBOUNCE_DELAY);
  };
})());

// Helper function to create cancelable promises
function makeCancelable(promise) {
  let hasCanceled_ = false;
  
  const wrappedPromise = new Promise((resolve, reject) => {
    promise.then(
      val => hasCanceled_ ? reject({isCanceled: true}) : resolve(val),
      error => hasCanceled_ ? reject({isCanceled: true}) : reject(error)
    );
  });

  return {
    promise: wrappedPromise,
    cancel() {
      hasCanceled_ = true;
    }
  };
}


// --- Inline autocomplete for .book-part field (contenteditable version) ---
window.setupBookPartAutocomplete = function(){
  // --- PATCH: Define NT_BOOKS and ALL_BOOKS for dynamic suggestions ---
  const NT_BOOKS = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation"
  ];
  const ALL_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", ...NT_BOOKS
  ];

  // --- PATCH: bookSuggestions will be set dynamically ---
  let bookSuggestions = ALL_BOOKS;
  let lastAcceptedSuggestion = null;
  let previousSuggestedBook = null;
  let lastSuggestedBook = null;
  let userInput = '';
  let chapterUserInput = '';
  let chapterLastAcceptedSuggestion = null;
  let chapterSuggestions = [];
  let verseUserInput = '';
  let verseLastAcceptedSuggestion = null;
  let verseSuggestions = [];

  function setCaretToEnd(el) {
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function renderSuggestion(bookSpan) {
    const normalizedInput = userInput.toLowerCase();

    if (normalizedInput === '') {
      if (lastSuggestedBook) {
        bookSpan.innerText = lastSuggestedBook;
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(bookSpan);
        sel.removeAllRanges();
        sel.addRange(range);
      } else {
        bookSpan.innerText = '';
      }
      return;
    }

    // Get all matches
    const matches = bookSuggestions.filter(s => s.toLowerCase().startsWith(normalizedInput));

    // If current lastSuggestedBook still matches, keep it
    if (
      lastSuggestedBook &&
      lastSuggestedBook.toLowerCase().startsWith(normalizedInput)
    ) {
      bookSpan.innerText = lastSuggestedBook;
      const sel = window.getSelection();
      const range = document.createRange();
      range.setStart(bookSpan.firstChild, userInput.length);
      range.setEnd(bookSpan.firstChild, lastSuggestedBook.length);
      sel.removeAllRanges();
      sel.addRange(range);
      return;
    }

    // Otherwise use the best current match
    if (matches.length > 0) {
      const suggestion = matches[0];
      lastSuggestedBook = suggestion;

      if (lastSuggestedBook !== previousSuggestedBook) {
        previousSuggestedBook = lastSuggestedBook;

        const refArea = document.getElementById('referenceTextArea');
        if (refArea) {
          const chapterParts = refArea.querySelectorAll('.chapter-part');
          const verseParts = refArea.querySelectorAll('.verse-part');
          chapterParts.forEach(el => el.innerText = '1');
          verseParts.forEach(el => el.innerText = '1');
        }
      }
      
      bookSpan.innerText = suggestion;
      const sel = window.getSelection();
      const range = document.createRange();
      range.setStart(bookSpan.firstChild, userInput.length);
      range.setEnd(bookSpan.firstChild, suggestion.length);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      // No matches
      bookSpan.innerText = userInput;
      lastSuggestedBook = null;
      setCaretToEnd(bookSpan);
    }
  }


  function renderChapterSuggestion(chapterSpan) {
    if (!chapterSuggestions.length) return;
    if (chapterUserInput === '') {
      if (chapterLastAcceptedSuggestion) {
        chapterSpan.textContent = chapterLastAcceptedSuggestion;
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(chapterSpan);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      return;
    }
    const suggestion = chapterSuggestions.find(s => s.startsWith(chapterUserInput));
    if (suggestion) {
      chapterSpan.textContent = suggestion;
      const sel = window.getSelection();
      const range = document.createRange();
      range.setStart(chapterSpan.firstChild, chapterUserInput.length);
      range.setEnd(chapterSpan.firstChild, suggestion.length);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      chapterSpan.textContent = chapterUserInput;
      setCaretToEnd(chapterSpan);
    }
  }

  function renderVerseSuggestion(verseSpan) {
    if (!verseSuggestions.length) return;
    if (verseUserInput === '') {
      if (verseLastAcceptedSuggestion) {
        verseSpan.textContent = verseLastAcceptedSuggestion;
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(verseSpan);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      return;
    }
    const suggestion = verseSuggestions.find(s => s.startsWith(verseUserInput));
    if (suggestion) {
      verseSpan.textContent = suggestion;
      const sel = window.getSelection();
      const range = document.createRange();
      range.setStart(verseSpan.firstChild, verseUserInput.length);
      range.setEnd(verseSpan.firstChild, suggestion.length);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      verseSpan.textContent = verseUserInput;
      setCaretToEnd(verseSpan);
    }
  }

  // --- PATCH: Listen for translation change and reset bookSuggestions ---
  window.addEventListener('bible-rows-selected', function() {
    // Use the current book list for the loaded translation
    if (Array.isArray(window._currentBookSuggestions)) {
      bookSuggestions = window._currentBookSuggestions;
    } else {
      bookSuggestions = ALL_BOOKS;
    }
  });

  document.addEventListener('focusin', function(e) {
    const refArea = document.getElementById('referenceTextArea');
    if (!refArea) return;
    const bookPart = e.target.closest('.book-part');
    const chapterPart = e.target.closest('.chapter-part');
    const versePart = e.target.closest('.verse-part');
    if (bookPart && refArea.contains(bookPart)) {
      // --- PATCH: Always use window._currentBookSuggestions if available ---
      if (Array.isArray(window._currentBookSuggestions)) {
        bookSuggestions = window._currentBookSuggestions;
      } else {
        bookSuggestions = ALL_BOOKS;
      }
      lastAcceptedSuggestion = bookPart.innerText.trim() || bookSuggestions[0];
      userInput = '';
    } else if (chapterPart && refArea.contains(chapterPart)) {
      // console.log('[DEBUG] focusin on chapter-part');
      // Build chapter suggestions for current book
      const bookEl = refArea.querySelector('.book-part');
      const selectedBook = bookEl ? bookEl.innerText.trim() : '';
      // console.log('[DEBUG] window._lastLoadedBibleData:', window._lastLoadedBibleData);
      // console.log('[DEBUG] selectedBook:', selectedBook);
      if (window._lastLoadedBibleData && selectedBook) {
        const chaptersSet = new Set();
        window._lastLoadedBibleData.forEach(row => {
          const match = row.Reference.match(/^(.+?)\s(\d+):(\d+)$/);
          if (match && match[1].trim() === selectedBook) {
            chaptersSet.add(match[2]);
          }
        });
        chapterSuggestions = Array.from(chaptersSet).sort((a,b)=>Number(a)-Number(b));
        // console.log('[DEBUG] chapterSuggestions:', chapterSuggestions); // <-- log chapter suggestions
      } else {
        chapterSuggestions = [];
      }
      chapterLastAcceptedSuggestion = chapterPart.innerText.trim() || (chapterSuggestions[0] || '1');
      chapterUserInput = '';
    } else if (versePart && refArea.contains(versePart)) {
      // console.log('[DEBUG] focusin on verse-part');
      // Build verse suggestions for current book/chapter
      const bookEl = refArea.querySelector('.book-part');
      const chapterEl = refArea.querySelector('.chapter-part');
      const selectedBook = bookEl ? bookEl.innerText.trim() : '';
      const selectedChapter = chapterEl ? chapterEl.innerText.trim() : '';
      // console.log('[DEBUG] window._lastLoadedBibleData:', window._lastLoadedBibleData);
      // console.log('[DEBUG] selectedBook:', selectedBook);
      // console.log('[DEBUG] selectedChapter:', selectedChapter);
      if (window._lastLoadedBibleData && selectedBook && selectedChapter) {
        const versesSet = new Set();
        window._lastLoadedBibleData.forEach(row => {
          const match = row.Reference.match(/^(.+?)\s(\d+):(\d+)$/);
          if (match && match[1].trim() === selectedBook && match[2] === selectedChapter) {
            versesSet.add(match[3]);
          }
        });
        verseSuggestions = Array.from(versesSet).sort((a,b)=>Number(a)-Number(b));
        // console.log('[DEBUG] verseSuggestions:', verseSuggestions); // <-- log verse suggestions
      } else {
        verseSuggestions = [];
      }
      verseLastAcceptedSuggestion = versePart.innerText.trim() || (verseSuggestions[0] || '1');
      verseUserInput = '';
    }
  });

  document.addEventListener('keydown', function(e) {
    const refArea = document.getElementById('referenceTextArea');
    if (!refArea) return;
    const bookPart = document.activeElement.closest('.book-part');
    const chapterPart = document.activeElement.closest('.chapter-part');
    const versePart = document.activeElement.closest('.verse-part');
    if (!(bookPart || chapterPart || versePart) || !refArea.contains(document.activeElement)) return;

    // Helper to focus next part
    function focusNext(current) {
      let next = null;
      if (current.classList.contains('book-part')) {
        next = refArea.querySelector('.chapter-part');
      } else if (current.classList.contains('chapter-part')) {
        next = refArea.querySelector('.verse-part');
      } else if (current.classList.contains('verse-part')) {
        next = refArea.querySelector('.book-part');
      }
      if (next) {
        next.focus();
        // Select all text in the next part
        requestAnimationFrame(() => {
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(next);
          sel.removeAllRanges();
          sel.addRange(range);
        });
      }
    }

    // Helper to focus previous part
    function focusPrev(current) {
      let prev = null;
      if (current.classList.contains('book-part')) {
        prev = refArea.querySelector('.verse-part');
      } else if (current.classList.contains('chapter-part')) {
        prev = refArea.querySelector('.book-part');
      } else if (current.classList.contains('verse-part')) {
        prev = refArea.querySelector('.chapter-part');
      }
      if (prev) {
        prev.focus();
        requestAnimationFrame(() => {
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(prev);
          sel.removeAllRanges();
          sel.addRange(range);
        });
      }
    }

    if (bookPart) {
      if (e.key === 'Backspace') {
        e.preventDefault();
        if (userInput.length > 0) {
          userInput = userInput.slice(0, -1);
        }
        renderSuggestion(bookPart);
        // No reset here
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // Only allow input if it matches a suggestion
        const nextInput = userInput + e.key;
        const matches = bookSuggestions.some(s => s.toLowerCase().startsWith(nextInput.toLowerCase()));
        if (!matches) {
          e.preventDefault();
          return;
        }
        e.preventDefault();
        userInput = nextInput;
        renderSuggestion(bookPart);
        // No reset here
      } else if ((e.key === 'ArrowRight' || e.key === 'Tab')) {
        e.preventDefault();
        // Reset chapter and verse to 1 if book-part changed before moving focus
        if (bookPart.innerText.trim() !== lastAcceptedSuggestion) {
          const chapterParts = refArea.querySelectorAll('.chapter-part');
          const verseParts = refArea.querySelectorAll('.verse-part');
          chapterParts.forEach(el => el.innerText = '1');
          verseParts.forEach(el => el.innerText = '1');
        }
        // --- Store and log available chapters for selected book ---
        const selectedBook = bookPart.innerText.trim();
        if (window._lastLoadedBibleData && selectedBook) {
          // Find all chapters for the selected book
          const chaptersSet = new Set();
          window._lastLoadedBibleData.forEach(row => {
            // row.Reference: e.g. 'Genesis 1:1'
            const match = row.Reference.match(/^(.+?)\s(\d+):(\d+)$/);
            if (match && match[1].trim() === selectedBook) {
              chaptersSet.add(match[2]);
           
            }
          });
          const chapters = Array.from(chaptersSet).sort((a,b)=>Number(a)-Number(b));
          // console.log('[BibleTable] Available chapters for', selectedBook, ':', chapters);
        }
        // Move to next part
        focusNext(bookPart);
      } else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
        e.preventDefault();
        const table = window.bibleTableInstance;
        if (!table || typeof table.getSelectedRows !== 'function') return;

        const selectedRows = table.getSelectedRows();
        if (!selectedRows.length) return;

        const currentRow = selectedRows[0];
        const nextRow = e.key === 'ArrowDown'
          ? currentRow.getNextRow()
          : currentRow.getPrevRow();
        if (!nextRow) return;

        table.deselectRow();
        nextRow.select();

        // Only scroll if next row is outside visible range
        const tableHolder = document.querySelector('#bible-table .tabulator-tableholder');
        const rowEl = nextRow.getElement();
        if (tableHolder && rowEl) {
          const rowRect = rowEl.getBoundingClientRect();
          const holderRect = tableHolder.getBoundingClientRect();

          const isAbove = rowRect.top < holderRect.top;
          const isBelow = rowRect.bottom > holderRect.bottom;

          if (isAbove) {
            table.scrollToRow(nextRow.getData().Reference, "top");
          } else if (isBelow) {
            table.scrollToRow(nextRow.getData().Reference, "bottom");
          }
        }

        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [nextRow.getData()] }
        }));

        return;
      } else if (e.key === 'Enter') {
        e.preventDefault();

        const table = window.bibleTableInstance;
        if (table && typeof table.getSelectedRows === 'function') {
          const selectedRows = table.getSelectedRows();
          if (selectedRows.length > 0 && typeof window.updateLiveTextArea === 'function') {
            const selectedData = selectedRows.map(r => r.getData());
            window.updateLiveTextArea(selectedData, null);
          }
        }

        return;
      } else if (e.key === 'Escape') {
        e.preventDefault();
        bookPart.blur();
      } else if ((e.key === 'ArrowLeft' || (e.key === 'Tab' && e.shiftKey))) {
        e.preventDefault();
        // Reset chapter and verse to 1 if book-part changed before moving focus
        if (bookPart.innerText.trim() !== lastAcceptedSuggestion) {
          const chapterParts = refArea.querySelectorAll('.chapter-part');
          const verseParts = refArea.querySelectorAll('.verse-part');
          chapterParts.forEach(el => el.innerText = '1');
          verseParts.forEach(el => el.innerText = '1');
        }
        // Move to previous part
        focusPrev(bookPart);
      }
    } else if (chapterPart) {
      if (e.key === 'Backspace') {
        e.preventDefault();
        if (chapterUserInput.length > 0) {
          chapterUserInput = chapterUserInput.slice(0, -1);
        }
        renderChapterSuggestion(chapterPart);
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && /[0-9]/.test(e.key)) {
        const nextInput = chapterUserInput + e.key;
        const matches = chapterSuggestions.some(s => s.startsWith(nextInput));
        if (!matches) {
          e.preventDefault();
          return;
        }
        e.preventDefault();
        chapterUserInput = nextInput;
        renderChapterSuggestion(chapterPart);
        const currentChapter = chapterPart.innerText.trim();
        if (currentChapter !== chapterLastAcceptedSuggestion) {
          chapterLastAcceptedSuggestion = currentChapter;

          const verseParts = refArea.querySelectorAll('.verse-part');
          verseParts.forEach(el => el.textContent = '1');
        }
      } else if ((e.key === 'ArrowRight' || e.key === 'Tab')) {
        e.preventDefault();
        // Accept suggestion
        const newChapter = chapterPart.textContent.trim();
        if (newChapter !== chapterLastAcceptedSuggestion) {
          chapterLastAcceptedSuggestion = newChapter;
          chapterPart.textContent = newChapter;
          // Reset verse to 1 when chapter changes
          const verseParts = refArea.querySelectorAll('.verse-part');
          verseParts.forEach(el => el.textContent = '1');
        }
        // Move to next part
        focusNext(chapterPart);
      } else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
        e.preventDefault();
        const table = window.bibleTableInstance;
        if (!table || typeof table.getSelectedRows !== 'function') return;

        const selectedRows = table.getSelectedRows();
        if (!selectedRows.length) return;

        const currentRow = selectedRows[0];
        const nextRow = e.key === 'ArrowDown'
          ? currentRow.getNextRow()
          : currentRow.getPrevRow();
        if (!nextRow) return;

        table.deselectRow();
        nextRow.select();


        // Only scroll if next row is outside visible range

        const tableHolder = document.querySelector('#bible-table .tabulator-tableholder');
               const rowEl = nextRow.getElement();
        if (tableHolder && rowEl) {
          const rowRect = rowEl.getBoundingClientRect();
          const holderRect = tableHolder.getBoundingClientRect();

          const isAbove = rowRect.top < holderRect.top;
          const isBelow = rowRect.bottom > holderRect.bottom;

          if (isAbove) {
            table.scrollToRow(nextRow.getData().Reference, "top");
          } else if (isBelow) {
            table.scrollToRow(nextRow.getData().Reference, "bottom");
          }
        }

        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [nextRow.getData()] }
        }));

        return;
      } else if (e.key === 'Enter') {
        e.preventDefault();

        const table = window.bibleTableInstance;
        if (table && typeof table.getSelectedRows === 'function') {
          const selectedRows = table.getSelectedRows();
          if (selectedRows.length > 0 && typeof window.updateLiveTextArea === 'function') {
            const selectedData = selectedRows.map(r => r.getData());
            window.updateLiveTextArea(selectedData, null);
          }
        }

        return;
      } else if (e.key === 'Escape') {
        e.preventDefault();
        chapterPart.blur();
      } else if ((e.key === 'ArrowLeft' || e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault();
        focusPrev(chapterPart);
      }
    } else if (versePart) {
      if (e.key === 'Backspace') {
        e.preventDefault();
        if (verseUserInput.length > 0) {
          verseUserInput = verseUserInput.slice(0, -1);
        }
        renderVerseSuggestion(versePart);
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && /[0-9]/.test(e.key)) {
        const nextInput = verseUserInput + e.key;
        const matches = verseSuggestions.some(s => s.startsWith(nextInput));
        if (!matches) {
          e.preventDefault();
          return;
        }
        e.preventDefault();
        verseUserInput = nextInput;
        renderVerseSuggestion(versePart);
      } else if ((e.key === 'ArrowRight' || e.key === 'Tab')) {
        e.preventDefault();
        // Accept suggestion
        if (versePart.textContent.trim() !== verseLastAcceptedSuggestion) {
          verseLastAcceptedSuggestion = versePart.textContent.trim();
          versePart.textContent = verseLastAcceptedSuggestion;
        }
        // Move to next part
        focusNext(versePart);
      } else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
        e.preventDefault();
        const table = window.bibleTableInstance;
        if (!table || typeof table.getSelectedRows !== 'function') return;

        const selectedRows = table.getSelectedRows();
        if (!selectedRows.length) return;

        const currentRow = selectedRows[0];
        const nextRow = e.key === 'ArrowDown'
          ? currentRow.getNextRow()
          : currentRow.getPrevRow();
        if (!nextRow) return;

        table.deselectRow();
        nextRow.select();

        // Only scroll if next row is outside visible range
        const tableHolder = document.querySelector('#bible-table .tabulator-tableholder');
        const rowEl = nextRow.getElement();
        if (tableHolder && rowEl) {
          const rowRect = rowEl.getBoundingClientRect();
          const holderRect = tableHolder.getBoundingClientRect();

          const isAbove = rowRect.top < holderRect.top;
          const isBelow = rowRect.bottom > holderRect.bottom;

          if (isAbove) {
            table.scrollToRow(nextRow.getData().Reference, "top");
          } else if (isBelow) {
            table.scrollToRow(nextRow.getData().Reference, "bottom");
          }
        }


        window.dispatchEvent(new CustomEvent('bible-rows-selected', {
          detail: { bibleData: [nextRow.getData()] }
        }));

        return;
      } else if (e.key === 'Enter') {
        e.preventDefault();

        const table = window.bibleTableInstance;
        if (table && typeof table.getSelectedRows === 'function') {
          const selectedRows = table.getSelectedRows();
          if (selectedRows.length > 0 && typeof window.updateLiveTextArea === 'function') {
            const selectedData = selectedRows.map(r => r.getData());
            window.updateLiveTextArea(selectedData, null);
          }
        }

        return;
      } else if (e.key === 'Escape') {
        e.preventDefault();
        versePart.blur();
      } else if ((e.key === 'ArrowLeft' || e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault();
        focusPrev(versePart);
      }
    }
  });
};

// Select all text when clicking any editable-part
// Use requestAnimationFrame for smoother selection

document.addEventListener('click', function(e) {
  const refArea = document.getElementById('referenceTextArea');
  if (!refArea) return;
  const editable = e.target.closest('.editable-part');
  if (editable && refArea.contains(editable)) {
    requestAnimationFrame(() => {
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(editable);
      sel.removeAllRanges();
      sel.addRange(range);
    });
  }
});

// Dynamically set .book-part, .chapter-part, and .verse-part to the first row in the bible-table
(function setReferencePartsFromFirstRow() {
  function setPartsFromFirstRow() {
    const refArea = document.getElementById('referenceTextArea');
    if (!refArea) return;
    const bookPart = refArea.querySelector('.book-part');
    const chapterPart = refArea.querySelector('.chapter-part');
    const versePart = refArea.querySelector('.verse-part');
    if (!bookPart || !chapterPart || !versePart) return;
    if (!window._lastLoadedBibleData || !window._lastLoadedBibleData.length) return false;
    const first = window._lastLoadedBibleData[0];
    if (!first || !first.Reference) return false;
    const match = first.Reference.match(/^(.*\D)(\d+):(\d+)$/);
    if (!match) return false;
    bookPart.textContent = match[1].trim();
    chapterPart.textContent = match[2];
    versePart.textContent = match[3];
    return true;
  }
  // Try immediately, else poll until data is loaded
  if (!setPartsFromFirstRow()) {
    const interval = setInterval(() => {
      if (setPartsFromFirstRow()) clearInterval(interval);
    }, 200);
  }
})();
