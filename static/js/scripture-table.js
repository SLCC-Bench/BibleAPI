document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.getElementById('bible-translation');
    if (!dropdown) return;

    // Helper to load and display verses in the scripture-table using Tabulator with virtual DOM
    async function loadScriptureTable(translationName) {
            // Flag to suppress MutationObserver during manual row click
            let suppressReferenceObserver = false;
        // Initialize tableDiv at the top
        const tableDiv = document.getElementById('scripture-table');
        if (!tableDiv) return;
        tableDiv.innerHTML = 'Loading...';

        // Listen for changes in book, chapter, verse spans and update table selection
        function selectTableRowFromReference() {
            const bookSpan = document.getElementById('book');
            const chapterSpan = document.getElementById('chapter');
            const verseSpan = document.getElementById('verse');
            if (!bookSpan || !chapterSpan || !verseSpan) return;
            const book = bookSpan.textContent.trim();
            const chapter = chapterSpan.textContent.trim();
            const verse = verseSpan.textContent.trim();
            const ref = `${book} ${chapter}:${verse}`;
            if (!tableDiv._tabulator) return;
            const tabulator = tableDiv._tabulator;
            const allRows = tabulator.getRows();
            const allData = tabulator.getData();
            const rowIndex = allData.findIndex(d => d.Reference === ref);
            if (suppressReferenceObserver) return;
            if (rowIndex >= 0) {
                tabulator.deselectRow();
                allRows[rowIndex].select();
                // Only scroll if not triggered by mouse (i.e., only for programmatic/search navigation)
                if (!window._suppressScrollOnSelect) {
                    const tableHolder = tableDiv.querySelector('.tabulator-tableholder');
                    if (tableHolder) {
                        const holderRect = tableHolder.getBoundingClientRect();
                        const rowElem = allRows[rowIndex].getElement();
                        const rowRect = rowElem.getBoundingClientRect();
                        if (rowRect.top < holderRect.top) {
                            allRows[rowIndex].scrollTo("top");
                        } else if (rowRect.bottom > holderRect.bottom) {
                            allRows[rowIndex].scrollTo("bottom");
                        }
                    }
                }
            }
        }

        // Use MutationObserver for contenteditable spans
        function observeSpan(span) {
            if (!span) return;
            const observer = new MutationObserver(() => {
                selectTableRowFromReference();
            });
            observer.observe(span, { childList: true, characterData: true, subtree: true });
            span.addEventListener('blur', selectTableRowFromReference);
        }
        ['book', 'chapter', 'verse'].forEach(id => {
            observeSpan(document.getElementById(id));
        });
        try {
            const res = await fetch(`/api/verses/${encodeURIComponent(translationName)}`);
            if (!res.ok) {
                tableDiv.innerHTML = 'Failed to load verses.';
                return;
            }
            const data = await res.json();
            if (!data.verses || !Array.isArray(data.verses)) {
                tableDiv.innerHTML = 'No verses found.';
                return;
            }
            // Clear previous table if any
            tableDiv.innerHTML = '';
            // Destroy previous Tabulator instance if exists
            if (tableDiv._tabulator) {
                tableDiv._tabulator.destroy();
            }
            // Create Tabulator table with virtual DOM, columns not resizable
            const tabulator = new Tabulator(tableDiv, {
                data: data.verses,
                layout: "fitColumns",
                height: 300,
                virtualDom: true,
                selectable: 1, // Only one row selectable at a time
                columns: [
                    { title: "Translation", field: "Translation", width: 220, headerSort: false, resizable: false },
                    { title: "Reference", field: "Reference", width: 200, headerSort: false, resizable: false },
                    { title: "Verse", field: "Verse", widthGrow: 3, headerSort: false, resizable: false }
                ],
                placeholder: "No verses found."
            });
            tableDiv._tabulator = tabulator;

            // Helper to update reference spans
            function updateReferenceSpans(rowData) {
                if (!rowData || !rowData.Reference) return;
                // Reference format: Book Chapter:Verse
                const refMatch = rowData.Reference.match(/^([\w\s]+)\s+(\d+):(\d+)$/);
                if (refMatch) {
                    const bookSpan = document.getElementById('book');
                    const chapterSpan = document.getElementById('chapter');
                    const verseSpan = document.getElementById('verse');
                    if (bookSpan) bookSpan.textContent = refMatch[1];
                    if (chapterSpan) chapterSpan.textContent = refMatch[2];
                    if (verseSpan) verseSpan.textContent = refMatch[3];
                }
            }

            // Select and highlight the first row after table is fully built
            tabulator.on("tableBuilt", function() {
                const rows = tabulator.getRows();
                if (rows.length > 0) {
                    tabulator.deselectRow();
                    rows[0].select();
                    updateReferenceSpans(rows[0].getData());
                }
            });

            let lastClickedRowIndex = null;

            // Keyboard navigation for row selection
            tableDiv.tabIndex = 0; // Make div focusable

            tableDiv.addEventListener('keydown', function(e) {
                // No debounce: process every ArrowUp/ArrowDown event immediately for max speed

                // Handle navigation to referenceTextArea spans
                if (e.key === 'Tab' || e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    // Determine which span to focus based on direction
                    // Default: book > chapter > verse > book
                    const bookSpan = document.getElementById('book');
                    const chapterSpan = document.getElementById('chapter');
                    const verseSpan = document.getElementById('verse');
                    let target = null;
                    if ((e.key === 'Tab' && !e.shiftKey) || e.key === 'ArrowRight') {
                        // Move to book span by default
                        target = bookSpan;
                    } else if ((e.key === 'Tab' && e.shiftKey) || e.key === 'ArrowLeft') {
                        // Move to verse span by default
                        target = verseSpan;
                    }
                    if (target) {
                        target.focus();
                        setTimeout(() => {
                            const sel = window.getSelection();
                            const range = document.createRange();
                            range.selectNodeContents(target);
                            sel.removeAllRanges();
                            sel.addRange(range);
                        }, 0);
                    }
                    return;
                }

                if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

                const selectedRows = tabulator.getSelectedRows();
                if (!selectedRows.length) return;

                const currentRow = selectedRows[0];
                const nextRow = (e.key === 'ArrowDown')
                                ? currentRow.getNextRow()
                                : currentRow.getPrevRow();
                if (!nextRow || nextRow === currentRow) return;

                e.preventDefault();
                currentRow.deselect();
                nextRow.select();

                requestAnimationFrame(() => {
                    // Update reference spans to match selected row
                    const rowData = nextRow.getData();
                    if (rowData && rowData.Reference) {
                        const refMatch = rowData.Reference.match(/^([\w\s]+)\s+(\d+):(\d+)$/);
                        if (refMatch) {
                            const bookSpan = document.getElementById('book');
                            const chapterSpan = document.getElementById('chapter');
                            const verseSpan = document.getElementById('verse');
                            if (bookSpan) bookSpan.textContent = refMatch[1];
                            if (chapterSpan) chapterSpan.textContent = refMatch[2];
                            if (verseSpan) verseSpan.textContent = refMatch[3];
                        }
                    }

                    // Only scroll if not fully visible
                    const tableHolder = tableDiv.querySelector('.tabulator-tableholder');
                    if (tableHolder) {
                        const holderRect = tableHolder.getBoundingClientRect();
                        const rowElem = nextRow.getElement();
                        const rowRect = rowElem.getBoundingClientRect();
                        if (rowRect.top < holderRect.top) {
                            nextRow.scrollTo("top");
                        } else if (rowRect.bottom > holderRect.bottom) {
                            nextRow.scrollTo("bottom");
                        }
                    }

                    // Dispatch event for row selection (for UI sync)
                    window.dispatchEvent(new CustomEvent('bible-rows-selected', {
                        detail: { bibleData: [nextRow.getData()] }
                    }));
                });
            });

            // Shift+Click range selection and update reference spans
            tabulator.on("rowClick", function(e, row) {
                const allRows = tabulator.getRows();
                const allData = tabulator.getData();
                const clickedData = row.getData();
                const clickedIndex = allData.findIndex(d =>
                    d.Translation === clickedData.Translation &&
                    d.Reference === clickedData.Reference &&
                    d.Verse === clickedData.Verse
                );

                if (e.shiftKey && lastClickedRowIndex !== null) {
                    // Select range between lastClickedRowIndex and clickedIndex
                    const start = Math.min(lastClickedRowIndex, clickedIndex);
                    const end = Math.max(lastClickedRowIndex, clickedIndex);
                    tabulator.deselectRow();
                    for (let i = start; i <= end; i++) {
                        allRows[i].select();
                    }
                } else {
                    // Single click: select only the clicked row
                    tabulator.deselectRow();
                    row.select();
                    lastClickedRowIndex = clickedIndex;
                }
                // Suppress scrollTo('top') for mouse selection
                window._suppressScrollOnSelect = true;
                suppressReferenceObserver = true;
                updateReferenceSpans(clickedData);
                setTimeout(() => {
                    suppressReferenceObserver = false;
                    window._suppressScrollOnSelect = false;
                }, 0);
                // Do NOT scroll to top on row click
            });
        } catch (e) {
            tableDiv.innerHTML = 'Error loading verses.';
        }
    }

    // Listen for changes on the dropdown (works for both native and Select2)
    if (window.jQuery && $(dropdown).select2) {
        $(dropdown).on('change', function () {
            const selected = this.value;
            if (selected) {
                loadScriptureTable(selected);
            }
        });
    } else {
        dropdown.addEventListener('change', function () {
            const selected = dropdown.value;
            if (selected) {
                loadScriptureTable(selected);
            }
        });
    }

    // Load the table for the initial selection after translations are loaded
    // Wait for translations to be loaded by bible-translation-dropdown.js
    function tryInitialLoad() {
        if (dropdown.options.length > 0 && dropdown.value) {
            loadScriptureTable(dropdown.value);
        } else {
            setTimeout(tryInitialLoad, 100);
        }
    }
    tryInitialLoad();
});
