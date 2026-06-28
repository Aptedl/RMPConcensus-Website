from flask import Flask, render_template, request
from Utilities import Utilities

app = Flask(__name__)

@app.route("/professor", methods=["POST", "GET"])
def professor():
    print("PROF")
    return render_template("index.html", page="professor")

@app.route("/class", methods=["POST", "GET"])
def classWeb():
    print("CLASS")
    return render_template("index.html", page="class")

@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template("index.html", page="/")

@app.route("/profName", methods=["POST"])
def getProfConcensus():
    prof = request.form.get("profName")
    uni = request.form.get("uniName")

    url = Utilities.getURL(Utilities, uni, prof)
    data = Utilities.getProfReviews(Utilities, url)
    concensus = Utilities.generateResponse(Utilities, data)

    return render_template("index.html", page="professor", concensus_text=concensus)

@app.route("/className", methods=["POST"])
def getClassConcensus():
    className = request.form.get("className")
    uni = request.form.get("uniName")
    dept = request.form.get("deptName")
    print(className, uni, dept)

    concensus = Utilities.generateResponse(uni, dept, className)

    return render_template("index.html", page="class", concensus_text=concensus)

if __name__ == "__main__":
    app.run(debug=True)