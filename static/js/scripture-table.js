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
            new Tabulator(tableDiv, {
                data: data.verses,
                layout: "fitColumns",
                height: 400,
                virtualDom: true,
                columns: [
                    { title: "Translation", field: "Translation", width: 220, headerSort: false, resizable: false },
                    { title: "Reference", field: "Reference", width: 200, headerSort: false, resizable: false },
                    { title: "Verse", field: "Verse", widthGrow: 3, headerSort: false, resizable: false }
                ],
                placeholder: "No verses found."
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
