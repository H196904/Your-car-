from datetime import datetime
import os
from flask import Flask, jsonify, render_template, request
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
  role = db.Column(db.String(20), nullable=False)  # 'rider', 'driver', 'admin'
  status = db.Column(db.String(20), default='active')  # 'active', 'inactive'
  city = db.Column(db.String(50), default='الخرطوم')


class Ride(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  rider_phone = db.Column(db.String(20), nullable=False)
  driver_phone = db.Column(db.String(20), nullable=True)
  pickup = db.Column(db.String(200), nullable=False)
  dropoff = db.Column(db.String(200), nullable=False)
  car_type = db.Column(db.String(50), nullable=False)
  fare = db.Column(db.Float, default=2500.0)
  status = db.Column(
      db.String(30), default='Search'
  )  # 'Search', 'Accepted', 'Completed', 'Cancelled'
  created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
  db.create_all()
  # إنشاء مدير افتراضي إذا لم يكن موجوداً
  if not User.query.filter_by(phone='0912345678').first():
    admin = User(
        phone='0912345678', name='المدير العام', role='admin', city='الخرطوم'
    )
    db.session.add(admin)
    db.session.commit()


# --- مسارات عرض صفحات HTML الأساسية ---
@app.route('/')
def home():
  return render_template('index.html')


@app.route('/admin')
def admin_page():
  return render_template('admin.html')


# --- مسارات API (تسجيل الدخول والرحلات والإدارة) ---
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
