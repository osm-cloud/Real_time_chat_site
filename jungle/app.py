from flask import Flask, Blueprint, url_for, render_template, request, jsonify, flash, redirect, session
from flask_socketio import SocketIO, emit, join_room, leave_room, send, SocketIO
from pymongo import MongoClient
import random
from string import ascii_uppercase
from markupsafe import Markup
import requests
import os
import re
import threading
import time
import re
from dotenv import load_dotenv

load_dotenv(verbose=True)

#==========
#flask, DB, AI 등등 설정
uri = os.getenv('URL')
client = MongoClient(uri, 27017)
db = client.dbjungle
auth_key = os.getenv('auth_key')

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'static/user_profile'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#==========
#Chat room DB 
rooms = list(db.Chat_data.find({},{"_id":False}))

all_list = []
for room_data in rooms:
    for room_name in room_data.keys():
        all_list.append(room_name)

#==========
#블루 프린트 관리

from views import login, channels, friend
app.register_blueprint(login.bp)
app.register_blueprint(channels.bp)
app.register_blueprint(friend.bp)

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login.render'))

@app.route("/channels/main/c", methods=["POST", "GET"])
def channels_c():
    if 'user_id' not in session:
        return redirect(url_for('login.render'))
    else:
        return render_template('channels.html')

#==========
#DB 리로드

def reload_DB():
    global rooms 
    global all_list

    all_list = []

    rooms = list(db.Chat_data.find({},{"_id":False}))

    for room_data in rooms:
        for room_name in room_data.keys():
            all_list.append(room_name)

def user_room_DB_reload():
    global user_DM_DB_list
    global user_Group_DB_list

    user_info = list(db.user.find({"id":session["user_id"]},{"_id":False,"DM_list": True,"group_list": True}))

    user_DM_DB_list = []
    user_Group_DB_list = []

    for info in user_info:
        user_DM_DB_list = info["DM_list"]
    for info in user_info:
        user_Group_DB_list = info["group_list"]

#==========
#DeepL

def deepL(message):
    url_for_deepl = 'https://api-free.deepl.com/v2/translate'
    params = {'auth_key' : auth_key, 'text' : message, 'source_lang' : 'KO', "target_lang": 'EN' }

    result = requests.post(url_for_deepl, data=params, verify=False)
    return result.json()['translations'][0]["text"]

def deepLE(message):
    url_for_deepl = 'https://api-free.deepl.com/v2/translate'
    params = {'auth_key' : auth_key, 'text' : message, 'source_lang' : 'EN', "target_lang": 'KO' }
    result = requests.post(url_for_deepl, data=params, verify=False)
    return result.json()['translations'][0]["text"]

#==========

#=============
#실시간 채팅 DB 

@app.route("/channels/info", methods=["POST", "GET"])
def channel_info():
    reload_DB()
    user_id = session.get('user_id')
    if request.args.get("type") != "user":
        info_type, s1 = request.args.get("type").split("?")

    elif request.args.get("type") == "user":
        user = db.user.find_one({"id": user_id}, {"photo": True})
        user_photo = user.get("photo", "default.jpg")
        return jsonify({
            "user_id": user_id,
            "user_photo": user_photo,
        })
    
    if info_type == "friend":
        room = s1
        chat_data = db.Chat_data.find_one({room: {"$exists": True}}, {"_id": False, room: True})

        if not chat_data:
            return jsonify({"error": "Room not found"}), 404

        room_data = chat_data.get(room, {})
        members = room_data.get("members", [])
        messages = room_data.get("messages", [])
        
        chat_room = db.Chat_data.find_one({room: {"$exists": True}}, {"_id": False, f"{room}.members": True})
        room_name_data=db.Chat_data.find_one({room: {"$exists": True}},{"_id": False,f"{room}.room_name": True})
        if chat_room:
            fri_id_list = chat_room.get(room, {}).get("members", [])
            room_name = room_name_data.get(room, {}).get("room_name", [])
        else:
            fri_id_list = []

        
        if not fri_id_list or len(fri_id_list) < 2:
            return jsonify({"error": "Not enough members"}), 400
        
        try:
            fri_id_list.remove(user_id)
        except ValueError:
            pass
        
        last_message = messages[-1]["message"] if messages else "No messages yet"
        friend = db.user.find_one({"id": str(fri_id_list[0])}, {"photo": True})
        
        if not friend:
            return jsonify({"error": "Friend not found"}), 404
        return jsonify({
            "fri_id": str(fri_id_list[0]),
            "fri_photo": friend.get("photo", "default.jpg"),
            "fri_preview": last_message,
            "room_name": room_name
        })
    
    elif info_type == "name":  # 기본적으로 'name'을 기반으로 친구 정보 검색
        name = s1
        friend = db.user.find_one({"id": name}, {"photo": True})
        return jsonify({
            "_photo": friend.get("photo", "default.jpg")
        })

