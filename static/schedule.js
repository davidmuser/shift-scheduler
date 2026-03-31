/* Schedule Page JavaScript - Handle scheduling and results */

// Keep the last batch of solutions so we can switch between k variations
let LAST_SOLUTIONS = [];
let SELECTED_SOLUTION_INDEX = 0;
// Start with editing enabled so managers can immediately tweak assignments
// on generated schedules without having to toggle a separate mode.
let EDIT_MODE = true;
// List of all workers and mapping from shift_id -> workers who offered
// (expressed interest in) that shift. Populated from /api/schedule.
let ALL_WORKERS = [];
let INTERESTED_BY_SHIFT = {};

// Session context (business/role) comes from hidden element on the page
const sessionContextEl = document.getElementById('sessionContext');
const SESSION_CONTEXT = {
    business: sessionContextEl?.dataset?.business || '',
    role: sessionContextEl?.dataset?.role || ''
};

// Initialize interest sections after DOM ready
document.addEventListener('DOMContentLoaded', () => {
    refreshInterestSections();
});

// Update weight value display when slider changes
document.querySelectorAll('.slider').forEach(slider => {
    slider.addEventListener('input', (e) => {
        const valueSpan = e.target.nextElementSibling;
        if (valueSpan && valueSpan.classList.contains('weight-value')) {
            valueSpan.textContent = e.target.value;
        }
    });
});

async function refreshInterestSections() {
    const workerSection = document.getElementById('workerInterestSection');
    const managerSection = document.getElementById('managerInterestSection');
    const info = document.getElementById('interestInfo');

    if (SESSION_CONTEXT.role === 'Worker') {
        workerSection?.classList.remove('hidden');
        managerSection?.classList.add('hidden');
        info?.classList.remove('hidden');
        info.textContent = 'You are signed in as a Worker. Mark shifts you want and the solver will prioritize only those choices.';
        await loadWorkerShiftInterests();
    } else if (SESSION_CONTEXT.role === 'Manager') {
        managerSection?.classList.remove('hidden');
        workerSection?.classList.add('hidden');
        info?.classList.remove('hidden');
        info.textContent = 'Manager view. See which shifts have interested workers before running the solver.';
        await loadManagerInterestDashboard();
    } else {
        workerSection?.classList.add('hidden');
        managerSection?.classList.add('hidden');
    }
}

