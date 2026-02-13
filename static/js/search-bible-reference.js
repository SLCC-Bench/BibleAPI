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
    let bookSuggestions = [];
    let bookUserInput = "";
    let lastAcceptedBookSuggestion = bookSpan.textContent.trim() || "Genesis";

    let chapterSuggestions = [];
    let chapterUserInput = "";
    let lastAcceptedChapterSuggestion = document.getElementById("chapter").textContent.trim() || "1";

    const verseSpan = document.getElementById("verse");
    let verseSuggestions = [];
    let verseUserInput = verseSpan.textContent.trim() || "1";
    let lastAcceptedVerseSuggestion = verseSpan.textContent.trim() || "1";

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
            window.lastApiBooks = Array.isArray(data.books) ? data.books : [];
            // --- PATCH: Always produce array of strings ---
            // Normalize API response to array of book names
            let newBookSuggestions = [];
            let newChapterSuggestions = [];
            if (Array.isArray(data.books)) {
                if (typeof data.books[0] === 'object') {
                    newBookSuggestions = data.books.map(b => b.BookName || b.name || b.book || String(b));
                    // Find selected book for chapter suggestions
                    const selectedBook = bookSpan.textContent.trim() || newBookSuggestions[0];
                    const bookObj = data.books.find(b => (b.BookName || b.name || b.book || String(b)) === selectedBook);
                    if (bookObj && bookObj.chapters) {
                        newChapterSuggestions = Object.keys(bookObj.chapters).map(ch => String(ch));
                    }
                } else {
                    newBookSuggestions = data.books;
                }
            } else if (Array.isArray(data)) {
                if (typeof data[0] === 'object') {
                    newBookSuggestions = data.map(b => b.BookName || b.name || b.book || String(b));
                } else {
                    newBookSuggestions = data;
                }
            } else if (typeof data === 'object' && data !== null) {
                if (Array.isArray(data.bookNames)) {
                    newBookSuggestions = data.bookNames;
                } else if (data.books && typeof data.books === 'object') {
                    newBookSuggestions = Object.values(data.books).map(b => typeof b === 'object' ? (b.BookName || b.name || b.book || String(b)) : b);
                } else {
                    newBookSuggestions = Object.values(data).map(b => typeof b === 'object' ? (b.BookName || b.name || b.book || String(b)) : b);
                }
            } else {
                newBookSuggestions = [];
            }
            // Remove falsy values and ensure all are strings
            newBookSuggestions = newBookSuggestions.filter(Boolean).map(b => String(b));
            bookSuggestions = newBookSuggestions;
            chapterSuggestions = newChapterSuggestions;
            // When translation changes, update verseSuggestions for first book/chapter
            if (Array.isArray(window.lastApiBooks)) {
                const bookObj = window.lastApiBooks.find(b => (b.BookName || b.name || b.book || String(b)) === (bookSuggestions[0] || "Genesis"));
                if (bookObj && bookObj.chapters) {
                    const firstChapter = Object.keys(bookObj.chapters)[0];
                    if (firstChapter && bookObj.chapters[firstChapter]) {
                        verseSuggestions = bookObj.chapters[firstChapter].map(v => String(v));
                    } else {
                        verseSuggestions = [];
                    }
                } else {
                    verseSuggestions = [];
                }
            } else {
                verseSuggestions = [];
            }
            // console.log('verseSuggestions:', verseSuggestions);
        } catch (err) {
            bookSuggestions = [];
            chapterSuggestions = [];
        }
    }

    // Render the book span with autofill suggestion or user input
    function renderBook() {
        if (bookUserInput === "") {
            bookSpan.textContent = lastAcceptedBookSuggestion;
            selectSpan(bookSpan, 0, lastAcceptedBookSuggestion.length);
            return;
        }
        // Find suggestion matching user input
        const bookSuggestion = bookSuggestions.find(s =>
            s.toLowerCase().startsWith(bookUserInput.toLowerCase())
        );
        if (bookSuggestion) {
            bookSpan.textContent = bookSuggestion;
            selectSpan(bookSpan, bookUserInput.length, bookSuggestion.length);
            lastAcceptedBookSuggestion = bookSuggestion;
            // When book changes, reset chapter and verse to 1:1
            const chapterSpan = document.getElementById("chapter");
            const verseSpan = document.getElementById("verse");
            if (chapterSpan) {
                chapterSpan.textContent = "1";
                chapterUserInput = "1";
                lastAcceptedChapterSuggestion = "1";
            }
            if (verseSpan) {
                verseSpan.textContent = "1";
                verseUserInput = "1";
                lastAcceptedVerseSuggestion = "1";
            }
            // Update chapter and verse suggestions when book changes
            if (Array.isArray(window.lastApiBooks)) {
                const bookObj = window.lastApiBooks.find(b => (b.BookName || b.name || b.book || String(b)) === bookSuggestion);
                if (bookObj && bookObj.chapters) {
                    chapterSuggestions = Object.keys(bookObj.chapters).map(ch => String(ch));
                    // Default to first chapter for verse suggestions
                    const firstChapter = chapterSuggestions[0];
                    if (firstChapter && bookObj.chapters[firstChapter]) {
                        verseSuggestions = bookObj.chapters[firstChapter].map(v => String(v));
                    } else {
                        verseSuggestions = [];
                    }
                } else {
                    verseSuggestions = [];
                }
            } else {
                verseSuggestions = [];
            }
        } else {
            bookSpan.textContent = bookUserInput;
            selectSpan(bookSpan, bookUserInput.length, bookUserInput.length);
        }
}

