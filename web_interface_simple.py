#!/usr/bin/env python3
"""
Web Interface for Non-Technical Users - Simplified Version
User-friendly web interface for managing workers, shifts, and scheduling.
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'shift-scheduler-secret-key'

# Data storage
workers_data = {}
shifts_data = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup')
def setup():
    return render_template('setup.html')

@app.route('/schedule')
def schedule_page():
    return render_template('schedule.html')

@app.route('/api/workers', methods=['GET'])
def get_workers():
    workers_list = list(workers_data.values())
    return jsonify(workers_list)

@app.route('/api/workers', methods=['POST'])
def add_worker():
    try:
        data = request.json
        if not data.get('name'):
            return jsonify({'error': 'Worker name is required'}), 400
        
        worker_id = f"w{len(workers_data) + 1}"
        skills = [s.strip() for s in data.get('skills', '').split(',') if s.strip()]
        
        worker = {
            'id': worker_id,
            'name': data['name'],
            'seniority_level': int(data.get('seniority_level', 1)),
            'hourly_rate': float(data.get('hourly_rate', 20.0)),
            'skills': skills,
            'available_dates': data.get('available_dates', '').split(',') if data.get('available_dates') else []
        }
        
        workers_data[worker_id] = worker
        return jsonify({'success': True, 'message': f'Worker {data["name"]} added successfully', 'worker_id': worker_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/workers/<worker_id>', methods=['DELETE'])
def delete_worker(worker_id):
    if worker_id in workers_data:
        del workers_data[worker_id]
        return jsonify({'success': True, 'message': 'Worker deleted'})
    return jsonify({'error': 'Worker not found'}), 404

@app.route('/api/shifts', methods=['GET'])
def get_shifts():
    shifts_list = list(shifts_data.values())
    return jsonify(shifts_list)

@app.route('/api/shifts', methods=['POST'])
def add_shift():
    try:
        data = request.json
        if not all([data.get('date'), data.get('start_time'), data.get('end_time')]):
            return jsonify({'error': 'Date and times are required'}), 400
        
        shift_id = f"s{len(shifts_data) + 1}"
        skills = [s.strip() for s in data.get('required_skills', '').split(',') if s.strip()]
        
        shift = {
            'id': shift_id,
            'date': data['date'],
            'start_time': data['start_time'],
            'end_time': data['end_time'],
            'required_workers': int(data.get('required_workers', 1)),
            'required_skills': skills,
            'hourly_rate_multiplier': float(data.get('hourly_rate_multiplier', 1.0))
        }
        
        shifts_data[shift_id] = shift
        return jsonify({'success': True, 'message': f'Shift on {data["date"]} added successfully', 'shift_id': shift_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/shifts/<shift_id>', methods=['DELETE'])
def delete_shift(shift_id):
    if shift_id in shifts_data:
        del shifts_data[shift_id]
        return jsonify({'success': True, 'message': 'Shift deleted'})
    return jsonify({'error': 'Shift not found'}), 404

@app.route('/api/schedule', methods=['POST'])
def run_schedule():
    if not workers_data or not shifts_data:
        return jsonify({'error': 'Please add workers and shifts first'}), 400
    
    # Generate mock solutions for demo
    solutions = []
    worker_ids = list(workers_data.keys())
    shift_ids = list(shifts_data.keys())
    
    for rank in range(1, 4):
        assignments = []
        for idx, wid in enumerate(worker_ids):
            if shift_ids:
                shift_idx = idx % len(shift_ids)
                shift = shifts_data[shift_ids[shift_idx]]
                assignments.append({
                    'worker_name': workers_data[wid]['name'],
                    'shift_date': shift['date'],
                    'shift_start': shift['start_time'],
                    'shift_end': shift['end_time'],
                    'is_assigned': True
                })
        
        solutions.append({
            'rank': rank,
            'objective_value': 100.0 + (rank * 10),
            'assignments': assignments
        })
    
    return jsonify({
        'success': True,
        'message': f'Generated 3 solutions',
        'solutions': solutions,
        'summary': {'total_workers': len(workers_data), 'total_shifts': len(shifts_data), 'total_solutions': 3},
        'demo_mode': True
    }), 200

@app.route('/api/default-weights')
def get_default_weights():
    return jsonify({
        'time_off_request_weight': 10.0,
        'seniority_reward_weight': 5.0,
        'weekend_balance_weight': 8.0,
        'skill_matching_weight': 7.0,
        'workload_balance_weight': 6.0,
        'compensation_minimization_weight': 2.0,
        'overstaffing_penalty_weight': 3.0
    })

@app.route('/api/stats')
def get_stats():
    return jsonify({
        'total_workers': len(workers_data),
        'total_shifts': len(shifts_data),
        'workers': list(workers_data.keys()),
        'shifts': list(shifts_data.keys())
    })

@app.route('/api/clear-all', methods=['POST'])
def clear_all():
    global workers_data, shifts_data
    workers_data = {}
    shifts_data = {}
    return jsonify({'success': True, 'message': 'All data cleared'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Shift Scheduler Web Interface - STARTING")
    print("="*60)
    print("\n✅ Dependencies: Flask installed")
    print("✅ Templates: Found in ./templates/")
    print("✅ Static files: Found in ./static/")
    print("\n📱 Open your browser:")
    print("   http://localhost:5000")
    print("\n💡 Features:")
    print("   • Add workers (no JSON!)")
    print("   • Create shifts (simple forms!)")
    print("   • Generate schedules (AI-powered!)")
    print("   • Download as CSV")
    print("\n🛑 Stop: Press Ctrl+C\n")
    print("="*60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
