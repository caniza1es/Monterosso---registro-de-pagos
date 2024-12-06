# models/paymentModel.py
from mongoengine import Document, ReferenceField, DateField, IntField, DictField, CASCADE
from datetime import datetime, timedelta

class Payment(Document):
    student = ReferenceField('Student', required=True, reverse_delete_rule=CASCADE)
    transaction_day = DateField(required=True, default=datetime.today)  # Nueva fecha de transacción
    start_date = DateField(required=True, default=datetime.today)
    number_of_days = IntField(required=True)
    days_consumed = DictField(default={})  # Formato: {'YYYY-MM-DD': True/False}

    meta = {
        'collection': 'payments'
    }

    def get_covered_dates(self):
        """Calcula las fechas cubiertas por el pago, excluyendo sábados y domingos."""
        dates = []
        current_date = self.start_date
        while len(dates) < self.number_of_days:
            if current_date.weekday() < 5:  # 0= lunes, 6= domingo
                dates.append(current_date)
            current_date += timedelta(days=1)
        return dates

    def is_active(self):
        """Determina si el pago está activo (hoy está dentro del rango de fechas pagadas)."""
        today = datetime.today().date()
        covered_dates = self.get_covered_dates()
        return covered_dates and covered_dates[0].date() <= today <= covered_dates[-1].date()

    def end_date(self):
        """Retorna la última fecha cubierta por el pago."""
        dates = self.get_covered_dates()
        return dates[-1].strftime('%Y-%m-%d') if dates else None
