from datetime import datetime
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taxi_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- جداول قاعدة البيانات ---
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  phone = db.Column(db.String(20), unique=True, nullable=False)
  name = db.Column(db.String(100), nullable=False)
  role = db.Column(db.String(20), nullable=False)
  status = db.Column(db.String(20), default='active')
  city = db.Column(db.String(50), default='الخرطوم')


class Ride(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  rider_phone = db.Column(db.String(20), nullable=False)
  driver_phone = db.Column(db.String(20), nullable=True)
  pickup = db.Column(db.String(200), nullable=False)
  dropoff = db.Column(db.String(200), nullable=False)
  car_type = db.Column(db.String(50), nullable=False)
  fare = db.Column(db.Float, default=2500.0)
  status = db.Column(db.String(30), default='Search')
  created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
  db.create_all()
  if not User.query.filter_by(phone='0912345678').first():
    admin = User(
        phone='0912345678', name='المدير العام', role='admin', city='الخرطوم'
    )
    db.session.add(admin)
    db.session.commit()


# --- واجهة المستخدم الرئيسية (بدون الحاجة لمجلد templates) ---
@app.route('/')
def home():
  return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تطبيق التاسي - السودان</title>
        <style>
            body { font-family: Tahoma, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; text-align: right; }
            .card { background: white; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            input, select, button { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
            button { background: #10b981; color: white; border: none; font-weight: bold; cursor: pointer; }
            button:hover { background: #059669; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div id="login-screen" class="card">
            <h2>تسجيل الدخول / إنشاء حساب</h2>
            <input type="text" id="phone" placeholder="رقم الهاتف (مثال: 0912345678)">
            <input type="text" id="name" placeholder="الاسم الكامل">
            <select id="role">
                <option value="rider">راكب</option>
                <option value="driver">سائق</option>
            </select>
            <button onclick="login()">دخول</button>
        </div>

        <div id="app-screen" class="card hidden">
            <h2 id="welcome-msg">مرحباً</h2>
            <div id="rider-section" class="hidden">
                <h3>طلب رحلة جديدة</h3>
                <input type="text" id="pickup" placeholder="مكان الانطلاق (مثال: الخرطوم 2)">
                <input type="text" id="dropoff" placeholder="الوجهة (مثال: أمدرمان)">
                <select id="car_type">
                    <option value="Economy">اقتصادي (أمجاد)</option>
                    <option value="VIP">تاسي فاخر</option>
                </select>
                <button onclick="requestRide()">اطلب الآن</button>
            </div>
            <div id="driver-section" class="hidden">
                <h3>لوحة السائق</h3>
                <p>حالة الاتصال: <span style="color:green;">متصل</span></p>
                <div id="available-rides">لا توجد رحلات متاحة حالياً</div>
            </div>
            <button onclick="logout()" style="background:#ef4444; margin-top:20px;">تسجيل خروج</button>
        </div>

        <script>
            async function login() {
                const phone = document.getElementById('phone').value;
                const name = document.getElementById('name').value;
                const role = document.getElementById('role').value;
                if(!phone) { alert('الرجاء إدخال رقم الهاتف'); return; }

                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone, name, role})
                });
                const data = await res.json();
                if(data.success) {
                    localStorage.setItem('user', JSON.stringify(data.user));
                    loadUI(data.user);
                } else {
                    alert(data.message);
                }
            }

            function loadUI(user) {
                document.getElementById('login-screen').classList.add('hidden');
                document.getElementById('app-screen').classList.remove('hidden');
                document.getElementById('welcome-msg').innerText = `مرحباً، ${user.name} (${user.role === 'rider' ? 'راكب' : 'سائق'})`;
                if(user.role === 'rider') {
                    document.getElementById('rider-section').classList.remove('hidden');
                } else {
                    document.getElementById('driver-section').classList.remove('hidden');
                }
            }

            async function requestRide() {
                const user = JSON.parse(localStorage.getItem('user'));
                const pickup = document.getElementById('pickup').value;
                const dropoff = document.getElementById('dropoff').value;
                const car_type = document.getElementById('car_type').value;

                const res = await fetch('/api/rides', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({rider_phone: user.phone, pickup, dropoff, car_type})
                });
                const data = await res.json();
                if(data.success) {
                    alert('تم إرسال طلب الرحلة بنجاح! برقم: ' + data.ride_id);
                }
            }

            function logout() {
                localStorage.removeItem('user');
                location.reload();
            }

            window.onload = function() {
                const user = localStorage.getItem('user');
                if(user) loadUI(JSON.parse(user));
            }
        </script>
    </body>
    </html>
    """


# --- مسارات API ---
@app.route('/api/login', methods=['POST'])
def login():
  data = request.json
  phone = data.get('phone')
  role = data.get('role', 'rider')
  name = data.get('name', 'مستخدم جديد')

  if not phone:
    return jsonify({'success': False, 'message': 'رقم الهاتف مطلوب'}), 400

  user = User.query.filter_by(phone=phone).first()
  if user:
    if user.status == 'inactive':
      return jsonify(
          {'success': False, 'message': 'هذا الحساب موقوف من الإدارة'}
      ), 403
    return jsonify({
        'success': True,
        'user': {'name': user.name, 'phone': user.phone, 'role': user.role},
    })
  else:
    new_user = User(phone=phone, name=name, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({
        'success': True,
        'user': {
            'name': new_user.name,
            'phone': new_user.phone,
            'role': new_user.role,
        },
    })


@app.route('/api/rides', methods=['POST'])
def create_ride():
  data = request.json
  ride = Ride(
      rider_phone=data.get('rider_phone'),
      pickup=data.get('pickup'),
      dropoff=data.get('dropoff'),
      car_type=data.get('car_type'),
      fare=data.get('fare', 3000.0),
  )
  db.session.add(ride)
  db.session.commit()
  return jsonify({'success': True, 'ride_id': ride.id})


@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
  drivers = User.query.filter_by(role='driver').all()
  rides = Ride.query.order_by(Ride.created_at.desc()).all()
  return jsonify({
      'stats': {
          'total_drivers': len(drivers),
          'completed_rides': Ride.query.filter_by(status='Completed').count(),
      },
      'drivers': [{
          'phone': d.phone,
          'name': d.name,
          'city': d.city,
          'status': d.status,
      } for d in drivers],
      'rides': [{
          'id': r.id,
          'rider': r.rider_phone,
          'driver': r.driver_phone or 'غير محدد',
          'pickup': r.pickup,
          'dropoff': r.dropoff,
          'status': r.status,
      } for r in rides],
  })


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