async function loadWorkerShiftInterests() {
    const listEl = document.getElementById('workerShiftsList');
    if (!listEl) return;

    try {
        const [shiftsResp, myResp] = await Promise.all([
            fetch('/api/shifts'),
            fetch('/api/shift-interests/me')
        ]);

        if (!shiftsResp.ok) {
            listEl.innerHTML = '<div class="empty-list">Unable to load shifts.</div>';
            return;
        }
        const shifts = await shiftsResp.json();

        let myInterests = { shift_ids: [] };
        if (myResp.ok) {
            myInterests = await myResp.json();
        }
        const interestedSet = new Set(myInterests.shift_ids || []);

        if (!shifts.length) {
            listEl.innerHTML = '<div class="empty-list">No shifts available yet.</div>';
            return;
        }

        listEl.innerHTML = shifts.map(shift => {
            const isInterested = interestedSet.has(shift.id);
            const skills = Array.isArray(shift.required_skills)
                ? shift.required_skills.join(', ')
                : (Array.isArray(shift.required_skills_objects) ? shift.required_skills_objects.map(s => s.name).join(', ') : '');
            const btnLabel = isInterested ? 'Withdraw' : "I'm interested";
            const btnClass = isInterested ? 'btn btn-secondary' : 'btn btn-primary';
            return `
                <div class="list-item">
                    <div class="list-item-content">
                        <div class="list-item-title">${formatDate(shift.date)} • ${formatTime(shift.start_time)}-${formatTime(shift.end_time)}</div>
                        <div class="list-item-detail">
                            Needed: ${shift.required_workers} • Multiplier: ${shift.hourly_rate_multiplier}x ${skills ? '• Skills: ' + skills : ''}
                        </div>
                    </div>
                    <div class="list-item-actions">
                        <button class="${btnClass}" data-shift="${shift.id}" onclick="toggleInterest(${shift.id}, ${isInterested})">${btnLabel}</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Load worker interests failed', err);
        listEl.innerHTML = '<div class="empty-list">Could not load shifts.</div>';
    }
}

async function loadManagerInterestDashboard() {
    const listEl = document.getElementById('managerInterestList');
    if (!listEl) return;
    try {
        const resp = await fetch('/api/shift-interests');
        if (!resp.ok) {
            listEl.innerHTML = '<div class="empty-list">No interest data yet.</div>';
            return;
        }
        const data = await resp.json();
        if (!data.length) {
            listEl.innerHTML = '<div class="empty-list">No interests recorded yet.</div>';
            return;
        }
        listEl.innerHTML = data.map(row => `
            <div class="list-item">
                <div class="list-item-content">
                    <div class="list-item-title">${formatDate(row.date)} • ${formatTime(row.start_time)}-${formatTime(row.end_time)}</div>
                    <div class="list-item-detail">Interested workers (${row.count}): ${row.interested_workers.join(', ')}</div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Load manager interests failed', err);
        listEl.innerHTML = '<div class="empty-list">Could not load interest data.</div>';
    }
}

async function toggleInterest(shiftId, currentlyInterested) {
    try {
        const method = currentlyInterested ? 'DELETE' : 'POST';
        const resp = await fetch(`/api/shifts/${shiftId}/interest`, { method });
        if (!resp.ok) {
            const err = await resp.json();
            alert(err.error || 'Unable to update interest');
            return;
        }
        await refreshInterestSections();
    } catch (err) {
        console.error('Toggle interest failed', err);
        alert('Could not update interest.');
    }
}

// Handle schedule form submission
document.getElementById('scheduleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Show loading state
    document.getElementById('scheduleForm').style.display = 'none';
    document.getElementById('loadingState').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    
    try {
        // Collect form data
        const topK = document.getElementById('topK').value;
        const weights = {
            time_off_request_weight: parseFloat(document.getElementById('timeOffWeight').value),
            seniority_reward_weight: parseFloat(document.getElementById('seniorityWeight').value),
            weekend_balance_weight: parseFloat(document.getElementById('weekendWeight').value),
            skill_matching_weight: parseFloat(document.getElementById('skillWeight').value),
            workload_balance_weight: parseFloat(document.getElementById('workloadWeight').value),
            compensation_minimization_weight: parseFloat(document.getElementById('payWeight').value),
            overstaffing_penalty_weight: parseFloat(document.getElementById('overstaffingWeight')?.value || '3')
        };
        
        // Make API call
        const response = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ top_k: topK, weights: weights })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to generate schedule');
        }
        
        // Display results
        displayResults(result);
        
    } catch (error) {
        console.error('Error generating schedule:', error);
        showError(error.message);
    } finally {
        // Hide loading state
        document.getElementById('loadingState').classList.add('hidden');
        document.getElementById('scheduleForm').style.display = 'block';
    }
});

