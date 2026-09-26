// NHGCC Entrance Desk Check-In Terminal Logic

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('memberSearch');
    const tableBody = document.getElementById('attendanceTableBody');
    const serviceDateInput = document.getElementById('serviceDate');
    const serviceTypeSelect = document.getElementById('serviceType');
    const totalPresentBadge = document.getElementById('totalPresentCount');
    const quickAddModal = document.getElementById('quickAddModal');
    const quickAddForm = document.getElementById('quickAddForm');
    const openQuickAddBtn = document.getElementById('openQuickAddBtn');
    const closeQuickAddBtn = document.getElementById('closeQuickAddBtn');
    const cancelQuickAddBtn = document.getElementById('cancelQuickAddBtn');

    // Web Audio Synthesizer for instant check-in audio chime (No external audio file needed!)
    let audioCtx = null;
    function playChime(success = true) {
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);

            if (success) {
                // High joyful two-tone chime
                osc.type = 'sine';
                osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
                osc.frequency.setValueAtTime(880.00, audioCtx.currentTime + 0.1); // A5
                gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
                osc.start(audioCtx.currentTime);
                osc.stop(audioCtx.currentTime + 0.35);
            } else {
                // Low soft blip for undo
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(329.63, audioCtx.currentTime); // E4
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.2);
                osc.start(audioCtx.currentTime);
                osc.stop(audioCtx.currentTime + 0.2);
            }
        } catch (e) {
            console.debug('Audio not supported or permitted yet', e);
        }
    }

    // Live Instant Filter / Search
    if (searchInput) {
        searchInput.focus();

        // Keyboard shortcut: pressing '/' focuses the search box
        window.addEventListener('keydown', function(e) {
            if (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });

        searchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            const rows = tableBody.querySelectorAll('tr.member-row');
            let visibleCount = 0;

            rows.forEach(row => {
                const name = row.getAttribute('data-name') || '';
                const phone = row.getAttribute('data-phone') || '';
                const code = row.getAttribute('data-code') || '';
                const dept = row.getAttribute('data-dept') || '';

                if (!query || name.includes(query) || phone.includes(query) || code.includes(query) || dept.includes(query)) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            const noMatchRow = document.getElementById('noMatchRow');
            if (noMatchRow) {
                noMatchRow.style.display = (visibleCount === 0 && query !== '') ? '' : 'none';
            }
        });
    }

    // Handle Service Date and Service Type Change
    if (serviceDateInput) {
        serviceDateInput.addEventListener('change', function () {
            const date = this.value;
            const type = serviceTypeSelect ? serviceTypeSelect.value : 'Sunday Service';
            window.location.href = `/attendance/checkin?date=${encodeURIComponent(date)}&service_type=${encodeURIComponent(type)}`;
        });
    }

    if (serviceTypeSelect) {
        serviceTypeSelect.addEventListener('change', function () {
            const type = this.value;
            const date = serviceDateInput ? serviceDateInput.value : '';
            window.location.href = `/attendance/checkin?date=${encodeURIComponent(date)}&service_type=${encodeURIComponent(type)}`;
        });
    }

    // Check-in Toggle Click Handler (Delegated)
    if (tableBody) {
        tableBody.addEventListener('click', function (e) {
            const btn = e.target.closest('.btn-checkin');
            if (!btn) return;

            const memberId = btn.getAttribute('data-id');
            const serviceDate = serviceDateInput.value;
            const serviceType = serviceTypeSelect ? serviceTypeSelect.value : 'Sunday Service';

            btn.disabled = true;
            btn.innerHTML = `<span class="spinner"></span> Updating...`;

            fetch('/attendance/api/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    member_id: memberId,
                    service_date: serviceDate,
                    service_type: serviceType
                })
            })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                if (data.success) {
                    const row = btn.closest('tr');
                    const timeCell = row.querySelector('.check-time-cell');

                    if (data.is_present) {
                        btn.classList.add('is-present');
                        btn.innerHTML = `<i class="bi bi-check-circle-fill"></i> Present`;
                        if (timeCell) {
                            timeCell.innerHTML = `<span class="badge badge-success">${data.check_in_time}</span>`;
                        }
                        playChime(true);
                        showToast(data.message, 'success');
                    } else {
                        btn.classList.remove('is-present');
                        btn.innerHTML = `<i class="bi bi-circle"></i> Mark Present`;
                        if (timeCell) {
                            timeCell.innerHTML = `<span class="badge badge-gray">—</span>`;
                        }
                        playChime(false);
                        showToast(data.message, 'info');
                    }

                    // Update live total counter badge
                    if (totalPresentBadge && data.total_present !== undefined) {
                        totalPresentBadge.innerText = data.total_present;
                    }
                } else {
                    showToast(data.message || 'Check-in failed', 'danger');
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = `<i class="bi bi-circle"></i> Mark Present`;
                showToast('Network error during check-in', 'danger');
                console.error(err);
            });
        });
    }

    // Modal Opening & Closing
    function openModal() {
        if (quickAddModal) {
            quickAddModal.classList.add('active');
            const firstInput = quickAddModal.querySelector('input[name="full_name"]');
            if (firstInput) setTimeout(() => firstInput.focus(), 150);
        }
    }

    function closeModal() {
        if (quickAddModal) {
            quickAddModal.classList.remove('active');
            if (quickAddForm) quickAddForm.reset();
        }
    }

    if (openQuickAddBtn) openQuickAddBtn.addEventListener('click', openModal);
    if (closeQuickAddBtn) closeQuickAddBtn.addEventListener('click', closeModal);
    if (cancelQuickAddBtn) cancelQuickAddBtn.addEventListener('click', closeModal);

    // Close on clicking backdrop
    if (quickAddModal) {
        quickAddModal.addEventListener('click', function (e) {
            if (e.target === quickAddModal) closeModal();
        });
    }

    // Modal Form Submission via AJAX (Instant Add & Check-in)
    if (quickAddForm) {
        quickAddForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const submitBtn = quickAddForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = 'Registering...';

            const formData = new FormData(quickAddForm);

            fetch('/attendance/quick-add', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Register & Mark Present';

                if (data.success && data.member) {
                    closeModal();
                    showToast(data.message, 'success');
                    playChime(true);

                    // Insert the new member row at the top of the table
                    const m = data.member;
                    const newRow = document.createElement('tr');
                    newRow.className = 'member-row';
                    newRow.setAttribute('data-name', m.full_name.toLowerCase());
                    newRow.setAttribute('data-phone', m.phone.toLowerCase());
                    newRow.setAttribute('data-code', m.member_code.toLowerCase());
                    newRow.setAttribute('data-dept', m.department.toLowerCase());
                    newRow.style.backgroundColor = '#ecfdf5'; // slight highlight

                    newRow.innerHTML = `
                        <td style="font-weight: 700; color: #1e3e62;">${m.member_code}</td>
                        <td>
                            <div style="font-weight: 700; color: #0f172a; font-size: 14.5px;">${m.full_name}</div>
                            <div style="font-size: 11.5px; color: #64748b;">${m.address || 'Address pending'}</div>
                        </td>
                        <td>
                            <a href="tel:${m.phone}" style="color: #2563eb; text-decoration: none; font-weight: 600;">${m.phone || '—'}</a>
                        </td>
                        <td><span class="badge badge-gold">${m.department || 'New Member'}</span></td>
                        <td><span class="badge badge-warning">${m.status || 'First-Timer'}</span></td>
                        <td class="check-time-cell text-center"><span class="badge badge-success">Just Now</span></td>
                        <td class="text-center">
                            <button class="btn-checkin is-present" data-id="${m.id}">
                                <i class="bi bi-check-circle-fill"></i> Present
                            </button>
                        </td>
                    `;

                    tableBody.insertBefore(newRow, tableBody.firstChild);

                    // Increment present counter
                    if (totalPresentBadge) {
                        const current = parseInt(totalPresentBadge.innerText) || 0;
                        totalPresentBadge.innerText = current + 1;
                    }
                } else {
                    showToast(data.message || 'Registration failed', 'danger');
                }
            })
            .catch(err => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Register & Mark Present';
                showToast('Error registering new attendee', 'danger');
                console.error(err);
            });
        });
    }
});

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toastNotificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastNotificationContainer';
        container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `flash-alert flash-${type}`;
    toast.style.cssText = 'min-width: 280px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.15); margin: 0;';
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}
