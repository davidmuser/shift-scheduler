# 🌐 Web Interface - Non-Coder Friendly

A beautiful, easy-to-use web interface for shift scheduling. **No coding, no JSON files, no technical knowledge needed!**

## ✨ Features

- 🎯 **Dead Simple Interface** - Just click buttons and fill in forms
- 👥 **Easy Worker Management** - Add workers with one click
- 📅 **Simple Shift Creation** - Create shifts in seconds
- 🎨 **Beautiful Design** - Professional, modern interface
- 📊 **Interactive Scheduling** - Adjust priorities with sliders
- 📥 **Download Results** - Export schedules as CSV
- ⚡ **Real-Time Validation** - Instant feedback on errors
- 📱 **Mobile Friendly** - Works on phones and tablets

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Web Server
```bash
python web_interface.py
```

### 3. Open in Browser
Go to: **http://localhost:5000**

### 4. Register or Join a Business
- First visit `/api/register-business` via the UI (coming soon) or a POST request to create a business and manager session.
- Share the generated **join link** `/join/<business_number>` with workers so they can join and get a worker session.
- All data is scoped per-business automatically.

That's it! You're ready to schedule.

## 📖 How to Use

### Step 1: Add Workers
1. Click "➕ Add Workers & Shifts"
2. Fill in worker details:
   - **Worker Name** - Their name
   - **Seniority Level** - 1 (Entry) to 4 (Lead)
   - **Hourly Rate** - What they earn per hour
   - **Skills** - Any speceial skills (optional)
   - **Available Dates** - Days they can work (optional)
3. Click "➕ Add Worker"
4. Repeat for each team member

### Step 2: Add Shifts
1. On the same page, fill in shift details:
   - **Shift Date** - Which day
   - **Start Time** - When shift starts
   - **End Time** - When shift ends
   - **Workers Needed** - How many people
   - **Pay Multiplier** - 1.0 = normal, 1.5 = 50% extra, etc.
   - **Required Skills** - Any specific skills needed (optional)
2. Click "📅 Add Shift"
3. Repeat for each shift

### Step 3: Generate Schedule
1. Click "🎯 Generate Schedule"
2. Adjust the sliders:
   - **Respect Time-Off** - How important are days off?
   - **Reward Senior Workers** - Favor experienced staff?
   - **Balance Weekends** - Fair weekend distribution?
   - **Skill Matching** - Assign by skills?
   - **Balance Workload** - Equal shifts for all?
   - **Minimize Cost** - Lower payroll?
3. Click "🚀 Generate Schedule"
4. See multiple scheduling options!

### Step 3.5: (Optional) Collect Shift Interest
- Workers can mark "I'm interested" on specific shifts from the Schedule page (Worker view).
- Managers can see interest counts per shift on the Interest Dashboard.
- The solver automatically limits assignments to interested workers when interest exists for a shift.

### Step 4: Use the Results
- 📊 Review each solution
- 📥 Download as CSV to import elsewhere
- 🔄 Create new schedule with different priorities

## 💡 Understanding the Interface

### Workers Panel
**Who**: Your team members
**What**: Name, pay rate, skills, availability
**Why**: System needs to know who's available and qualified

### Shifts Panel
**What**: Jobs to fill
**When**: Date and time
**How Many**: People needed
**Multiplier**: Extra pay for nights/weekends? Set 1.5 for 50% extra

### Optimization Weights
**Higher number** = System cares more about this factor

Examples:
- **High "Respect Time-Off"**: Workers love when requests are honored
- **High "Reward Seniority"**: Give experienced staff preference
- **High "Balance Weekends"**: No one person gets all weekends
- **High "Minimize Cost"**: Keep payroll low (careful with this!)

## 🛠️ API Reference (For Developers)

### GET `/` 
Home page - see statistics

### GET `/setup`
Worker and shift management page

### POST `/api/workers`
Add a worker
```json
{
  "name": "John Smith",
  "seniority_level": 2,
  "hourly_rate": 20.00,
  "skills": "cash handling, customer service",
  "available_dates": "2025-03-25, 2025-03-26"
}
```

### GET `/api/workers`
Get all workers

### DELETE `/api/workers/<worker_id>`
Remove a worker

### POST `/api/shifts`
Add a shift
```json
{
  "date": "2025-03-25",
  "start_time": "09:00",
  "end_time": "17:00",
  "required_workers": 2,
  "required_skills": "cash handling",
  "hourly_rate_multiplier": 1.5
}
```

