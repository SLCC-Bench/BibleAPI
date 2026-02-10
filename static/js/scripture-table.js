document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.getElementById('bible-translation');
    if (!dropdown) return;

    // Helper to load and display verses in the scripture-table using Tabulator with virtual DOM
    async function loadScriptureTable(translationName) {
        const tableDiv = document.getElementById('scripture-table');
        if (!tableDiv) return;
        tableDiv.innerHTML = 'Loading...';
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

            let lastClickedRowIndex = null;

            // Keyboard navigation for row selection
            tableDiv.tabIndex = 0; // Make div focusable

            tableDiv.addEventListener('keydown', function(e) {
                if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;

                const selectedRows = tabulator.getSelectedRows();
                if (!selectedRows.length) return;

                const currentRow = selectedRows[0];
                const currentData = currentRow.getData();
                const allData = tabulator.getData();
                const currentIndex = allData.findIndex(d =>
                    d.Translation === currentData.Translation &&
                    d.Reference === currentData.Reference &&
                    d.Verse === currentData.Verse
                );

                let newIndex = currentIndex;
                if (e.key === 'ArrowDown' && currentIndex < allData.length - 1) {
                    newIndex++;
                } else if (e.key === 'ArrowUp' && currentIndex > 0) {
                    newIndex--;
                } else {
                    return;
                }

                e.preventDefault();
                // Deselect old row
                tabulator.deselectRow();

                // Select new row
                const newRow = tabulator.getRows()[newIndex];
                if (newRow) {
                    newRow.select();

                    // Only scroll if not fully visible
                    const tableHolder = tableDiv.querySelector('.tabulator-tableholder');
                    if (tableHolder) {
                        const holderRect = tableHolder.getBoundingClientRect();
                        const rowElem = newRow.getElement();
                        const rowRect = rowElem.getBoundingClientRect();
                        if (rowRect.top < holderRect.top) {
                            newRow.scrollTo("top");
                        } else if (rowRect.bottom > holderRect.bottom) {
                            newRow.scrollTo("bottom");
                        }
                    }
                }
            });

            // Shift+Click range selection
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
