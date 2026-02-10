document.addEventListener('DOMContentLoaded', function() {
    // Tab switching logic
    const tabUser = document.getElementById('tabUser');
    const tabBible = document.getElementById('tabBible');
    const userSection = document.getElementById('userSection');
    const bibleSection = document.getElementById('bibleSection');
    tabUser.onclick = function() {
        tabUser.className = 'flex-1 py-3 text-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition';
        tabBible.className = 'flex-1 py-3 text-lg font-semibold bg-blue-100 text-blue-700 hover:bg-blue-200 transition';
        userSection.style.display = '';
        bibleSection.style.display = 'none';
    };
    tabBible.onclick = function() {
        tabBible.className = 'flex-1 py-3 text-lg font-semibold bg-green-600 text-white hover:bg-green-700 transition';
        tabUser.className = 'flex-1 py-3 text-lg font-semibold bg-blue-100 text-blue-700 hover:bg-blue-200 transition';
        userSection.style.display = 'none';
        bibleSection.style.display = '';
    };
    // Default to User tab
    tabUser.click();
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
                        <td class="px-3 py-2">${user.email}</td>
                        <td class="px-3 py-2">${user.orgname || ''}</td>
                        <td class="px-3 py-2">${user.mobile || ''}</td>
                        <td class="px-3 py-2 text-center">${user.isEmailVerified ? '✔️' : ''}</td>
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
                document.getElementById('email').value = user.email;
                document.getElementById('orgname').value = user.orgname || '';
                document.getElementById('mobile').value = user.mobile || '';
                document.getElementById('isEmailVerified').checked = !!user.isEmailVerified;
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
        const email = document.getElementById('email').value;
        const orgname = document.getElementById('orgname').value;
        const mobile = document.getElementById('mobile').value;
        const password = document.getElementById('password').value;
        const isEmailVerified = document.getElementById('isEmailVerified').checked ? 1 : 0;
        const isRegistered = document.getElementById('isRegistered').checked ? 1 : 0;
        const payload = { id, firstname, lastname, username, email, orgname, mobile, isEmailVerified, isRegistered };
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
                document.getElementById('deleteUserName').textContent = user.username || user.email || user.id;
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
    // Bible DB Upload JS
    const bibleUploadForm = document.getElementById('bibleUploadForm');
    const bibleFile = document.getElementById('bibleFile');
    const bibleName = document.getElementById('bibleName');
    const uploadMsg = document.getElementById('uploadMsg');
    bibleUploadForm.onsubmit = function(e) {
        e.preventDefault();
        showLoading();
        uploadMsg.textContent = '';
        const file = bibleFile.files[0];
        const name = bibleName.value.trim();
        const abbr = document.getElementById('bibleAbbr').value.trim();
        const year = document.getElementById('bibleYear').value.trim();
        if (!file || !name) {
            showToast('Please provide a Bible name and select a file.', 'error');
            hideLoading();
            return;
        }
        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);
        formData.append('abbreviation', abbr);
        formData.append('year', year);
        fetch('/api/upload-bible', {
            method: 'POST',
            body: formData
        })
        .then(res => {
            hideLoading();
            if (!res.ok) {
                showToast('Server error: ' + res.status, 'error');
                return Promise.reject();
            }
            return res.json();
        })
        .then(result => {
            if (result && result.success) {
                showToast('Upload successful!', 'success');
                bibleFile.value = '';
                bibleName.value = '';
                document.getElementById('bibleAbbr').value = '';
                document.getElementById('bibleYear').value = '';
                setTimeout(fetchBibles, 300); // Delay to allow spinner to hide
            } else if (result) {
                showToast(result.error || 'Upload failed.', 'error');
            }
        })
        .catch(() => {
            hideLoading();
        })
        .finally(() => {
            // hideLoading(); // Already called above
        });
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
    function renderBibleTable() {
        const search = document.getElementById('bibleSearch').value.trim().toLowerCase();
        let filtered = bibleList.filter(bible =>
            bible.name.toLowerCase().includes(search) ||
            (bible.abbreviation || '').toLowerCase().includes(search) ||
            (bible.language || '').toLowerCase().includes(search) ||
            (bible.year || '').toLowerCase().includes(search)
        );
        filtered.sort((a, b) => {
            let valA = (a[bibleSortKey] || '').toLowerCase();
            let valB = (b[bibleSortKey] || '').toLowerCase();
            if (valA < valB) return bibleSortAsc ? -1 : 1;
            if (valA > valB) return bibleSortAsc ? 1 : -1;
            return 0;
        });
        const tbody = document.getElementById('biblesTbody');
        tbody.innerHTML = '';
        filtered.forEach(bible => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-green-50 transition';
            tr.innerHTML = `
                <td class="px-3 py-2">${bible.name}</td>
                <td class="px-3 py-2">${bible.abbreviation || ''}</td>
                <td class="px-3 py-2">${bible.language || ''}</td>
                <td class="px-3 py-2">${bible.year || ''}</td>
                <td class="px-3 py-2 flex gap-2">
                    <button class="text-blue-700 hover:underline" onclick="openBibleViewer('${bible.name.replace(/'/g, "\\'")}')">View</button>
                    <button class="text-green-700 hover:underline" onclick="showRenameBible('${bible.name.replace(/'/g, "\\'")}', '${bible.abbreviation ? bible.abbreviation.replace(/'/g, "\\'") : ''}')">Edit</button>
                    <button class="text-red-700 hover:underline" onclick="showDeleteBible('${bible.name.replace(/'/g, "\\'")}')">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
    document.getElementById('bibleSearch').addEventListener('input', renderBibleTable);
    document.getElementById('sortBibleName').onclick = function() {
        bibleSortKey = 'name';
        bibleSortAsc = bibleSortKey === 'name' ? !bibleSortAsc : true;
        renderBibleTable();
    };
    document.getElementById('sortBibleAbbr').onclick = function() {
        bibleSortKey = 'abbreviation';
        bibleSortAsc = bibleSortKey === 'abbreviation' ? !bibleSortAsc : true;
        renderBibleTable();
    };
    document.getElementById('sortBibleLang').onclick = function() {
        bibleSortKey = 'language';
        bibleSortAsc = bibleSortKey === 'language' ? !bibleSortAsc : true;
        renderBibleTable();
    };
    document.getElementById('sortBibleYear').onclick = function() {
        bibleSortKey = 'year';
        bibleSortAsc = bibleSortKey === 'year' ? !bibleSortAsc : true;
        renderBibleTable();
    };
    window.showRenameBible = function(name, abbr) {
        const bible = bibleList.find(b => b.name === name);
        document.getElementById('bibleRenameForm').style.display = '';
        document.getElementById('editBibleName').value = name;
        document.getElementById('editBibleOldName').value = name;
        document.getElementById('editBibleAbbr').value = abbr || '';
        document.getElementById('editBibleYear').value = bible && bible.year ? bible.year : '';
        document.getElementById('editBibleFile').value = '';
        document.getElementById('renameMsg').textContent = '';
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
    document.getElementById('cancelEditBible').onclick = function() {
        document.getElementById('bibleRenameForm').style.display = 'none';
        document.getElementById('renameMsg').textContent = '';
    };
    document.getElementById('bibleRenameForm').onsubmit = function(e) {
        e.preventDefault();
        showLoading();
        const oldName = document.getElementById('editBibleOldName').value;
        const newName = document.getElementById('editBibleName').value.trim();
        const newAbbr = document.getElementById('editBibleAbbr').value.trim();
        const newYear = document.getElementById('editBibleYear').value.trim();
        const fileInput = document.getElementById('editBibleFile');
        const file = fileInput.files[0];
        if (!newName) {
            showToast('Bible name cannot be empty.', 'error');
            hideLoading();
            return;
        }
        const formData = new FormData();
        formData.append('old_name', oldName);
        formData.append('new_name', newName);
        formData.append('new_abbreviation', newAbbr);
        formData.append('new_year', newYear);
        if (file) formData.append('file', file);
        fetch('/api/update-bible', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                showToast('Bible updated!', 'success');
                document.getElementById('bibleRenameForm').style.display = 'none';
                fetchBibles();
            } else {
                showToast(result.error || 'Update failed.', 'error');
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
    fetchBibles();


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
});