### GET `/api/shifts`
Get all shifts

### DELETE `/api/shifts/<shift_id>`
Remove a shift

### POST `/api/schedule`
Generate schedules
```json
{
  "top_k": 3,
  "weights": {
    "time_off_request_weight": 10.0,
    "seniority_reward_weight": 5.0,
    "weekend_balance_weight": 8.0,
    "skill_matching_weight": 7.0,
    "workload_balance_weight": 6.0,
    "compensation_minimization_weight": 2.0,
    "overstaffing_penalty_weight": 3.0
  }
}
```

### GET `/api/stats`
Get current data statistics

### POST `/api/clear-all`
Clear all data (testing only)

## 🎨 Customization

### Change Colors
Edit `static/style.css`:
```css
:root {
    --primary: #3498db;      /* Main blue */
    --success: #27ae60;      /* Green */
    --danger: #e74c3c;       /* Red */
    /* ... etc ... */
}
```

### Change Port
In `web_interface.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to 8080
```

### Add More Languages
HTML templates use simple English - easy to translate!

## ⚠️ Troubleshooting

### "Cannot connect to localhost:5000"
- Make sure Python is running: `python web_interface.py`
- Check you're using http:// (not https://)
- Try a different port if 5000 is in use

### "Worker not added"
- Check all required fields (name is mandatory)
- Make sure hourly rate is a number
- Check browser console for errors (F12)

### "No solutions found"
- Make sure you have workers and shifts added
- Check that shifts aren't impossible (e.g., no available workers)
- Try adjusting optimization weights

### Weights are confusing
- Leave defaults - they work well!
- Higher = more important to the scheduler
- Start with just adjusting one or two

## 📊 Example Scenario

**Your Coffee Shop:**

**Workers:**
- Alice (Seniority: 3, Rate: $18) - Skills: barista
- Bob (Seniority: 1, Rate: $15) - Skills: cashier
- Carol (Seniority: 2, Rate: $16) - Skills: barista, cashier

**Shifts:**
- Mon 6am-2pm (2 workers, need barista)
- Mon 2pm-10pm (1 worker, any skill)
- Tue 6am-2pm (2 workers, need barista)
- Tue 2pm-10pm (1 worker, any skill)

**Weights:**
- Time-Off: 10 (respect requests)
- Seniority: 5 (somewhat favor experienced)
- Weekends: 8 (balance fair)
- Skills: 7 (match skills)
- Workload: 6 (fair distribution)
- Cost: 2 (not too concerned about payroll)
- Overstaffing: 3 (avoid overstaffing)

**Result:** 3 different schedule options to choose from!

## 🔐 Security Notes

**For Testing Only:**
- The web server is insecure by default
- Don't expose to internet without HTTPS
- Add authentication for production

**Production Setup:**
1. Use a real web server (Gunicorn, uWSGI)
2. Add HTTPS with SSL certificates
3. Add user authentication
4. Use a database instead of in-memory storage
5. Set `debug=False`

## 📞 Support

### Common Questions

**Q: Can I use this on my phone?**
A: Yes! The interface is fully responsive.

**Q: Can I save schedules?**
A: Currently in-memory (deleted on restart). Download CSV to keep copies!

**Q: Can multiple people use this at once?**
A: Only one session at a time. For multiple users, deploy to a server with a database.

**Q: How do I backup my data?**
A: Export each schedule as CSV from the Results page.

## 🚀 Next Steps

1. ✅ Start the server: `python web_interface.py`
2. ✅ Open http://localhost:5000
3. ✅ Add a few workers
4. ✅ Create some shifts
5. ✅ Generate schedules
6. ✅ Try different weights
7. ✅ Download results

Enjoy easy scheduling! 🎉

---

## 📝 Notes

- All data is stored in memory (lost on server restart)
- Numbers format automatically - just type!
- Dates use YYYY-MM-DD format (pick from calendar, or type)
- Skills are case-sensitive ("barista" ≠ "Barista")
- Hourly rate can be decimal ($15.50 OK)

## 🎯 What's Next?

Future enhancements could include:
- Database persistence
- User authentication
- Multi-team support
- Email notifications
- Calendar integration
- API rate limiting
- Advanced analytics
- Automatic shift swaps
- Time off request approvals

Happy scheduling! 📅✨
