(function () {
    // Add pointer cursor to editable spans for better UX
    const style = document.createElement('style');
    style.textContent = `
        #book, #chapter, #verse {
            cursor: pointer !important;
        }
    `;
    document.head.appendChild(style);

    // Get references to the book span and translation dropdown
    const bookSpan = document.getElementById("book");
    const translationDropdown = document.getElementById("bible-translation");
    if (!bookSpan || !translationDropdown) return;

    // State variables for suggestions and user input
    let suggestions = [];
    let userInput = "";
    let lastAcceptedSuggestion = bookSpan.textContent.trim() || "Genesis";

    // Fetch book suggestions from the API based on translation
    async function fetchSuggestions() {
        let translation = translationDropdown.value;
        if (!translation) {
            // If no translation selected, default to first option
            if (translationDropdown.options.length > 0) {
                translationDropdown.value = translationDropdown.options[0].value;
                translation = translationDropdown.value;
            }
        }
        const url = `/api/book-structure/${encodeURIComponent(translation)}`;
        if (!translation) return;
        try {
            const res = await fetch(url);
            const data = await res.json();
            // --- PATCH: Always produce array of strings ---
            // Normalize API response to array of book names
            let newSuggestions = [];
            if (Array.isArray(data.books)) {
                if (typeof data.books[0] === 'object') {
                    newSuggestions = data.books.map(b => b.BookName || b.name || b.book || String(b));
                } else {
                    newSuggestions = data.books;
                }
            } else if (Array.isArray(data)) {
                if (typeof data[0] === 'object') {
                    newSuggestions = data.map(b => b.BookName || b.name || b.book || String(b));
                } else {
                    newSuggestions = data;
                }
            } else if (typeof data === 'object' && data !== null) {
                if (Array.isArray(data.bookNames)) {
                    newSuggestions = data.bookNames;
                } else if (data.books && typeof data.books === 'object') {
                    newSuggestions = Object.values(data.books).map(b => typeof b === 'object' ? (b.BookName || b.name || b.book || String(b)) : b);
                } else {
                    newSuggestions = Object.values(data).map(b => typeof b === 'object' ? (b.BookName || b.name || b.book || String(b)) : b);
                }
            } else {
                newSuggestions = [];
            }
            // Remove falsy values and ensure all are strings
            newSuggestions = newSuggestions.filter(Boolean).map(b => String(b));
            suggestions = newSuggestions;
        } catch (err) {
            suggestions = [];
        }
    }

    // Render the book span with autofill suggestion or user input
    function renderBook() {
        if (userInput === "") {
            bookSpan.textContent = lastAcceptedSuggestion;
            selectSpan(bookSpan, 0, lastAcceptedSuggestion.length);
            return;
        }
        // Find suggestion matching user input
        const suggestion = suggestions.find(s =>
            s.toLowerCase().startsWith(userInput.toLowerCase())
        );
        if (suggestion) {
            bookSpan.textContent = suggestion;
            selectSpan(bookSpan, userInput.length, suggestion.length);
        } else {
            bookSpan.textContent = userInput;
            selectSpan(bookSpan, userInput.length, userInput.length);
        }
    }

    // Select a range of text in a span for highlighting
    function selectSpan(span, start, end) {
        if (!span.firstChild) return;
        const range = document.createRange();
        range.setStart(span.firstChild, start);
        range.setEnd(span.firstChild, end);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }

    // Handle keyboard input for the book span
    bookSpan.addEventListener("keydown", function (e) {
        if (e.key === "Backspace") {
            e.preventDefault();
            userInput = userInput.slice(0, -1);
            renderBook();
        } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            // Allow typing to replace selection
            const sel = window.getSelection();
            if (sel && sel.rangeCount && sel.toString().length > 0) {
                // Replace selection with new char
                userInput = userInput.slice(0, sel.anchorOffset) + e.key;
            } else {
                userInput += e.key;
            }
            // Only allow input if it matches a suggestion
            const matches = suggestions.some(s => s.toLowerCase().startsWith(userInput.toLowerCase()));
            if (!matches) {
                e.preventDefault();
                userInput = userInput.slice(0, -1); // revert last char
                return;
            }
            e.preventDefault();
            renderBook();
        } else if (e.key === "ArrowRight" || e.key === "Tab" || e.key === "Enter") {
            // Accept suggestion and move focus if needed
            if (window.getSelection().toString().length > 0) {
                e.preventDefault();
                lastAcceptedSuggestion = bookSpan.textContent;
                userInput = bookSpan.textContent;
                selectSpan(bookSpan, userInput.length, userInput.length);
                if (e.key !== "ArrowRight") bookSpan.blur();
            }
        }
    });

    // On blur, validate book name and revert if invalid
    bookSpan.addEventListener("blur", function () {
        const currentText = bookSpan.textContent.trim();
        const found = suggestions.find(
            s => s.toLowerCase() === currentText.toLowerCase()
        );
        if (found) {
            lastAcceptedSuggestion = found;
            userInput = found;
            bookSpan.textContent = found;
        } else {
            userInput = "";
            renderBook();
        }
    });

    // When translation changes, fetch new suggestions and reset autofill
    function handleTranslationChange() {
        fetchSuggestions().then(() => {
            userInput = "";
            lastAcceptedSuggestion = suggestions[0] || "Genesis";
            renderBook();
        });
    }

    // Attach handler for both native and Select2 dropdown
    // Always attach both handlers for robustness
    translationDropdown.addEventListener("change", handleTranslationChange);
    if (window.jQuery && window.jQuery(translationDropdown).select2) {
        window.jQuery(translationDropdown).on('select2:select', handleTranslationChange);
    }

    // Wait for dropdown to be populated before fetching suggestions
    async function waitForDropdownValue() {
        let tries = 0;
        while ((!translationDropdown.value || !translationDropdown.options.length) && tries < 50) {
            await new Promise(r => setTimeout(r, 100));
            tries++;
        }
        return translationDropdown.value;
    }

    // Initial load: fetch suggestions and render autofill
    (async function () {
        await waitForDropdownValue();
        await fetchSuggestions();
        userInput = "";
        lastAcceptedSuggestion = suggestions[0] || "Genesis";
        renderBook();
        // ...
    })();

    // Highlight entire value on click/tap for book, chapter, verse spans
    document.addEventListener('click', function(e) {
        const editable = e.target;
        if (
            editable &&
            (editable.id === 'book' ||
             editable.id === 'chapter' ||
             editable.id === 'verse')
        ) {
            // Select all text in the span
            setTimeout(() => {
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(editable);
                sel.removeAllRanges();
                sel.addRange(range);
            }, 0);
        }
    });

    // Tab navigation for book, chapter, verse spans
    function focusNextEditable(current) {
        if (!current) return;
        let next = null;
        if (current.id === 'book') {
            next = document.getElementById('chapter');
        } else if (current.id === 'chapter') {
            next = document.getElementById('verse');
        } else if (current.id === 'verse') {
            next = document.getElementById('book');
        }
        if (next) {
            next.focus();
            setTimeout(() => {
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(next);
                sel.removeAllRanges();
                sel.addRange(range);
            }, 0);
        }
    }
    function focusPrevEditable(current) {
        if (!current) return;
        let prev = null;
        if (current.id === 'book') {
            prev = document.getElementById('verse');
        } else if (current.id === 'chapter') {
            prev = document.getElementById('book');
        } else if (current.id === 'verse') {
            prev = document.getElementById('chapter');
        }
        if (prev) {
            prev.focus();
            setTimeout(() => {
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(prev);
                sel.removeAllRanges();
                sel.addRange(range);
            }, 0);
        }
    }

    // Add Tab/Shift+Tab navigation to all three spans
    ['book', 'chapter', 'verse'].forEach(id => {
        const span = document.getElementById(id);
        if (!span) return;
        span.addEventListener('keydown', function(e) {
            // ...existing code for input, autofill, etc...
            if (e.key === "Tab") {
                e.preventDefault();
                if (e.shiftKey) {
                    // Reverse cycle: book -> verse -> chapter -> book
                    focusPrevEditable(span);
                } else {
                    focusNextEditable(span);
                }
            }
            // ...existing code for ArrowRight, Enter, etc...
        });
    });

})();
