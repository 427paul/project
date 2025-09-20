from flask import Flask, jsonify, render_template
from sklearn.decomposition import PCA
from sklearn.datasets import load_iris
from sklearn.preprocessing import StandardScaler
import pandas as pd
from flask_cors import CORS
app = Flask(__name__)
CORS(app) # CORS 허용

@app.route('/')
def goto():
    return render_template('index.html')
@app.route('/pca_data')
def pca_data():
    # Iris 데이터셋 로드
    iris=load_iris()
    X=pd.DataFrame(iris.data, columns=iris.feature_names)
    # z-점수 표준화
    scaler=StandardScaler()
    X_scaled=scaler.fit_transform(X)
    # PCA 주성분 변환
    pca=PCA(n_components=2)
    points=pca.fit_transform(X_scaled)
    # 꽃 이름을 라벨에 매핑
    flower_names={0: "setosa", 1: "versicolor", 2: "virginica"}
 # 데이터 변환 및 int64 -> int로 변환 (JSON에서는 int64 미지원)
    data=[{
        'x': float(point[0]),
        'y': float(point[1]),
        'label': flower_names[iris.target[i]], # 라벨을 꽃 이름으로 변환
    } for i, point in enumerate(points)]
    # JSON으로 반환
    return jsonify(data)
if __name__=='__main__':
    app.run(debug=True)  