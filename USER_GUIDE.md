# Shift Scheduler – User Guide

This guide is for **non-technical users** (managers and workers) who want to run the web interface and generate schedules without touching code.

---

## 1. What You Can Do

With the web interface you can:

- Register or join a business and keep data scoped per business
- Add workers (name, seniority, pay, skills, availability)
- Create shifts (date, time, workers needed, skill requirements, pay multiplier)
- Let workers mark which shifts they want (“I’m available” / interest)
- Generate several schedule options using sliders to set priorities
- Edit the generated options (reassign shifts, mark unresolved, add comments)
- Publish one final schedule and lock it so workers can’t change availability
- Let workers see their own published shifts in a simple view
- Download any schedule as a CSV file

---

## 2. Starting the Web App

### 2.1 One-time setup

1. Open a terminal in the project folder:

   ```bash
   cd shift-scheduler
   ```

2. (Recommended) Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or on Windows
   # venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### 2.2 Start the web interface

From the project folder:

```bash
python web_interface.py
```

You should see output similar to:

```text
🚀 Starting Shift Scheduler Web Interface...
📱 Open your browser and go to: http://localhost:5000
💡 No coding needed - just fill in the forms!
🛑 Press Ctrl+C to stop the server
```

Then open a browser and go to:

- **http://localhost:5000**

---

## 3. High-Level Flow

### As a Manager

1. Register your business / log in as manager
2. Add workers
3. Add shifts
4. (Optional) Ask workers to mark which shifts they’re interested in
5. Generate **k** schedule options and compare them
6. Edit assignments if needed
7. Publish the chosen schedule (this locks worker availability for that period)

### As a Worker

1. Use the join link from your manager to join the business
2. Log in as yourself
3. Go to the **Availability** page to mark shifts you can work
4. After the manager publishes a schedule, see your assigned shifts in the
   **Published Schedule** section

---

## 4. Manager Walkthrough

### 4.1 Register / log in

- When the interface is configured with business registration and login:
  - Use the register flow to create a business as a manager
  - Share the join link (e.g. `/join/<business_number>`) with workers
  - Workers join and are linked to your business automatically

If you are already in a manager session you will see your **business name** and role
at the top of the schedule page.

### 4.2 Add workers

1. Navigate to **“➕ Add Workers & Shifts”**.
2. In the **Workers** section, fill in:
   - **Name** – Worker’s name
   - **Seniority Level** – e.g. 1 (junior) up to higher numbers for more senior staff
   - **Hourly Rate** – Pay per hour
   - **Skills** – Optional; list any skills (ICU, cash handling, etc.)
   - **Availability / Unavailable dates** – Optional; days they can or cannot work
3. Click **“➕ Add Worker”**.
4. Repeat for each worker.

Behind the scenes, each worker also gets a login identity so they can later mark
availability and view their published shifts.

### 4.3 Add shifts

On the same **Add Workers & Shifts** page:

1. In the **Shifts** section, fill in:
   - **Date** – `YYYY-MM-DD` (or recurring weekly if supported)
   - **Start Time** – e.g. `09:00`
   - **End Time** – e.g. `17:00`
   - **Workers Needed** – how many people you need for this shift
   - **Pay Multiplier** – `1.0` normal, `1.5` for 50% extra, etc.
   - **Required Skills** – optional specific skills needed
2. Click **“📅 Add Shift”**.
3. Repeat until all shifts are created.

### 4.4 See worker interest in shifts (optional)

On the **Schedule** page, the top area shows role-specific sections:

- **Worker view** – each worker can mark interest (“I’m interested”) in specific shifts.
- **Manager view** – you can see how many workers showed interest in each shift and who.

The solver uses this interest data so that, where interest exists, it prefers
assignments among the interested workers for that shift.

### 4.5 Generate schedules

Go to **“🎯 Generate Schedule”**.

1. Set **Number of Solutions** (top-k) – how many different schedule options you want.
2. Adjust sliders to set priorities:
   - **Respect Time-Off**
   - **Reward Senior Workers**
   - **Balance Weekends**
   - **Skill Matching**
   - **Balance Workload**
   - **Minimize Cost**
   - **Avoid Overstaffing**
