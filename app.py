from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timedelta
import json
import random
import string
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=1024*1024)

# Store rooms and their data
rooms = {}

def cleanup_old_rooms():
    current_time = datetime.now()
    rooms_to_remove = []
    for room_code, room_data in rooms.items():
        last_activity = datetime.fromisoformat(
            max(client['joined_at'] for client in room_data['clients'].values())
        ) if room_data['clients'] else datetime.fromisoformat(room_data.get('created_at', current_time.isoformat()))
        
        if (current_time - last_activity).total_seconds() > app.config['ROOM_CLEANUP_TIME']:
            rooms_to_remove.append(room_code)
    
    for room_code in rooms_to_remove:
        del rooms[room_code]

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def broadcast_room_update(room_code):
    if room_code in rooms:
        socketio.emit('room_update', {
            'buzzerEnabled': rooms[room_code]['buzzer_enabled'],
            'hostName': rooms[room_code]['host_name'],
            'clients': rooms[room_code]['clients'],
            'hasBuzzed': list(rooms[room_code]['has_buzzed'])
        }, room=room_code)

def broadcast_buzz_list(room_code):
    if room_code in rooms:
        sorted_timestamps = sorted(rooms[room_code]['timestamps'], key=lambda x: x['timestamp'])
        for i, ts in enumerate(sorted_timestamps, 1):
            ts['position'] = i
        socketio.emit('buzz_list_update', sorted_timestamps, room=room_code)

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/create_room', methods=['POST'])
def create_room():
    cleanup_old_rooms()
    if len(rooms) >= app.config['MAX_ROOMS']:
        return jsonify({'status': 'error', 'message': 'Maximum number of rooms reached'}), 503
        
    room_code = generate_room_code()
    host_name = request.json.get('hostName', 'Host')
    rooms[room_code] = {
        'timestamps': [],
        'host': request.remote_addr,
        'host_name': host_name,
        'clients': {},
        'buzzer_enabled': False,
        'has_buzzed': set(),
        'buzzer_unlock_time': None,
        'created_at': datetime.now().isoformat()
    }
    session['room'] = room_code
    session['is_host'] = True
    session['name'] = host_name
    return jsonify({'status': 'success', 'room': room_code})

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    broadcast_room_update(room)
    broadcast_buzz_list(room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)

@app.route('/join_room', methods=['POST'])
def join_room_http():
    room_code = request.json.get('room').upper()
    player_name = request.json.get('playerName', f'Player {len(rooms.get(room_code, {}).get("clients", {})) + 1}')
    
    if room_code in rooms:
        if len(rooms[room_code]['clients']) >= app.config['MAX_CLIENTS_PER_ROOM']:
            return jsonify({'status': 'error', 'message': 'Room is full'}), 503
            
        client_id = str(random.randint(10000, 99999))
        rooms[room_code]['clients'][client_id] = {
            'name': player_name,
            'joined_at': datetime.now().isoformat()
        }
        session['room'] = room_code
        session['client_id'] = client_id
        session['is_host'] = False
        session['name'] = player_name
        broadcast_room_update(room_code)
        return jsonify({'status': 'success', 'clientId': client_id})
    return jsonify({'status': 'error', 'message': 'Room not found'}), 404

@app.route('/room/<room_code>')
def room(room_code):
    if room_code not in rooms:
        return redirect(url_for('index'))
    is_host = session.get('is_host', False)
    return render_template('index.html', room=room_code, is_host=is_host)

@app.route('/buzz', methods=['POST'])
def buzz():
    room_code = session.get('room')
    if not room_code or room_code not in rooms:
        return jsonify({'status': 'error', 'message': 'Invalid room'}), 400
    
    if not rooms[room_code]['buzzer_enabled']:
        return jsonify({'status': 'error', 'message': 'Buzzer is disabled'}), 403
    
    client_id = session.get('client_id')
    if client_id in rooms[room_code]['has_buzzed']:
        return jsonify({'status': 'error', 'message': 'You have already buzzed'}), 403
    
    data = request.json
    client_timestamp = data.get('timestamp')
    client_offset = data.get('timeOffset', 0)
    
    adjusted_timestamp = client_timestamp - client_offset
    
    reaction_time = None
    if rooms[room_code]['buzzer_unlock_time']:
        reaction_time = adjusted_timestamp - rooms[room_code]['buzzer_unlock_time']
    
    player_name = session.get('name', 'Unknown Player')
    
    rooms[room_code]['has_buzzed'].add(client_id)
    rooms[room_code]['timestamps'].append({
        'timestamp': adjusted_timestamp,
        'formatted_time': datetime.fromtimestamp(adjusted_timestamp / 1000.0).strftime('%H:%M:%S.%f')[:-3],
        'player_name': player_name,
        'reaction_time': reaction_time
    })

    # Check if all participants have buzzed
    all_client_ids = set(rooms[room_code]['clients'].keys())
    if all_client_ids and all_client_ids.issubset(rooms[room_code]['has_buzzed']):
        rooms[room_code]['buzzer_enabled'] = True
        rooms[room_code]['buzzer_unlock_time'] = datetime.now().timestamp() * 1000
    
    broadcast_room_update(room_code)
    broadcast_buzz_list(room_code)
    return jsonify({'status': 'success'})

@app.route('/server_time')
def get_server_time():
    return jsonify({
        'serverTime': datetime.now().timestamp() * 1000
    })

@app.route('/toggle_buzzer/<room_code>', methods=['POST'])
def toggle_buzzer(room_code):
    if room_code in rooms and request.remote_addr == rooms[room_code]['host']:
        rooms[room_code]['buzzer_enabled'] = not rooms[room_code]['buzzer_enabled']
        if rooms[room_code]['buzzer_enabled']:
            rooms[room_code]['buzzer_unlock_time'] = datetime.now().timestamp() * 1000
        else:
            rooms[room_code]['buzzer_unlock_time'] = None
        broadcast_room_update(room_code)
        return jsonify({
            'status': 'success',
            'buzzerEnabled': rooms[room_code]['buzzer_enabled'],
            'serverTime': datetime.now().timestamp() * 1000,
            'buzzerUnlockTime': rooms[room_code]['buzzer_unlock_time']
        })
    return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

@app.route('/reset/<room_code>', methods=['POST'])
def reset(room_code):
    if room_code in rooms and request.remote_addr == rooms[room_code]['host']:
        rooms[room_code]['timestamps'] = []
        rooms[room_code]['buzzer_enabled'] = False
        rooms[room_code]['has_buzzed'] = set()
        rooms[room_code]['buzzer_unlock_time'] = None
        broadcast_room_update(room_code)
        broadcast_buzz_list(room_code)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

@app.route('/leave_room/<room_code>', methods=['POST'])
def leave_room_http(room_code):
    if room_code in rooms:
        client_id = session.get('client_id')
        if client_id and client_id in rooms[room_code]['clients']:
            del rooms[room_code]['clients'][client_id]
            broadcast_room_update(room_code)
        session.clear()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Room not found'}), 404

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)