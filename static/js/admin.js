document.addEventListener('DOMContentLoaded', function() {
    // Tab switching logic
    const tabUser = document.getElementById('tabUser');
    const tabBible = document.getElementById('tabBible');
    const tabLanguage = document.getElementById('tabLanguage');
    const tabSong = document.getElementById('tabSong');
    const tabRegCode = document.getElementById('tabRegCode');
    const userSection = document.getElementById('userSection');
    const bibleSection = document.getElementById('bibleSection');
    const languageSection = document.getElementById('languageSection');
    const songSection = document.getElementById('songSection');
    const regCodeSection = document.getElementById('regCodeSection');

    function setActiveTab(active) {
        const tabs = { user: tabUser, bible: tabBible, language: tabLanguage, song: tabSong, regCode: tabRegCode };
        const sections = { user: userSection, bible: bibleSection, language: languageSection, song: songSection, regCode: regCodeSection };
        const activeColors = {
            user: 'bg-blue-600 text-white hover:bg-blue-700',
            bible: 'bg-green-600 text-white hover:bg-green-700',
            language: 'bg-purple-600 text-white hover:bg-purple-700',
            song: 'bg-orange-600 text-white hover:bg-orange-700',
            regCode: 'bg-teal-600 text-white hover:bg-teal-700'
        };
        const inactiveColor = 'bg-blue-100 text-blue-700 hover:bg-blue-200';
        Object.keys(tabs).forEach(key => {
            tabs[key].className = `flex-1 py-3 text-lg font-semibold transition ${key === active ? activeColors[key] : inactiveColor}`;
            sections[key].style.display = key === active ? '' : 'none';
        });
    }

    tabUser.onclick = () => setActiveTab('user');
    tabBible.onclick = () => setActiveTab('bible');
    tabLanguage.onclick = () => { setActiveTab('language'); fetchLanguages(); };
    tabSong.onclick = () => { setActiveTab('song'); if (window.fetchSongs) window.fetchSongs(); };
    tabRegCode.onclick = () => { setActiveTab('regCode'); fetchRegCodes(); };

    // Default to User tab
    setActiveTab('user');
    // Toast function
    function showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        let color = 'bg-blue-600';
        if (type === 'success') color = 'bg-green-600';
        if (type === 'error') color = 'bg-red-600';
        toast.className = `${color} text-white px-6 py-3 rounded shadow-lg font-semibold text-center relative flex items-center gap-2`;
        toast.innerHTML = `
            <span class="flex-1">${message}</span>
            <button class="ml-4 text-white text-xl font-bold focus:outline-none hover:text-gray-200" style="line-height:1;" aria-label="Close">&times;</button>
        `;
        const closeBtn = toast.querySelector('button');
        closeBtn.onclick = () => {
            toast.classList.add('opacity-0');
            setTimeout(() => toast.remove(), 300);
        };
        document.getElementById('toastContainer').appendChild(toast);
        if (type !== 'error') {
            setTimeout(() => {
                toast.classList.add('opacity-0');
                setTimeout(() => toast.remove(), 500);
            }, duration);
        }
    }
    // Spinner helpers
    function showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }
    function hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
    // User CRUD JS
    function fetchUsers() {
        showLoading();
        fetch('/api/users')
            .then(res => res.json())
            .then(data => {
                const tbody = document.getElementById('usersTbody');
                tbody.innerHTML = '';
                (data.users || []).forEach(user => {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-blue-50 transition';
                    tr.innerHTML = `
                        <td class="px-3 py-2">${user.id}</td>
                        <td class="px-3 py-2">${user.firstname}</td>
                        <td class="px-3 py-2">${user.lastname}</td>
                        <td class="px-3 py-2">${user.username}</td>
                        <td class="px-3 py-2">${user.orgname || ''}</td>
                        <td class="px-3 py-2">${user.mobile || ''}</td>
                        <td class="px-3 py-2 text-center">${user.isRegistered ? '✔️' : ''}</td>
                        <td class="px-3 py-2 flex gap-2">
                            <button onclick="editUser(${user.id})" class="text-blue-600 hover:underline" title="Edit User">✏️</button>
                            <button onclick="showDeleteUser(${user.id})" class="text-red-600 hover:underline" title="Delete User">🗑️</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(() => {
                hideLoading();
            })
            .finally(() => {
                hideLoading();
            });
    }
    function editUser(id) {
        showLoading();
        fetch('/api/users')
            .then(res => res.json())
            .then(data => {
                const user = (data.users || []).find(u => u.id === id);
                if (!user) return;
                document.getElementById('userId').value = user.id;
                document.getElementById('firstname').value = user.firstname;
                document.getElementById('lastname').value = user.lastname;
                document.getElementById('username').value = user.username;
                document.getElementById('orgname').value = user.orgname || '';
                document.getElementById('mobile').value = user.mobile || '';
                document.getElementById('isRegistered').checked = !!user.isRegistered;
                document.getElementById('password').value = '';
            })
            .catch(() => {
                hideLoading();
            })
            .finally(() => {
                hideLoading();
            });
    }
    window.editUser = editUser;
    document.getElementById('userForm').onsubmit = function(e) {
        e.preventDefault();
        showLoading();
        const id = document.getElementById('userId').value;
        const firstname = document.getElementById('firstname').value;
        const lastname = document.getElementById('lastname').value;
        const username = document.getElementById('username').value;
        const orgname = document.getElementById('orgname').value;
        const mobile = document.getElementById('mobile').value;
        const password = document.getElementById('password').value;
        const isRegistered = document.getElementById('isRegistered').checked ? 1 : 0;
        const payload = { id, firstname, lastname, username, orgname, mobile, isRegistered };
        if (password) payload.password = password;
        const method = id ? 'PUT' : 'POST';
        fetch('/api/users', {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then (result => {
            if (result.success) {
                showToast(id ? 'User updated.' : 'User created.', 'success');
                document.getElementById('userForm').reset();
                document.getElementById('userId').value = '';
            } else {
                showToast(result.error || 'Operation failed.', 'error');
            }
            fetchUsers();
        })
        .catch(() => {
            hideLoading();
        })
        .finally(() => {
            hideLoading();
        });
    };
    document.getElementById('resetBtn').onclick = function() {
        showLoading();
        document.getElementById('userForm').reset();
        document.getElementById('userId').value = '';
        showToast('Form reset.', 'info');
        hideLoading();
    };
    function showDeleteUser(id) {
        showLoading();
        fetch('/api/users')
            .then(res => res.json())
            .then(data => {
                const user = (data.users || []).find(u => u.id === id);
                if (!user) return;
                document.getElementById('deleteUserModal').style.display = '';
                document.getElementById('deleteUserName').textContent = user.username || user.id;
                document.getElementById('confirmDeleteUser').setAttribute('data-user', id);
                document.getElementById('deleteUserMsg').textContent = '';
            })
            .catch(() => {
                hideLoading();
            })
            .finally(() => {
                hideLoading();
            });
    }
    window.showDeleteUser = showDeleteUser;
    document.getElementById('cancelDeleteUser').onclick = function() {
        document.getElementById('deleteUserModal').style.display = 'none';
        document.getElementById('deleteUserMsg').textContent = '';
    };
    document.getElementById('confirmDeleteUser').onclick = function() {
        showLoading();
        const id = this.getAttribute('data-user');
        fetch('/api/users', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                showToast('User deleted.', 'success');
                setTimeout(() => {
                    document.getElementById('deleteUserModal').style.display = 'none';
                    fetchUsers();
                }, 700);
            } else {
                showToast(result.error || 'Delete failed.', 'error');
            }
        })
        .catch(() => {
            hideLoading();
        })
        .finally(() => {
            hideLoading();
        });
    };
    // Bible Upload/Edit Modal JS
    let bibleFormMode = 'upload'; // 'upload' or 'edit'

    function openBibleModal(mode, bible) {
        bibleFormMode = mode;
        const modal = document.getElementById('bibleFormModal');
        const title = document.getElementById('bibleModalTitle');
        const submitBtn = document.getElementById('bibleModalSubmitBtn');
        const fileLabel = document.getElementById('bibleModalFileLabel');
        const fileInput = document.getElementById('bibleModalFile');

        document.getElementById('bibleModalForm').reset();
        document.getElementById('bibleModalOldName').value = '';

        if (mode === 'upload') {
            title.textContent = 'Upload Bible';
            submitBtn.textContent = 'Upload';
            fileLabel.innerHTML = 'Attach Bible <span class="text-red-500">*</span>';
            fileInput.required = true;
        } else {
            title.textContent = 'Edit Bible';
            submitBtn.textContent = 'Save';
            fileLabel.innerHTML = 'Attach Bible <span class="text-gray-400 font-normal">(optional)</span>';
            fileInput.required = false;
            if (bible) {
                document.getElementById('bibleModalOldName').value = bible.name;
                document.getElementById('bibleModalName').value = bible.name;
                document.getElementById('bibleModalAbbr').value = bible.abbreviation || '';
                document.getElementById('bibleModalYear').value = bible.year || '';
            }
        }

        modal.style.display = '';
    }

    function closeBibleModal() {
        document.getElementById('bibleFormModal').style.display = 'none';
    }

    document.getElementById('uploadBibleBtn').onclick = function() {
        openBibleModal('upload');
    };
    document.getElementById('closeBibleModal').onclick = closeBibleModal;
    document.getElementById('cancelBibleModal').onclick = closeBibleModal;

    document.getElementById('bibleModalForm').onsubmit = function(e) {
        e.preventDefault();
        showLoading();
        const name = document.getElementById('bibleModalName').value.trim();
        const abbr = document.getElementById('bibleModalAbbr').value.trim();
        const year = document.getElementById('bibleModalYear').value.trim();
        const file = document.getElementById('bibleModalFile').files[0];

        if (!name) {
            showToast('Bible name is required.', 'error');
            hideLoading();
            return;
        }

        const formData = new FormData();
        formData.append('name', name);
        formData.append('abbreviation', abbr);
        formData.append('year', year);
        if (file) formData.append('file', file);

        if (bibleFormMode === 'upload') {
            if (!file) {
                showToast('Please attach a Bible file.', 'error');
                hideLoading();
                return;
            }
            fetch('/api/upload-bible', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(result => {
                    if (result && result.success) {
                        showToast('Upload successful!', 'success');
                        closeBibleModal();
                        fetchBibles();
                    } else {
                        showToast((result && result.error) || 'Upload failed.', 'error');
                    }
                })
                .catch(() => showToast('Upload error.', 'error'))
                .finally(() => hideLoading());
        } else {
            const oldName = document.getElementById('bibleModalOldName').value;
            formData.append('old_name', oldName);
            formData.append('new_name', name);
            formData.append('new_abbreviation', abbr);
            formData.append('new_year', year);
            fetch('/api/update-bible', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(result => {
                    if (result && result.success) {
                        showToast('Bible updated!', 'success');
                        closeBibleModal();
                        fetchBibles();
                    } else {
                        showToast((result && result.error) || 'Update failed.', 'error');
                    }
                })
                .catch(() => showToast('Update error.', 'error'))
                .finally(() => hideLoading());
        }
    };
    // Bible List and Rename JS
    let bibleList = [];
    let bibleSortKey = 'name';
    let bibleSortAsc = true;
    function fetchBibles() {
        showLoading();
        fetch('/api/translations')
            .then(res => res.json())
            .then(data => {
                bibleList = data.translations || [];
                renderBibleTable();
            })
            .catch(() => {
                hideLoading();
            })
            .finally(() => {
                hideLoading();
            });
    }
    let LANGUAGE_NAMES = {};

    function resolveLanguageName(code) {
        if (!code) return 'Unknown';
        const lower = code.trim().toLowerCase();
        return LANGUAGE_NAMES[lower] || code.trim();
    }

    // Language Management
    let languageList = [];

    function fetchLanguages() {
        showLoading();
        fetch('/api/languages')
            .then(res => res.json())
            .then(data => {
                LANGUAGE_NAMES = data;
                languageList = Object.entries(data).map(([code, name]) => ({ code, name }));
                renderLanguageTable();
            })
            .catch(() => {})
            .finally(() => hideLoading());
    }

    function renderLanguageTable() {
        const search = document.getElementById('languageSearch').value.trim().toLowerCase();
        const filtered = languageList.filter(l =>
            l.code.toLowerCase().includes(search) ||
            l.name.toLowerCase().includes(search)
        );
        const tbody = document.getElementById('languagesTbody');
        tbody.innerHTML = '';
        filtered.forEach(l => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-purple-50 transition';
            tr.innerHTML = `
                <td class="px-4 py-2 font-mono text-purple-800">${l.code}</td>
                <td class="px-4 py-2">${l.name}</td>
                <td class="px-4 py-2 flex gap-3">
                    <button class="text-purple-700 hover:underline text-sm" onclick="showEditLanguage('${l.code.replace(/'/g, "\\'")}', '${l.name.replace(/'/g, "\\'")}')">Edit</button>
                    <button class="text-red-700 hover:underline text-sm" onclick="showDeleteLanguage('${l.code.replace(/'/g, "\\'")}', '${l.name.replace(/'/g, "\\'")}')">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    document.getElementById('languageSearch').addEventListener('input', renderLanguageTable);

    function openLanguageModal(mode, code, name) {
        document.getElementById('languageModalForm').reset();
        document.getElementById('languageModalOldCode').value = '';
        const codeInput = document.getElementById('languageModalCode');
        if (mode === 'edit') {
            document.getElementById('languageModalTitle').textContent = 'Edit Language';
            document.getElementById('languageModalSubmitBtn').textContent = 'Save';
            document.getElementById('languageModalOldCode').value = code;
            codeInput.value = code;
            codeInput.readOnly = true;
            codeInput.classList.add('bg-gray-100');
            document.getElementById('languageModalName').value = name;
        } else {
            document.getElementById('languageModalTitle').textContent = 'Add Language';
            document.getElementById('languageModalSubmitBtn').textContent = 'Add';
            codeInput.readOnly = false;
            codeInput.classList.remove('bg-gray-100');
        }
        document.getElementById('languageFormModal').style.display = '';
    }

    function closeLanguageModal() {
        document.getElementById('languageFormModal').style.display = 'none';
    }

    document.getElementById('addLanguageBtn').onclick = () => openLanguageModal('add');
    document.getElementById('closeLanguageModal').onclick = closeLanguageModal;
    document.getElementById('cancelLanguageModal').onclick = closeLanguageModal;

    window.showEditLanguage = function(code, name) {
        openLanguageModal('edit', code, name);
    };

    window.showDeleteLanguage = function(code, name) {
        document.getElementById('deleteLanguageName').textContent = `${name} (${code})`;
        document.getElementById('confirmDeleteLanguage').setAttribute('data-code', code);
        document.getElementById('deleteLanguageModal').style.display = '';
    };

    document.getElementById('cancelDeleteLanguage').onclick = function() {
        document.getElementById('deleteLanguageModal').style.display = 'none';
    };

    document.getElementById('confirmDeleteLanguage').onclick = function() {
        const code = this.getAttribute('data-code');
        showLoading();
        fetch(`/api/languages/${encodeURIComponent(code)}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(result => {
                if (result.success) {
                    showToast('Language deleted.', 'success');
                    document.getElementById('deleteLanguageModal').style.display = 'none';
                    fetchLanguages();
                } else {
                    showToast(result.error || 'Delete failed.', 'error');
                }
            })
            .catch(() => showToast('Delete error.', 'error'))
            .finally(() => hideLoading());
    };

    document.getElementById('languageModalForm').onsubmit = function(e) {
        e.preventDefault();
        const code = document.getElementById('languageModalCode').value.trim().toLowerCase();
        const name = document.getElementById('languageModalName').value.trim();
        if (!code || !name) {
            showToast('Code and name are required.', 'error');
            return;
        }
        showLoading();
        fetch('/api/languages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, name })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                showToast('Language saved.', 'success');
                closeLanguageModal();
                fetchLanguages();
            } else {
                showToast(result.error || 'Save failed.', 'error');
            }
        })
        .catch(() => showToast('Save error.', 'error'))
        .finally(() => hideLoading());
    };

    function renderBibleTable() {
        const search = document.getElementById('bibleSearch').value.trim().toLowerCase();
        let filtered = bibleList.filter(bible =>
            bible.name.toLowerCase().includes(search) ||
            (bible.abbreviation || '').toLowerCase().includes(search) ||
            resolveLanguageName(bible.language).toLowerCase().includes(search) ||
            (bible.language || '').toLowerCase().includes(search) ||
            (bible.year || '').toLowerCase().includes(search)
        );

        // Group by resolved language name
        const groups = {};
        filtered.forEach(bible => {
            const lang = resolveLanguageName(bible.language);
            if (!groups[lang]) groups[lang] = [];
            groups[lang].push(bible);
        });

        // Sort language group keys
        const sortedLangs = Object.keys(groups).sort((a, b) => a.localeCompare(b));

        // Sort bibles within each group
        sortedLangs.forEach(lang => {
            groups[lang].sort((a, b) => {
                let valA = (a[bibleSortKey] || '').toLowerCase();
                let valB = (b[bibleSortKey] || '').toLowerCase();
                if (valA < valB) return bibleSortAsc ? -1 : 1;
                if (valA > valB) return bibleSortAsc ? 1 : -1;
                return 0;
            });
        });

        const tbody = document.getElementById('biblesTbody');
        tbody.innerHTML = '';

        sortedLangs.forEach(lang => {
            // Language group header row
            const groupRow = document.createElement('tr');
            groupRow.innerHTML = `<td colspan="4" class="px-4 py-2 bg-green-200 text-green-900 font-bold text-xs uppercase tracking-wider">${lang}</td>`;
            tbody.appendChild(groupRow);

            groups[lang].forEach(bible => {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-green-50 transition';
                tr.innerHTML = `
                    <td class="px-4 py-2">${bible.name}</td>
                    <td class="px-4 py-2">${bible.abbreviation || ''}</td>
                    <td class="px-4 py-2">${bible.year || ''}</td>
                    <td class="px-4 py-2 flex gap-3">
                        <button class="text-blue-700 hover:underline text-sm" onclick="openBibleViewer('${bible.name.replace(/'/g, "\\'")}')">View</button>
                        <button class="text-green-700 hover:underline text-sm" onclick="showRenameBible('${bible.name.replace(/'/g, "\\'")}')">Edit</button>
                        <button class="text-red-700 hover:underline text-sm" onclick="showDeleteBible('${bible.name.replace(/'/g, "\\'")}')">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
    }
    document.getElementById('bibleSearch').addEventListener('input', renderBibleTable);
    document.getElementById('sortBibleName').onclick = function() {
        if (bibleSortKey === 'name') bibleSortAsc = !bibleSortAsc;
        else { bibleSortKey = 'name'; bibleSortAsc = true; }
        renderBibleTable();
    };
    document.getElementById('sortBibleAbbr').onclick = function() {
        if (bibleSortKey === 'abbreviation') bibleSortAsc = !bibleSortAsc;
        else { bibleSortKey = 'abbreviation'; bibleSortAsc = true; }
        renderBibleTable();
    };
    document.getElementById('sortBibleYear').onclick = function() {
        if (bibleSortKey === 'year') bibleSortAsc = !bibleSortAsc;
        else { bibleSortKey = 'year'; bibleSortAsc = true; }
        renderBibleTable();
    };
    window.showRenameBible = function(name) {
        const bible = bibleList.find(b => b.name === name);
        openBibleModal('edit', bible || { name });
    };
    window.showDeleteBible = function(name) {
        document.getElementById('deleteBibleModal').style.display = '';
        document.getElementById('deleteBibleName').textContent = name;
        document.getElementById('confirmDeleteBible').setAttribute('data-bible', name);
        document.getElementById('deleteBibleMsg').textContent = '';
    };
    window.downloadBible = function(name) {
        showLoading();
        fetch('/api/download/bible/zip')
            .then(res => {
                if (!res.ok) {
                    showToast('Download failed: ' + res.status, 'error');
                    hideLoading();
                    return Promise.reject();
                }
                return res.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'bible_all.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                showToast('Download started!', 'success');
                hideLoading();
            })
            .catch(() => {
                hideLoading();
                showToast('Download error.', 'error');
            });
    };
    window.downloadAllBibles = function() {
        showLoading();
        fetch('/api/download/bible/zip')
            .then(res => {
                if (!res.ok) {
                    showToast('Download failed: ' + res.status, 'error');
                    hideLoading();
                    return Promise.reject();
                }
                return res.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'bible_all.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                showToast('All Bibles downloaded!', 'success');
                hideLoading();
            })
            .catch(() => {
                hideLoading();
                showToast('Download error.', 'error');
            });
    };
    document.getElementById('cancelDeleteBible').onclick = function() {
        document.getElementById('deleteBibleModal').style.display = 'none';
        document.getElementById('deleteBibleMsg').textContent = '';
    };
    document.getElementById('confirmDeleteBible').onclick = function() {
        const name = this.getAttribute('data-bible');
        fetch('/api/delete-bible', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                showToast('Bible deleted!', 'success');
                setTimeout(() => {
                    document.getElementById('deleteBibleModal').style.display = 'none';
                    fetchBibles();
                }, 700);
            } else {
                showToast(result.error || 'Delete failed.', 'error');
            }
        })
        .catch(() => {
            hideLoading();
        })
        .finally(() => {
            hideLoading();
        });
    };
    fetchUsers();
    // Load languages first so Bible table grouping resolves codes correctly
    fetch('/api/languages')
        .then(res => res.json())
        .then(data => { LANGUAGE_NAMES = data; })
        .finally(() => fetchBibles());


    // Bible Viewer Modal logic