// Render the chapter span, only allow input if chapter is in available suggestions
function renderChapter() {
    const chapterSpan = document.getElementById("chapter");
    if (chapterUserInput === "") {
        chapterSpan.textContent = lastAcceptedChapterSuggestion;
        selectSpan(chapterSpan, 0, lastAcceptedChapterSuggestion.length);
        return;
    }
    // Only allow input if it matches a suggestion
    const isValid = chapterSuggestions.includes(chapterUserInput);
    if (isValid) {
        chapterSpan.textContent = chapterUserInput;
        selectSpan(chapterSpan, chapterUserInput.length, chapterUserInput.length);
        lastAcceptedChapterSuggestion = chapterUserInput;
        // console.log('lastAcceptedChapterSuggestion:', lastAcceptedChapterSuggestion);
        // Update verse suggestions when chapter changes
        if (Array.isArray(window.lastApiBooks)) {
            const bookObj = window.lastApiBooks.find(b => (b.BookName || b.name || b.book || String(b)) === lastAcceptedBookSuggestion);
            if (bookObj && bookObj.chapters && bookObj.chapters[chapterUserInput]) {
                verseSuggestions = bookObj.chapters[chapterUserInput].map(v => String(v));
            } else {
                verseSuggestions = [];
            }
        } else {
            verseSuggestions = [];
        }
        // console.log('verseSuggestions:', verseSuggestions);
    } else {
        // Revert to last accepted if invalid
        chapterUserInput = lastAcceptedChapterSuggestion;
        chapterSpan.textContent = lastAcceptedChapterSuggestion;
        selectSpan(chapterSpan, 0, lastAcceptedChapterSuggestion.length);
    }
// Render the verse span, only allow input if verse is in available suggestions
function renderVerse() {
    if (verseUserInput === "") {
        verseSpan.textContent = lastAcceptedVerseSuggestion;
        selectSpan(verseSpan, 0, lastAcceptedVerseSuggestion.length);
        return;
    }
    // Only allow input if it matches a suggestion
    const isValid = verseSuggestions.includes(verseUserInput);
    if (isValid) {
        verseSpan.textContent = verseUserInput;
        selectSpan(verseSpan, verseUserInput.length, verseUserInput.length);
        lastAcceptedVerseSuggestion = verseUserInput;
        // console.log('lastAcceptedVerseSuggestion:', lastAcceptedVerseSuggestion);
    } else {
        // Revert to last accepted if invalid
        verseUserInput = lastAcceptedVerseSuggestion;
        verseSpan.textContent = lastAcceptedVerseSuggestion;
        selectSpan(verseSpan, 0, lastAcceptedVerseSuggestion.length);
    }
}
    // Handle keyboard input for the verse span
    verseSpan.addEventListener("keydown", function (e) {
        if (e.key === "Backspace") {
            e.preventDefault();
            verseUserInput = verseUserInput.slice(0, -1);
            renderVerse();
        } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            // Allow typing to replace selection
            const sel = window.getSelection();
            if (sel && sel.rangeCount && sel.toString().length > 0) {
                // Replace selection with new char
                verseUserInput = verseUserInput.slice(0, sel.anchorOffset) + e.key;
            } else {
                verseUserInput += e.key;
            }
            // Only allow input if it matches a suggestion
            const isValid = verseSuggestions.includes(verseUserInput);
            if (!isValid) {
                e.preventDefault();
                verseUserInput = verseUserInput.slice(0, -1); // revert last char
                renderVerse();
                return;
            }
            e.preventDefault();
            renderVerse();
        } else if (e.key === "ArrowRight" || e.key === "Tab" || e.key === "Enter") {
            // Accept input and move focus if needed
            if (window.getSelection().toString().length > 0) {
                e.preventDefault();
                lastAcceptedVerseSuggestion = verseSpan.textContent;
                verseUserInput = verseSpan.textContent;
                selectSpan(verseSpan, verseUserInput.length, verseUserInput.length);
                if (e.key !== "ArrowRight") verseSpan.blur();
            }
        }
    });
    // On blur, validate verse and revert if invalid
    verseSpan.addEventListener("blur", function () {
        const currentText = verseSpan.textContent.trim();
        const isValid = verseSuggestions.includes(currentText);
        if (isValid) {
            lastAcceptedVerseSuggestion = currentText;
            verseUserInput = currentText;
            verseSpan.textContent = currentText;
            // console.log('lastAcceptedVerseSuggestion:', lastAcceptedVerseSuggestion);
        } else {
            verseUserInput = lastAcceptedVerseSuggestion;
            verseSpan.textContent = lastAcceptedVerseSuggestion;
            selectSpan(verseSpan, 0, lastAcceptedVerseSuggestion.length);
        }
    });
}
        // Handle keyboard input for the chapter span
        const chapterSpan = document.getElementById("chapter");
        chapterSpan.addEventListener("keydown", function (e) {
            if (e.key === "Backspace") {
                e.preventDefault();
                chapterUserInput = chapterUserInput.slice(0, -1);
                renderChapter();
            } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                // Allow typing to replace selection
                const sel = window.getSelection();
                if (sel && sel.rangeCount && sel.toString().length > 0) {
                    // Replace selection with new char
                    chapterUserInput = chapterUserInput.slice(0, sel.anchorOffset) + e.key;
                } else {
                    chapterUserInput += e.key;
                }
                // Only allow input if it matches a suggestion
                const isValid = chapterSuggestions.includes(chapterUserInput);
                if (!isValid) {
                    e.preventDefault();
                    chapterUserInput = chapterUserInput.slice(0, -1); // revert last char
                    renderChapter();
                    return;
                }
                e.preventDefault();
                renderChapter();
            } else if (e.key === "ArrowRight" || e.key === "Tab" || e.key === "Enter") {
                // Accept input and move focus if needed
                if (window.getSelection().toString().length > 0) {
                    e.preventDefault();
                    lastAcceptedChapterSuggestion = chapterSpan.textContent;
                    chapterUserInput = chapterSpan.textContent;
                    selectSpan(chapterSpan, chapterUserInput.length, chapterUserInput.length);
                    if (e.key !== "ArrowRight") chapterSpan.blur();
                }
            }
        });
        // On blur, validate chapter and revert if invalid
        chapterSpan.addEventListener("blur", function () {
            const currentText = chapterSpan.textContent.trim();
            const isValid = chapterSuggestions.includes(currentText);
            if (isValid) {
                lastAcceptedChapterSuggestion = currentText;
                chapterUserInput = currentText;
                chapterSpan.textContent = currentText;
                // console.log('lastAcceptedChapterSuggestion:', lastAcceptedChapterSuggestion);
            } else {
                chapterUserInput = lastAcceptedChapterSuggestion;
                chapterSpan.textContent = lastAcceptedChapterSuggestion;
                selectSpan(chapterSpan, 0, lastAcceptedChapterSuggestion.length);
            }
        });


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
                bookUserInput = bookUserInput.slice(0, -1);
                renderBook();
            } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                // Allow typing to replace selection
                const sel = window.getSelection();
                if (sel && sel.rangeCount && sel.toString().length > 0) {
                    // Replace selection with new char
                    bookUserInput = bookUserInput.slice(0, sel.anchorOffset) + e.key;
                } else {
                    bookUserInput += e.key;
                }
                // Only allow input if it matches a suggestion
                const matches = bookSuggestions.some(s => s.toLowerCase().startsWith(bookUserInput.toLowerCase()));
                if (!matches) {
                    e.preventDefault();
                    bookUserInput = bookUserInput.slice(0, -1); // revert last char
                    return;
                }
                e.preventDefault();
                renderBook();
            } else if (e.key === "ArrowRight" || e.key === "Tab" || e.key === "Enter") {
                // Accept suggestion and move focus if needed
                if (window.getSelection().toString().length > 0) {
                    e.preventDefault();
                    lastAcceptedBookSuggestion = bookSpan.textContent;
                    bookUserInput = bookSpan.textContent;
                    selectSpan(bookSpan, bookUserInput.length, bookUserInput.length);
                    if (e.key !== "ArrowRight") bookSpan.blur();
                }
            }
        });

    // On blur, validate book name and revert if invalid
        bookSpan.addEventListener("blur", function () {
            const currentText = bookSpan.textContent.trim();
            const found = bookSuggestions.find(
                s => s.toLowerCase() === currentText.toLowerCase()
            );
            if (found) {
                lastAcceptedBookSuggestion = found;
                bookUserInput = found;
                bookSpan.textContent = found;
                // console.log('lastAcceptedBookSuggestion:', lastAcceptedBookSuggestion);
            } else {
                bookUserInput = "";
                renderBook();
            }
        });

    // When translation changes, fetch new suggestions and reset autofill
    function handleTranslationChange() {
        fetchSuggestions().then(() => {
            bookUserInput = "";
            lastAcceptedBookSuggestion = bookSuggestions[0] || "Genesis";
            renderBook();
            // Update book suggestions display after translation selection
            const bookSuggestionsList = document.getElementById('bookSuggestionsList');
            if (bookSuggestionsList) {
                bookSuggestionsList.innerHTML = '';
                if (bookSuggestions.length) {
                    // Group by Old and New Testament
                    const oldTestament = bookSuggestions.slice(0, 39);
                    const newTestament = bookSuggestions.slice(39);
                    // Old Testament section
                    const oldDiv = document.createElement('div');
                    oldDiv.className = 'mb-2';
                    oldDiv.innerHTML = '<span class="font-bold text-blue-700 block mb-1 sticky top-0 bg-white z-10">Old Testament</span>';
                    for (const book of oldTestament) {
                        const span = document.createElement('span');
                        span.className = 'px-2 py-1 bg-gray-200 rounded block mb-1';
                        span.textContent = book;
                        oldDiv.appendChild(span);
                    }
                    // New Testament section
                    const newDiv = document.createElement('div');
                    newDiv.innerHTML = '<span class="font-bold text-green-700 block mb-1 sticky top-0 bg-white z-10">New Testament</span>';
                    for (const book of newTestament) {
                        const span = document.createElement('span');
                        span.className = 'px-2 py-1 bg-gray-200 rounded block mb-1';
                        span.textContent = book;
                        newDiv.appendChild(span);
                    }
                    bookSuggestionsList.appendChild(oldDiv);
                    bookSuggestionsList.appendChild(newDiv);
                } else {
                    bookSuggestionsList.innerHTML = '<span class="text-gray-400">No books found</span>';
                }
            }
        });
    }

    // Attach handler for both native and Select2 dropdown
    // Always attach both handlers for robustness
    translationDropdown.addEventListener("change", handleTranslationChange);
    if (window.jQuery && window.jQuery(translationDropdown).select2) {
        window.jQuery(translationDropdown).on('select2:select', handleTranslationChange);
    }

    // Wait for dropdown to be populated before fetching book suggestions
    async function waitForDropdownValue() {
        let tries = 0;
        while ((!translationDropdown.value || !translationDropdown.options.length) && tries < 50) {
            await new Promise(r => setTimeout(r, 100));
            tries++;
        }
        return translationDropdown.value;
    }

    // Initial load: fetch book suggestions and render autofill
    (async function () {
        await waitForDropdownValue();
        await fetchSuggestions();
        bookUserInput = "";
        lastAcceptedBookSuggestion = bookSuggestions[0] || "Genesis";
        renderBook();
        // Update book suggestions display after initial load
        const bookSuggestionsList = document.getElementById('bookSuggestionsList');
        if (bookSuggestionsList) {
            bookSuggestionsList.innerHTML = '';
            if (bookSuggestions.length) {
                // Group by Old and New Testament
                const oldTestament = bookSuggestions.slice(0, 39);
                const newTestament = bookSuggestions.slice(39);
                // Old Testament section
                const oldDiv = document.createElement('div');
                oldDiv.className = 'mb-2';
                oldDiv.innerHTML = '<span class="font-bold text-blue-700 block mb-1 sticky top-0 bg-white z-10">Old Testament</span>';
                for (const book of oldTestament) {
                    const span = document.createElement('span');
                    span.className = 'px-2 py-1 bg-gray-200 rounded block mb-1';
                    span.textContent = book;
                    oldDiv.appendChild(span);
                }
                // New Testament section
                const newDiv = document.createElement('div');
                newDiv.innerHTML = '<span class="font-bold text-green-700 block mb-1 sticky top-0 bg-white z-10">New Testament</span>';
                for (const book of newTestament) {
                    const span = document.createElement('span');
                    span.className = 'px-2 py-1 bg-gray-200 rounded block mb-1';
                    span.textContent = book;
                    newDiv.appendChild(span);
                }
                bookSuggestionsList.appendChild(oldDiv);
                bookSuggestionsList.appendChild(newDiv);
            } else {
                bookSuggestionsList.innerHTML = '<span class="text-gray-400">No books found</span>';
            }
        }
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
                // (Removed: Do not update bookSuggestionsList on Tab or arrow keys)
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

    // Add Tab/Shift+Tab, ArrowLeft/ArrowRight navigation, and ArrowUp/ArrowDown table sync to all three spans
    ['book', 'chapter', 'verse'].forEach(id => {
        const span = document.getElementById(id);
        if (!span) return;
        span.addEventListener('keydown', function(e) {
            // ...existing code for input, autofill, etc...
            if (e.key === "Tab" || e.key === "ArrowRight") {
                e.preventDefault();
                if ((e.key === "Tab" && e.shiftKey) || e.key === "ArrowLeft") {
                    // Reverse cycle: book -> verse -> chapter -> book
                    focusPrevEditable(span);
                } else {
                    focusNextEditable(span);
                }
            } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                focusPrevEditable(span);
            } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
                // Forward ArrowUp/ArrowDown to the scripture table for row navigation
                const tableDiv = document.getElementById('scripture-table');
                if (tableDiv) {
                    const keyboardEvent = new KeyboardEvent('keydown', {
                        key: e.key,
                        bubbles: true,
                        cancelable: true
                    });
                    tableDiv.dispatchEvent(keyboardEvent);
                    e.preventDefault();
                }
            }
            // ...existing code for Enter, etc...
        });
    });

})();
