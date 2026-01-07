from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor

app = Flask(__name__)
app.secret_key = "change-this-secret"  # ใช้ flash message

# MySQL Config (XAMPP)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "atm_db"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


def get_account_or_404(acc: str):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT account_number, username, balance FROM accounts WHERE account_number=%s", (acc,))
    account = cur.fetchone()
    cur.close()
    return account


@app.route("/")
def index():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT account_number, username, balance FROM accounts ORDER BY account_number")
    accounts = cur.fetchall()

    cur.execute("SELECT COALESCE(SUM(balance), 0) AS total_balance FROM accounts")
    total_balance = cur.fetchone()["total_balance"]
    cur.close()

    return render_template("index.html", accounts=accounts, total_balance=total_balance)


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        acc = request.form.get("account_number", "").strip()
        user = request.form.get("username", "").strip()
        bal_raw = request.form.get("balance", "").strip()

        if not acc or not user:
            flash("กรุณากรอกเลขบัญชีและชื่อผู้ใช้", "danger")
            return redirect(url_for("create"))

        try:
            bal = float(bal_raw) if bal_raw else 0.0
            if bal < 0:
                flash("ยอดเงินเริ่มต้นต้องไม่ติดลบ", "danger")
                return redirect(url_for("create"))
        except ValueError:
            flash("ยอดเงินเริ่มต้นไม่ถูกต้อง", "danger")
            return redirect(url_for("create"))

        cur = mysql.connection.cursor()
        # เช็คซ้ำ
        cur.execute("SELECT 1 FROM accounts WHERE account_number=%s", (acc,))
        if cur.fetchone():
            cur.close()
            flash("เลขบัญชีนี้มีอยู่แล้ว", "danger")
            return redirect(url_for("create"))

        cur.execute(
            "INSERT INTO accounts (account_number, username, balance) VALUES (%s, %s, %s)",
            (acc, user, bal),
        )
        mysql.connection.commit()
        cur.close()

        flash("สร้างบัญชีสำเร็จ", "success")
        return redirect(url_for("index"))

    return render_template("create.html")


@app.route("/edit/<acc>", methods=["GET", "POST"])
def edit(acc):
    account = get_account_or_404(acc)
    if not account:
        flash("ไม่พบบัญชี", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        user = request.form.get("username", "").strip()
        if not user:
            flash("กรุณากรอกชื่อผู้ใช้", "danger")
            return redirect(url_for("edit", acc=acc))

        cur = mysql.connection.cursor()
        cur.execute("UPDATE accounts SET username=%s WHERE account_number=%s", (user, acc))
        mysql.connection.commit()
        cur.close()

        flash("แก้ไขข้อมูลบัญชีสำเร็จ", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", account=account)


@app.route("/deposit/<acc>", methods=["GET", "POST"])
def deposit(acc):
    account = get_account_or_404(acc)
    if not account:
        flash("ไม่พบบัญชี", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            flash("จำนวนเงินไม่ถูกต้อง", "danger")
            return redirect(url_for("deposit", acc=acc))

        if amount <= 0:
            flash("จำนวนเงินต้องฝากมากกว่า 0", "danger")
            return redirect(url_for("deposit", acc=acc))

        cur = mysql.connection.cursor()
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number=%s", (amount, acc))
        mysql.connection.commit()
        cur.close()

        flash("ฝากเงินสำเร็จ", "success")
        return redirect(url_for("index"))

    return render_template("deposit.html", account=account)


@app.route("/withdraw/<acc>", methods=["GET", "POST"])
def withdraw(acc):
    account = get_account_or_404(acc)
    if not account:
        flash("ไม่พบบัญชี", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            flash("จำนวนเงินไม่ถูกต้อง", "danger")
            return redirect(url_for("withdraw", acc=acc))

        if amount <= 0:
            flash("จำนวนเงินถอนต้องมากกว่า 0", "danger")
            return redirect(url_for("withdraw", acc=acc))

        # กันยอดติดลบ
        if float(account["balance"]) < amount:
            flash("ยอดเงินไม่พอสำหรับการถอน", "danger")
            return redirect(url_for("withdraw", acc=acc))

        cur = mysql.connection.cursor()
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number=%s", (amount, acc))
        mysql.connection.commit()
        cur.close()

        flash("ถอนเงินสำเร็จ", "success")
        return redirect(url_for("index"))

    return render_template("withdraw.html", account=account)


@app.route("/delete/<acc>")
def delete(acc):
    account = get_account_or_404(acc)
    if not account:
        flash("ไม่พบบัญชี", "danger")
        return redirect(url_for("index"))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM accounts WHERE account_number=%s", (acc,))
    mysql.connection.commit()
    cur.close()

    flash("ลบบัญชีสำเร็จ", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":

    app.run(debug=True)
