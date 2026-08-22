from flask import Flask, render_template, request, jsonify
from Utilities import Utilities, Professor

app = Flask(__name__)

@app.route("/professor", methods=["POST", "GET"])
def professor():
    return render_template("index.html", page="professor")

@app.route("/class", methods=["POST", "GET"])
def classWeb():
    return render_template("index.html", page="class")

@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template("index.html", page="/")

@app.route("/dept", methods=["POST"])
def dept():
    return render_template("index.html", page="dept")

@app.route("/profName", methods=["POST"])
def getProfConcensus():
    prof = request.form.get("profName")
    uni = request.form.get("uniName")

    url = Utilities.getURL(Utilities, uni, prof)
    data = Utilities.getProfReviews(Utilities, Professor(url=url))
    concensus = Utilities.generateResponse(Utilities, data.reviews)

    return render_template("index.html", page="professor", concensus_text=concensus)

@app.route("/className", methods=["POST"])
def getClassConcensus():
    className = request.form.get("className")
    uni = request.form.get("uniName")
    dept = request.form.get("deptName")

    concensus = Utilities.generateResponse(Utilities, uni, dept, className)

    return render_template("index.html", page="class", concensus_text=concensus)

@app.route("/submitDept", methods=["POST"])
def compareDepts():
    uni = request.form.get("uni")
    dept = request.form.get("dept")
    avgRating, highProfName, lowProfName, highProfRating, lowProfRating = Utilities.getAvgRating(Utilities, uni, dept)
    chart1, chart2 = Utilities.getPlots(Utilities, uni, dept)

    return jsonify({
        "avgRating": avgRating,
        "highProfName": highProfName,
        "highProfRating": highProfRating,
        "lowProfName": lowProfName,
        "lowProfRating": lowProfRating,
        "chart1": chart1,
        "chart2": chart2
    })

@app.route("/getDepts", methods=["POST"])
def get_depts():
    uni = request.form.get("uni")
    deptList = Utilities.getAllDepts(Utilities, uni)
    return jsonify(deptList)

if __name__ == "__main__":
    app.run(debug=True)