// Display scheduling results
function displayResults(data) {
    LAST_SOLUTIONS = Array.isArray(data.solutions) ? data.solutions : [];
    ALL_WORKERS = Array.isArray(data.workers) ? data.workers : [];
    INTERESTED_BY_SHIFT = data.interested_by_shift || {};
    SELECTED_SOLUTION_INDEX = 0;

    // Show results section
    document.getElementById('resultsSection').classList.remove('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    
    // Update summary
    const summary = data.summary;
    document.getElementById('resultsSummary').innerHTML = `
        ✅ Successfully generated <strong>${LAST_SOLUTIONS.length}</strong> schedule options 
        for <strong>${summary.total_workers}</strong> workers and <strong>${summary.total_shifts}</strong> shifts
    `;

    // Build solution selector pills so managers can quickly compare k options
    const selector = document.getElementById('solutionSelector');
    if (selector) {
        if (LAST_SOLUTIONS.length > 1) {
            selector.classList.remove('hidden');
            selector.innerHTML = LAST_SOLUTIONS.map((solution, index) => `
                <button class="solution-pill ${index === SELECTED_SOLUTION_INDEX ? 'selected' : ''}" data-index="${index}">
                    <span class="solution-pill-title">Option ${solution.rank}</span>
                    <span class="solution-pill-score">Score ${solution.objective_value.toFixed(2)}</span>
                    ${index === 0 ? '<span class="badge badge-best">Best</span>' : ''}
                </button>
            `).join('');

            selector.querySelectorAll('.solution-pill').forEach(btn => {
                btn.addEventListener('click', () => {
                    const idx = parseInt(btn.dataset.index || '0', 10) || 0;
                    setSelectedSolution(idx);
                });
            });
        } else {
            selector.classList.add('hidden');
            selector.innerHTML = '';
        }
    }

    // Render the initially selected solution (best option by default)
    setSelectedSolution(SELECTED_SOLUTION_INDEX);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Build <option> tags for the worker-select dropdown on an assignment row,
// including an unresolved option and marking workers who offered this shift.
function buildWorkerOptionsMarkup(shiftId, currentWorkerId) {
    const sidStr = String(shiftId || '');
    const interestedRaw = INTERESTED_BY_SHIFT[sidStr] || INTERESTED_BY_SHIFT[shiftId] || [];
    const interestedSet = new Set(interestedRaw.map(v => String(v)));

    let options = '';
    options += '<option value="">-- keep as is --</option>';
    options += '<option value="__unresolved">Unresolved (no one assigned)</option>';
    options += '<option value="__unresolved_with_comment">Unresolved with comment…</option>';

    ALL_WORKERS.forEach(w => {
        const widStr = String(w.id);
        const labelSuffix = interestedSet.has(widStr) ? ' (offered)' : '';
        const selected = String(currentWorkerId || '') === widStr ? ' selected' : '';
        options += `<option value="${widStr}"${selected}>${escapeHtml(w.name)}${labelSuffix}</option>`;
    });

    return options;
}

// Render the currently selected solution card and its Gantt chart
function setSelectedSolution(index) {
    if (!LAST_SOLUTIONS.length) return;
    if (index < 0 || index >= LAST_SOLUTIONS.length) {
        index = 0;
    }
    SELECTED_SOLUTION_INDEX = index;

    const selector = document.getElementById('solutionSelector');
    if (selector) {
        selector.querySelectorAll('.solution-pill').forEach((btn, idx) => {
            btn.classList.toggle('selected', idx === SELECTED_SOLUTION_INDEX);
        });
    }

    const solution = LAST_SOLUTIONS[SELECTED_SOLUTION_INDEX];
    const container = document.getElementById('solutionsContainer');
    if (container) {
        container.innerHTML = renderSolutionDetailCard(solution);
        // Wire up editing interactions (clicking on status pills) for this solution
        attachAssignmentEditHandlers(SELECTED_SOLUTION_INDEX);
    }

    const ganttContainer = document.getElementById('ganttContainer');
    if (ganttContainer) {
        ganttContainer.innerHTML = '';
        const chart = buildGanttForSolution(solution);
        ganttContainer.appendChild(chart);
    }
}

// Build a nicely grouped card for a single solution, organized by day
function renderSolutionDetailCard(solution) {
    const assignments = Array.isArray(solution.assignments) ? [...solution.assignments] : [];

    assignments.sort((a, b) => {
        const ad = (a.shift_date || '').localeCompare(b.shift_date || '');
        if (ad !== 0) return ad;
        return (a.shift_start || '').localeCompare(b.shift_start || '');
    });

    const groupedByDate = {};
    assignments.forEach(a => {
        const key = a.shift_date || 'Unknown date';
        if (!groupedByDate[key]) groupedByDate[key] = [];
        groupedByDate[key].push(a);
    });

    const dateKeys = Object.keys(groupedByDate).sort();

    const daysMarkup = dateKeys.map(dateKey => {
        const dayAssignments = groupedByDate[dateKey];
        const itemsMarkup = dayAssignments.map(assignment => {
            const optionsMarkup = buildWorkerOptionsMarkup(assignment.shift_id, assignment.worker_id);
            const sid = assignment.shift_id || '';
            const sidStr = String(sid);
            const unresolvedComment = (solution._unresolvedComments && solution._unresolvedComments[sidStr]) || '';

            return `
                <div class="assignment-item ${assignment.is_assigned ? 'assigned' : 'not-assigned'}" 
                     data-worker-id="${assignment.worker_id || ''}" 
                     data-worker-name="${assignment.worker_name || ''}" 
                     data-shift-id="${sid}">
                    <div class="assignment-main">
                        <span class="assignment-worker">${assignment.worker_name}</span>
                        <span class="assignment-status-pill">${assignment.is_assigned ? 'Assigned' : 'Not assigned'}</span>
                        <select class="assignment-worker-select" data-shift-id="${sid}">
                            ${optionsMarkup}
                        </select>
                    </div>
                    <div class="assignment-meta">
                        <span>${formatTime(assignment.shift_start)}–${formatTime(assignment.shift_end)}</span>
                        ${assignment.shift_id ? `<span class="assignment-shift-id">Shift #${assignment.shift_id}</span>` : ''}
                        ${unresolvedComment ? `<span class="assignment-comment">Unresolved: ${escapeHtml(unresolvedComment)}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="solution-day-group">
                <div class="solution-day-header">
                    <span class="solution-day-label">${formatDate(dateKey)}</span>
                    <span class="solution-day-count">${dayAssignments.length} assignments</span>
                </div>
                <div class="solution-day-assignments">
                    ${itemsMarkup}
                </div>
            </div>
        `;
    }).join('');

    const totalAssignments = assignments.length;

    return `
        <div class="solution-card solution-card-selected">
            <div class="solution-card-header">
                <div>
                    <h3>Option ${solution.rank}</h3>
                    <p class="solution-subtitle">Objective score ${solution.objective_value.toFixed(2)}</p>
                </div>
                <div class="solution-meta">
                    ${solution._edited ? '<span class="badge badge-edited">Edited</span>' : '<span class="badge badge-best">Selected</span>'}
                    <span class="solution-count-badge">${totalAssignments} assignments</span>
                </div>
            </div>
            ${daysMarkup || '<p class="empty-list">No assignments in this option.</p>'}
        </div>
    `;
}

// Attach click handlers to each assignment status pill so managers can
// toggle Assigned/Not assigned while in EDIT_MODE.
function attachAssignmentEditHandlers(solutionIndex) {
    const container = document.getElementById('solutionsContainer');
    if (!container) return;

    const items = container.querySelectorAll('.assignment-item');
    items.forEach(item => {
        const statusEl = item.querySelector('.assignment-status-pill');
        if (!statusEl) return;

        const workerIdAttr = item.getAttribute('data-worker-id') || '';
        const workerNameAttr = item.getAttribute('data-worker-name') || '';
        const shiftIdAttr = item.getAttribute('data-shift-id') || '';

        statusEl.addEventListener('click', () => {
            if (!EDIT_MODE) return; // only editable when edit mode is enabled
            toggleAssignmentForSolution(
                solutionIndex,
                {
                    workerId: workerIdAttr,
                    workerName: workerNameAttr,
                    shiftId: shiftIdAttr
                },
                item,
                statusEl
            );
        });

        const workerSelect = item.querySelector('.assignment-worker-select');
        if (workerSelect) {
            workerSelect.addEventListener('change', () => {
                const selected = workerSelect.value;
                if (!EDIT_MODE || !selected) {
                    // If editing is disabled or user chose the placeholder, reset dropdown
                    return;
                }
                handleWorkerSelectChange(solutionIndex, {
                    shiftId: shiftIdAttr,
                    selectedWorkerId: selected
                });
            });
        }
    });
}

// Handle selection of a different worker (or unresolved) for a given shift
// within a specific solution. This updates the underlying assignments and
// re-renders the solution card and Gantt so everything stays consistent.
function handleWorkerSelectChange(solutionIndex, payload) {
    const solution = LAST_SOLUTIONS[solutionIndex];
    if (!solution || !Array.isArray(solution.assignments)) return;

    const { shiftId, selectedWorkerId } = payload;
    const sidStr = String(shiftId || '');

    // Unresolved variants: clear all assignments for this shift
    if (selectedWorkerId === '__unresolved' || selectedWorkerId === '__unresolved_with_comment') {
        solution.assignments.forEach(a => {
            if (String(a.shift_id) === sidStr) {
                a.is_assigned = false;
            }
        });

        solution._unresolvedComments = solution._unresolvedComments || {};
        if (selectedWorkerId === '__unresolved_with_comment') {
            const comment = window.prompt('Add a note for this unresolved shift (optional):', solution._unresolvedComments[sidStr] || '');
            solution._unresolvedComments[sidStr] = comment || '';
        } else {
            // plain unresolved clears any existing comment
            solution._unresolvedComments[sidStr] = '';
        }

        solution._edited = true;
        // Re-render the current solution and Gantt chart
        setSelectedSolution(solutionIndex);
        return;
    }

    // Assign to a specific worker: there is only one ScheduleAssignment per
    // (shift_id, worker_id) in the original solver output, so when the
    // manager picks a different worker we repoint the existing assignment
    // object to that worker instead of looking for a pre-existing row.

    // Clear previous assignment flags for this shift id
    solution.assignments.forEach(a => {
        if (String(a.shift_id) === sidStr) {
            a.is_assigned = false;
        }
    });

    // Find the assignment object for this shift (there should be at least one)
    const target = solution.assignments.find(a => String(a.shift_id) === sidStr);
    if (!target) {
        // No matching shift in this solution; nothing to update.
        return;
    }

    // Look up the chosen worker so we can set both id and name
    const worker = ALL_WORKERS.find(w => String(w.id) === String(selectedWorkerId));
    if (worker) {
        target.worker_id = worker.id;
        target.worker_name = worker.name;
    } else {
        // Fallback: at least update the id
        target.worker_id = selectedWorkerId;
    }
    target.is_assigned = true;
    solution._edited = true;

    // Clearing any unresolved comment now that the shift is explicitly assigned
    if (solution._unresolvedComments && solution._unresolvedComments[sidStr]) {
        solution._unresolvedComments[sidStr] = '';
    }

    setSelectedSolution(solutionIndex);
}

// Flip the is_assigned flag for a specific assignment within a solution,
// update the DOM classes/text, and refresh the Gantt view so everything
// stays in sync with the edited schedule.
function toggleAssignmentForSolution(solutionIndex, identity, itemEl, statusEl) {
    const solution = LAST_SOLUTIONS[solutionIndex];
    if (!solution || !Array.isArray(solution.assignments)) return;

    const { workerId, workerName, shiftId } = identity;
    let assignment = null;

    // Try to match using numeric worker_id + shift_id when available.
    const workerIdNum = workerId && !Number.isNaN(parseInt(workerId, 10)) ? parseInt(workerId, 10) : null;
    const shiftIdNum = shiftId && !Number.isNaN(parseInt(shiftId, 10)) ? parseInt(shiftId, 10) : null;

    if (workerIdNum !== null && shiftIdNum !== null) {
        assignment = solution.assignments.find(a =>
            String(a.worker_id) === String(workerIdNum) &&
            String(a.shift_id) === String(shiftIdNum)
        );
    }

    // Fallback for cases where worker_id isn't present in the JSON
    if (!assignment && shiftId) {
        assignment = solution.assignments.find(a =>
            String(a.shift_id) === String(shiftId) &&
            String(a.worker_name || '') === String(workerName || '')
        );
    }

    if (!assignment) return;

    assignment.is_assigned = !assignment.is_assigned;
    solution._edited = true;

    itemEl.classList.toggle('assigned', assignment.is_assigned);
    itemEl.classList.toggle('not-assigned', !assignment.is_assigned);
    statusEl.textContent = assignment.is_assigned ? 'Assigned' : 'Not assigned';

    // Rebuild the Gantt chart to reflect the updated assignment pattern
    const ganttContainer = document.getElementById('ganttContainer');
    if (ganttContainer) {
        ganttContainer.innerHTML = '';
        const chart = buildGanttForSolution(solution);
        ganttContainer.appendChild(chart);
    }
}

// Build a Gantt chart DOM element for one solution, using a one-week day-based view
function buildGanttForSolution(solution) {
    const assignments = solution.assignments || [];

    // Group assigned shifts by worker and collect distinct shift dates
    const workerMap = new Map();
    const dateSet = new Set();

    assignments.forEach(a => {
        // Only visualize shifts that are actually assigned
        if (!a.shift_date || a.is_assigned === false) return;
        const worker = a.worker_name || (`ID ${a.worker_id}`);
        if (!workerMap.has(worker)) workerMap.set(worker, []);
        workerMap.get(worker).push(a);
        dateSet.add(a.shift_date);
    });

    if (!dateSet.size) {
        const empty = document.createElement('div');
        empty.className = 'gantt-card';
        empty.textContent = `Solution ${solution.rank} \\u2014 no assignments`;
        return empty;
    }

    // Determine a one-week window starting from the earliest shift date
    const dateList = Array.from(dateSet)
        .map(d => new Date(d + 'T00:00:00'))
        .sort((a, b) => a - b);

    const weekStart = new Date(dateList[0]);
    weekStart.setHours(0, 0, 0, 0);

    const days = [];
    for (let i = 0; i < 7; i++) {
        const d = new Date(weekStart);
        d.setDate(weekStart.getDate() + i);
        days.push(d);
    }

    // Precompute per-day metadata: weekend flag, today flag, and shift counts
    const dateCounts = {};
    assignments.forEach(a => {
        if (!a.shift_date) return;
        dateCounts[a.shift_date] = (dateCounts[a.shift_date] || 0) + 1;
    });

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const dayMeta = days.map(d => {
        const dateStr = d.toISOString().slice(0, 10);
        const isWeekend = d.getDay() === 0 || d.getDay() === 6;
        const isToday = d.getTime() === today.getTime();
        const count = dateCounts[dateStr] || 0;
        return { dateStr, isWeekend, isToday, count };
    });

    // Container
    const card = document.createElement('div');
    card.className = 'gantt-card';

    const title = document.createElement('h3');
    const weekEnd = days[days.length - 1];
    title.textContent = `Option ${solution.rank} — Week of ${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}–${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    card.appendChild(title);

    // Day-of-week header
    const header = document.createElement('div');
    header.className = 'gantt-header';
    days.forEach((d, idx) => {
        const meta = dayMeta[idx];
        const cell = document.createElement('div');
        cell.className = 'gantt-time-cell';
        if (meta.isWeekend) cell.classList.add('weekend');
        if (meta.isToday) cell.classList.add('today');

        const label = document.createElement('div');
        label.className = 'gantt-day-label';
        label.textContent = d.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });

        const count = document.createElement('div');
        count.className = 'gantt-day-count';
        count.textContent = meta.count ? `${meta.count} shift${meta.count === 1 ? '' : 's'}` : 'No shifts';

        cell.appendChild(label);
        cell.appendChild(count);
        header.appendChild(cell);
    });
    card.appendChild(header);

    // Small legend to clarify the weekly view semantics
    const legend = document.createElement('p');
    legend.className = 'gantt-legend';
    legend.textContent = 'Each row is a worker; colored blocks show the shifts they were assigned this week.';
    card.appendChild(legend);

    // Grid container
    const grid = document.createElement('div');
    grid.className = 'gantt-grid';

    // For each worker, create a row with 7 day cells and place bars into the correct day
    workerMap.forEach((tasks, worker) => {
        const row = document.createElement('div');
        row.className = 'gantt-row';

        const label = document.createElement('div');
        label.className = 'gantt-worker-label';
        label.textContent = worker;
        row.appendChild(label);

        const timeline = document.createElement('div');
        timeline.className = 'gantt-timeline';
        timeline.style.gridTemplateColumns = `repeat(${days.length}, 1fr)`;

        // Create 7 day cells
        const dayCells = [];
        for (let i = 0; i < days.length; i++) {
            const meta = dayMeta[i];
            const cell = document.createElement('div');
            cell.className = 'gantt-cell';
            if (meta.isWeekend) cell.classList.add('weekend');
            if (meta.isToday) cell.classList.add('today');
            timeline.appendChild(cell);
            dayCells.push(cell);
        }

        // Place a bar in the cell for the matching day
        tasks.forEach(t => {
            if (!t.shift_date) return;
            const dateObj = new Date(t.shift_date + 'T00:00:00');
            dateObj.setHours(0, 0, 0, 0);
            const dayIndex = Math.round((dateObj - weekStart) / (1000 * 60 * 60 * 24));
            if (dayIndex < 0 || dayIndex >= days.length) return; // outside this week window

            const bar = document.createElement('div');
            bar.className = 'gantt-bar';
            bar.title = `${formatDate(t.shift_date)} ${formatTime(t.shift_start)}-${formatTime(t.shift_end)}\n${t.worker_name}`;

            const workerLabel = document.createElement('div');
            workerLabel.className = 'gantt-bar-worker';
            workerLabel.textContent = t.worker_name || `ID ${t.worker_id}`;

            const timeLabel = document.createElement('div');
            timeLabel.className = 'gantt-bar-time';
            timeLabel.textContent = `${formatTime(t.shift_start)}–${formatTime(t.shift_end)}`;

            bar.appendChild(workerLabel);
            bar.appendChild(timeLabel);

            dayCells[dayIndex].appendChild(bar);
        });

        row.appendChild(timeline);
        grid.appendChild(row);
    });

    card.appendChild(grid);
    return card;
}

// Parse assignment date/time into a Date object; supports time-only or ISO datetime
function parseAssignmentDateTime(dateStr, timeStr) {
    if (!dateStr && timeStr && timeStr.includes('T')) return new Date(timeStr);
    if (timeStr && timeStr.includes('T')) return new Date(timeStr);
    // timeStr likely 'HH:MM' or 'HH:MM:SS'
    const t = (timeStr || '').substring(0,5);
    const iso = `${dateStr}T${t}:00`;
    return new Date(iso);
}

// Show error message
function showError(message) {
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('errorMessage').textContent = message;
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Format time for display
function formatTime(timeString) {
    const time = timeString.substring(0, 5);
    const [hours, minutes] = time.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

// Download results as CSV
document.getElementById('downloadBtn').addEventListener('click', () => {
    if (!LAST_SOLUTIONS.length) {
        alert('No schedules available to download yet.');
        return;
    }

    let csv = 'Solution,Worker,Date,Start Time,End Time,Assigned\n';

    LAST_SOLUTIONS.forEach((solution, solutionIndex) => {
        const assignments = Array.isArray(solution.assignments) ? solution.assignments : [];
        assignments.forEach(assignment => {
            const date = assignment.shift_date || '';
            const startTime = assignment.shift_start || '';
            const endTime = assignment.shift_end || '';
            const worker = assignment.worker_name || '';
            const status = assignment.is_assigned ? 'Assigned' : 'Not assigned';
            csv += `${solutionIndex + 1},"${worker}","${date}","${startTime}","${endTime}","${status}"\n`;
        });
    });
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `schedule_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
});

// Toggle edit mode so managers can tweak assignments inside a generated option
document.addEventListener('DOMContentLoaded', () => {
    const editBtn = document.getElementById('toggleEditBtn');
    if (!editBtn) return;

    const updateButtonState = () => {
        if (EDIT_MODE) {
            editBtn.textContent = '✅ Editing Enabled';
        } else {
            editBtn.textContent = '✏️ Enable Editing';
        }
    };

    updateButtonState();

    editBtn.addEventListener('click', () => {
        EDIT_MODE = !EDIT_MODE;
        updateButtonState();

        // Re-render current solution to ensure edited badge/state is shown
        if (LAST_SOLUTIONS.length) {
            setSelectedSolution(SELECTED_SOLUTION_INDEX);
        }
    });
});

// Publish the currently selected schedule option so workers can see it
// and the period becomes locked for availability changes.
document.addEventListener('DOMContentLoaded', () => {
    const publishBtn = document.getElementById('publishBtn');
    if (!publishBtn) return;

    publishBtn.addEventListener('click', async () => {
        if (!LAST_SOLUTIONS.length) {
            alert('No schedule to publish yet. Generate a schedule first.');
            return;
        }

        const solution = LAST_SOLUTIONS[SELECTED_SOLUTION_INDEX] || LAST_SOLUTIONS[0];
        const payload = {
            solution: {
                rank: solution.rank,
                objective_value: solution.objective_value,
                assignments: Array.isArray(solution.assignments) ? solution.assignments : [],
                unresolved_comments: solution._unresolvedComments || {}
            }
        };

        publishBtn.disabled = true;
        publishBtn.textContent = 'Publishing...';
        try {
            const resp = await fetch('/api/schedule/publish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || data.message || 'Failed to publish schedule');
            }

            alert(data.message || 'Schedule published and locked.');
        } catch (err) {
            console.error('Publish schedule failed', err);
            alert(err.message || 'Failed to publish schedule.');
        } finally {
            publishBtn.disabled = false;
            publishBtn.textContent = '📣 Publish Selected Schedule';
        }
    });
});

// Create new schedule
document.getElementById('newScheduleBtn').addEventListener('click', () => {
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('scheduleForm').style.display = 'block';
    window.scrollTo(0, 0);
});

// Load default weights on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/default-weights');
        const weights = await response.json();
        
        // Update sliders and values using API field names
        document.getElementById('timeOffWeight').value = weights.respect_time_off_requests;
        document.getElementById('timeOffWeight').nextElementSibling.textContent = weights.respect_time_off_requests;
        
        document.getElementById('seniorityWeight').value = weights.reward_seniority;
        document.getElementById('seniorityWeight').nextElementSibling.textContent = weights.reward_seniority;
        
        document.getElementById('weekendWeight').value = weights.balance_weekend_shifts;
        document.getElementById('weekendWeight').nextElementSibling.textContent = weights.balance_weekend_shifts;
        
        document.getElementById('skillWeight').value = weights.reward_skill_matching;
        document.getElementById('skillWeight').nextElementSibling.textContent = weights.reward_skill_matching;
        
        document.getElementById('workloadWeight').value = weights.balance_workload;
        document.getElementById('workloadWeight').nextElementSibling.textContent = weights.balance_workload;
        
        document.getElementById('payWeight').value = weights.minimize_compensation;
        document.getElementById('payWeight').nextElementSibling.textContent = weights.minimize_compensation;

        const overstaffEl = document.getElementById('overstaffingWeight');
        if (overstaffEl) {
            overstaffEl.value = weights.minimize_overstaffing;
            overstaffEl.nextElementSibling.textContent = weights.minimize_overstaffing;
        }
    } catch (error) {
        console.error('Error loading default weights:', error);
    }
});
