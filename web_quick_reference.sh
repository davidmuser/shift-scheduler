#!/bin/bash
# Quick Reference Card for Web Interface

cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        🌐 SHIFT SCHEDULER - WEB INTERFACE QUICK START         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

┌─ 🚀 START THE SERVER ────────────────────────────────────────┐
│                                                               │
│  Option 1 (Easiest):                                          │
│  $ ./run_web.sh                                               │
│                                                               │
│  Option 2:                                                    │
│  $ python web_interface.py                                    │
│                                                               │
│  Option 3:                                                    │
│  $ pip install flask                                          │
│  $ python web_interface.py                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 📱 OPEN IN BROWSER ─────────────────────────────────────────┐
│                                                               │
│  Go to: http://localhost:5000                                │
│                                                               │
│  OR on another device:                                        │
│  http://[YOUR_COMPUTER_IP]:5000                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 📋 WHAT YOU CAN DO ─────────────────────────────────────────┐
│                                                               │
│  1️⃣  ADD WORKERS                                             │
│      • Name, seniority level, hourly rate                    │
│      • Skills (optional)                                      │
│      • Available dates (optional)                             │
│      • Click "Add Worker"                                     │
│                                                               │
│  2️⃣  CREATE SHIFTS                                           │
│      • Date, start time, end time                            │
│      • Workers needed                                         │
│      • Pay multiplier (1.0 = normal, 1.5 = 50% extra)       │
│      • Required skills (optional)                             │
│      • Click "Add Shift"                                      │
│                                                               │
│  3️⃣  GENERATE SCHEDULE                                       │
│      • Adjust weight sliders (optional)                       │
│      • Click "Generate Schedule"                              │
│      • Get 3 different solutions                              │
│                                                               │
│  4️⃣  DOWNLOAD RESULTS                                        │
│      • Click "Download as CSV"                                │
│      • Open in Excel/Google Sheets                            │
│      • Use for real scheduling                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ ⚖️  WEIGHT SLIDERS (Optimization Priorities) ──────────────┐
│                                                               │
│  Move sliders to emphasize what matters:                      │
│                                                               │
│  ⬇️  LOW (0)        = Don't care about this                   │
│  ⬆️  MEDIUM (5-10)  = Somewhat important                      │
│  ⬆️  HIGH (15-20)   = Very important                          │
│                                                               │
│  Default weights work well for most cases!                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 🎯 TYPICAL WORKFLOW ────────────────────────────────────────┐
│                                                               │
│  1. Open http://localhost:5000                               │
│  2. Click [➕ Add Workers & Shifts]                           │
│  3. Add 3-5 workers (fill form, click Add)                   │
│  4. Add 4-8 shifts (fill form, click Add)                    │
│  5. Click [✅ Proceed to Scheduling]                          │
│  6. Click [🚀 Generate Schedule]                              │
│  7. Review 3 solution options                                │
│  8. Click [📥 Download as CSV]                               │
│                                                               │
│  ⏱️  Total time: 5-10 minutes                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 📂 WHERE TO FIND FILES ─────────────────────────────────────┐
│                                                               │
│  Main Interface:                                              │
│  └─ web_interface.py                                         │
│                                                               │
│  Web Pages:                                                   │
│  ├─ templates/index.html (home)                              │
│  ├─ templates/setup.html (workers & shifts)                  │
│  └─ templates/schedule.html (generate schedule)              │
│                                                               │
│  Styling & Scripts:                                           │
│  ├─ static/style.css                                         │
│  ├─ static/setup.js                                          │
│  └─ static/schedule.js                                       │
│                                                               │
│  Documentation:                                               │
│  ├─ WEB_INTERFACE_GUIDE.md (detailed user guide)             │
│  ├─ WEB_INTERFACE_SUMMARY.md (overview)                      │
│  ├─ WEB_INTERFACE_DEMO.md (visual walkthrough)               │
│  └─ WEB_INTERFACE_STATUS.md (checklist)                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ ❓ QUICK QUESTIONS ─────────────────────────────────────────┐
│                                                               │
│  Q: How do I add a worker?                                   │
│  A: Go to /setup, fill the form, click [Add Worker]          │
│                                                               │
│  Q: What's the hourly rate multiplier?                       │
│  A: 1.0 = normal, 1.5 = 50% extra (for nights/weekends)     │
│                                                               │
│  Q: What do the weights do?                                  │
│  A: Higher weight = system cares more about that factor      │
│                                                               │
│  Q: Can I use this on my phone?                              │
│  A: Yes! It's responsive and works on all devices            │
│                                                               │
│  Q: How do I export the schedule?                            │
│  A: Click "Download as CSV" - works with Excel/Sheets        │
│                                                               │
│  Q: Will my data be saved?                                   │
│  A: Currently in-memory (cleared on restart). Download CSV!   │
│                                                               │
│  Q: Does it work offline?                                    │
│  A: Yes! No internet connection needed, just local server     │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 🔧 TROUBLESHOOTING ─────────────────────────────────────────┐
│                                                               │
│  Can't connect to localhost:5000?                             │
│  → Make sure python web_interface.py is running              │
│  → Check you're using http:// not https://                  │
│  → Try a different port if 5000 is taken                     │
│                                                               │
│  Port 5000 already in use?                                   │
│  → Edit web_interface.py, change port=5000 to port=8000     │
│  → Restart server                                             │
│                                                               │
│  "Worker not added" error?                                   │
│  → Check that Name field is filled (required)                │
│  → Make sure Hourly Rate is a number                         │
│  → Check browser console (F12) for details                   │
│                                                               │
│  No solutions generated?                                      │
│  → Make sure you have workers AND shifts added               │
│  → Check that shifts aren't impossible                       │
│  → Try adjusting optimization weights                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ 📚 LEARN MORE ──────────────────────────────────────────────┐
│                                                               │
│  Full User Guide:                                             │
│  $ cat WEB_INTERFACE_GUIDE.md                                │
│                                                               │
│  Visual Walkthrough:                                          │
│  $ cat WEB_INTERFACE_DEMO.md                                 │
│                                                               │
│  Architecture Overview:                                       │
│  $ cat WEB_INTERFACE_SUMMARY.md                              │
│                                                               │
│  Implementation Status:                                       │
│  $ cat WEB_INTERFACE_STATUS.md                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─ ✨ FEATURES AT A GLANCE ────────────────────────────────────┐
│                                                               │
│  ✅ No JSON files - just fill in forms                       │
│  ✅ No command line - point and click                        │
│  ✅ Beautiful interface - professional design                │
│  ✅ Mobile responsive - works on phones                      │
│  ✅ Multiple solutions - choose the best                     │
│  ✅ Adjustable priorities - your values matter               │
│  ✅ Export to CSV - use in Excel/Sheets                      │
│  ✅ Smart scheduling - AI-powered fair distribution          │
│  ✅ Easy for beginners - no technical knowledge needed       │
│  ✅ Fast results - 5-10 minutes to schedule                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  🎉 Ready to schedule? Start with: python web_interface.py   ║
║                                                                ║
║  Then open: http://localhost:5000                             ║
║                                                                ║
║  Enjoy! 🚀                                                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF
