from flask import Flask, Blueprint, url_for, render_template, request, jsonify, flash, session , redirect
from pymongo import MongoClient
import requests
import time
import os
from dotenv import load_dotenv

bp = Blueprint('login', __name__, url_prefix='/login')

uri = os.getenv('URL')
client = MongoClient(uri, 27017)
db = client.dbjungle



@bp.route('/')
def render():
    return render_template('login.html')

@bp.route('/c', methods=['GET', 'POST'])
def c():
    if request.method == 'POST':
        id = request.form['login_id']
        pw = request.form['login_pw']

        login_DB = list(db.user.find({}))
        for data in login_DB:
            if id == data["id"] and pw == data["pw"]:

                session['user_id'] = str(data["id"])
                return redirect(url_for('channels_c'))
    flash('사용자 아이디 또는 비밀번호가 잘못되었습니다.', 'danger')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('로그아웃 성공!', 'success')
    return redirect(url_for('login.c'))


@bp.route('/signup', methods=['POST'])
def signup():
    
    id = request.form['signup_id']
    pw1 = request.form['signup_pw1']
    pw2 = request.form['signup_pw2']
    
    if pw1 != pw2:
        flash("두 비밀번호가 같지 않습니다. 다시 회원가입 해주세요", 'danger')
        return render_template('login.html')
    
    existing_user = db.user.find_one({"id": id})  # 아이디 중복 확인
    if existing_user:
        flash("아이디가 중복됩니다. 다시 회원가입 해주세요", 'danger')
        return render_template('login.html')
    
    # 아이디가 중복되지 않은 경우 회원가입 진행
    doc = {
        "id": id,
        "pw": pw1,
        "photo": "default_user.png",
        "DM_list":[],
        "group_list": [],
        "friend_requests": [],
        "friends": []
    }
    db.user.insert_one(doc)
    flash("회원가입이 완료되었습니다. 로그인해주세요.", 'success')
    return render_template('login.html')

@bp.route('/pw', methods=['POST'])
def pw():
    session.clear()
    return render_template('login.html')