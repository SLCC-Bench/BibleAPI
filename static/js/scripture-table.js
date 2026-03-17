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
            if (!tableDiv._tabulator) return;
            const tabulator = tableDiv._tabulator;
            const allRows = tabulator.getRows();
            const allData = tabulator.getData();

            // --- Begin: Canonical to API book name mapping ---
            // Find the SortingNumber for the canonical (UI) book name
            let sortingNumber = null;
            if (window.GENERIC_BOOKS_SORTING) {
                const genericBook = window.GENERIC_BOOKS_SORTING.find(b => b.name.toLowerCase() === book.toLowerCase());
                if (genericBook) sortingNumber = genericBook.sortingNumber;
            }
            // Find the API book name for this SortingNumber (from window.lastApiBooks)
            let apiBookName = book;
            if (window.lastApiBooks && sortingNumber != null) {
                const apiBook = window.lastApiBooks.find(b => b.SortingNumber === sortingNumber);
                if (apiBook && apiBook.BookName) apiBookName = apiBook.BookName;
            }
            // Compose the reference string as it appears in the API data
            const ref = `${apiBookName} ${chapter}:${verse}`;
            // --- End: Canonical to API book name mapping ---

            if (suppressReferenceObserver) return;
            const rowIndex = allData.findIndex(d => d.Reference === ref);
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
                    const apiBookName = refMatch[1];
                    const chapter = refMatch[2];
                    const verse = refMatch[3];
                    let genericBookName = apiBookName;
                    // Try to map API book name to canonical GENERIC_BOOKS_SORTING name using SortingNumber
                    if (window.lastApiBooks && window.GENERIC_BOOKS_SORTING) {
                        const apiBook = window.lastApiBooks.find(b => (b.BookName || b.name || b.book) === apiBookName);
                        if (apiBook && apiBook.SortingNumber) {
                            const genericBook = window.GENERIC_BOOKS_SORTING.find(gb => gb.sortingNumber === apiBook.SortingNumber);
                            if (genericBook) genericBookName = genericBook.name;
                        }
                    }
                    const bookSpan = document.getElementById('book');
                    const chapterSpan = document.getElementById('chapter');
                    const verseSpan = document.getElementById('verse');
                    if (bookSpan) bookSpan.textContent = genericBookName;
                    if (chapterSpan) chapterSpan.textContent = chapter;
                    if (verseSpan) verseSpan.textContent = verse;
                }
            }

            // Select and highlight the first row after table is fully built
            tabulator.on("tableBuilt", function() {
                const rows = tabulator.getRows();
                const bookSpan = document.getElementById('book');
                const chapterSpan = document.getElementById('chapter');
                const verseSpan = document.getElementById('verse');
                const bookValue = bookSpan ? bookSpan.textContent.trim() : "";
                const chapterValue = chapterSpan ? chapterSpan.textContent.trim() : "";
                const verseValue = verseSpan ? verseSpan.textContent.trim() : "";
                // Map canonical book name to API book name
                let sortingNumber = null;
                if (window.GENERIC_BOOKS_SORTING) {
                    const genericBook = window.GENERIC_BOOKS_SORTING.find(b => b.name.toLowerCase() === bookValue.toLowerCase());
                    if (genericBook) sortingNumber = genericBook.sortingNumber;
                }
                let apiBookName = bookValue;
                if (window.lastApiBooks && sortingNumber != null) {
                    const apiBook = window.lastApiBooks.find(b => b.SortingNumber === sortingNumber);
                    if (apiBook && apiBook.BookName) apiBookName = apiBook.BookName;
                }
                const ref = `${apiBookName} ${chapterValue}:${verseValue}`;
                // Find the row index for the current reference
                const allData = tabulator.getData();
                const rowIndex = allData.findIndex(d => d.Reference === ref);
                if (rows.length > 0) {
                    tabulator.deselectRow();
                    // Focus the table before selecting the row
                    tabulator.element.focus();
                    if (rowIndex >= 0) {
                        rows[rowIndex].select();
                        // Scroll the selected row to the top of the table
                        const tableHolder = tabulator.element.querySelector('.tabulator-tableholder');
                        if (tableHolder) {
                            const rowElem = rows[rowIndex].getElement();
                            if (rowElem) {
                                // Calculate offset to scroll row to top
                                const holderRect = tableHolder.getBoundingClientRect();
                                const rowRect = rowElem.getBoundingClientRect();
                                const scrollTop = tableHolder.scrollTop + (rowRect.top - holderRect.top);
                                tableHolder.scrollTop = scrollTop;
                            }
                        }
                    }
                }
            });

            let lastClickedRowIndex = null;

            // Keyboard navigation for row selection
            tableDiv.tabIndex = 0; // Make div focusable

            tableDiv.addEventListener('keydown', function(e) {
                // ...existing code...
                // Handle navigation to referenceTextArea spans
                if (e.key === 'Tab' || e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const bookSpan = document.getElementById('book');
                    const verseSpan = document.getElementById('verse');
                    let target = null;
                    if ((e.key === 'Tab' && !e.shiftKey) || e.key === 'ArrowRight') {
                        target = bookSpan;
                    } else if ((e.key === 'Tab' && e.shiftKey) || e.key === 'ArrowLeft') {
                        target = verseSpan;
                    }
                    if (target) {
                        target.focus();
                        const sel = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(target);
                        sel.removeAllRanges();
                        sel.addRange(range);
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

                // Update reference spans to match selected row (use canonical book name)
                updateReferenceSpans(nextRow.getData());

                // Only scroll if not fully visible
                const tableHolder = tableDiv.querySelector('.tabulator-tableholder');
                if (tableHolder) {
                    const holderRect = tableHolder.getBoundingClientRect();
                    const rowElem = nextRow.getElement();
                    const rowRect = rowElem.getBoundingClientRect();
                    if (rowRect.top < holderRect.top || rowRect.bottom > holderRect.bottom) {
                        rowElem.scrollIntoView({ block: 'nearest', behavior: 'auto' });
                    }
                }

                // Dispatch event for row selection (for UI sync)
                window.dispatchEvent(new CustomEvent('bible-rows-selected', {
                    detail: { bibleData: [nextRow.getData()] }
                }));
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
                suppressReferenceObserver = false;
                window._suppressScrollOnSelect = false;
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