#==========
#실시간 채팅 ajax

@app.route("/channels/main/deeplE", methods=["POST", "GET"])
def chat_deeplE():
    text_input = request.args.get("message")  # GET 요청에서 message 파라미터 가져오기
    if not text_input:
        return "Error: No message received", 400  # 메시지가 없으면 400 에러 반환
    return deepLE(text_input)  # deepL 함수 처리 후 반환

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

def convert_links(text):
    url_pattern = re.compile(r'(https?://[^\s]+)')
    text1 = Markup(re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', text))
    return text1


@app.route("/channels/main/deepl", methods=["POST", "GET"])
def chat_deepl():
    text_input = request.args.get("message")  # GET 요청에서 message 파라미터 가져오기
    if not text_input:
        return "Error: No message received", 400  # 메시지가 없으면 400 에러 반환
    return deepL(text_input)  # deepL 함수 처리 후 반환

@app.route('/channels/main/uploader', methods=['GET', 'POST'])
def uploader_file():
    if request.method == 'POST':
        f = request.files['file']
        filename = session["user_id"] + ".png"
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.Chat_data.update_one(
                    {"id": session["user_id"]},  # 방 이름으로 조건을 지정
                    {"$push": {f"photo": {filename}}}  # messages 배열에 content 추가
                )
        return 'file uploaded successfully'



@app.route("/channels/group_list", methods=["POST", "GET"])
def group_list():
    reload_DB()
    select = request.args.get("Group")
    user_room_DB_reload()
    
    if (select == "all"):
        return all_list
    elif(select == "user"):
        return user_DM_DB_list
    elif(select == "group"):
        return user_Group_DB_list
    return

@app.route("/channels/group_messages", methods=["POST", "GET"])
def group_messages():
    reload_DB()
    session['room'] =  request.args.get("Group")
    room = session.get("room")
            
    for room_data in rooms:
        for room_code in room_data.keys():
            if room == room_code:
                reload_DB()
                return room_data[room_code]["messages"]

@app.route("/channels/group_move", methods=["POST", "GET"])
def group_move():
    reload_DB()
    session['room'] = request.args.get("Group")
    room = session.get("room")
            
    for room_data in rooms:
        for room_code in room_data.keys():
            if room == room_code:
                reload_DB()
                messages = room_data[room_code]["messages"]
                return render_template("channels.html", code=room, messages=messages)
    return

@app.route("/channels/group_create", methods=["POST", "GET"])
def group_create():
    room = generate_unique_code(8)
    doc= {
        room:
        {
            "room_name":"room",
            "members":'',
            "messages":
            [
            ]
        }
    }
    reload_DB()
    db.Chat_data.insert_one(doc)
    reload_DB()
    return
#============
#filter ling
def filter_bad_words(text):
    bad_words = [word["Curse"] for word in db.tlqkf.find({},{"_id":False})]
    for word in bad_words:
        text = re.sub(r'\b' + re.escape(word) + r'\b', '♥' * len(word), text)
    return text

#==========
#socketio

@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get('user_id')
    if room not in all_list:
        return
    message=convert_links(data["message"])
    Filter = filter_bad_words(message)
    content = {
        "name": session.get("user_id"),
        "message": Filter
    }
    
    send(content, to=room)
    for room_data in rooms:
        for room_code in room_data.keys():
            if room == room_code:
                db.Chat_data.update_one(
                    {room: {"$exists": True}},  # 방 이름으로 조건을 지정
                    {"$push": {f"{room}.messages": content}}  # messages 배열에 content 추가
                )

@socketio.on("connect")
def connect(auth):
    reload_DB()
    room = session.get("room")
    name = session.get("user_id")
    if room not in all_list:
        leave_room(room)
        return
    
    join_room(room)

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("user_id")
    leave_room(room)

if __name__ == '__main__':  
    socketio.run(app, host='0.0.0.0', port=5007, debug=True)