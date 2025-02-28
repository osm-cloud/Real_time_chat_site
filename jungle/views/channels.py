from flask import Flask, Blueprint, url_for, render_template, request, jsonify, flash, session , redirect

bp = Blueprint('channels', __name__, url_prefix='/channels')

@bp.route('/')
def render():
    return redirect(url_for('channels.c'))

@bp.route('/c', methods=['GET', 'POST'])
def c():
    if 'user_id' not in session:
        return redirect(url_for('login.render'))
    else:
        return render_template('channels.html')

@bp.route('/logout', methods=['GET'])
def logout():
    session.pop('user_id', None)
    flash('로그아웃 성공!', 'success')
    return jsonify({"result":"sucess"})

@bp.route('/l', methods=['GET'])
def l():
    return redirect(url_for('login.c'))

@bp.route('/send_message')
def send_message():
    return jsonify()