from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import json
import io
import matplotlib.pyplot as plt
from datetime import datetime
from database import get_connection, initialize_database
from models import get_user, User

app = Flask(__name__)
app.secret_key = 'secret-key'

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    from models import users  # Importa el diccionario de usuarios definido en models.py
    for user in users.values():
        if user.id == user_id:
            return user
    return None


# Definición de productos: cada uno con precio de venta y costo por defecto
PRODUCTS = {
    "Cuadro 21.5 x 35.5 cm": {"precio": 499, "costo": 300},
    "Cuadro 28 x 43 cm": {"precio": 549, "costo": 330},
    "Cuadro 30 x 45 cm": {"precio": 599, "costo": 360}
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username)
        if user and user.password == password:
            login_user(user)
            flash("¡Sesión iniciada exitosamente!", "success")
            return redirect(url_for("ventas"))
        else:
            flash("Credenciales inválidas. Intente nuevamente.", "danger")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))

@app.route('/')
def index():
    return redirect(url_for('ventas'))

@app.route('/ventas', methods=['GET'])
@login_required
def ventas():
    return render_template('ventas.html', products=PRODUCTS)

@app.route('/registrar_venta', methods=['POST'])
@login_required
def registrar_venta():
    order_data = request.form.get('order_data')
    destinatario = request.form.get('destinatario')
    descripcion = request.form.get('descripcion')
    if not order_data:
        flash("No hay productos en la venta.", "danger")
        return redirect(url_for('ventas'))
    try:
        order = json.loads(order_data)
    except Exception as e:
        flash("Error al procesar la venta.", "danger")
        return redirect(url_for('ventas'))
    
    total = 0
    total_cost = 0
    detalles = []
    for item in order:
        producto = item['producto']
        cantidad = int(item['cantidad'])
        precio = PRODUCTS[producto]["precio"]
        costo = float(item['costo'])
        total += precio * cantidad
        total_cost += costo * cantidad
        detalles.append((producto, cantidad, precio, costo))
    
    ganancia = total - total_cost
    conn = get_connection()
    cursor = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO ventas (fecha, total, ganancia, destinatario, descripcion) VALUES (?, ?, ?, ?, ?)",
        (fecha, total, ganancia, destinatario, descripcion)
    )
    venta_id = cursor.lastrowid
    for detalle in detalles:
        producto, cantidad, precio, costo = detalle
        cursor.execute(
            "INSERT INTO detalle_venta (venta_id, producto, cantidad, precio_unitario, costo_unitario) VALUES (?, ?, ?, ?, ?)",
            (venta_id, producto, cantidad, precio, costo)
        )
    conn.commit()
    conn.close()
    flash("Venta registrada exitosamente!", "success")
    return redirect(url_for('ventas'))

@app.route('/reportes')
@login_required
def reportes():
    conn = get_connection()
    cursor = conn.cursor()
    # Calcular la cantidad total de cuadros vendidos
    cursor.execute("SELECT SUM(cantidad) FROM detalle_venta")
    result = cursor.fetchone()
    cuadros_vendidos = result[0] if result[0] is not None else 0

    # Calcular ingresos totales y ganancias totales a partir de la tabla ventas
    cursor.execute("SELECT SUM(total), SUM(ganancia) FROM ventas")
    resumen = cursor.fetchone()
    conn.close()
    total_revenue = resumen[0] if resumen[0] is not None else 0
    total_gain = resumen[1] if resumen[1] is not None else 0

    return render_template('reportes.html',
                           cuadros_vendidos=cuadros_vendidos,
                           total_revenue=total_revenue,
                           total_gain=total_gain)

@app.route('/historial')
@login_required
def historial():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, fecha, total, ganancia, destinatario, descripcion FROM ventas ORDER BY id DESC")
    ventas_data = cursor.fetchall()
    conn.close()
    return render_template('historial.html', ventas=ventas_data)

