document.addEventListener('DOMContentLoaded', async function() {
    const dropdown = document.getElementById('bible-translation');
    if (!dropdown) return;

    try {
        const res = await fetch('/api/translations');
        const data = await res.json();
        dropdown.innerHTML = '';

        if (data.translations && data.translations.length > 0) {
            // Language code to readable name map
            const languageNames = {
                'en': 'English',
                'fil': 'Filipino',
                'tl': 'Tagalog',
                'es': 'Spanish',
                'de': 'German',
                'fr': 'French',
                'ko': 'Korean',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ru': 'Russian',
                'pt': 'Portuguese',
                'it': 'Italian',
                'nl': 'Dutch',
                'pl': 'Polish',
                'sv': 'Swedish',
                'no': 'Norwegian',
                'fi': 'Finnish',
                'da': 'Danish',
                'el': 'Greek',
                'he': 'Hebrew',
                // Add more as needed
            };

            const groups = {};
            data.translations.forEach(t => {
                let lang = t.language || 'Other';
                let label = languageNames[lang] || lang;
                if (!groups[label]) groups[label] = [];
                groups[label].push(t);
            });

            Object.keys(groups).forEach(langLabel => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = langLabel;
                groups[langLabel].forEach(t => {
                    const option = document.createElement('option');
                    option.value = t.name;
                    // Store abbr and year as data attributes for Select2 template
                    option.dataset.abbr = t.abbreviation || '';
                    option.dataset.year = t.year || '';
                    option.textContent = `${t.name} (${t.abbreviation}) ${t.year}`;
                    optgroup.appendChild(option);
                });
                dropdown.appendChild(optgroup);
            });
        } else {
            const option = document.createElement('option');
            option.textContent = 'No translations found';
            dropdown.appendChild(option);
        }
    } catch (err) {
        const option = document.createElement('option');
        option.textContent = 'Error loading translations';
        dropdown.appendChild(option);
    }

    // Initialize Select2 with custom template for bold abbr
    if (window.jQuery && $(dropdown).select2) {
        $(dropdown).select2({
            templateResult: function (state) {
                if (!state.id) return state.text;
                const abbr = state.element ? state.element.dataset.abbr : '';
                const year = state.element ? state.element.dataset.year : '';
                const name = state.text.split(' (')[0];
                if (abbr) {
                    // Format: name (abbr) year, abbr bold
                    return $(
                        `<span>${name} (<b>${abbr}</b>) ${year}</span>`
                    );
                }
                return state.text;
            },
            templateSelection: function (state) {
                if (!state.id) return state.text;
                const abbr = state.element ? state.element.dataset.abbr : '';
                const year = state.element ? state.element.dataset.year : '';
                const name = state.text.split(' (')[0];
                if (abbr) {
                    return $(
                        `<span>${name} (<b>${abbr}</b>) ${year}</span>`
                    );
                }
                return state.text;
            },
            escapeMarkup: function (m) { return m; }
        });

        // Remove scripture-table update logic from here
        // $(dropdown).on('change', ...);
    } else {
        // Remove scripture-table update logic from here
        // dropdown.addEventListener('change', ...);
    }

    // Remove loadScriptureTable function from here

    // Remove initial scripture-table load from here
    // if (dropdown.value) { ... }
});
