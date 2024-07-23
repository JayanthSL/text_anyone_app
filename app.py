from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_socketio import SocketIO, emit, join_room
import qrcode
from io import BytesIO

app = Flask(__name__)
socketio = SocketIO(app)

rooms = {}
user_rooms = {}
room_join_status = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create_room", methods=["POST"])
def create_room():
    user_id = request.form.get("user_id")
    room_code = request.form.get("room_code")

    if not user_id or not room_code:
        return jsonify({"error": "Missing user_id or room_code"}), 400

    if room_code not in rooms:
        rooms[room_code] = set()

    rooms[room_code].add(user_id)
    user_rooms[user_id] = room_code
    room_join_status[room_code] = False

    return render_template("wait_for_join.html", room_code=room_code, user_id=user_id)


@app.route("/join_room", methods=["POST"])
def join_room_route():
    user_id = request.form.get("user_id")
    room_code = request.form.get("room_code")

    if not user_id or not room_code:
        return jsonify({"error": "Missing user_id or room_code"}), 400

    if room_code not in rooms:
        return jsonify({"error": "Room does not exist"}), 404

    rooms[room_code].add(user_id)
    user_rooms[user_id] = room_code
    room_join_status[room_code] = True

    socketio.emit(
        "room_status", {"room_code": room_code, "status": True}, room=room_code
    )

    return redirect(url_for("chat", user_id=user_id, room_code=room_code))


@app.route("/chat")
def chat():
    user_id = request.args.get("user_id")
    room_code = request.args.get("room_code")

    if not user_id or not room_code:
        return redirect(url_for("index"))

    return render_template("chat.html", user_id=user_id, room_code=room_code)


@app.route("/qr_code/<room_code>")
def qr_code(room_code):
    url = url_for("join_room_with_code", room_code=room_code, _external=True)
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


@app.route("/join_room_with_code/<room_code>")
def join_room_with_code(room_code):
    return render_template("join_with_code.html", room_code=room_code)


@app.route("/check_room_status/<room_code>")
def check_room_status(room_code):
    if room_code in room_join_status:
        return jsonify({"joined": room_join_status[room_code]})
    return jsonify({"joined": False})


@socketio.on("message")
def handle_message(data):
    room_code = data["room_code"]
    message = data["message"]
    emit("message", {"user_id": data["user_id"], "message": message}, room=room_code)


@socketio.on("join")
def on_join(data):
    user_id = data["user_id"]
    room_code = data["room_code"]
    join_room(room_code)
    emit(
        "message",
        {"user_id": "System", "message": f"{user_id} has entered the room."},
        room=room_code,
    )
    room_join_status[room_code] = True
    emit("room_status", {"room_code": room_code, "status": True}, room=room_code)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=12000, debug=True)
