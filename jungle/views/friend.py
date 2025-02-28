from flask import Flask, Blueprint, url_for, render_template, request, jsonify, flash, redirect, session
from pymongo import MongoClient
import random
import json
from string import ascii_uppercase
import os
from dotenv import load_dotenv

bp = Blueprint('friend', __name__, url_prefix='/friend')
uri = os.getenv('URL')
client = MongoClient(uri, 27017)
db = client.dbjungle

rooms = list(db.Chat_data.find({},{"_id":False}))

# def create_room():


def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

def reload_DB():
    global rooms 
    global all_list

    all_list = []

    rooms = list(db.Chat_data.find({},{"_id":False}))

    for room_data in rooms:
        for room_name in room_data.keys():
            all_list.append(room_name)

@bp.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    data = request.get_json()
    sender_id = session['user_id']  # 요청 보낸 사람
    receiver_id = data.get("receiver_id")  # 요청 받는 사람
    #자신한테 친구 요청
    if sender_id == receiver_id:
        return {"message": "You cannot send a request to yourself"}
    receiver = db.user.find_one({"id": receiver_id})
    # 상대방이 이미 친구라면 요청 불가
    if not receiver:
        return {"message": "Non-existent user"}
    elif sender_id in receiver.get("friends", []):
        return {"message": "Already friends"}
    elif sender_id in receiver.get("friend_requests", []):
        return {"message": "This request has already been sent"}
    db.user.update_one({"id": receiver_id}, {"$push": {"friend_requests": sender_id}})

    return {"message": "Friend request sent"}

@bp.route('/friend_list', methods=['GET'])
def friend_list():
    client_id = session['user_id']
    friend_list = list(db.user.find({'id': client_id}, {"_id": 0,"id":0,"pw":0,"friend_requests":0, "DM_list":0, "group_list": 0}))
    return jsonify({'result': 'success', 'friend_list': friend_list})


@bp.route('/friend_request_list', methods=['GET'])
def friend_request_list():
    client_id = session['user_id']
    friend_request_list = list(db.user.find({'id': client_id}, {"_id": 0,"id":0,"pw":0,"friends":0, "DM_list":0, "group_list": 0}))
    return jsonify({'result': 'success', 'friend_request_list': friend_request_list})

@bp.route('/accept_request', methods=['POST'])
def accept_request():
    data = request.get_json()
    sender_id = session['user_id'] #현재 사용자
    user_id = data.get("user_id") #수락할 친구 ID
    if not sender_id or not user_id:
        return jsonify({"msg": "Invalid request"}), 400
    db.user.update_one(
        {"id": sender_id},
        {
            "$pull": {"friend_requests": user_id},  # 친구 요청에서 제거 $pull은 지정된 조건과 일치하는 것을 지워버립니다
            "$addToSet": {"friends": user_id}  # 친구 목록에 추가 (중복 방지) $addset은 존재 하지 않을 때 추가합니다다
        }
    )
    db.user.update_one(
        {"id": user_id},
        {
            "$pull": {"friend_requests": sender_id},  # 친구 요청에서 제거
            "$addToSet": {"friends": sender_id}  # 친구 목록에 추가 (중복 방지)
        }
    )
    room = generate_unique_code(8)
    doc= {
        room:
        {
            "room_name":"",
            "members": [sender_id,user_id],
            "messages": []
        }
    }
    reload_DB()
    db.Chat_data.insert_one(doc)
    db.user.update_one({
        "id": user_id},
        {
            "$addToSet": {"DM_list": room}  
        })
    db.user.update_one({
        "id": sender_id},
        {
            "$addToSet": {"DM_list": room}  
        })
    reload_DB()
    return jsonify({"msg": f"{user_id}님과 친구가 되었습니다!"})

@bp.route('/decline_request', methods=['POST'])
def decline_request():
    data = request.get_json()
    sender_id = session['user_id'] #현재 사용자
    user_id = data.get("user_id") #수락할 친구 ID
    if not sender_id or not user_id:
        return jsonify({"msg": "Invalid request"}), 400
    result = db.user.update_one(
        {"id": sender_id},
        {
            "$pull": {"friend_requests": user_id},  # 친구 요청에서 제거
        }
    )
    return jsonify({"msg": f"{user_id}님의 요청을 거절하였습니다"})

@bp.route('/room_invite', methods=['POST'])
def room_invite():
    data = request.get_json()
    sender_id = str(session['user_id'])  # 현재 사용자
    user_id = str(data.get("user_id"))  # 수락할 친구 ID
    room_name = data.get("room_name")
    if isinstance(user_id, str):  
        user_id = json.loads(user_id.replace("'", '"'))  # 따옴표 변환 후 JSON 변환
    user_list = [str(sender_id)] + [str(i) for i in user_id]
    room = generate_unique_code(8)
    doc= {
        room:
        {
            "room_name":room_name,
            "members": user_list,
            "messages": []
        }
    }
    reload_DB()
    db.Chat_data.insert_one(doc)
    db.user.update_one(
        {"id": sender_id},
        {
            "$addToSet": {"group_list": room}  # 친구 목록에 추가 (중복 방지) $addset은 존재 하지 않을 때 추가합니다다
        }
    )
    for i in user_list:
        db.user.update_one(
            {"id": i},
            {
                "$addToSet": {"group_list": room}  # 친구 목록에 추가 (중복 방지) $addset은 존재 하지 않을 때 추가합니다다
            }
        )

    for users in user_id:
        db.Chat_data.update_one(
            {room_name: {"$exists": True}},  # 방 이름으로 조건을 지정
            {"$push": {f"members": users}}  # messages 배열에 content 추가
        )
        
    return jsonify({"msg": "방 생성 완료!"})