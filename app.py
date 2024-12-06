from flask import Flask, session, request, render_template, flash, redirect, url_for
from helpers.setupHelpers import readconfig
from models.studentModel import Student
from models.paymentModel import Payment
from mongoengine import connect

from datetime import datetime, timedelta

def get_covered_dates(start_date, number_of_days):
    """Calcula las fechas cubiertas por el pago, excluyendo sábados y domingos."""
    dates = []
    current_date = start_date
    while len(dates) < number_of_days:
        if current_date.weekday() < 5:  # 0= lunes, 6= domingo
            dates.append(current_date)
        current_date += timedelta(days=1)
    return dates




config = readconfig()
app = Flask(__name__)
app.secret_key = config["secret_key"]
connect(host=config["db"])

@app.route("/", methods=["GET", "POST"])
def login():
    if "active" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        pin = request.form.get("pin")
        if pin == config["pin"]:
            session["active"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("PIN Incorrecto", "error")
    return render_template("login.html")

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "active" not in session:
        return redirect(url_for("login"))
    estudiantes = Student.objects.all()
    return render_template("dashboard.html", estudiantes=estudiantes)

@app.route("/add_student", methods=["POST"])
def add_student():
    if "active" not in session:
        return redirect(url_for("login"))

    nombre = request.form.get("nombre")
    grado = request.form.get("grado")

    if not nombre or not grado:
        flash("Todos los campos son obligatorios.", "error")
        return redirect(url_for("dashboard"))

    try:
        nuevo_estudiante = Student(nombre=nombre, grado=grado)
        nuevo_estudiante.save()
        flash(f"Estudiante {nombre} agregado correctamente.", "success")
    except Exception as e:
        flash("Hubo un error al agregar al estudiante.", "error")

    return redirect(url_for("dashboard"))

@app.route("/student/<student_id>", methods=["GET"])
def student_detail(student_id):
    if "active" not in session:
        return redirect(url_for("login"))
    
    try:
        estudiante = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        flash("Estudiante no encontrado.", "error")
        return redirect(url_for("dashboard"))
    pagos = Payment.objects(student=estudiante).order_by('-start_date')
    
    return render_template("student_detail.html", estudiante=estudiante, pagos=pagos)

@app.route("/delete_payment/<payment_id>", methods=["POST"])
def delete_payment(payment_id):
    if "active" not in session:
        flash("No autorizado.", "danger")
        return redirect(url_for("login"))

    try:
        pago = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        flash("Pago no encontrado.", "danger")
        return redirect(url_for("dashboard"))

    pago.delete()
    flash("Pago eliminado correctamente.", "success")
    return redirect(url_for("student_detail", student_id=pago.student.id))


@app.route("/add_payment/<student_id>", methods=["POST"])
def add_payment(student_id):
    if "active" not in session:
        flash("No autorizado.", "danger")
        return redirect(url_for("login"))

    try:
        estudiante = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        flash("Estudiante no encontrado.", "danger")
        return redirect(url_for("dashboard"))

    start_date_str = request.form.get("start_date")
    number_of_days = request.form.get("number_of_days")

    if not start_date_str or not number_of_days:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("student_detail", student_id=student_id))

    try:
        number_of_days = int(number_of_days)
        if number_of_days < 1:
            flash("El número de días debe ser al menos 1.", "danger")
            return redirect(url_for("student_detail", student_id=student_id))
    except ValueError:
        flash("Número de días debe ser un número entero.", "danger")
        return redirect(url_for("student_detail", student_id=student_id))

    try:
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Fecha de inicio inválida.", "danger")
        return redirect(url_for("student_detail", student_id=student_id))

    covered_dates_new = get_covered_dates(start_date_obj, number_of_days)
    covered_dates_new_set = set(date.strftime('%Y-%m-%d') for date in covered_dates_new)
    existing_pagos = Payment.objects(student=estudiante)
    existing_dates = set()
    for pago in existing_pagos:
        for date_str in pago.days_consumed.keys():
            existing_dates.add(date_str)
    if covered_dates_new_set.intersection(existing_dates):
        flash("El nuevo pago se solapa con pagos existentes. Por favor, elige otras fechas.", "danger")
        return redirect(url_for("student_detail", student_id=student_id))
    days_consumed = {date.strftime('%Y-%m-%d'): False for date in covered_dates_new}

    new_payment = Payment(
        student=estudiante,
        start_date=start_date_obj,
        number_of_days=number_of_days,
        days_consumed=days_consumed
    )
    new_payment.save()

    flash("Pago agregado correctamente.", "success")
    return redirect(url_for("student_detail", student_id=student_id))


@app.route("/mark_consumption/<payment_id>/<date>", methods=["POST"])
def mark_consumption(payment_id, date):
    if "active" not in session:
        flash("No autorizado.", "error")
        return redirect(url_for("login"))

    try:
        pago = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        flash("Pago no encontrado.", "error")
        return redirect(url_for("dashboard"))

    if date not in pago.days_consumed:
        flash("Fecha no válida.", "error")
        return redirect(url_for("student_detail", student_id=pago.student.id))

    pago.days_consumed[date] = not pago.days_consumed[date]
    pago.save()

    estado = "Consumido" if pago.days_consumed[date] else "No Consumido"
    flash(f"Consumo para el día {date} marcado como {estado}.", "success")
    return redirect(url_for("student_detail", student_id=pago.student.id))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

def main():
    app.run(debug=True)

if __name__ == "__main__":
    main()