@app.route('/venta/<int:venta_id>')
@login_required
def venta_detalle(venta_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT producto, cantidad, precio_unitario, costo_unitario FROM detalle_venta WHERE venta_id = ?", (venta_id,))
    detalles = cursor.fetchall()
    cursor.execute("SELECT destinatario, descripcion FROM ventas WHERE id = ?", (venta_id,))
    sale_info = cursor.fetchone()
    conn.close()
    sale_header = {
        "destinatario": sale_info[0] if sale_info and sale_info[0] else "No especificado",
        "descripcion": sale_info[1] if sale_info and sale_info[1] else "Sin descripción"
    }
    return render_template('venta_detalle.html', venta_id=venta_id, detalles=detalles, sale_header=sale_header)

@app.route('/eliminar_venta/<int:venta_id>', methods=['POST'])
@login_required
def eliminar_venta(venta_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detalle_venta WHERE venta_id = ?", (venta_id,))
    cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
    conn.commit()
    conn.close()
    flash("Venta eliminada exitosamente.", "success")
    return redirect(url_for('historial'))

@app.route('/editar_venta/<int:venta_id>', methods=['GET', 'POST'])
@login_required
def editar_venta(venta_id):
    conn = get_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        destinatario = request.form.get("destinatario")
        descripcion = request.form.get("descripcion")
        # Actualizar metadatos de la venta
        cursor.execute("UPDATE ventas SET destinatario = ?, descripcion = ? WHERE id = ?",
                       (destinatario, descripcion, venta_id))
        # Obtener arrays de datos para cada detalle (existentes y nuevos)
        detail_ids = request.form.getlist("detail_id[]")
        productos = request.form.getlist("producto[]")
        cantidades = request.form.getlist("cantidad[]")
        costos = request.form.getlist("costo[]")
        for i in range(len(productos)):
            # Si detail_id está vacío, se considera un nuevo registro
            d_id = detail_ids[i] if i < len(detail_ids) else ""
            producto = productos[i]
            cantidad = int(cantidades[i])
            costo = float(costos[i])
            # Se obtiene el precio unitario del catálogo para ese producto
            precio = PRODUCTS[producto]["precio"]
            if not d_id.strip():
                # Insertar nuevo detalle si no existe ID
                cursor.execute(
                    "INSERT INTO detalle_venta (venta_id, producto, cantidad, precio_unitario, costo_unitario) VALUES (?, ?, ?, ?, ?)",
                    (venta_id, producto, cantidad, precio, costo)
                )
            else:
                # Actualizar detalle existente
                cursor.execute(
                    "UPDATE detalle_venta SET producto = ?, cantidad = ?, costo_unitario = ? WHERE id = ?",
                    (producto, cantidad, costo, d_id)
                )
        # Recalcular los totales de la venta a partir de los detalles
        cursor.execute(
            "SELECT SUM(precio_unitario * cantidad), SUM(costo_unitario * cantidad) FROM detalle_venta WHERE venta_id = ?",
            (venta_id,)
        )
        result = cursor.fetchone()
        new_total = result[0] if result[0] is not None else 0
        new_total_cost = result[1] if result[1] is not None else 0
        new_ganancia = new_total - new_total_cost
        # Actualizar la venta con los nuevos totales
        cursor.execute(
            "UPDATE ventas SET total = ?, ganancia = ? WHERE id = ?",
            (new_total, new_ganancia, venta_id)
        )
        conn.commit()
        conn.close()
        flash("Venta actualizada exitosamente.", "success")
        return redirect(url_for('historial'))
    else:
        # En modo GET, recuperar metadatos y detalles de la venta
        cursor.execute("SELECT destinatario, descripcion FROM ventas WHERE id = ?", (venta_id,))
        sale_info = cursor.fetchone()
        cursor.execute("SELECT id, producto, cantidad, precio_unitario, costo_unitario FROM detalle_venta WHERE venta_id = ?", (venta_id,))
        sale_details = cursor.fetchall()
        conn.close()
        sale = {
            "destinatario": sale_info[0] if sale_info and sale_info[0] else "",
            "descripcion": sale_info[1] if sale_info and sale_info[1] else ""
        }
        return render_template("editar_venta.html", venta_id=venta_id, sale=sale, sale_details=sale_details, products=PRODUCTS)



@app.route('/grafico.png')
@login_required
def grafico():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha, total FROM ventas ORDER BY fecha")
    ventas_data = cursor.fetchall()
    conn.close()
    
    if not ventas_data:
        fig, ax = plt.subplots(figsize=(6,4))
        ax.text(0.5, 0.5, 'No hay datos', horizontalalignment='center', verticalalignment='center')
    else:
        fechas = [v[0] for v in ventas_data]
        totales = [v[1] for v in ventas_data]
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(fechas, totales, marker='o')
        ax.set_title("Evolución de Ventas Totales")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Total MXN")
        plt.xticks(rotation=45)
        plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    return send_file(img, mimetype='image/png')

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