3. Click **“🚀 Generate Schedule”**.

You’ll see:

- A short summary of how many workers, shifts, and options were generated
- A row of **solution option pills** (Option 1, Option 2, …) when k > 1
- A detailed card for the selected option, grouped by date
- A Gantt-style chart showing who works on which days

### 4.6 Edit a generated schedule

Inside the **Generated Schedules** section:

- Use **“✏️ Enable Editing”** to toggle editing mode.
- For each assignment row you can:
  - Click the status pill (**Assigned / Not assigned**) to quickly toggle assignment
  - Use the dropdown to:
    - Reassign the shift to another worker (workers who “offered” that shift are marked)
    - Mark the shift as **“Unresolved (no one assigned)”**
    - Mark it as **“Unresolved with comment…”** and attach a note

All edits apply to the in-memory solution:

- The **detail card** updates
- The **Gantt chart** updates
- The **CSV export** and **Publish** payload include your changes

### 4.7 Publish and lock a schedule

Once you’re happy with a particular option:

1. Make sure that option is selected in the solution pills.
2. Click **“📣 Publish Selected Schedule”**.
3. The app sends the edited assignments and unresolved comments to the backend.
4. A new published schedule record is stored for your business, covering the date range
   of the assignments.
5. That published schedule is **locked**, meaning:
   - Workers can no longer change their interest/availability for shifts inside the
     published date range.

You’ll see a confirmation message with the published period.

---

## 5. Worker Walkthrough

### 5.1 Join a business

1. Get a **join link** from your manager (`/join/<business_number>`).
2. Open it in your browser and enter your name.
3. You will be linked to the manager’s business and get a worker login.

### 5.2 Mark availability / interest

1. Go to the **Availability** page.
2. You’ll see a **weekly calendar** (7 days) with shift cards.
3. For each shift card:
   - Check **“I’m available”** to show interest
   - Uncheck it to remove interest
4. Press **“Save availability”** to persist your choices.

If a manager has already **published and locked** a schedule that covers some of the
shifts in the displayed week:

- You’ll see a **lock notice** explaining the locked period.
- Checkboxes for locked shifts will be **disabled** and show “Locked by manager”.
- Attempts to change availability for locked dates are blocked by the server.

### 5.3 View your published shifts

On the **Availability** page, under the week grid, you’ll see a
**Published Schedule** card when a locked schedule exists for your business.

It shows:

- The published date range
- A list of your assigned shifts in that period:
  - `YYYY-MM-DD • HH:MM–HH:MM`

If you have no shifts in the published schedule, you’ll see a message saying so.

---

## 6. CSV Export

On the **Generated Schedules** page you can always click:

- **“📥 Download as CSV”**

This downloads all current options and their assignments as a CSV file that can be
opened in Excel or Google Sheets.

Each row includes:

- Solution number
- Worker name
- Date
- Start time
- End time
- Assigned / Not assigned

---

## 7. Tips & Troubleshooting

### 7.1 If no schedules are generated

- Make sure you have **at least one worker** and **at least one shift**.
- Confirm shifts and workers are in the same business.
- Check that there is at least one worker available and skilled enough for each shift.
- Try loosening weights or reducing top-k to start with a simpler problem.

### 7.2 If workers can’t change availability

- A manager might have **published and locked** a schedule that covers those dates.
- The availability page will show a lock banner with the locked period.
- This is expected: once locked, availability for those dates cannot be changed.

### 7.3 If the web page won’t load

- Ensure `python web_interface.py` is still running in the terminal.
- Check that you’re using `http://localhost:5000` in the browser.
- If port 5000 is in use by another app, change the port in `web_interface.py` and restart.

---

## 8. What’s Next

Once you are comfortable with the interface you can:

- Decide on default weight presets for your business
- Add more workers and shifts as your team grows
- Use the CSV export for payroll or reporting
- Work with a developer to add authentication, persistence, or integrations

You now have a complete, user-friendly shift scheduling tool that doesn’t require
any coding knowledge. Enjoy scheduling! 🎉