window.openBibleViewer = function(name) {
    showLoading();
    fetch(`/api/verses/${encodeURIComponent(name)}`)
        .then(res => res.json())
        .then(data => {
            const contentDiv = document.getElementById('bibleViewerContent');
            if (!data.verses || !data.verses.length) {
                contentDiv.innerHTML = '<div class="text-red-600">No verses found.</div>';
            } else {
                // Group by book (Reference format: "Book Chapter:Verse")
                let grouped = {};
                data.verses.forEach(v => {
                    let ref = v.Reference || '';
                    let book = ref.split(' ')[0];
                    if (!grouped[book]) grouped[book] = [];
                    grouped[book].push(v);
                });
                let html = '';
                for (let book in grouped) {
                    html += `<div class="mb-4"><h4 class="font-bold text-blue-600 mb-2">${book}</h4>`;
                    grouped[book].forEach(v => {
                        html += `<div class="mb-1"><span class="font-semibold">${v.Reference}:</span> <span>${v.Verse}</span></div>`;
                    });
                    html += `</div>`;
                }
                contentDiv.innerHTML = html;
            }
            document.getElementById('bibleViewerModal').style.display = '';
        })
        .catch(() => {
            document.getElementById('bibleViewerContent').innerHTML = '<div class="text-red-600">Error loading Bible content.</div>';
            document.getElementById('bibleViewerModal').style.display = '';
        })
        .finally(() => {
            hideLoading();
        });
};
document.getElementById('closeBibleViewer').onclick = function() {
    document.getElementById('bibleViewerModal').style.display = 'none';
    document.getElementById('bibleViewerContent').innerHTML = '';
};

    // Registration Codes
    let regCodeList = [];

    function fetchRegCodes() {
        showLoading();
        fetch('/api/registration-codes')
            .then(res => res.json())
            .then(data => {
                regCodeList = data.codes || [];
                renderRegCodesTable();
            })
            .catch(() => showToast('Failed to load registration codes.', 'error'))
            .finally(() => hideLoading());
    }

    function trialDaysLabel(days) {
        if (!days) return '<span class="text-gray-400">—</span>';
        if (days == 1) return '1 Day';
        if (days == 7) return '7 Days';
        if (days == 15) return '15 Days';
        if (days == 30) return '1 Month';
        return `${days} Days`;
    }

    function renderRegCodesTable() {
        const search = document.getElementById('regCodeSearch').value.trim().toLowerCase();
        const filtered = regCodeList.filter(c =>
            c.registration_code.toLowerCase().includes(search) ||
            c.registration_type.toLowerCase().includes(search) ||
            (c.expiration_date || '').toLowerCase().includes(search)
        );
        const tbody = document.getElementById('regCodesTbody');
        tbody.innerHTML = '';
        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="px-4 py-6 text-center text-gray-400">No registration codes found.</td></tr>';
            return;
        }
        filtered.forEach(c => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-teal-50 transition';

            // ID
            const tdId = document.createElement('td');
            tdId.className = 'px-4 py-2 text-gray-500 text-sm';
            tdId.textContent = c.id;
            tr.appendChild(tdId);

            // Registration Code — ellipsis + copy on hover for plain-text codes
            const tdCode = document.createElement('td');
            tdCode.className = 'px-4 py-2 max-w-[220px]';

            if (c.is_used) {
                // Encrypted: truncate, show full hash as tooltip
                const span = document.createElement('span');
                span.className = 'font-mono text-xs text-gray-400 block truncate';
                span.title = c.registration_code;
                span.textContent = c.registration_code;
                tdCode.appendChild(span);
            } else {
                // Plain text: truncate + copy icon revealed on hover
                const wrapper = document.createElement('div');
                wrapper.className = 'flex items-center gap-2';

                const span = document.createElement('span');
                span.className = 'font-mono text-sm truncate';
                span.title = c.registration_code;
                span.textContent = c.registration_code;

                const copyBtn = document.createElement('button');
                copyBtn.type = 'button';
                copyBtn.title = 'Copy to clipboard';
                copyBtn.style.cssText = 'flex-shrink:0;opacity:0;transition:opacity 0.15s;color:#9ca3af;';
                copyBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>`;

                copyBtn.onmouseenter = () => copyBtn.style.color = '#0d9488';
                copyBtn.onmouseleave = () => copyBtn.style.color = '#9ca3af';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(c.registration_code)
                        .then(() => showToast('Code copied!', 'success', 1500))
                        .catch(() => {
                            const tmp = document.createElement('input');
                            tmp.value = c.registration_code;
                            document.body.appendChild(tmp);
                            tmp.select();
                            document.execCommand('copy');
                            document.body.removeChild(tmp);
                            showToast('Code copied!', 'success', 1500);
                        });
                };

                tdCode.addEventListener('mouseenter', () => copyBtn.style.opacity = '1');
                tdCode.addEventListener('mouseleave', () => copyBtn.style.opacity = '0');

                wrapper.appendChild(span);
                wrapper.appendChild(copyBtn);
                tdCode.appendChild(wrapper);
            }
            tr.appendChild(tdCode);

            // Type
            const tdType = document.createElement('td');
            tdType.className = 'px-4 py-2';
            tdType.innerHTML = c.registration_type === 'permanent'
                ? '<span class="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded">Permanent</span>'
                : '<span class="bg-yellow-100 text-yellow-700 text-xs font-semibold px-2 py-0.5 rounded">Trial</span>';
            tr.appendChild(tdType);

            // Duration
            const tdDuration = document.createElement('td');
            tdDuration.className = 'px-4 py-2 text-sm';
            tdDuration.innerHTML = c.registration_type === 'trial' ? trialDaysLabel(c.trial_days) : '<span class="text-gray-400">—</span>';
            tr.appendChild(tdDuration);

            // Expiry
            const tdExpiry = document.createElement('td');
            tdExpiry.className = 'px-4 py-2 text-sm';
            tdExpiry.innerHTML = c.expiration_date || '<span class="text-gray-400">Not yet set</span>';
            tr.appendChild(tdExpiry);

            // Device ID
            const tdDevice = document.createElement('td');
            tdDevice.className = 'px-4 py-2 max-w-[180px]';
            if (c.device_id) {
                const span = document.createElement('span');
                span.className = 'font-mono text-xs text-gray-500 block truncate';
                span.title = c.device_id;
                span.textContent = c.device_id;
                tdDevice.appendChild(span);
            } else {
                tdDevice.innerHTML = '<span class="text-gray-300">—</span>';
            }
            tr.appendChild(tdDevice);

            // Status
            const tdStatus = document.createElement('td');
            tdStatus.className = 'px-4 py-2';
            let statusBadge;
            if (!c.is_used) {
                statusBadge = '<span class="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded">Available</span>';
            } else if (c.registration_type === 'trial' && c.expiration_date && new Date(c.expiration_date) < new Date(new Date().toDateString())) {
                statusBadge = '<span class="bg-orange-100 text-orange-700 text-xs font-semibold px-2 py-0.5 rounded">Expired</span>';
            } else {
                statusBadge = '<span class="bg-red-100 text-red-700 text-xs font-semibold px-2 py-0.5 rounded">Used</span>';
            }
            tdStatus.innerHTML = statusBadge;
            tr.appendChild(tdStatus);

            // Actions
            const tdActions = document.createElement('td');
            tdActions.className = 'px-4 py-2 flex items-center gap-2';

            // Expire button — only for active trial codes that are not yet expired
            const isActiveTrial = c.is_used &&
                c.registration_type === 'trial' &&
                (!c.expiration_date || new Date(c.expiration_date) >= new Date(new Date().toDateString()));
            if (isActiveTrial) {
                const expireBtn = document.createElement('button');
                expireBtn.type = 'button';
                expireBtn.className = 'text-orange-400 hover:text-orange-600 transition';
                expireBtn.title = 'Manually expire';
                expireBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
                expireBtn.onclick = () => showExpireRegCode(c.id, c.registration_code);
                tdActions.appendChild(expireBtn);
            }

            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'text-red-500 hover:text-red-700 transition';
            deleteBtn.title = 'Delete code';
            deleteBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>`;
            deleteBtn.onclick = () => showDeleteRegCode(c.id, c.registration_code);
            tdActions.appendChild(deleteBtn);
            tr.appendChild(tdActions);

            tbody.appendChild(tr);
        });
    }

    document.getElementById('regCodeSearch').addEventListener('input', renderRegCodesTable);

    function showDeleteRegCode(id, code) {
        document.getElementById('deleteRegCodeValue').textContent = code;
        document.getElementById('confirmDeleteRegCode').setAttribute('data-id', id);
        document.getElementById('deleteRegCodeModal').style.display = '';
    }
    window.showDeleteRegCode = showDeleteRegCode;

    document.getElementById('cancelDeleteRegCode').onclick = function() {
        document.getElementById('deleteRegCodeModal').style.display = 'none';
    };

    function showExpireRegCode(id, code) {
        document.getElementById('expireRegCodeValue').textContent = code;
        document.getElementById('confirmExpireRegCode').setAttribute('data-id', id);
        document.getElementById('expireRegCodeModal').style.display = '';
    }
    window.showExpireRegCode = showExpireRegCode;

    document.getElementById('cancelExpireRegCode').onclick = function() {
        document.getElementById('expireRegCodeModal').style.display = 'none';
    };

    document.getElementById('confirmExpireRegCode').onclick = function() {
        const id = this.getAttribute('data-id');
        showLoading();
        fetch(`/api/registration-codes/${id}/expire`, { method: 'POST' })
            .then(res => res.json())
            .then(result => {
                if (result.success) {
                    showToast('Registration code expired.', 'success');
                    document.getElementById('expireRegCodeModal').style.display = 'none';
                    fetchRegCodes();
                } else {
                    showToast(result.error || 'Failed to expire code.', 'error');
                }
            })
            .catch(() => showToast('Request failed.', 'error'))
            .finally(() => hideLoading());
    };

    document.getElementById('confirmDeleteRegCode').onclick = function() {
        const id = this.getAttribute('data-id');
        showLoading();
        fetch(`/api/registration-codes/${id}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(result => {
                if (result.success) {
                    showToast('Registration code deleted.', 'success');
                    document.getElementById('deleteRegCodeModal').style.display = 'none';
                    fetchRegCodes();
                } else {
                    showToast(result.error || 'Delete failed.', 'error');
                }
            })
            .catch(() => showToast('Request failed.', 'error'))
            .finally(() => hideLoading());
    };

    // Generate random code: XXXXX-XXXXX-XXXXX-XXXXX (uppercase alphanumeric)
    function generateRandomCode() {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // no 0/O/1/I to avoid confusion
        const group = () => Array.from({ length: 5 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
        return `${group()}-${group()}-${group()}-${group()}`;
    }

    // Create Registration Code Modal
    function openCreateRegCodeModal() {
        document.getElementById('newRegCode').value = generateRandomCode();
        setRegType('trial');
        setTrialDays('7');
        document.getElementById('createRegCodeModal').style.display = '';
    }

    function closeCreateRegCodeModal() {
        document.getElementById('createRegCodeModal').style.display = 'none';
    }

    function setRegType(type) {
        document.getElementById('newRegType').value = type;
        const isTrial = type === 'trial';
        // Type button active states
        document.getElementById('typeBtnTrial').className = isTrial
            ? 'regtype-btn flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 border-yellow-400 bg-yellow-400 text-white transition font-semibold text-sm shadow'
            : 'regtype-btn flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 border-gray-200 bg-white text-gray-500 transition font-semibold text-sm hover:border-yellow-400 hover:text-yellow-600';
        document.getElementById('typeBtnPermanent').className = !isTrial
            ? 'regtype-btn flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 border-blue-500 bg-blue-500 text-white transition font-semibold text-sm shadow'
            : 'regtype-btn flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 border-gray-200 bg-white text-gray-500 transition font-semibold text-sm hover:border-blue-400 hover:text-blue-600';
        // Show/hide duration and permanent note
        document.getElementById('trialDurationSection').style.display = isTrial ? '' : 'none';
        document.getElementById('permanentNote').classList.toggle('hidden', isTrial);
    }

    function setTrialDays(days) {
        const isCustom = days === 'custom';
        document.getElementById('newTrialDays').value = isCustom ? '' : days;
        document.getElementById('customDaysSection').classList.toggle('hidden', !isCustom);
        if (isCustom) {
            document.getElementById('customDaysInput').focus();
        }
        document.querySelectorAll('.duration-btn').forEach(btn => {
            const active = btn.dataset.days === String(days);
            btn.className = active
                ? 'duration-btn py-2 rounded-lg border-2 border-teal-500 bg-teal-500 text-white text-sm font-semibold transition'
                : 'duration-btn py-2 rounded-lg border-2 border-gray-200 bg-white text-gray-500 text-sm font-semibold hover:border-teal-400 hover:text-teal-700 transition';
        });
    }

    document.getElementById('customDaysInput').addEventListener('input', function() {
        document.getElementById('newTrialDays').value = this.value;
    });

    document.getElementById('createRegCodeBtn').onclick = openCreateRegCodeModal;
    document.getElementById('closeCreateRegCodeModal').onclick = closeCreateRegCodeModal;
    document.getElementById('cancelCreateRegCode').onclick = closeCreateRegCodeModal;
    document.getElementById('generateCodeBtn').onclick = () => {
        document.getElementById('newRegCode').value = generateRandomCode();
    };
    document.getElementById('typeBtnTrial').onclick = () => setRegType('trial');
    document.getElementById('typeBtnPermanent').onclick = () => setRegType('permanent');
    document.querySelectorAll('.duration-btn').forEach(btn => {
        btn.onclick = () => setTrialDays(btn.dataset.days);
    });

    document.getElementById('createRegCodeForm').onsubmit = function(e) {
        e.preventDefault();
        const code = document.getElementById('newRegCode').value.trim();
        const regType = document.getElementById('newRegType').value;
        let trialDays = regType === 'trial' ? document.getElementById('newTrialDays').value : null;
        if (regType === 'trial' && (!trialDays || trialDays < 1)) {
            showToast('Please enter a valid number of days.', 'error');
            document.getElementById('customDaysInput').focus();
            return;
        }

        showLoading();
        fetch('/api/registration-codes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ registration_code: code, registration_type: regType, trial_days: trialDays })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                showToast('Registration code created.', 'success');
                closeCreateRegCodeModal();
                fetchRegCodes();
            } else {
                showToast(result.error || 'Failed to create code.', 'error');
            }
        })
        .catch(() => showToast('Request failed.', 'error'))
        .finally(() => hideLoading());
    };
});


